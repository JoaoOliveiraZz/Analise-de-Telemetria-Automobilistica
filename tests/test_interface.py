"""Verificações de contrato, figuras e interação do protótipo Streamlit."""
from contextlib import contextmanager
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from telemetria_lmu.dashboard.data import DataContractError, delta_curve, load_session

HAS_UI = bool(importlib.util.find_spec('streamlit') and importlib.util.find_spec('plotly'))


@contextmanager
def fixture():
    """Sessão sintética restrita aos testes, sem dependência de gravações locais."""
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        config = {'versao':'teste','data_definicao':'2026-11-24','voltas':[8,11,12,13],
            'referencia':13,'regioes_cautela':[], 'trechos':[
                {'id':'T01','nome':'Primeiro','inicio_m':5,'fim_m':10},
                {'id':'T02','nome':'Segundo','inicio_m':10,'fim_m':15}]}
        aligned, native, features = [], [], []
        for lap, factor in [(8,1.3),(11,1.2),(12,1.1),(13,1.)]:
            for i,d in enumerate([5.,10.,15.]):
                aligned.append({'volta':lap,'distancia_m':d,'tempo_relativo_s':i*factor})
                for field,val in [('distancia',d),('velocidade',100+i),('freio',0),('acelerador',100)]:
                    native.append({'volta':lap,'variavel':field,'tempo_relativo_s':i*factor,
                                   'ts':i*factor,'valor':val})
            for t in config['trechos']:
                features.append({'volta':lap,'trecho':t['id'],'nome_trecho':t['nome'],
                    'inicio_m':t['inicio_m'],'fim_m':t['fim_m'],'cautela_distancia':False,
                    'tempo_trecho_s':factor,'delta_trecho_s':factor-1,'volta_referencia':13,
                    'velocidade_entrada_kmh':100.,'velocidade_minima_kmh':100.,'velocidade_saida_kmh':102.,
                    'tempo_freio_aplicado_s':0.,'tempo_freio_forte_s':0.,
                    'tempo_acelerador_maximo_s':factor,'inicio_frenagem_m':np.nan})
        pd.DataFrame(aligned).to_parquet(root/'voltas_alinhadas.parquet')
        pd.DataFrame(native).to_parquet(root/'amostras_nativas.parquet')
        pd.DataFrame(features).to_parquet(root/'caracteristicas_por_trecho.parquet')
        pd.DataFrame([{'volta':v,'apta_para_analise':True,'volta_completa':True,'interrupcoes':0,'tempo_oficial_s':3.}
                      for v in config['voltas']]).to_csv(root/'resumo_voltas.csv',index=False)
        (root/'config.json').write_text(json.dumps(config),encoding='utf-8')
        manifest = {'configuracao':config,'sha256':{name:hashlib.sha256((root/name).read_bytes()).hexdigest()
                    for name in ['voltas_alinhadas.parquet','amostras_nativas.parquet','resumo_voltas.csv']}}
        (root/'manifesto_trechos.json').write_text(json.dumps(manifest),encoding='utf-8')
        yield root


class InterfaceDataTest(unittest.TestCase):
    def test_delta_local_e_acumulado_preservam_as_origens(self):
        with fixture() as root:
            s = load_session(root,root,root/'config.json')
            accumulated = delta_curve(s,8,s.segment('T02'))
            local = delta_curve(s,8,s.segment('T02'),local=True)
            self.assertAlmostEqual(accumulated.delta_s.iloc[0],.3)
            self.assertAlmostEqual(local.delta_s.iloc[0],0)
            self.assertAlmostEqual(local.delta_s.iloc[-1],.3)

    def test_rejeita_bases_de_outra_extracao(self):
        with fixture() as root:
            p = root/'resumo_voltas.csv'
            p.write_text(p.read_text()+'\n',encoding='utf-8')
            with self.assertRaises(DataContractError):
                load_session(root,root,root/'config.json')

    def test_rejeita_delta_adulterado_na_tabela(self):
        with fixture() as root:
            p = root/'caracteristicas_por_trecho.parquet'
            f = pd.read_parquet(p)
            f.loc[0,'delta_trecho_s'] = 99
            f.to_parquet(p)
            with self.assertRaises(DataContractError):
                load_session(root,root,root/'config.json')


@unittest.skipUnless(HAS_UI, 'Instale requirements-interface.txt para testar a interface.')
class InterfaceUITest(unittest.TestCase):
    def test_mapa_mantem_a_mesma_escala_ao_filtrar_voltas(self):
        from telemetria_lmu.dashboard.charts import heatmap
        with fixture() as root:
            s = load_session(root,root,root/'config.json')
            all_laps = heatmap(s,[8,11,12]).data[0]
            filtered = heatmap(s,[12]).data[0]
            self.assertEqual(all_laps.zmax,filtered.zmax)
            self.assertEqual(filtered.zmin,-filtered.zmax)

    def test_pedais_preservam_degraus_nativos(self):
        from telemetria_lmu.dashboard.charts import telemetry
        with fixture() as root:
            s = load_session(root,root,root/'config.json')
            fig = telemetry(s,[12,13],s.segment('T02'),True)
            self.assertEqual(fig.data[1].line.shape,'hv')
            self.assertEqual(fig.data[2].line.shape,'hv')
            self.assertAlmostEqual(fig.data[3].y[0],0)

    def test_filtros_e_estado_vazio_sem_erros(self):
        from streamlit.testing.v1 import AppTest
        with fixture() as root, patch.dict(os.environ,{'LMU_BASES':str(root),'LMU_TABELAS':str(root),'LMU_CONFIG':str(root/'config.json')}):
            app = AppTest.from_file(str(ROOT/'app.py'),default_timeout=30).run()
            self.assertFalse(app.exception)
            app.selectbox(key='target_lap').set_value(8).run()
            self.assertFalse(app.exception)
            self.assertEqual(app.metric[1].value,'+0,600 s')
            app.selectbox(key='segment').set_value('T01').run()
            app.toggle(key='all_laps_detail').set_value(True).run()
            app.radio(key='delta_origin').set_value('Início comum aos 5 m').run()
            self.assertFalse(app.exception)
            app.multiselect(key='visible_laps').set_value([]).run()
            self.assertFalse(app.exception)
            self.assertTrue(any('Selecione ao menos' in el.value for el in app.info))


if __name__ == '__main__':
    unittest.main()
