"""Leitura auditada e cálculos da interface, sem dependência de Streamlit."""
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path

import numpy as np
import pandas as pd

from ..gerar_graficos_exploratorios import grade_comum


class DataContractError(ValueError):
    """Bases incompatíveis com o método fixado para a sessão."""


@dataclass
class Session:
    aligned: pd.DataFrame
    native: pd.DataFrame
    features: pd.DataFrame
    summary: pd.DataFrame
    config: dict

    @property
    def reference(self):
        return int(self.config['referencia'])

    @property
    def laps(self):
        return sorted(self.features.volta.unique().tolist())

    def rows(self, lap):
        return self.features.loc[self.features.volta == lap].sort_values('inicio_m').copy()

    def segment(self, code):
        return next(t for t in self.config['trechos'] if t['id'] == code)


def default_paths(root):
    # Usa a execução local existente; um checkout independente recebe caminhos pelo lançador.
    base = Path(os.environ.get('LMU_BASES', root / 'data/processed/sessao/bases'))
    if 'LMU_BASES' not in os.environ and not base.exists():
        base = root.parent / 'dados_processados_v2'
    tables = Path(os.environ.get('LMU_TABELAS', root / 'data/processed/trechos_bahrain_outer_v1'))
    config = Path(os.environ.get('LMU_CONFIG', root / 'config/trechos_bahrain_outer_v1.json'))
    return tuple(p.resolve() for p in (base, tables, config))


def signature(paths):
    base, tables, config = paths
    files = [base / name for name in ['voltas_alinhadas.parquet', 'amostras_nativas.parquet', 'resumo_voltas.csv']]
    files += [tables / 'caracteristicas_por_trecho.parquet', tables / 'manifesto_trechos.json', config]
    return tuple((str(p), p.stat().st_mtime_ns, p.stat().st_size) for p in files)


def load_session(base, tables, config_path):
    config = json.loads(config_path.read_text(encoding='utf-8'))
    manifest = json.loads((tables / 'manifesto_trechos.json').read_text(encoding='utf-8'))
    if manifest['configuracao'] != config:
        raise DataContractError('A configuração difere daquela usada para extrair as características.')
    for name, digest in manifest['sha256'].items():
        if hashlib.sha256((base / name).read_bytes()).hexdigest() != digest:
            raise DataContractError(f'A tabela de características pertence a outra versão da base: {name}')
    aligned = grade_comum(pd.read_parquet(base / 'voltas_alinhadas.parquet'))
    native = pd.read_parquet(base / 'amostras_nativas.parquet')
    features = pd.read_parquet(tables / 'caracteristicas_por_trecho.parquet')
    summary = pd.read_csv(base / 'resumo_voltas.csv')
    approved = summary.loc[summary.apta_para_analise]
    laps = set(config['voltas'])
    if any(set(df.volta) != laps for df in [aligned, native, features, approved]):
        raise DataContractError('A seleção de voltas diverge entre as bases.')
    if not approved.volta_completa.all() or not approved.interrupcoes.eq(0).all() or not approved.tempo_oficial_s.gt(0).all():
        raise DataContractError('A sessão contém voltas não aprovadas para análise.')
    expected = {(v, t['id']) for v in laps for t in config['trechos']}
    if features.duplicated(['volta', 'trecho']).any() or set(zip(features.volta, features.trecho)) != expected:
        raise DataContractError('Combinações de volta e trecho ausentes ou duplicadas.')
    numeric = ['tempo_trecho_s', 'delta_trecho_s', 'inicio_m', 'fim_m', 'velocidade_entrada_kmh',
               'velocidade_saida_kmh', 'velocidade_minima_kmh', 'tempo_freio_aplicado_s',
               'tempo_acelerador_maximo_s']
    if not np.isfinite(features[numeric].to_numpy()).all():
        raise DataContractError('Características centrais com valores não finitos.')
    reference = features.loc[features.volta == config['referencia']].set_index('trecho')
    if not features.volta_referencia.eq(config['referencia']).all():
        raise DataContractError('Referência divergente na tabela de características.')
    for lap, frame in features.groupby('volta'):
        a = aligned.loc[aligned.volta == lap].sort_values('distancia_m')
        for t in config['trechos']:
            row = frame.loc[frame.trecho == t['id']].iloc[0]
            if row.inicio_m != t['inicio_m'] or row.fim_m != t['fim_m']:
                raise DataContractError('Limites de trechos divergentes.')
            times = np.interp([t['inicio_m'], t['fim_m']], a.distancia_m, a.tempo_relativo_s)
            if not np.isclose(row.tempo_trecho_s, times[1] - times[0], atol=1e-8, rtol=0):
                raise DataContractError('Tempos por trecho divergentes da grade espacial.')
            if not np.isclose(row.delta_trecho_s, row.tempo_trecho_s-reference.loc[t['id'], 'tempo_trecho_s'], atol=1e-8, rtol=0):
                raise DataContractError('Delta local divergente da referência.')
    limits = config['trechos']
    if limits[0]['inicio_m'] != aligned.distancia_m.min() or limits[-1]['fim_m'] != aligned.distancia_m.max():
        raise DataContractError('Trechos fora do suporte comum.')
    if any(a['fim_m'] != b['inicio_m'] for a, b in zip(limits, limits[1:])):
        raise DataContractError('Lacuna ou sobreposição entre trechos.')
    return Session(aligned, native, features, approved, config)


def delta_curve(session, lap, segment=None, local=False):
    a = session.aligned.loc[session.aligned.volta == lap].sort_values('distancia_m')
    b = session.aligned.loc[session.aligned.volta == session.reference].sort_values('distancia_m')
    if not np.array_equal(a.distancia_m, b.distancia_m):
        raise DataContractError('Suportes espaciais incompatíveis.')
    delta = (a.tempo_relativo_s.to_numpy() - a.tempo_relativo_s.iloc[0]
             - b.tempo_relativo_s.to_numpy() + b.tempo_relativo_s.iloc[0])
    out = pd.DataFrame({'distancia_m': a.distancia_m.to_numpy(), 'delta_s': delta})
    if segment:
        out = out.loc[out.distancia_m.between(segment['inicio_m'], segment['fim_m'])].copy()
    if local:
        out['delta_s'] -= out.delta_s.iloc[0]
    return out


def native_signal(session, lap, variable, start, end):
    """Atribui distância à amostra nativa; preserva vizinhas para recorte visual."""
    lap_data = session.native.loc[session.native.volta == lap]
    d = lap_data.loc[lap_data.variavel == 'distancia'].sort_values('ts')
    signal = lap_data.loc[lap_data.variavel == variable].sort_values('ts')
    support = signal.tempo_relativo_s.between(d.tempo_relativo_s.iloc[0], d.tempo_relativo_s.iloc[-1])
    signal = signal.loc[support]
    distance = np.interp(signal.tempo_relativo_s, d.tempo_relativo_s, d.valor)
    left = max(0, np.searchsorted(distance, start, side='left') - 1)
    right = min(len(signal), np.searchsorted(distance, end, side='right') + 1)
    return pd.DataFrame({'distancia_m': distance[left:right], 'valor': signal.valor.to_numpy()[left:right]})
