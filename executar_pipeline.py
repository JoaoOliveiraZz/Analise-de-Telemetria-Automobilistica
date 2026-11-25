"""Executa preparação, validação e análise exploratória de uma sessão LMU."""
import argparse
from datetime import datetime, timezone
import hashlib
from importlib.metadata import version
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
SRC = ROOT / 'src' / 'telemetria_lmu'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('banco', type=Path, help='Arquivo DuckDB exportado pelo LMU')
    parser.add_argument('--saida', type=Path, help='Pasta nova para os resultados')
    parser.add_argument('--passo-m', type=float, default=5)
    parser.add_argument('--limite-gap-s', type=float, default=.03)
    parser.add_argument('--trechos', type=Path, help='JSON de limites fixos para extrair tempos e características')
    args = parser.parse_args()
    banco = args.banco.resolve()
    if not banco.is_file():
        parser.error(f'Banco não encontrado: {banco}')
    if args.trechos and not args.trechos.is_file():
        parser.error(f'Configuração não encontrada: {args.trechos}')
    agora = datetime.now(timezone.utc)
    saida = (args.saida or ROOT / 'data' / 'processed' / agora.strftime('%Y%m%dT%H%M%S%fZ')).resolve()
    if saida.exists():
        parser.error(f'Escolha uma pasta nova: {saida}')
    with banco.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    bases, graficos = saida / 'bases', saida / 'graficos'

    def etapa(script, *parametros):
        subprocess.run([sys.executable, str(SRC / script), *map(str, parametros)], check=True)

    etapa('prepare_telemetry.py', banco, '--saida', bases,
          '--passo-m', args.passo_m, '--limite-gap-s', args.limite_gap_s)
    etapa('validar_alinhamento.py', bases)
    etapa('gerar_graficos_exploratorios.py', '--dados', bases, '--saida', graficos)
    if args.trechos:
        etapa('extrair_caracteristicas.py', '--dados', bases, '--config', args.trechos,
              '--saida', saida / 'tabelas')
    manifesto = {
        'inicio_utc': agora.isoformat(), 'banco': banco.name, 'sha256_banco': digest,
        'parametros': {'passo_m': args.passo_m, 'limite_gap_s': args.limite_gap_s},
        'python': sys.version.split()[0],
        'dependencias': {nome: version(nome) for nome in ('duckdb', 'pandas', 'numpy', 'pyarrow', 'matplotlib')},
        'bases': 'bases', 'graficos': 'graficos',
    }
    if args.trechos:
        manifesto['tabelas'] = 'tabelas'
        manifesto['sha256_config_trechos'] = hashlib.sha256(args.trechos.read_bytes()).hexdigest()
    (saida / 'manifesto.json').write_text(json.dumps(manifesto, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(f'Pipeline concluído: {saida}')


if __name__ == '__main__':
    main()
