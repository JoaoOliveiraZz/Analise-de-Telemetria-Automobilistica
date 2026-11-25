"""Componentes de tela; cada seção coordena figuras e dados já calculados."""
import pandas as pd
import streamlit as st

from . import charts
from .theme import PLOT_CONFIG


def number(value, decimals=3, signed=False):
    return (f'{value:+.{decimals}f}' if signed else f'{value:.{decimals}f}').replace('.',',')


def lap_time(seconds):
    return f'{int(seconds//60)}:{seconds%60:06.3f}'.replace('.',',')


def chart(fig, key):
    st.plotly_chart(fig, width='stretch', theme=None, config=PLOT_CONFIG, key=key)


def sidebar(session):
    with st.sidebar:
        st.markdown('<div class="sidebar-brand">LMU<span> / </span>TELEMETRIA</div>'
                    '<div class="session-chip">Bahrain Outer Circuit · Estudo piloto</div>', unsafe_allow_html=True)
        st.caption('COMPARAÇÃO DE DESEMPENHO')
        options = [v for v in session.laps if v != session.reference]
        target = st.selectbox('Volta em análise', options, index=options.index(12) if 12 in options else 0,
                              format_func=lambda v:f'Volta {v}', key='target_lap')
        st.caption(f'Referência fixa: volta {session.reference} · menor tempo oficial da sessão selecionada.')
        codes = [t['id'] for t in session.config['trechos']]
        segment = st.selectbox('Trecho em detalhe', codes, index=1 if len(codes)>1 else 0,
            format_func=lambda code:f"{code} · {session.segment(code)['inicio_m']:g}–{session.segment(code)['fim_m']:g} m", key='segment')
        visible = st.multiselect('Voltas no panorama', options, default=options,
                                 format_func=lambda v:f'Volta {v}', key='visible_laps')
        st.divider()
        st.caption('SESSÃO VALIDADA')
        st.write(f'**{len(session.laps)} voltas** completas e sem interrupções')
        st.write(f"**{len(codes)} trechos** · 5–3.500 m")
        st.caption('Azul no mapa = menos tempo.\n\nVermelho = mais tempo que a referência.')
        st.divider()
        st.caption('Análise descritiva de uma sessão. As diferenças observadas não demonstram causalidade.')
    return target, session.segment(segment), visible


def header(session, target):
    st.markdown('<div class="eyebrow">BAHRAIN OUTER CIRCUIT / ANÁLISE EXPLORATÓRIA</div>', unsafe_allow_html=True)
    st.title('Análise de desempenho')
    st.caption(f'Volta {target} em relação à volta {session.reference} · descubra onde o tempo foi ganho ou perdido.')
    f = session.rows(target)
    loss = f.loc[f.delta_trecho_s.idxmax()]
    gain = f.loc[f.delta_trecho_s.idxmin()]
    a,b,c,d = st.columns(4)
    a.metric('Tempo analisado', lap_time(f.tempo_trecho_s.sum()),
             help='Tempo entre 5 e 3.500 m. O tempo oficial da volta inteira aparece em Dados e método.')
    b.metric('Delta total', number(f.delta_trecho_s.sum(), signed=True)+' s',
             help='Positivo: mais tempo que a referência. Negativo: menos tempo.')
    c.metric('Maior perda local', loss.trecho, number(loss.delta_trecho_s,signed=True)+' s', delta_color='off')
    d.metric('Maior ganho local', gain.trecho if gain.delta_trecho_s<0 else 'Sem ganho',
             number(gain.delta_trecho_s,signed=True)+' s' if gain.delta_trecho_s<0 else 'Todos os trechos com perda', delta_color='off')


def overview(session, target, visible):
    if not visible:
        st.info('Selecione ao menos uma volta em “Voltas no panorama” para visualizar os gráficos gerais.')
        return
    with st.container(border=True):
        st.subheader('Onde cada volta ganha ou perde tempo')
        st.caption('Diferença local em segundos · azul indica ganho, vermelho indica perda · escala simétrica e fixa para a sessão.')
        chart(charts.heatmap(session, visible), 'segment_heatmap')
        st.caption('T02 inclui a região de 720–755 m com interpretação cautelosa. Consulte Comparar trecho para investigar os sinais.')
    with st.container(border=True):
        st.subheader('Como a diferença se acumula ao longo da volta')
        st.caption('Todas as curvas começam em zero aos 5 m. Subida indica perda local; descida indica recuperação.')
        chart(charts.accumulated(session, visible, target), 'accumulated_delta')
    f = session.rows(target)
    loss = f.loc[f.delta_trecho_s.idxmax()]
    gains = int((f.delta_trecho_s < 0).sum())
    st.write(f'Na volta **{target}**, a maior perda ocorre em **{loss.trecho}** '
             f'(**{number(loss.delta_trecho_s,signed=True)} s**). '
             f'Há ganho local em **{gains} de {len(f)} trechos**, considerando os valores calculados antes do arredondamento.')
    st.caption('Diferenças de poucos milésimos representam proximidade numérica; não foi estimada uma margem de incerteza física.')


