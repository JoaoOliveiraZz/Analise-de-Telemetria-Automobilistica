# Análise de telemetria do Le Mans Ultimate

Pipeline em Python para transformar uma sessão DuckDB do simulador em bases auditadas, gráficos comparáveis por distância e tabelas de tempos e características por trecho. O estágio atual cobre pré-processamento e análise exploratória do estudo piloto.

```text
repositorio/
├── executar_pipeline.py       # Entrada única: prepara, valida e gera gráficos
├── iniciar_interface.py       # Inicia o painel local no navegador
├── app.py                     # Coordenação dos componentes da interface
├── requirements.txt           # Dependências diretas e versões
├── requirements-interface.txt # Dependências opcionais do painel
├── src/telemetria_lmu/         # Processamento, qualidade e análise
│   └── dashboard/             # Leitura auditada, figuras, componentes e tema
├── data/raw/                  # Exportações DuckDB locais, ignoradas pelo Git
├── data/processed/            # Saídas por execução, ignoradas pelo Git
└── docs/metodologia.md        # Critérios, produtos e limites do estudo piloto
```

## Execução local

Use Python 3.12 e uma exportação DuckDB do Le Mans Ultimate. Execute na raiz do repositório. No PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe executar_pipeline.py "data/raw/sessao.duckdb"
```

Coloque sua exportação em `data/raw/` ou passe o caminho do banco já existente. No Linux ou macOS, use `python3.12` para criar o ambiente e `.venv/bin/python` para executar os comandos. O banco é aberto somente para leitura.

Cada execução bem-sucedida gera uma pasta em `data/processed/` com `bases/`, `graficos/` e `manifesto.json`. O manifesto registra o hash SHA-256 da entrada, os parâmetros e as versões usadas. `--saida` permite indicar outra pasta nova. Os padrões são grade de 5 m e interrupção para intervalos superiores a 0,03 s no GPS Time.

O diagnóstico de sincronização é uma auditoria complementar, independente da geração dos gráficos de desempenho:

```powershell
.\.venv\Scripts\python.exe src/telemetria_lmu/diagnosticar_sincronizacao.py "data/raw/sessao.duckdb" --saida data/processed/diagnostico
```

O diagnóstico verifica a gravação inteira para investigar sua qualidade. A comparação de desempenho usa somente as voltas aprovadas pelo filtro. Veja os [critérios e resultados do estudo piloto](docs/metodologia.md).

As comparações seguem o [método v1](docs/metodo_comparacao.md): referência fixa, mesmo intervalo comum entre todas as voltas e delta acumulado zerado no início. Os testes de suporte espacial podem ser executados com `python -m unittest discover -s tests` no ambiente do projeto.

Os [nove trechos fixos e as definições das características](docs/trechos.md) estão na configuração `config/trechos_bahrain_outer_v1.json`, específica das voltas 8, 11, 12 e 13 desta sessão. Para extrair as tabelas de uma base já preparada:

```powershell
.\.venv\Scripts\python.exe src/telemetria_lmu/extrair_caracteristicas.py --dados data/processed/EXECUCAO/bases --saida data/processed/tabelas_trechos
```

Para incluí-las na execução completa, acrescente `--trechos config/trechos_bahrain_outer_v1.json` ao comando do pipeline. A extração rejeita seleções de voltas ou suportes espaciais incompatíveis; outras sessões exigem configuração própria. A saída contém CSV, uma cópia CSV com separadores brasileiros para Excel, Parquet e um manifesto com hashes das entradas, configuração e script. Use uma pasta de saída nova a cada execução.

O repositório versiona código e documentação. As gravações, os Parquets, os relatórios e gráficos gerados, o ambiente virtual e os materiais acadêmicos de entrega permanecem fora do versionamento.

## Interface exploratória

O protótipo usa Streamlit e Plotly, com filtros de volta e trecho, mapa de deltas do azul ao vermelho, delta acumulado, comparação dos sinais nativos de velocidade/freio/acelerador, velocidades nos limites e exportação CSV. A referência permanece fixa na volta 13 conforme o método do estudo. O painel é local, sem envio das bases a um serviço externo.

Na raiz do repositório, com o ambiente virtual ativo:

```powershell
python -m pip install -r requirements-interface.txt
python iniciar_interface.py
```

Neste workspace, que possui o ambiente virtual na pasta acima do repositório, também é possível executar a partir da raiz do workspace:

```powershell
.\.venv\Scripts\python.exe repositorio\iniciar_interface.py
```

O navegador abre em `http://127.0.0.1:8501`. Use `--sem-abrir` para iniciar somente o servidor e Ctrl+C no terminal para encerrá-lo. `--porta` permite escolher outra porta. O servidor escuta apenas no computador local.

A sessão atual é localizada automaticamente em `../dados_processados_v2` e `data/processed/trechos_bahrain_outer_v1`. Em outro checkout, informe as pastas geradas pelo pipeline, que não são distribuídas pelo Git:

```powershell
python iniciar_interface.py --dados data/processed/EXECUCAO/bases --tabelas data/processed/EXECUCAO/tabelas --config config/trechos_bahrain_outer_v1.json
```

As bases e as tabelas devem pertencer à mesma extração: o carregamento verifica os hashes de entrada do manifesto, a seleção das voltas, os limites, os tempos e os deltas. Não há geração de dados de demonstração na interface. Arquivos ausentes ou incompatíveis produzem uma mensagem de erro, sem misturar saídas antigas.

`dashboard/data.py` concentra leitura e cálculo; `charts.py`, as figuras Plotly; `components.py`, as seções e os filtros; `theme.py` e `.streamlit/config.toml`, a aparência. O arquivo principal apenas coordena essas partes. O cache é invalidado por alteração das fontes.

Na comparação detalhada, a origem do delta pode alternar entre o início do trecho e os 5 m; essa mudança visual não altera sua diferença local. As velocidades de entrada e saída correspondem aos limites operacionais do trecho. A região de 720–755 m é sombreada em T02 e acompanhada da ressalva metodológica.

Execute `python -m unittest discover -s tests` para verificar o método, a extração e a interface. Os testes do painel utilizam uma sessão sintética exclusiva dos testes e AppTest para verificar filtros, alternância de origem, gráficos e estado sem voltas selecionadas; não dependem da gravação local.
