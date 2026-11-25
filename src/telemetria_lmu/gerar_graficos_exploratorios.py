"""Compara somente as voltas aptas registradas pela preparação v2."""
import argparse
from math import ceil
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

CAMPOS = [('velocidade', 'Velocidade (km/h)'), ('acelerador', 'Acelerador (%)'),
          ('freio', 'Freio (%)')]


def grade_comum(alinhadas):
    """Mesmo suporte para todos os pares, sem extrapolar extremidades."""
    grades = []
    for _, d in alinhadas.groupby('volta'):
        if d.distancia_m.duplicated().any():
            raise ValueError('Distâncias duplicadas em uma volta')
        d = d.sort_values('distancia_m')
        if (not np.isfinite(d[['distancia_m', 'tempo_relativo_s']].to_numpy()).all()
                or not (np.diff(d.tempo_relativo_s) > 0).all()):
            raise ValueError('Coordenadas de comparação inválidas')
        grades.append(set(d.distancia_m))
    if not grades:
        raise ValueError('Não há voltas para comparar')
    comum = sorted(set.intersection(*grades))
    if len(comum) < 2 or not np.allclose(np.diff(comum), np.diff(comum)[0], rtol=0, atol=1e-8):
        raise ValueError('Grade comum insuficiente ou descontínua')
    return alinhadas.loc[alinhadas.distancia_m.isin(comum)].copy()


