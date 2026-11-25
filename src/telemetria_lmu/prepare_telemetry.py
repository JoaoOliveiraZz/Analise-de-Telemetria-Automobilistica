"""Prepara voltas completas, cronometradas e sem lacunas do DuckDB do LMU."""
import argparse
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

BASE_RATE = 100
CANAIS = {
    'Ground Speed': 'velocidade', 'Throttle Pos': 'acelerador',
    'Brake Pos': 'freio', 'Steering Pos': 'direcao', 'Lap Dist': 'distancia',
    'Total Dist': 'distancia_total', 'G Force Lat': 'g_lateral',
    'G Force Long': 'g_longitudinal', 'Path Lateral': 'posicao_lateral',
    'Fuel Level': 'combustivel',
}
ESSENCIAIS = {'velocidade', 'acelerador', 'freio', 'distancia'}


def dados(con, tabela):
    nome = '"' + tabela.replace('"', '""') + '"'
    return con.execute(f'SELECT * FROM {nome} ORDER BY rowid').df()


def eventos(con, tabela):
    return (dados(con, tabela).dropna(subset=['ts', 'value'])
            .drop_duplicates('ts', keep='last').sort_values('ts').reset_index(drop=True))


def canais_nativos(con, tempos):
    catalogo = dados(con, 'channelsList').set_index('channelName')
    canais = {}
    for nome, apelido in CANAIS.items():
        if nome not in catalogo.index:
            continue
        freq = int(catalogo.loc[nome, 'frequency'])
        if freq <= 0 or BASE_RATE % freq:
            raise ValueError(f'Frequência não suportada: {nome} ({freq} Hz)')
        indices = np.arange(0, len(tempos), BASE_RATE // freq)
        valores = dados(con, nome)['value'].to_numpy(dtype=float)
        if len(valores) != len(indices):
            raise ValueError(f'{nome}: {len(valores)} amostras, esperadas {len(indices)}')
        canais[apelido] = pd.DataFrame({
            'canal': nome, 'variavel': apelido, 'frequencia_hz': freq,
            'unidade': str(catalogo.loc[nome, 'unit']),
            'indice_canal': np.arange(len(indices)), 'indice_gps_time': indices,
            'ts': tempos[indices], 'valor': valores,
            'metodo_tempo': 'indice_frequencia_fase_zero',
        })
    if faltantes := ESSENCIAIS - canais.keys():
        raise ValueError(f'Canais essenciais ausentes: {sorted(faltantes)}')
    return canais


def trecho(frame, inicio, fim):
    return frame.loc[(frame.ts >= inicio) & (frame.ts < fim)]


def reset_na_borda(ts, resets, evento):
    candidatos = resets[(ts[resets] <= evento) & (evento <= ts[resets + 1])]
    return int(candidatos[0]) if len(candidatos) == 1 else None


def alinhar(nativos, distancia, inicio, passo):
    td = distancia.ts.to_numpy()
    d = distancia.valor.to_numpy()
    suporte = {}
    for canal, amostras in nativos.items():
        dentro = amostras.loc[amostras.ts.between(td[0], td[-1])]
        if len(dentro) < 2 or not np.isfinite(dentro.valor).all():
            raise ValueError(f'{canal} sem amostras finitas suficientes no trecho espacial')
        # Cada sinal mantém sua frequência até receber uma coordenada espacial.
        suporte[canal] = (np.interp(dentro.ts, td, d), dentro.valor.to_numpy())
    inicio_m = max(x[0][0] for x in suporte.values())
    fim_m = min(x[0][-1] for x in suporte.values())
    grade = np.arange(np.ceil(inicio_m / passo), np.floor(fim_m / passo) + 1) * passo
    if len(grade) < 2:
        raise ValueError('grade espacial comum insuficiente')
    return pd.DataFrame({
        'distancia_m': grade, 'tempo_relativo_s': np.interp(grade, d, td) - inicio,
        **{nome: np.interp(grade, x, y) for nome, (x, y) in suporte.items()},
    })


def processar(con, passo, limite_gap):
    t = dados(con, 'GPS Time')['value'].to_numpy(dtype=float)
    dt = np.diff(t)
    if (len(t) < 2 or not np.isfinite(t).all() or np.any(dt <= 0)
            or not .009 <= np.median(dt) <= .011):
        raise ValueError('GPS Time inválido ou incompatível com base de 100 Hz')
    canais = canais_nativos(con, t)
    voltas = eventos(con, 'Lap')
    oficiais = eventos(con, 'Lap Time')
    if len(voltas) < 2 or voltas.value.duplicated().any():
        raise ValueError('Lap precisa conter pelo menos duas voltas com identificadores únicos')
    tabelas = set(con.execute('SHOW TABLES').fetchnumpy()['name'])
    gear = eventos(con, 'Gear').rename(columns={'value': 'marcha'}) if 'Gear' in tabelas else None
    dist = canais['distancia']
    td = dist.ts.to_numpy()
    resets = np.flatnonzero(np.diff(dist.valor) < -10)
    gap_idx = np.flatnonzero(dt > limite_gap + 1e-9)
    gaps = pd.DataFrame({'inicio_s': t[gap_idx], 'fim_s': t[gap_idx + 1],
                         'duracao_s': dt[gap_idx]})
    resumo, temporal, espacial, nativas = [], [], [], []
    for i, evento in enumerate(voltas.itertuples(index=False)):
        numero, inicio = int(evento.value), float(evento.ts)
        fechado = i + 1 < len(voltas)
        fim = float(voltas.ts.iloc[i + 1]) if fechado else float(t[-1])
        ts = t[(t >= inicio) & (t < fim)]
        abertura = reset_na_borda(td, resets, inicio)
        fechamento = reset_na_borda(td, resets, fim) if fechado else None
        d = (trecho(dist.iloc[abertura + 1:fechamento + 1], inicio, fim)
             if abertura is not None and fechamento is not None else dist.iloc[:0])
        completa = (fechado and t[0] <= inicio < fim <= t[-1] and len(d) >= 2
                    and np.isfinite(d.valor).all() and (np.diff(d.valor) > 0).all())
        candidatos = oficiais.loc[np.isclose(oficiais.ts, fim, atol=.05, rtol=0)] if fechado else oficiais.iloc[:0]
        oficial = (float(candidatos.loc[(candidatos.ts - fim).abs().idxmin(), 'value'])
                   if not candidatos.empty else np.nan)
        afetados = gaps.loc[(gaps.inicio_s < fim) & (gaps.fim_s > inicio)]
        motivos = []
        if not completa:
            motivos.append('sem evento de encerramento' if not fechado else 'volta parcial ou distância não monotônica entre resets')
        if fechado and (not np.isfinite(oficial) or oficial <= 0):
            motivos.append('tempo oficial ausente ou zerado')
        if not afetados.empty:
            motivos.append('interrupção de coleta')
        if not motivos:
            por_canal = {nome: trecho(frame, inicio, fim) for nome, frame in canais.items()}
            try:
                alinhada = alinhar(por_canal, d, inicio, passo)
            except ValueError as exc:
                motivos.append(str(exc))
        if not motivos:
            alinhada['volta'] = numero
            espacial.append(alinhada)
            bloco = pd.DataFrame({'ts': ts})
            for nome, frame in por_canal.items():
                src = frame[['ts', 'valor']].rename(columns={'valor': nome})
                bloco = pd.merge_asof(bloco, src, on='ts', direction='backward',
                                       tolerance=1 / frame.frequencia_hz.iloc[0] + 1e-6)
                nativas.append(frame.assign(volta=numero, tempo_relativo_s=frame.ts - inicio))
            if gear is not None:
                bloco = pd.merge_asof(bloco, gear, on='ts', direction='backward')
            temporal.append(bloco.assign(volta=numero, tempo_relativo_s=bloco.ts - inicio))
        resumo.append({'volta': numero, 'inicio_s': inicio, 'fim_s': fim,
                       'duracao_cronometro_s': fim - inicio, 'tempo_oficial_s': oficial,
                       'amostras': len(ts), 'volta_completa': completa,
                       'interrupcoes': len(afetados), 'apta_para_analise': not motivos,
                       'motivo_exclusao': '; '.join(motivos)})
    return pd.DataFrame(resumo), gaps, temporal, espacial, nativas


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('banco', type=Path)
    p.add_argument('--saida', type=Path, default=Path('dados_processados_v2'))
    p.add_argument('--passo-m', type=float, default=5.0)
    p.add_argument('--limite-gap-s', type=float, default=.03)
    args = p.parse_args()
    if not np.isfinite(args.passo_m) or args.passo_m <= 0:
        p.error('--passo-m deve ser finito e positivo')
    if not np.isfinite(args.limite_gap_s) or args.limite_gap_s <= 1 / BASE_RATE:
        p.error('--limite-gap-s deve ser finito e maior que 0,01 s')
    # Uma pasta nova evita misturar saídas de execuções com filtros diferentes.
    if args.saida.exists():
        p.error(f'Escolha uma pasta de saída nova: {args.saida} já existe')
    with duckdb.connect(str(args.banco), read_only=True) as con:
        resumo, gaps, temporal, espacial, nativas = processar(con, args.passo_m, args.limite_gap_s)
    args.saida.mkdir(parents=True)
    resumo.to_csv(args.saida / 'resumo_voltas.csv', index=False)
    gaps.to_csv(args.saida / 'interrupcoes_temporais.csv', index=False)
    aprovadas = resumo.loc[resumo.apta_para_analise, 'volta'].tolist()
    relatorio = [f'Banco: {args.banco.name}', f'Grade espacial: {args.passo_m:g} m',
                 f'Interrupção: intervalo > {args.limite_gap_s:g} s no GPS Time',
                 f'Voltas aptas: {aprovadas}',
                 'Critérios: eventos e resets nas duas bordas, distância crescente, tempo oficial positivo e ausência de interrupções.',
                 'Tempos dos canais amostrados reconstruídos por índice e frequência; fase comum é hipótese.',
                 'Eixos de força G preservados com os nomes do banco; não corrigidos.',
                 '', resumo.to_string(index=False)]
    (args.saida / 'relatorio_qualidade.txt').write_text('\n'.join(relatorio), encoding='utf-8')
    if not aprovadas:
        raise SystemExit(f'Nenhuma volta apta; consulte {args.saida / "resumo_voltas.csv"}')
    for nome, frames in [('voltas_validadas', temporal), ('voltas_alinhadas', espacial),
                         ('amostras_nativas', nativas)]:
        pd.concat(frames, ignore_index=True).to_parquet(args.saida / f'{nome}.parquet', index=False)
    print(f'Voltas aptas: {aprovadas}. Saída: {args.saida.resolve()}')


if __name__ == '__main__':
    main()
