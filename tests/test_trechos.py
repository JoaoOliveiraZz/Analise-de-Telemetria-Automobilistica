"""Verifica bordas temporais, pulsos de pedal e cobertura dos trechos."""
import copy
import json
from pathlib import Path
import sys
import unittest

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src' / 'telemetria_lmu'))
from extrair_caracteristicas import intervalos_zoh, media_linear, primeira_sustentada, validar_config


class IntegracaoTest(unittest.TestCase):
    def test_duracao_recorta_as_duas_bordas(self):
        a, b, v = intervalos_zoh([0, 1, 2, 3], [0, 100, 0, 0], .5, 1.5)
        self.assertAlmostEqual(np.sum((b - a)[v >= 99]), .5)
        self.assertAlmostEqual(np.sum((b - a) * v), 50)

    def test_trechos_contiguos_nao_contam_duas_vezes(self):
        def integral(inicio, fim):
            a, b, v = intervalos_zoh([0, 1, 2, 3], [0, 100, 20, 0], inicio, fim)
            return np.sum((b - a) * v)
        self.assertAlmostEqual(integral(.2, 1.3) + integral(1.3, 2.8), integral(.2, 2.8))

    def test_nao_extrapola_pedal(self):
        with self.assertRaises(ValueError):
            intervalos_zoh([0, 1], [0, 100], -.01, .5)

    def test_pulso_curto_nao_e_aplicacao_sustentada(self):
        a, b, v = intervalos_zoh([0, .1, .2, .3, .4, .5], [100, 0, 100, 100, 100, 0], 0, .5)
        self.assertAlmostEqual(primeira_sustentada(a, b, v, 99, .2), .2)

    def test_media_da_velocidade_pondera_tempo(self):
        media, _, _ = media_linear([0, 1, 3], [0, 10, 10], .5, 2)
        self.assertAlmostEqual(media, (3.75 + 10) / 1.5)


class ConfigTest(unittest.TestCase):
    def setUp(self):
        self.config = json.loads((ROOT / 'config' / 'trechos_bahrain_outer_v1.json').read_text(encoding='utf-8'))
        self.base = pd.DataFrame([(v, d) for v in [8, 11, 12, 13] for d in range(5, 3501, 5)],
                                 columns=['volta', 'distancia_m'])

    def test_config_cobre_intervalo_comum(self):
        validar_config(self.config, self.base)
        self.assertEqual(sum(t['fim_m'] - t['inicio_m'] for t in self.config['trechos']), 3495)

    def test_rejeita_lacuna_entre_trechos(self):
        config = copy.deepcopy(self.config)
        config['trechos'][1]['inicio_m'] += 5
        with self.assertRaises(ValueError):
            validar_config(config, self.base)


if __name__ == '__main__':
    unittest.main()
