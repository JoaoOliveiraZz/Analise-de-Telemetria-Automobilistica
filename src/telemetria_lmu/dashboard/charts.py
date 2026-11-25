"""Figuras Plotly puras, reutilizáveis e independentes dos componentes de tela."""
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from .data import delta_curve, native_signal
from .theme import COLORS, MUTED, PANEL, TEXT


def style(fig, height):
    fig.update_layout(height=height, paper_bgcolor=PANEL, plot_bgcolor=PANEL,
        font={'family': 'Segoe UI, sans-serif', 'color': TEXT, 'size': 12},
        margin={'l': 75, 'r': 30, 't': 35, 'b': 45}, separators=',.',
        legend={'orientation': 'h', 'y': 1.08, 'x': 0, 'font': {'size': 12}},
        hoverlabel={'bgcolor': '#1e293b', 'font': {'color': TEXT}},
        hovermode='x unified')
    fig.update_xaxes(gridcolor='#25334a', zeroline=False, color=MUTED)
    fig.update_yaxes(gridcolor='#25334a', zeroline=False, color=MUTED,
                     automargin=True, title_standoff=12)
    return fig


def heatmap(session, laps):
    codes = [t['id'] for t in session.config['trechos']]
    f = session.features.loc[session.features.volta.isin(laps)]
    pivot = f.pivot(index='volta', columns='trecho', values='delta_trecho_s').reindex(index=laps, columns=codes)
    maxabs = max(float(session.features.delta_trecho_s.abs().max()), .001)
    z = pivot.to_numpy()
    texts = [[f'{v:+.3f}'.replace('.', ',') for v in row] for row in z]
    custom = [[[session.segment(code)['inicio_m'], session.segment(code)['fim_m'],
                float(f.loc[(f.volta==lap)&(f.trecho==code), 'tempo_trecho_s'].iloc[0])]
               for code in codes] for lap in laps]
    fig = go.Figure(go.Heatmap(x=codes, y=[f'Volta {v}' for v in laps], z=z.tolist(),
        text=texts, texttemplate='%{text}', textfont={'size': 13}, customdata=custom,
        xgap=5, ygap=5, zmin=-maxabs, zmax=maxabs, zmid=0,
        colorscale=[[0,'#2563eb'],[.5,'#edf2f7'],[1,'#dc2626']],
        colorbar={'title': {'text': 'Delta (s)'}, 'thickness': 12, 'len': .85},
        hovertemplate='%{y} · %{x}<br>%{customdata[0]}–%{customdata[1]} m<br>'
                      'Tempo: %{customdata[2]:.3f} s<br>Delta: %{z:+.3f} s<extra></extra>'))
    # Texto preto sobre células claras; branco apenas nos extremos saturados.
    fig.update_traces(textfont_color='#111827')
    for i, lap in enumerate(laps):
        for j, code in enumerate(codes):
            if abs(z[i,j]) > maxabs*.65:
                fig.add_annotation(x=code, y=f'Volta {lap}', text=texts[i][j],
                                   showarrow=False, font={'color':'white','size':13}, bgcolor='rgba(0,0,0,0)')
    style(fig, 160 + 55*len(laps))
    fig.update_layout(hovermode='closest', margin={'l':75,'r':25,'t':40,'b':10})
    fig.update_yaxes(autorange='reversed', showgrid=False)
    fig.update_xaxes(side='top', showgrid=False)
    return fig


def accumulated(session, laps, focus):
    fig = go.Figure()
    for lap in laps:
        d = delta_curve(session, lap)
        fig.add_trace(go.Scatter(x=d.distancia_m.tolist(), y=d.delta_s.tolist(), name=f'Volta {lap}',
            mode='lines', line={'color': COLORS[lap], 'width': 3 if lap==focus else 2},
            hovertemplate='%{y:+.3f} s<extra>%{fullData.name}</extra>'))
    fig.add_hline(y=0, line_color='#73849d', line_width=1)
    for t in session.config['trechos']:
        fig.add_vline(x=t['inicio_m'], line_color='#344155', line_width=1, line_dash='dot')
    style(fig, 350)
    fig.update_xaxes(title_text='Distância ao longo da volta (m)', range=[5,3500])
    fig.update_yaxes(title_text='Delta acumulado (s)')
    return fig


def telemetry(session, laps, segment, local):
    start, end = segment['inicio_m'], segment['fim_m']
    fig = make_subplots(rows=4, cols=1, shared_xaxes=True, vertical_spacing=.055)
    fields = [('velocidade','km/h'),('acelerador','%'),('freio','%')]
    for lap in laps:
        for row, (field, unit) in enumerate(fields, 1):
            s = native_signal(session, lap, field, start, end)
            fig.add_trace(go.Scatter(x=s.distancia_m.tolist(), y=s.valor.tolist(),
                name=f'Volta {lap}', legendgroup=str(lap), showlegend=row==1, mode='lines',
                line={'color':COLORS[lap], 'width':2, 'shape':'linear' if row==1 else 'hv'},
                hovertemplate=f'%{{y:.1f}} {unit}<extra>Volta {lap}</extra>'), row=row,col=1)
        delta = delta_curve(session, lap, segment, local)
        fig.add_trace(go.Scatter(x=delta.distancia_m.tolist(), y=delta.delta_s.tolist(),
            name=f'Volta {lap}', legendgroup=str(lap), showlegend=False, mode='lines',
            line={'color':COLORS[lap], 'width':2}, hovertemplate='%{y:+.3f} s<extra>%{fullData.name}</extra>'),row=4,col=1)
    for region in session.config['regioes_cautela']:
        if start < region['fim_m'] and end > region['inicio_m']:
            fig.add_vrect(x0=max(start,region['inicio_m']), x1=min(end,region['fim_m']),
                          fillcolor='#94a3b8', opacity=.14, line_width=0, row='all', col=1)
    for i, label in enumerate(['Velocidade (km/h)','Acelerador (%)','Freio (%)',
                              'Delta local (s)' if local else 'Delta acumulado (s)'], 1):
        fig.update_yaxes(title_text=label, row=i,col=1)
    for i in [2,3]:
        fig.update_yaxes(range=[-3,105], tickvals=[0,50,100], row=i,col=1)
    style(fig, 760)
    fig.update_layout(hoversubplots='axis')
    fig.update_xaxes(range=[start,end], showspikes=True, spikemode='across', spikesnap='cursor',
                     spikedash='dot', spikecolor='#7dd3fc')
    fig.update_xaxes(title_text='Distância ao longo da volta (m)', row=4,col=1)
    return fig


def speeds(session, laps, segment):
    fig = go.Figure()
    for lap in laps:
        f = session.features.loc[(session.features.volta==lap)&(session.features.trecho==segment['id'])].iloc[0]
        values = [float(f[c]) for c in ['velocidade_entrada_kmh','velocidade_minima_kmh','velocidade_saida_kmh']]
        fig.add_trace(go.Bar(x=['Entrada','Mínima','Saída'], y=values, name=f'Volta {lap}',
            marker_color=COLORS[lap], text=[f'{v:.1f}'.replace('.',',') for v in values], textposition='outside',
            cliponaxis=False, hovertemplate='%{x}: %{y:.1f} km/h<extra>%{fullData.name}</extra>'))
    style(fig, 340)
    fig.update_layout(barmode='group', margin={'l':75,'r':25,'t':55,'b':35})
    fig.update_yaxes(title_text='Velocidade (km/h)', rangemode='tozero')
    return fig
