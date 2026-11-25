"""Entrada da interface exploratória; execute com iniciar_interface.py."""
from pathlib import Path
import sys

import streamlit as st

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'src'))

from telemetria_lmu.dashboard.data import DataContractError, default_paths, load_session, signature
from telemetria_lmu.dashboard.components import header, overview, segment_detail, sidebar, sources
from telemetria_lmu.dashboard.theme import apply_theme


@st.cache_data(show_spinner='Conferindo a sessão e as tabelas…')
def cached_session(bases, tables, config, fingerprint):
    return load_session(Path(bases), Path(tables), Path(config))


def main():
    st.set_page_config(page_title='LMU | Análise de telemetria', page_icon='🏁', layout='wide')
    apply_theme()
    try:
        paths = default_paths(ROOT)
        session = cached_session(*map(str, paths), signature(paths))
    except (DataContractError, OSError, ValueError, KeyError) as exc:
        st.title('Análise de telemetria')
        st.error(f'Não foi possível abrir uma sessão consistente: {exc}')
        st.info('Execute iniciar_interface.py com --dados e --tabelas apontando para as saídas da mesma sessão. Consulte o README do projeto.')
        st.stop()
    target, segment, visible = sidebar(session)
    header(session, target)
    panorama, detalhe, metodo = st.tabs(['Panorama da sessão', 'Comparar trecho', 'Dados e método'])
    with panorama:
        overview(session, target, visible)
    with detalhe:
        segment_detail(session, target, segment)
    with metodo:
        sources(session, paths)


if __name__ == '__main__':
    main()
