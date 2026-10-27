# Estudo: do arquivo do TSE ao gráfico

Este é o caminho completo dos dados, etapa por etapa, com o porquê de cada decisão.

```
TSE (zips, ~480 MB)
  │  baixar_secao.py        baixa com nova tentativa e anti-cache
  ▼
dados/brutos/2026/secao/
  │  filtrar_secao.py       lê os zips em streaming e junta votos + horário por seção
  ▼
dados/processados/secoes_2026_2t.csv   (499 mil linhas, uma por urna, abre no pandas)
  │  analisar.py            ordena no tempo, acumula, acha eventos
  ▼
docs/dados/2026-2t/*.json  (~550 KB no total)
  │  validar.py             confere com o placar oficial do TSE
  ▼
docs/ (site)               só lê e desenha
```

## 1. Onde estão os dados

O TSE publica tudo no [Portal de Dados Abertos](https://dadosabertos.tse.jus.br/). O portal é um **CKAN**,
então dá para listar os arquivos por API, sem abrir o navegador:

```
https://dadosabertos.tse.jus.br/api/3/action/package_search?q=2026
https://dadosabertos.tse.jus.br/api/3/action/package_show?id=resultados-2026
```

Conjuntos que importam para Presidente:

| Conjunto | Arquivo | Usei? |
|---|---|---|
| `resultados-2026` | `votacao_secao_2026_BR.zip`: votos por candidato e seção, os dois turnos | sim |
| `resultados-2026` | `detalhe_votacao_secao_2026.zip` (entrada `_BR.csv`): aptos, comparecimento, brancos, nulos e **horário de recebimento** | sim |
| `candidatos-2026` | `consulta_cand_2026.zip`: nome de urna e partido | sim |
| `resultados-2026-boletim-de-urna` | `bweb_1t_<UF>_*.zip`: o boletim de urna completo, todos os cargos (5 GB no 1º turno) | alternativa (`filtrar.py`) |

Por que não usei o bweb como fonte principal: o do 2º turno ainda não tinha sido publicado em 27/10/2026,
e o do 1º turno tem 5 GB porque traz deputados, senadores etc. Os dois arquivos nacionais têm só Presidente
e cobrem os dois turnos.

Além disso, o site de resultados do TSE tem JSONs com o placar final (usados no `validar.py`):

```
https://resultados.tse.jus.br/oficial/ele2026/6258/dados/br/br-c0001-e006258-u.json   (2º turno, Presidente)
https://resultados.tse.jus.br/oficial/ele2026/6257/dados/br/br-c0001-e006257-u.json   (1º turno)
```

## 2. Como os arquivos são

- CSV com separador `;`, codificação **latin-1** (não UTF-8: "SÃO PAULO" vira lixo se ler errado).
- Textos entre aspas, números quase sempre sem aspas: use o módulo `csv`, não `split(";")`.
- Uma linha por **seção × candidato** no arquivo de votos; uma linha por **seção** no detalhe.
- A seção é identificada por **UF + município + zona + seção**. É a chave para juntar os dois arquivos.
- Brancos são o número 95 e nulos o 96.
- `DT_RECEBIMENTO_BU_HOR_TSE` está no **horário de Brasília**. Já os horários de abertura e encerramento
  da urna (no bweb) estão no horário **local**. Conferi assim: em Roraima (UTC−4), o boletim chega ao TSE
  pelo menos 65 minutos depois de ser emitido, o que só faz sentido se forem fusos diferentes.
- O CDN do TSE às vezes entrega uma versão velha do arquivo. Colocar `?cb=<número aleatório>` no fim da URL resolve.

## 3. Processar sem descompactar

O `votacao_secao_2026_BR.csv` tem 1,6 GB descompactado. Em vez de extrair, o script abre o zip e lê linha
a linha (`zipfile.open` + `io.TextIOWrapper` + `csv.DictReader`). A memória fica baixa e não sobra lixo no disco.

O resultado é o **formato largo**: uma linha por urna, uma coluna por candidato.

```
uf,cd_municipio,municipio,zona,secao,recebido,aptos,comparecimento,abstencoes,votos_13,votos_22,brancos,nulos
SP,71072,SÃO PAULO,256,119,2026-10-25T20:46:38,341,253,88,...
```

Esse CSV é o ponto bom para explorar por conta própria:

```python
import pandas as pd
df = pd.read_csv("dados/processados/secoes_2026_2t.csv", parse_dates=["recebido"])
df.groupby(df.recebido.dt.floor("10min"))[["votos_13", "votos_22"]].sum()   # ritmo da apuração
```

## 4. Refazer a apuração

A ideia toda cabe em três linhas:

1. Cada urna vira "minutos desde as 17h" (horário em que o boletim chegou).
2. Soma os votos de todas as urnas de cada minuto.
3. Faz a soma acumulada: o valor no minuto *m* é o placar naquele momento.

Isso é feito para o Brasil e para cada UF (`analisar.linha_do_tempo`). Com os acumulados:

| Evento | Como é calculado |
|---|---|
| Virada | o sinal de `votos_A − votos_B` muda (empate não conta) |
| Maior vantagem de cada lado | máximo e mínimo de `votos_A − votos_B` |
| Maior arrancada | janela de 10 min com maior `ΔA − ΔB`; as UFs que mais contribuíram nela |
| Resultado garantido | primeiro momento em que a vantagem > eleitores aptos das urnas que ainda faltam |
| % das urnas | urnas recebidas ÷ total de urnas do local |

## 5. Conferir

`validar.py` compara com o TSE: aptos e comparecimento batem em todas as UFs e os votos de cada candidato
batem exatamente. Duas diferenças explicadas:

- **41 seções no exterior** que não foram instaladas: o TSE as conta como "totalizadas", o pipeline deixa de fora (não têm voto).
- **Nulo técnico:** no 1º turno, os 5.246 votos do nº 28 aparecem no arquivo por seção, mas o TSE os soma aos nulos.
  O `config.NULOS_TECNICOS` faz o mesmo.

E os eventos reconstruídos batem com o que foi noticiado na noite do 2º turno: Flávio Bolsonaro passou à frente
às 19:44 (13,9% das urnas; o TSE mostrou 13,65% às 19:44:50), Lula retomou às 20:23 (47,3%; TSE 47,24% às 20:24)
e o resultado ficou garantido às 21:08 (anunciado entre 21h08 e 21h10).

## 6. O que os dados mostraram

- **2º turno:** Lula 64.256.232 (51,79%) × Flávio Bolsonaro 59.826.041 (48,21%). Lula liderou no começo,
  Flávio virou às 19:44 com o Sul chegando primeiro (PR, RS, SC), e Lula virou de volta às 20:23 com o Nordeste
  (BA, CE, SE). A maior vantagem de Flávio foi de 342 mil votos às 20:07; a de Lula, 4,43 milhões no fim.
- **Pausa de quase 2 horas:** quase nenhum boletim chegou entre 17h07 e 19h03. Foi quando o STF prorrogou a votação até
  19h em algumas seções e o TSE suspendeu a totalização.
- **1º turno:** Flávio Bolsonaro 47,03% × Lula 45,16%. Flávio liderou do começo ao fim; a maior vantagem foi de
  5,57 milhões às 19:05, e depois o Nordeste foi encurtando a diferença.

## 7. O site

`docs/` é HTML, CSS e JavaScript sem build. Os gráficos usam o [ECharts](https://echarts.apache.org/).

- `js/app.js`: estado (turno, local, momento, período) e eventos da página.
- `js/graficos.js`: as opções de cada gráfico.
- `js/calculos.js`: contas pequenas (valor no momento, período, ranking), testadas com `node --test`.
- O site não calcula eventos: eles vêm prontos do Python. Assim a análise fica num lugar só.

Cores: vermelho para Lula e azul para Flávio Bolsonaro, passando no teste de daltonismo nos temas claro e escuro. A cor segue
o candidato, não a posição, então não troca quando o 1º turno inverte a ordem.
