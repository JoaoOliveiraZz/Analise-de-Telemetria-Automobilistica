# Método de comparação do estudo piloto

Versão 1 · fixado em 19/11/2026.

## Escopo e pergunta

Descrever onde as voltas 8, 11 e 12 acumulam diferenças de tempo em relação à volta 13 e quais diferenças de velocidade e comandos coincidem com esses intervalos. A análise é retrospectiva, de um piloto em uma sessão. A escolha da volta mais rápida como referência não a torna uma trajetória ideal em todos os trechos.

## Seleção e referência

- Incluir somente voltas completas, com tempo oficial positivo e sem interrupções detectadas pelo pré-processamento v2. Resultado nesta sessão: 8, 11, 12 e 13.
- Referência fixa para esta exploração: volta 13, escolhida pelo menor tempo oficial positivo. Comparar as outras três com ela, sem trocar a referência conforme o trecho.
- Excluir da análise de desempenho 7 e 14 (parciais), 9 (tempo zerado) e 10 (interrupção). Conservar as ocorrências no resumo de qualidade.
- Usar a interseção da grade espacial de TODAS as voltas selecionadas. Neste banco: 700 pontos de 5 a 3.500 m, com passo de 5 m. Todos os pares e gráficos gerais passam a usar esse intervalo.

## Tempos e delta

Seja t_v(d) o tempo relativo ao evento de início da volta v ao atingir a distância d, estimado por interpolação das amostras nativas de Lap Dist. Para cada volta, definir o tempo acumulado do intervalo comum como T_v(d) = t_v(d) - t_v(5).

O delta é D_v(d) = T_v(d) - T_13(d). Assim, todas as curvas começam em zero aos 5 m.

- Delta positivo: a volta analisada gastou mais tempo que a referência desde o início do intervalo.
- Delta negativo: gastou menos tempo.
- Delta crescente entre dois pontos: perda naquele trecho.
- Delta decrescente: recuperação naquele trecho, mesmo que a volta ainda esteja atrás no acumulado.
- Diferença de um trecho [a, b]: D_v(b) - D_v(a), equivalente à diferença entre os tempos gastos por cada volta nesse mesmo trecho.

O recorte de um gráfico conserva a origem em 5 m. Seu título informa a variação local para não confundir a altura da curva com a perda no recorte. Não integrar valores de delta nem somá-los ponto a ponto. A soma dos deltas de trechos contíguos deve reproduzir o delta do intervalo total. O tempo oficial da volta continua sendo apresentado separadamente: o intervalo de 5 a 3.500 m não inclui as extremidades completas da volta.

## Sinais e medidas descritivas

Utilizar velocidade em km/h, acelerador e freio em porcentagem. Manter distância em metros e tempo em segundos. Atribuir a posição a cada sinal na sua frequência nativa antes de interpolar na grade. Não aplicar DTW, normalização ou suavização para alterar a correspondência espacial dos sinais.

Para as tabelas por trecho, fixar os limites antes do cálculo e usar as mesmas definições para todas as voltas:

- Velocidade de entrada e saída: valores interpolados nos limites fixos do trecho; mínima: menor valor no trecho, com sua posição.
- Freio aplicado: valor maior ou igual a 5%. Freio forte: maior ou igual a 80%.
- Acelerador próximo do máximo: valor maior ou igual a 99%. Diferenciar o primeiro cruzamento de uma aplicação sustentada; não tratar um pulso isolado como retomada definitiva.
- Duração de comandos: integrar os intervalos nativos, por retenção do valor à esquerda, recortando exatamente nos tempos dos limites espaciais. Não contar linhas da grade de 5 m como duração temporal. Não somar um intervalo que ultrapasse a borda do trecho.

Os limiares são definições operacionais, não limites físicos universais. Diferenças de poucos metros e cruzamentos isolados precisam de verificação nos sinais nativos. A definição e a extração foram implementadas em 19/11/2026: são nove trechos contíguos e 36 registros. Os limites, os cálculos e o dicionário das características estão em [trechos.md](trechos.md). A aplicação sustentada exige pelo menos 0,20 s consecutivos acima ou iguais a 99%, dentro do trecho e após seu mínimo de velocidade; isso não significa aceleração definitiva até a curva seguinte.

## Distância e evidência do vídeo

A distância é uma coordenada do simulador. Ela não foi comprovada como equivalente à trajetória efetivamente percorrida nem como uma coordenada física idêntica entre todas as linhas de condução. Divergência entre incremento de Lap Dist e integral de Ground Speed é um indicador de coerência a investigar, não prova isolada de falha. Total Dist pode compartilhar a origem de Lap Dist e não é uma verificação independente.

Entre 720 e 755 m, o delta da volta 12 diminui aproximadamente 0,135 s apesar de a velocidade registrada permanecer inferior. Há irregularidades entre avanço de distância e integral da velocidade nos registros nativos. O pesquisador relata que a recuperação é coerente com a inspeção do vídeo; o vídeo não foi medido nem inspecionado pelo código ou pelo assistente. Isso fornece apoio qualitativo, sem validar o valor exato ou confirmar uma trajetória mais curta.

Manter o trecho nas comparações, identificado como região de interpretação cautelosa. Não classificar automaticamente a queda como erro, não substituí-la por velocidade integrada e não corrigir o relógio. Confrontar eventos visuais em pontos físicos fixos da pista, registrando timestamps, taxa de quadros e incerteza da leitura quando o vídeo estiver disponível. Não apresentar esse trecho como exemplo de mecanismo causal comprovado.

## Limites e critérios de aceitação

A fase comum dos canais sem timestamps individuais continua sendo uma hipótese. A grade interpolada de 5 m não aumenta a resolução da distância nativa de 10 Hz. As forças G não fazem parte das métricas centrais enquanto seus eixos não forem confirmados.

A implementação deve rejeitar distâncias duplicadas, tempos não finitos ou não crescentes e grade comum descontínua. O delta deve começar em zero, reproduzir a diferença entre os tempos do intervalo e ser aditivo para trechos contíguos. Os três pares devem ter o mesmo início, fim e quantidade de pontos.

Os resultados descrevem associações nesta sessão. Não atribuir ganhos a um único comando, não realizar testes inferenciais tratando pontos vizinhos como independentes e não afirmar generalização com quatro voltas. O objetivo do módulo posterior de aprendizado de máquina será uma demonstração exploratória, cuja definição de alvo e avaliação precisa ser separada desta referência descritiva.

## Reprodução

Na raiz do repositório, usando uma saída do pipeline em `data/processed/EXECUCAO/bases`:

```powershell
.\.venv\Scripts\python.exe src/telemetria_lmu/gerar_graficos_exploratorios.py --dados data/processed/EXECUCAO/bases --saida data/processed/comparacao_metodo_v1
```

São gerados os três pares, seus gráficos e CSVs, além de `resumo_comparacoes.csv`. Na execução desta sessão, os arquivos antigos que terminavam aos 3.505 m permanecem históricos e não devem ser misturados com as novas comparações padronizadas.
