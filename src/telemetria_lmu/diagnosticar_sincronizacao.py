"""Diagnóstico reproduzível; lê o banco sem alterar os dados de origem.

Uso: .venv/Scripts/python diagnosticar_sincronizacao.py arquivo.duckdb
"""
import argparse
from pathlib import Path
import duckdb
import numpy as np
import pandas as pd


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('banco', type=Path)
    parser.add_argument('--saida', type=Path, default=Path('diagnostico_sincronizacao'))
    args = parser.parse_args()
    args.saida.mkdir(exist_ok=True, parents=True)
    with duckdb.connect(str(args.banco), read_only=True) as con:
        def load(name):
            return con.execute('SELECT * FROM "' + name.replace('"', '""') + '" ORDER BY rowid').df()
        t = load('GPS Time').value.to_numpy(float)
        v = load('Ground Speed').value.to_numpy(float) / 3.6
        gps = load('GPS Speed').value.to_numpy(float)
        dist = load('Total Dist').value.to_numpy(float)
        laps = load('Lap').sort_values('ts')
        meta = load('channelsList')
        counts = []
        for row in meta.itertuples():
            n = len(load(row.channelName))
            stride = 100 // row.frequency if row.frequency > 0 and 100 % row.frequency == 0 else None
            expected = len(t[::stride]) if stride else None
            counts.append(dict(canal=row.channelName,frequencia_hz=row.frequency,
                               amostras=n,esperadas=expected,compativel=n == expected if expected else None))
        pd.DataFrame(counts).to_csv(args.saida/'contagens.csv', index=False)
        # Os dez possíveis índices de fase do canal de 10 Hz.
        phase = []
        for k in range(10):
            ref = v[k::10]
            n = min(len(ref), len(gps))
            err = gps[:n] - ref[:n]
            phase.append(dict(fase_indice=k,pares=n,rmse_ms=float(np.sqrt(np.mean(err**2))),
                              erro_max_ms=float(np.max(np.abs(err)))))
        pd.DataFrame(phase).to_csv(args.saida/'fases_velocidade.csv',index=False)
        ts = t[::10]
        accel = np.gradient(v,t)
        # Não calcular evidência de derivada junto à interrupção ou nas bordas.
        gaps = np.flatnonzero(np.diff(t) > .03)
        safe = (ts > t[0]+.3) & (ts < t[-1]-.3)
        for i in gaps:
            safe &= (ts < t[i]-.3) | (ts > t[i+1]+.3)
        groups = [('total',np.ones(len(ts),bool))]
        for i in range(len(laps)-1):
            groups.append((f'volta_{int(laps.iloc[i].value)}',
                           (ts >= laps.iloc[i].ts) & (ts < laps.iloc[i+1].ts)))
        if len(gaps):
            groups += [('antes_gap',ts < t[gaps[0]]-.3),('depois_gap',ts > t[gaps[0]+1]+.3)]
        scans=[]
        for channel in ['G Force Lat','G Force Long','G Force Vert']:
            values=load(channel).value.to_numpy(float)*9.80665
            for group, mask in groups:
                for lag in np.round(np.arange(-.3,.301,.01),2):
                    predicted=np.interp(ts+lag,t,accel,left=np.nan,right=np.nan)
                    m=mask & safe & np.isfinite(predicted) & np.isfinite(values)
                    if m.sum()<40: continue
                    corr=np.corrcoef(values[m],predicted[m])[0,1]
                    scans.append(dict(canal=channel,trecho=group,deslocamento_s=lag,
                                      correlacao=corr,pares=int(m.sum()),
                                      rmse_sinal_invertido_ms2=np.sqrt(np.mean((values[m]+predicted[m])**2))))
        scans=pd.DataFrame(scans)
        scans.to_csv(args.saida/'correlacoes.csv',index=False)
        zero=scans[scans.deslocamento_s==0]
        zero.to_csv(args.saida/'eixos_sem_deslocamento.csv',index=False)
        mid=(ts[1:]+ts[:-1])/2
        derivative=np.diff(dist)/np.diff(ts)
        target=np.interp(mid,t,v)
        derr=pd.DataFrame(dict(ts=mid,dt_s=np.diff(ts),vel_distancia_ms=derivative,
                               velocidade_ms=target,erro_ms=derivative-target))
        derr.to_csv(args.saida/'distancia_velocidade.csv',index=False)
        resets=np.flatnonzero(np.diff(load('Lap Dist').value.to_numpy(float)) < -1000)
        borders=[]
        for r in resets:
            event=float(laps.iloc[np.argmin(abs(laps.ts.to_numpy()-ts[r+1]))].ts)
            borders.append(dict(ultima_distancia_antes_ts=ts[r],primeira_depois_ts=ts[r+1],
                                evento_lap_ts=event,evento_dentro_intervalo=ts[r]<=event<=ts[r+1]))
        pd.DataFrame(borders).to_csv(args.saida/'resets_eventos.csv',index=False)
        print('FASES GPS SPEED x GROUND SPEED (m/s)\n',pd.DataFrame(phase).to_string(index=False))
        print('\nEIXOS SEM DESLOCAMENTO\n',zero.to_string(index=False))
        print('\nRESETS\n',pd.DataFrame(borders).to_string(index=False))
        print('\nSaida:',args.saida.resolve())


if __name__ == '__main__':
    main()
