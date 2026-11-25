"""Regras de suporte espacial da comparação; execute com unittest discover."""
from pathlib import Path
import sys
import unittest

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src' / 'telemetria_lmu'))
from gerar_graficos_exploratorios import grade_comum


class GradeComumTest(unittest.TestCase):
    def setUp(self):
        self.base = pd.DataFrame({
            'volta': [8, 8, 8, 11, 11, 13, 13, 13],
            'distancia_m': [5, 10, 15, 5, 10, 5, 10, 15],
            'tempo_relativo_s': [.1, .2, .3, .1, .2, .1, .2, .3]})

    def test_suporte_de_todas_as_voltas_limita_o_par(self):
        comum = grade_comum(self.base)
        self.assertEqual(len(comum), 6)
        self.assertEqual(set(comum.distancia_m), {5, 10})
        self.assertEqual(set(comum.volta), {8, 11, 13})

    def test_nao_admite_distancia_duplicada(self):
        with self.assertRaises(ValueError):
            grade_comum(pd.concat([self.base, self.base.iloc[[0]]]))

    def test_nao_admite_tempo_reverso(self):
        self.base.loc[1, 'tempo_relativo_s'] = .01
        with self.assertRaises(ValueError):
            grade_comum(self.base)


if __name__ == '__main__':
    unittest.main()
