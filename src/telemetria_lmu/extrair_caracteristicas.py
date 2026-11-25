"""Extrai tempos e caracteristicas por limites espaciais fixos do estudo piloto."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from gerar_graficos_exploratorios import grade_comum

CONFIG_PADRAO = Path(__file__).resolve().parents[2] / 'config' / 'trechos_bahrain_outer_v1.json'


def intervalos_zoh(t, valores, inicio, fim):
    """Intersecao exata de [t_i,t_i+1) com [inicio,fim), sem extrapolacao."""
    t, valores = np.asarray(t, float), np.asarray(valores, float)
    if (len(t) < 2 or len(t) != len(valores) or not np.isfinite(t).all()
            or not np.isfinite(valores).all() or np.any(np.diff(t) <= 0)
            or inicio < t[0] or fim > t[-1] or fim <= inicio):
        raise ValueError('Sinal nativo sem suporte valido para o intervalo')
    a, b = np.maximum(t[:-1], inicio), np.minimum(t[1:], fim)
    mask = b > a
    return a[mask], b[mask], valores[:-1][mask]


def media_linear(t, v, inicio, fim):
    t, v = np.asarray(t, float), np.asarray(v, float)
    if inicio < t[0] or fim > t[-1] or np.any(np.diff(t) <= 0) or not np.isfinite(v).all():
        raise ValueError('Velocidade sem suporte temporal')
    knots = np.r_[inicio, t[(t > inicio) & (t < fim)], fim]
    values = np.interp(knots, t, v)
    return np.trapezoid(values, knots) / (fim - inicio), knots, values


def primeira_sustentada(a, b, valores, minimo, duracao):
    inicio = None
    for x, y, v in zip(a, b, valores):
        if v < minimo:
            inicio = None
            continue
        if inicio is None:
            inicio = x
        if y - inicio >= duracao - 1e-9:
            return float(inicio)
    return np.nan


def metricas(nativas, alinhada, trecho, limiares):
    sinal = {v: f.sort_values('ts') for v, f in nativas.groupby('variavel')}
    distancia = sinal['distancia']
    dt, dd = distancia.tempo_relativo_s.to_numpy(), distancia.valor.to_numpy()
    if not np.isfinite(dd).all() or np.any(np.diff(dd) <= 0):
        raise ValueError('Distancia nativa nao estritamente crescente')
    inicio, fim = trecho['inicio_m'], trecho['fim_m']
    if inicio < dd[0] or fim > dd[-1]:
        raise ValueError('Trecho fora da distancia nativa')
    ta, tb = np.interp([inicio, fim], dd, dt)
    # Tempos derivados da distancia nativa precisam reproduzir a base espacial.
    tempos_grade = np.interp([inicio, fim], alinhada.distancia_m, alinhada.tempo_relativo_s)
    if not np.allclose(tempos_grade, [ta, tb], rtol=0, atol=1e-8):
        raise ValueError('Tempos nativos e grade espacial divergentes nos limites')
    def pos(tempo):
        return float(np.interp(tempo, dt, dd)) if np.isfinite(tempo) else np.nan
    velocidade = sinal['velocidade']
    media, knots, values = media_linear(velocidade.tempo_relativo_s, velocidade.valor, ta, tb)
    indice_min = np.argmin(values)
    tmin = float(knots[indice_min])
    result = {'inicio_tempo_relativo_s': ta, 'fim_tempo_relativo_s': tb,
              'tempo_trecho_s': tb - ta,
              'velocidade_entrada_kmh': float(values[0]), 'velocidade_saida_kmh': float(values[-1]),
              'velocidade_minima_kmh': float(values[indice_min]), 'posicao_minima_m': pos(tmin),
              'velocidade_media_temporal_kmh': float(media)}
    for campo in ['freio', 'acelerador']:
        f = sinal[campo]
        a, b, v = intervalos_zoh(f.tempo_relativo_s, f.valor, ta, tb)
        if np.any((v < 0) | (v > 100)):
            raise ValueError(f'{campo}: percentual fora da faixa 0 a 100')
        duracoes = b - a
        result[f'{campo}_medio_pct'] = float(np.sum(v * duracoes) / (tb - ta))
        result[f'{campo}_maximo_pct'] = float(v.max())
        if campo == 'freio':
            aplicado = limiares['freio_aplicado_pct']
            result['tempo_freio_aplicado_s'] = float(duracoes[v >= aplicado].sum())
            result['tempo_freio_forte_s'] = float(duracoes[v >= limiares['freio_forte_pct']].sum())
            result['freio_ativo_na_entrada'] = bool(v[0] >= aplicado)
            # Somente novos cruzamentos; um sinal herdado na borda nao e um inicio.
            tt, vv = f.tempo_relativo_s.to_numpy(), f.valor.to_numpy()
            onset = tt[1:][(vv[1:] >= aplicado) & (vv[:-1] < aplicado)]
            onset = onset[(onset >= ta) & (onset < tb)]
            result['inicio_frenagem_m'] = pos(onset[0]) if len(onset) else np.nan
        else:
            maximo = limiares['acelerador_maximo_pct']
            result['tempo_acelerador_maximo_s'] = float(duracoes[v >= maximo].sum())
            result['tempo_acelerador_maximo_apos_minima_s'] = float(
                np.maximum(0, b - np.maximum(a, tmin))[v >= maximo].sum())
            if tmin < tb:
                a2, b2, v2 = intervalos_zoh(f.tempo_relativo_s, f.valor, tmin, tb)
                sustentada = primeira_sustentada(a2, b2, v2, maximo, limiares['sustentacao_minima_s'])
            else:
                sustentada = np.nan
            result['primeira_aplicacao_99_sustentada_apos_minima_m'] = pos(sustentada)
    return result


def validar_config(config, alinhadas):
    if set(alinhadas.volta) != set(config['voltas']) or config['referencia'] not in config['voltas']:
        raise ValueError('A configuracao requer as quatro voltas do estudo piloto')
    limites = config['trechos']
    if not limites or len({t['id'] for t in limites}) != len(limites):
        raise ValueError('Identificadores de trechos invalidos')
    grade = np.sort(alinhadas.distancia_m.unique())
    if limites[0]['inicio_m'] != grade[0] or limites[-1]['fim_m'] != grade[-1]:
        raise ValueError('Os trechos precisam cobrir exatamente o intervalo comum')
    for i, t in enumerate(limites):
        if t['inicio_m'] not in grade or t['fim_m'] not in grade or t['inicio_m'] >= t['fim_m']:
            raise ValueError('Limites fora da grade ou invertidos')
        if i and limites[i-1]['fim_m'] != t['inicio_m']:
            raise ValueError('Trechos com sobreposicao ou lacuna')


def gerar(dados, config_path, saida):
    config = json.loads(config_path.read_text(encoding='utf-8'))
    alinhadas = grade_comum(pd.read_parquet(dados / 'voltas_alinhadas.parquet'))
    nativas = pd.read_parquet(dados / 'amostras_nativas.parquet')
    resumo = pd.read_csv(dados / 'resumo_voltas.csv')
    aptas = resumo.loc[resumo.apta_para_analise]
    if (set(aptas.volta) != set(config['voltas']) or set(nativas.volta) != set(config['voltas'])
            or not aptas.volta_completa.all() or not aptas.interrupcoes.eq(0).all()
            or not aptas.tempo_oficial_s.gt(0).all()):
        raise ValueError('Bases ou resumo incompativeis com a selecao do estudo')
    validar_config(config, alinhadas)
    linhas = []
    for volta in config['voltas']:
        a = alinhadas.loc[alinhadas.volta == volta].sort_values('distancia_m')
        n = nativas.loc[nativas.volta == volta]
        for t in config['trechos']:
            cautela = any(r['inicio_m'] < t['fim_m'] and r['fim_m'] > t['inicio_m']
                          for r in config['regioes_cautela'])
            linhas.append({'volta': volta, 'trecho': t['id'], 'nome_trecho': t['nome'],
                           'inicio_m': t['inicio_m'], 'fim_m': t['fim_m'],
                           'cautela_distancia': cautela, **metricas(n, a, t, config['limiares'])})
    tabela = pd.DataFrame(linhas)
    ref = tabela.loc[tabela.volta == config['referencia']].set_index('trecho').tempo_trecho_s
    tabela['volta_referencia'] = config['referencia']
    tabela['delta_trecho_s'] = tabela.tempo_trecho_s - tabela.trecho.map(ref)
    totais = []
    for volta, f in tabela.groupby('volta', sort=False):
        a = alinhadas.loc[alinhadas.volta == volta].sort_values('distancia_m')
        tempo_comum = a.tempo_relativo_s.iloc[-1] - a.tempo_relativo_s.iloc[0]
        if not np.isclose(f.tempo_trecho_s.sum(), tempo_comum, rtol=0, atol=1e-8):
            raise ValueError('Tempos de trechos nao reproduzem o total')
        totais.append({'volta': volta, 'tempo_intervalo_comum_s': tempo_comum,
                       'tempo_oficial_volta_s': float(aptas.set_index('volta').loc[volta, 'tempo_oficial_s']),
                       'delta_intervalo_comum_s': f.delta_trecho_s.sum()})
    if saida.exists():
        raise ValueError(f'Escolha uma pasta de saida nova: {saida}')
    saida.mkdir(parents=True)
    tabela.to_parquet(saida / 'caracteristicas_por_trecho.parquet', index=False)
    tabela.to_csv(saida / 'caracteristicas_por_trecho.csv', index=False, encoding='utf-8-sig')
    # Copia para abertura direta no Excel em ambiente com separador decimal virgula.
    tabela.to_csv(saida / 'caracteristicas_por_trecho_excel.csv', index=False, sep=';', decimal=',', encoding='utf-8-sig')
    limites = pd.DataFrame(config['trechos']).rename(columns={'id': 'trecho', 'nome': 'nome_trecho'})
    limites.to_csv(saida / 'limites_trechos.csv', index=False)
    for campo, nome in [('tempo_trecho_s', 'tempos_por_trecho'), ('delta_trecho_s', 'deltas_por_trecho')]:
        wide = tabela.pivot(index='trecho', columns='volta', values=campo).rename(columns=lambda v: f'volta_{v}')
        limites.merge(wide, on='trecho').to_csv(saida / f'{nome}.csv', index=False)
    pd.DataFrame(totais).to_csv(saida / 'resumo_voltas_trechos.csv', index=False)
    manifesto = {'configuracao': config,
                 'sha256': {nome: hashlib.sha256((dados / nome).read_bytes()).hexdigest()
                            for nome in ['voltas_alinhadas.parquet', 'amostras_nativas.parquet', 'resumo_voltas.csv']},
                 'sha256_config': hashlib.sha256(config_path.read_bytes()).hexdigest(),
                 'sha256_script': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                 'linhas': len(tabela)}
    (saida / 'manifesto_trechos.json').write_text(json.dumps(manifesto, indent=2, ensure_ascii=False), encoding='utf-8')
    print(pd.DataFrame(totais).round(6).to_string(index=False))
    print(f'Geradas {len(tabela)} linhas em {saida.resolve()}')
    return tabela


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--dados', type=Path, required=True)
    p.add_argument('--config', type=Path, default=CONFIG_PADRAO)
    p.add_argument('--saida', type=Path, required=True)
    args = p.parse_args()
    gerar(args.dados, args.config, args.saida)


if __name__ == '__main__':
    main()