def segment_detail(session, target, segment):
    code = segment['id']
    st.subheader(f"{code} · {segment['inicio_m']:g}–{segment['fim_m']:g} m")
    names = {'T01':'Início e aproximação','T02':'Frenagem e saída 1','T03':'Ligação 1',
             'T04':'Frenagem e saída 2','T05':'Ligação 2','T06':'Transição, frenagem e saída 3',
             'T07':'Ligação 3','T08':'Frenagem e saída 4','T09':'Trecho final'}
    st.caption(names.get(code, segment['nome']))
    f = session.features.loc[(session.features.volta==target)&(session.features.trecho==code)].iloc[0]
    ref = session.features.loc[(session.features.volta==session.reference)&(session.features.trecho==code)].iloc[0]
    if f.cautela_distancia:
        st.warning('Este trecho contém a região de 720–755 m: a coerência entre distância e velocidade permanece em investigação. Os dados foram preservados. A faixa sombreada identifica a região nos gráficos.')
    a,b,c,d = st.columns(4)
    a.metric('Delta no trecho', number(f.delta_trecho_s,signed=True)+' s')
    b.metric('Tempo no trecho', number(f.tempo_trecho_s)+' s')
    c.metric('Freio ≥5%', number(f.tempo_freio_aplicado_s,2)+' s')
    d.metric('Acelerador ≥99%', number(f.tempo_acelerador_maximo_s,2)+' s')
    left,right = st.columns([1,2])
    with left:
        all_laps = st.toggle('Mostrar as quatro voltas', value=False, key='all_laps_detail')
    with right:
        mode = st.radio('Origem do delta', ['Início do trecho', 'Início comum aos 5 m'],
                        horizontal=True, key='delta_origin')
    laps = session.laps if all_laps else [target, session.reference]
    local = mode == 'Início do trecho'
    with st.container(border=True):
        st.subheader('Velocidade e comandos ao longo do trecho')
        st.caption('Passe o cursor para consultar valores. Pedais usam amostras nativas em degraus; arraste para ampliar e dê duplo clique para restaurar.')
        chart(charts.telemetry(session, laps, segment, local), 'telemetry_detail')
        origin = f"{segment['inicio_m']:g} m" if local else '5 m'
        st.caption(f'Delta zerado aos {origin}. A diferença total deste trecho é {number(f.delta_trecho_s,signed=True)} s, independentemente da origem escolhida.')
    with st.container(border=True):
        st.subheader('Velocidades de entrada e saída')
        st.caption('Entrada e saída correspondem aos limites fixos do trecho. A mínima considera o intervalo inteiro; esses pontos não são necessariamente as bordas físicas da curva.')
        chart(charts.speeds(session, laps, segment), 'entry_exit_speeds')
    fields = [('Tempo no trecho (s)','tempo_trecho_s'),('Velocidade na entrada (km/h)','velocidade_entrada_kmh'),
        ('Velocidade mínima (km/h)','velocidade_minima_kmh'),('Velocidade na saída (km/h)','velocidade_saida_kmh'),
        ('Início da frenagem (m)','inicio_frenagem_m'),('Freio aplicado ≥5% (s)','tempo_freio_aplicado_s'),
        ('Freio forte ≥80% (s)','tempo_freio_forte_s'),('Acelerador ≥99% (s)','tempo_acelerador_maximo_s')]
    comparison = pd.DataFrame([{'Medida':label, f'Volta {target}':number(f[field],2) if pd.notna(f[field]) else 'Não observado',
                                f'Volta {session.reference}':number(ref[field],2) if pd.notna(ref[field]) else 'Não observado'}
                              for label,field in fields])
    st.subheader('Características do trecho')
    st.dataframe(comparison, hide_index=True, width='stretch')
    st.caption('Início da frenagem: primeiro novo cruzamento de 5% dentro do trecho. Evento ausente não equivale a posição zero.')
    st.download_button('Baixar características deste trecho',
        session.features.loc[session.features.trecho==code].to_csv(index=False,sep=';',decimal=',').encode('utf-8-sig'),
        file_name=f'caracteristicas_{code}.csv',mime='text/csv',key='download_segment')


def sources(session, paths):
    st.subheader('Dados que sustentam esta análise')
    st.write('As quatro voltas passaram pelo filtro de voltas completas, tempo oficial positivo e ausência de interrupções detectadas. Os nove trechos cobrem o mesmo intervalo em todas elas. A interface lê as bases preparadas e confere sua compatibilidade com o manifesto da extração.')
    summary = session.summary[['volta','tempo_oficial_s']].rename(columns={'volta':'Volta','tempo_oficial_s':'Tempo oficial (s)'}).copy()
    summary['Tempo analisado (s)'] = summary.Volta.map(session.features.groupby('volta').tempo_trecho_s.sum())
    st.dataframe(summary,hide_index=True,width='stretch')
    st.subheader('Como interpretar os gráficos')
    st.markdown('''- **Delta local:** tempo do trecho menos o tempo da volta de referência no mesmo trecho.
- **Delta acumulado:** diferença desde os 5 m; cresce na perda e diminui na recuperação.
- **Pedais:** amostras nativas de 50 Hz; durações calculadas por retenção do valor anterior e recorte nas bordas.
- **Velocidade:** sinal nativo; valores nos limites interpolados. A grade de 5 m não aumenta a resolução física da distância de 10 Hz.
- **Cores das linhas:** identificam as voltas. As cores azul e vermelho do mapa identificam ganho e perda.''')
    st.info('A fase comum de parte dos canais continua sendo uma hipótese. A região de 720–755 m requer cautela. Quatro voltas de uma sessão permitem descrição dos dados, sem comprovar causalidade ou generalização.')
    with st.expander('Fontes locais e versão do método'):
        for label,path in zip(['Bases de sinais','Características por trecho','Configuração dos limites'],paths):
            st.text(f'{label}: {path}')
        st.text(f"Configuração: {session.config['versao']} · {session.config['data_definicao']}")
    st.download_button('Baixar tabela completa de características',
        session.features.to_csv(index=False,sep=';',decimal=',').encode('utf-8-sig'),
        file_name='caracteristicas_por_trecho.csv',mime='text/csv',key='download_all')
