# Tempos e características por trecho

Configuração `bahrain_outer_v1`, fixada em 19/11/2026 em `config/trechos_bahrain_outer_v1.json`. Inclui somente as voltas completas e sem interrupções 8, 11, 12 e 13, com referência fixa 13. Os limites foram escolhidos pela inspeção dos sinais de frenagem e velocidade da referência, antes da extração das características. São uma divisão operacional deste estudo, sem correspondência assumida com setores ou números oficiais de curvas.

| Trecho | Início–fim (m) | Região |
|---|---:|---|
| T01 | 5–500 | Início e aproximação |
| T02 | 500–1000 | Frenagem e saída 1 |
| T03 | 1000–1300 | Ligação 1 |
| T04 | 1300–1650 | Frenagem e saída 2 |
| T05 | 1650–1800 | Ligação 2 |
| T06 | 1800–2150 | Transição, frenagem e saída 3 |
| T07 | 2150–2800 | Ligação 3 |
| T08 | 2800–3200 | Frenagem e saída 4 |
| T09 | 3200–3500 | Trecho final |

As quatro regiões principais com freio ≥5% na referência começam aproximadamente aos 585, 1391, 1953 e 2878 m. Os trechos correspondentes incluem aproximação e parte da saída, para comparar a sequência de condução. Esses limites são descritivos e não foram otimizados por desempenho ou por um modelo. Uma aplicação futura deve manter a configuração ou registrar explicitamente uma nova versão.

## Cálculo

O tempo em cada limite é interpolado na distância nativa. A diferença entre os tempos do fim e do início é a duração do trecho. Os limites pertencem à grade comum de 5 m; os tempos são conferidos contra essa grade. Não há extrapolação. Os segmentos cobrem continuamente 5–3500 m e sua soma reproduz o tempo do intervalo comum, que difere do tempo oficial da volta inteira.

Velocidade usa interpolação linear no tempo entre amostras nativas; a média é a integral temporal dividida pela duração do trecho. A mínima considera as amostras internas e os valores interpolados nas duas bordas. Havendo empate, registra-se a primeira ocorrência. A posição dessa mínima é interpolada em Lap Dist.

Pedais usam retenção do valor anterior (ZOH) em suas amostras nativas. Cada intervalo é recortado nas bordas temporais do trecho. Médias são ponderadas pelas durações, e os tempos de aplicação são somas desses intervalos. As bordas contíguas não contam duração duas vezes. A duração temporal não é obtida contando pontos da grade espacial. A sincronização por índice e frequência nominal mantém as hipóteses documentadas no pré-processamento.

## Campos da tabela principal

| Campos | Definição |
|---|---|
| `volta`, `trecho`, `nome_trecho`, `inicio_m`, `fim_m` | Identificação e limites fixos em metros |
| `cautela_distancia` | Marca T02, que contém a região de 720–755 m ainda sob investigação |
| `inicio_tempo_relativo_s`, `fim_tempo_relativo_s` | Tempos dos limites em relação ao evento de início da volta |
| `tempo_trecho_s` | Duração entre os limites |
| `volta_referencia`, `delta_trecho_s` | Referência 13 e diferença local de duração; positivo significa mais tempo que a referência |
| `velocidade_entrada_kmh`, `velocidade_saida_kmh` | Velocidade nos limites; não necessariamente na entrada/saída física de uma curva |
| `velocidade_minima_kmh`, `posicao_minima_m` | Menor velocidade no trecho e posição da primeira ocorrência |
| `velocidade_media_temporal_kmh` | Média ponderada pelo tempo, não pela distância |
| `freio_medio_pct`, `freio_maximo_pct` | Média temporal e maior aplicação do freio |
| `tempo_freio_aplicado_s`, `tempo_freio_forte_s` | Duração com freio ≥5% e ≥80%, respectivamente |
| `freio_ativo_na_entrada` | Freio ≥5% no início do trecho |
| `inicio_frenagem_m` | Primeiro novo cruzamento de baixo de 5% para ≥5% dentro do trecho; freio herdado da borda não conta como novo início |
| `acelerador_medio_pct`, `acelerador_maximo_pct` | Média temporal e maior aplicação do acelerador |
| `tempo_acelerador_maximo_s` | Duração com acelerador ≥99% no trecho |
| `tempo_acelerador_maximo_apos_minima_s` | Parcela dessa duração a partir do instante da mínima de velocidade |
| `primeira_aplicacao_99_sustentada_apos_minima_m` | Posição inicial da primeira aplicação ≥99% sustentada por pelo menos 0,20 s após a mínima, dentro do trecho |

Se o acelerador já está ≥99% no instante da mínima e assim permanece por 0,20 s, esse instante é o início da aplicação elegível. Não é necessariamente um novo cruzamento do limiar. Uma mínima na borda final pode impedir a identificação de aplicação sustentada. Célula vazia/NaN significa evento não observado sob a definição, não posição zero. Aplicação sustentada não implica permanência no máximo até o final do trecho.

T02 permanece incluído, sem correção artificial de distância ou tempo. A divergência local de distância/velocidade e o apoio qualitativo relatado pelo pesquisador sobre o vídeo estão descritos no método de comparação. As características descrevem associações e não demonstram causalidade.

## Produtos e verificações

- `caracteristicas_por_trecho.csv` e `.parquet`: 36 registros, uma combinação volta–trecho por linha.
- `caracteristicas_por_trecho_excel.csv`: mesmos dados, com separador ponto e vírgula, decimal vírgula e UTF-8 com BOM.
- `tempos_por_trecho.csv` e `deltas_por_trecho.csv`: nove linhas, com as quatro voltas em colunas.
- `limites_trechos.csv`: limites e nomes.
- `resumo_voltas_trechos.csv`: total no intervalo comum, tempo oficial e delta total.
- `manifesto_trechos.json`: configuração e hashes SHA-256 para rastreabilidade.

Verificações: cobertura contínua dos limites; mesma seleção nas bases nativas, espaciais e no resumo de qualidade; reprodução dos tempos nas bordas; soma dos tempos dos trechos igual ao total comum; ausência de extrapolação e pedais no intervalo 0–100%. Os testes automatizados verificam recorte e aditividade da integração, rejeição de extrapolação, distinção entre pulso e aplicação sustentada, ponderação temporal da velocidade e rejeição de lacunas na configuração.

Os 36 registros continuam derivados de apenas quatro voltas de uma sessão. Não representam 36 observações independentes para avaliação de aprendizado de máquina. Tempos e distâncias apresentados com casas decimais resultam de interpolação; essa precisão numérica não comprova a mesma exatidão física.
