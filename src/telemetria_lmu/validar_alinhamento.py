from pathlib import Path
import argparse
import numpy as np
import pandas as pd

p = argparse.ArgumentParser(description='Audita a saída espacial do pré-processamento LMU v2')
p.add_argument('pasta', nargs='?', default='dados_processados_v2', type=Path)
a = p.parse_args()
base = a.pasta
alinhadas = pd.read_parquet(base / 'voltas_alinhadas.parquet')
resumo = pd.read_csv(base / 'resumo_voltas.csv')
colunas = {'volta', 'distancia_m', 'tempo_relativo_s', 'velocidade', 'acelerador', 'freio'}
if not colunas.issubset(alinhadas):
    raise ValueError(f'Colunas ausentes: {colunas-set(alinhadas.columns)}')
aptas = resumo.loc[resumo.apta_para_analise]
if (alinhadas.empty or set(alinhadas.volta) != set(aptas.volta)
        or not aptas.volta_completa.all() or not aptas.interrupcoes.eq(0).all()
        or not aptas.tempo_oficial_s.gt(0).all()):
    raise ValueError('A base espacial não corresponde às voltas completas, cronometradas e sem interrupções')
if not np.isfinite(alinhadas[['velocidade', 'acelerador', 'freio']].to_numpy()).all():
    raise ValueError('A base espacial contém valores não finitos nos sinais principais')

linhas = []
for volta, f in alinhadas.groupby('volta', sort=True):
    f = f.sort_values('distancia_m')
    d = f.distancia_m.to_numpy(float)
    t = f.tempo_relativo_s.to_numpy(float)
    dd = np.diff(d)
    dt = np.diff(t)
    r = resumo.loc[resumo.volta == volta]
    oficial = r.tempo_oficial_s.iloc[0] if len(r) else np.nan
    duracao = r.duracao_cronometro_s.iloc[0] if len(r) else np.nan
    linhas.append({
        'volta': int(volta),
        'amostras_espaciais': len(f),
        'distancia_inicial_m': d[0],
        'distancia_final_m': d[-1],
        'distancia_coberta_m': d[-1]-d[0],
        'tempo_inicial_s': t[0],
        'tempo_final_s': t[-1],
        'tempo_coberto_s': t[-1]-t[0],
        'duracao_volta_s': duracao,
        'tempo_oficial_s': oficial,
        'distancia_estritamente_crescente': bool(np.all(dd > 0)),
        'tempo_estritamente_crescente': bool(np.all(dt > 0)),
        'valores_finitos': bool(np.isfinite(d).all() and np.isfinite(t).all()),
        'maior_incremento_tempo_s': float(dt.max()) if len(dt) else np.nan,
        'aviso_limite_tempo': bool(t[0] > 0.25 or (np.isfinite(duracao) and duracao - t[-1] > .25)),
    })
resultado = pd.DataFrame(linhas)
resultado.to_csv(base / 'auditoria_alinhamento.csv', index=False)
print(resultado.to_string(index=False))

voltas = sorted(int(v) for v in alinhadas.volta.unique())
if voltas:
    partes = [alinhadas.loc[alinhadas.volta == v, 'distancia_m'] for v in voltas]
    comum = sorted(set(partes[0]).intersection(*[set(x) for x in partes[1:]]))
    print(f'\nVoltas na comparação: {voltas}')
    print(f'Pontos de distância comuns: {len(comum)}')
    if comum:
        print(f'Intervalo comum: {min(comum):.1f} a {max(comum):.1f} m')
    else:
        print('ATENÇÃO: Não existe uma grade espacial comum a todas as voltas.')
print(f'\nAuditoria salva em {base / "auditoria_alinhamento.csv"}')
if not resultado[['distancia_estritamente_crescente', 'tempo_estritamente_crescente',
                  'valores_finitos']].all().all():
    raise SystemExit('A auditoria espacial falhou; confira o CSV antes de gerar gráficos')
