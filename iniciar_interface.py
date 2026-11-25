"""Inicia a interface local de análise exploratória do LMU."""
import argparse
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dados', type=Path, help='Pasta das bases preparadas e validadas')
    parser.add_argument('--tabelas', type=Path, help='Pasta das características e do manifesto de trechos')
    parser.add_argument('--config', type=Path, help='JSON dos trechos fixos')
    parser.add_argument('--porta', type=int, default=8501)
    parser.add_argument('--sem-abrir', action='store_true', help='Não abre o navegador automaticamente')
    args = parser.parse_args()
    if not 1 <= args.porta <= 65535:
        parser.error('A porta deve estar entre 1 e 65535.')
    env = os.environ.copy()
    for name, value in [('LMU_BASES',args.dados),('LMU_TABELAS',args.tabelas),('LMU_CONFIG',args.config)]:
        if value:
            env[name] = str(value.resolve())
    try:
        import streamlit
    except ImportError:
        parser.error('Instale as dependências com python -m pip install -r requirements-interface.txt')
    result = subprocess.run([sys.executable,'-m','streamlit','run',str(ROOT/'app.py'),
        '--server.address','127.0.0.1','--server.port',str(args.porta),
        '--server.headless',str(args.sem_abrir).lower(),'--browser.gatherUsageStats','false'],
        cwd=ROOT,env=env)
    raise SystemExit(result.returncode)


if __name__ == '__main__':
    main()