def comparar_par(alinhadas, alvo, ref, saida, trecho=None):
    alinhadas = grade_comum(alinhadas)
    a = alinhadas.loc[alinhadas.volta == alvo].drop(columns='volta')
    b = alinhadas.loc[alinhadas.volta == ref].drop(columns='volta')
    par = a.merge(b, on='distancia_m', suffixes=('_alvo', '_referencia'),
                  validate='one_to_one').sort_values('distancia_m')
    if len(par) < 2:
        raise ValueError('Voltas sem intervalo espacial comum')
    delta = par.tempo_relativo_s_alvo - par.tempo_relativo_s_referencia
    par['delta_acumulado_s'] = delta - delta.iloc[0]
    par.insert(0, 'volta_alvo', alvo)
    par.insert(1, 'volta_referencia', ref)
    inicio = par.distancia_m.iloc[0]
    vistas = [(par, '')]
    if trecho is not None:
        recorte = par.loc[par.distancia_m.between(*trecho)]
        if len(recorte) < 2:
            raise ValueError('O trecho precisa conter pelo menos dois pontos comuns')
        vistas.append((recorte, f'_{trecho[0]:g}_{trecho[1]:g}m'))
    saida.mkdir(parents=True, exist_ok=True)
    par.to_csv(saida / f'delta_voltas_{alvo}_{ref}.csv', index=False)
    for d, sufixo in vistas:
        x0, x1 = d.distancia_m.iloc[[0, -1]]
        variacao = d.delta_acumulado_s.iloc[-1] - d.delta_acumulado_s.iloc[0]
        fig, axes = plt.subplots(4, 1, figsize=(13, 9), sharex=True, layout='constrained')
        for ax, (campo, rotulo) in zip(axes, CAMPOS):
            ax.plot(d.distancia_m, d[f'{campo}_alvo'], label=f'Volta {alvo}', color='#2563eb')
            ax.plot(d.distancia_m, d[f'{campo}_referencia'], label=f'Volta {ref}', color='#d97706')
            ax.set_ylabel(rotulo)
        axes[0].legend()
        axes[3].plot(d.distancia_m, d.delta_acumulado_s, color='#334155')
        axes[3].axhline(0, color='#94a3b8', linewidth=1)
        axes[3].set(xlabel='Distância ao longo da volta (m)', ylabel='Delta (s)', xlim=(x0, x1))
        for ax in axes:
            ax.grid(alpha=.2)
        fig.suptitle(f'Volta {alvo} em relação à {ref} | {x0:g} a {x1:g} m\n'
                     f'Delta zerado aos {inicio:g} m · variação no trecho: {variacao:+.3f} s')
        fig.savefig(saida / f'delta_voltas_{alvo}_{ref}{sufixo}.png', dpi=160)
        plt.close(fig)
        print(f'Volta {alvo} - {ref}: {variacao:+.3f} s entre {x0:g} e {x1:g} m')
    return {'volta_alvo': int(alvo), 'volta_referencia': int(ref),
            'inicio_m': float(inicio), 'fim_m': float(par.distancia_m.iloc[-1]),
            'pontos': len(par),
            'tempo_trecho_alvo_s': float(par.tempo_relativo_s_alvo.iloc[-1] - par.tempo_relativo_s_alvo.iloc[0]),
            'tempo_trecho_referencia_s': float(par.tempo_relativo_s_referencia.iloc[-1] - par.tempo_relativo_s_referencia.iloc[0]),
            'delta_trecho_s': float(par.delta_acumulado_s.iloc[-1])}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--dados', type=Path, default=Path('dados_processados_v2'))
    p.add_argument('--saida', type=Path, default=Path('graficos_exploratorios_v2'))
    p.add_argument('--volta', type=int, help='Gera somente a comparação desta volta')
    p.add_argument('--referencia', type=int, help='Volta de referência (padrão: menor tempo oficial)')
    p.add_argument('--trecho-m', type=float, nargs=2, metavar=('INICIO', 'FIM'),
                   help='Gera também um recorte do par, mantendo o delta acumulado')
    args = p.parse_args()
    resumo = pd.read_csv(args.dados / 'resumo_voltas.csv')
    aptas = resumo.loc[resumo.apta_para_analise].set_index('volta').tempo_oficial_s
    alinhadas = pd.read_parquet(args.dados / 'voltas_alinhadas.parquet')
    if aptas.empty or set(alinhadas.volta) != set(aptas.index):
        raise ValueError('A base espacial não corresponde à seleção de voltas aptas')
    if not aptas.gt(0).all() or not resumo.loc[resumo.apta_para_analise, 'interrupcoes'].eq(0).all():
        raise ValueError('A seleção precisa ter tempos oficiais positivos e ausência de interrupções')
    alinhadas = grade_comum(alinhadas)
    plt.rcParams.update({'axes.spines.top': False, 'axes.spines.right': False})
    ranking = aptas.sort_values(kind='stable')
    ref = args.referencia if args.referencia is not None else ranking.index[0]
    if args.volta is not None:
        if args.volta == ref or args.volta not in aptas.index or ref not in aptas.index:
            p.error('Escolha duas voltas aptas e distintas')
        comparar_par(alinhadas, args.volta, ref, args.saida, args.trecho_m)
        return
    if args.referencia is not None or args.trecho_m is not None:
        p.error('--referencia e --trecho-m precisam de --volta')
    nativas = pd.read_parquet(args.dados / 'amostras_nativas.parquet')
    if not len(aptas) or any(set(f.volta) != set(aptas.index) for f in (alinhadas, nativas)):
        raise ValueError('As bases não correspondem à seleção de voltas aptas')
    args.saida.mkdir(parents=True, exist_ok=True)

    fig, axes = plt.subplots(ceil(len(aptas) / 2), 2, squeeze=False,
                             figsize=(13, 3.4 * ceil(len(aptas) / 2)), sharex=True, sharey=True,
                             layout='constrained')
    for i, ax in enumerate(axes.flat):
        if i >= len(aptas):
            ax.set_visible(False)
            continue
        volta = aptas.index[i]
        for campo, cor in [('acelerador', '#15803d'), ('freio', '#dc2626')]:
            d = nativas.loc[(nativas.volta == volta) & (nativas.variavel == campo)].sort_values('ts')
            ax.plot(d.tempo_relativo_s, d.valor, color=cor, label=campo.capitalize())
        ax.set(title=f'Volta {volta} · {aptas.loc[volta]:.3f} s', ylabel='Aplicação (%)')
        ax.grid(alpha=.2)
    axes.flat[0].legend(loc='lower right')
    fig.supxlabel('Tempo desde o início da volta (s)')
    fig.suptitle('Acelerador e freio nas voltas aptas · amostras nativas')
    fig.savefig(args.saida / 'comandos_por_volta.png', dpi=160)
    plt.close(fig)

    fig, axes = plt.subplots(3, 1, figsize=(13, 8), sharex=True, layout='constrained')
    for volta, d in alinhadas.groupby('volta'):
        d = d.sort_values('distancia_m')
        for ax, (campo, rotulo) in zip(axes, CAMPOS):
            ax.plot(d.distancia_m, d[campo], label=f'Volta {volta}', linewidth=1)
            ax.set_ylabel(rotulo)
            ax.grid(alpha=.2)
    axes[0].legend(ncol=min(len(aptas), 4))
    axes[-1].set_xlabel('Distância ao longo da volta (m)')
    fig.suptitle('Comparação por distância · voltas completas e sem interrupções')
    fig.savefig(args.saida / 'comparacao_comandos_distancia.png', dpi=160)
    plt.close(fig)

    if len(aptas) < 2:
        return
    comparacoes = [comparar_par(alinhadas, volta, ref, args.saida)
                   for volta in aptas.index if volta != ref]
    pd.DataFrame(comparacoes).to_csv(args.saida / 'resumo_comparacoes.csv', index=False)


if __name__ == '__main__':
    main()
