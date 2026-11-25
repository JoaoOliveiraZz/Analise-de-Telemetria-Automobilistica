# Metodologia e contrato dos dados

## Entrada e processamento

O estudo piloto usa uma sessão de treino no Bahrain Outer Circuit, com veículo da classe GT3. O banco contém 58 canais, 40 tipos de eventos e três tabelas de catálogo e metadados. A entrada exige `channelsList`, `GPS Time`, `Lap`, `Lap Time` e os canais de velocidade, acelerador, freio e distância.

1. Ler a exportação em modo somente leitura. Reconstruir os tempos dos canais selecionados a partir de `GPS Time`, da frequência nominal e da ordem dos registros. Eventos mantêm seus próprios timestamps.
2. Selecionar voltas com eventos de início e fim, resets de distância nas bordas, distância crescente entre eles, tempo oficial positivo e ausência de interrupções detectadas. Por padrão, um intervalo superior a 0,03 s em `GPS Time` é tratado como interrupção.
3. Estimar a posição de cada amostra na frequência nativa e projetar os sinais para uma grade de distância. Freio e acelerador mantêm as amostras de 50 Hz até receberem uma posição. A grade fica limitada ao suporte comum dos sinais de cada volta.
4. Conferir a saída e gerar gráficos por tempo e distância. Comparar cada volta apta com a de menor tempo oficial, no intervalo comum a TODAS as voltas selecionadas, com delta zerado na primeira posição compartilhada. O contrato está em [Método de comparação](metodo_comparacao.md).

## Saídas por execução

| Arquivo ou pasta | Conteúdo |
|---|---|
| `bases/amostras_nativas.parquet` | Amostras das voltas aptas com canal, unidade, frequência, índices e timestamp reconstruído. |
| `bases/voltas_validadas.parquet` | Base temporal em 100 Hz. Canais mais lentos mantêm a última observação dentro da volta; pode haver nulos antes da primeira amostra. |
| `bases/voltas_alinhadas.parquet` | Sinais alinhados por distância para as voltas aptas. |
| `bases/resumo_voltas.csv` | Segmentos detectados, incluindo os excluídos, e motivos da seleção. |
| `bases/interrupcoes_temporais.csv` | Intervalos de interrupção detectados no relógio de referência. |
| `bases/auditoria_alinhamento.csv` | Verificação de cobertura, finitude e ordem das coordenadas espaciais e temporais. |
| `bases/relatorio_qualidade.txt` | Parâmetros e resumo da seleção. |
| `graficos/` | Comparações de comandos e velocidade e, quando há pelo menos duas voltas aptas, gráficos e CSVs dos deltas e resumo de todos os pares com a referência. |
| `manifesto.json` | Identificação da entrada, versões e parâmetros da execução. |

## Resultado de referência e limites

Na gravação piloto, as voltas 8, 11, 12 e 13 passaram pelo filtro, gerando 29.926 linhas na base temporal e 2.805 na espacial. A 7 é parcial, a 9 tem tempo oficial zerado, a 10 tem uma interrupção de 0,1225 s e a 14 não possui evento de encerramento. A volta 8 acumulou 2,256 s a mais que a 13 entre 5 e 3.505 m; o intervalo comum às quatro voltas termina em 3.500 m.

A correspondência entre os dois canais de velocidade sustenta o alinhamento desse par. A fase dos demais canais amostrados continua sendo uma hipótese. A posição é estimada a partir de `Lap Dist`, a 10 Hz, portanto a grade de 5 m não garante precisão física de 5 m. As forças G mantêm os rótulos originais. O diagnóstico identificou forte relação entre `G Force Lat` com sinal invertido e a aceleração longitudinal derivada da velocidade; a convenção dos eixos ainda precisa de confirmação.

A próxima etapa é definir trechos fixos, calcular o delta por trecho e relacioná-lo às diferenças de velocidade e de comandos. O estudo de uma única sessão não sustenta conclusões causais ou generalizações sobre outros pilotos e condições.
