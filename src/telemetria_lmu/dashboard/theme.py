"""Identidade visual compartilhada pelo painel e pelos gráficos."""
import streamlit as st

COLORS = {8: '#38bdf8', 11: '#c4a4ff', 12: '#34d399', 13: '#fbbf24'}
BACKGROUND = '#0b1120'
PANEL = '#111b2e'
TEXT = '#e8eef8'
MUTED = '#9caec7'
PLOT_CONFIG = {'displaylogo': False, 'scrollZoom': False,
               'modeBarButtonsToRemove': ['lasso2d', 'select2d'],
               'toImageButtonOptions': {'format': 'png', 'scale': 2}}


def apply_theme():
    st.markdown('''<style>
    .stApp { background: #0b1120; color: #e8eef8; }
    [data-testid="stHeader"] { background: rgba(11,17,32,.94); }
    [data-testid="stSidebar"] { background: #10192a; border-right: 1px solid #243249; }
    .block-container { padding-top: 4rem; padding-bottom: 3rem; max-width: 1600px; }
    h1, h2, h3 { letter-spacing: -.035em; }
    h1 { font-weight: 700; font-size: 2.3rem !important; }
    h2 { font-size: 1.35rem !important; }
    h3 { font-size: 1.05rem !important; }
    [data-testid="stMetric"] { background: #111b2e; border: 1px solid #26344c;
      border-radius: 12px; padding: 1.05rem 1.15rem; }
    [data-testid="stMetricValue"] { font-size: 1.65rem; font-variant-numeric: tabular-nums; }
    [data-testid="stMetricLabel"] { color: #a7b8cf; }
    [data-testid="stVerticalBlockBorderWrapper"] > div { border-radius: 12px; }
    .eyebrow { color: #7dd3fc; font-size: .74rem; letter-spacing: .16em; font-weight: 650; }
    .sidebar-brand { color: #f8fafc; font-size: 1.6rem; font-weight: 800; letter-spacing: -.06em; }
    .sidebar-brand span { color: #38bdf8; }
    .session-chip { color: #b7c6db; font-size: .82rem; margin: .3rem 0 1.4rem; }
    .stCaption { color: #a7b8cf; }
    button[data-baseweb="tab"] { font-size: .94rem; }
    </style>''', unsafe_allow_html=True)
