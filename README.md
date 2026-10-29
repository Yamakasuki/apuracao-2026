# Apuração 2026 · Presidente

Peguei os dados abertos do TSE da eleição para Presidente de 2026 e refiz a apuração minuto a minuto.
O site mostra quem liderou em cada momento, quando teve virada, o maior pico de vantagem de cada lado,
de quais estados e cidades vieram os votos e quantas pessoas votaram depois das 17h no 2º turno,
quando a votação foi prorrogada.

**Site:** https://yamakasuki.github.io/apuracao-2026/

## Como foi feito, passo a passo

1. **Achar os dados.** O TSE publica tudo no [Portal de Dados Abertos](https://dadosabertos.tse.jus.br/dataset/resultados-2026).
   O portal tem uma API (CKAN) que lista os arquivos de cada conjunto, então dá para achar tudo sem clicar em nada.
2. **Escolher os arquivos.** Usei três:
   - [votacao_secao_2026_BR.zip](https://cdn.tse.jus.br/estatistica/sead/odsele/votacao_secao/votacao_secao_2026_BR.zip): votos de cada candidato em cada seção, nos dois turnos (~240 MB);
   - [detalhe_votacao_secao_2026.zip](https://cdn.tse.jus.br/estatistica/sead/odsele/detalhe_votacao_secao/detalhe_votacao_secao_2026.zip): por seção, aptos, comparecimento e **o horário em que o boletim chegou ao TSE** (~235 MB);
   - [consulta_cand_2026.zip](https://cdn.tse.jus.br/estatistica/sead/odsele/consulta_cand/consulta_cand_2026.zip): nome de urna e partido.
3. **Baixar** (`baixar_secao.py`). O CDN do TSE às vezes entrega uma versão velha do arquivo; um `?cb=<número aleatório>` no fim da URL resolve.
4. **Juntar votos e horário** (`filtrar_secao.py`). Os CSVs são latin-1 com `;`. Leio os zips em streaming, sem descompactar,
   e junto os dois arquivos pela chave estado + município + zona + seção. Sai um CSV com uma linha por urna (499.207 linhas).
5. **Refazer a apuração** (`analisar.py`). Ordeno as urnas pelo horário de chegada do boletim, somo os votos minuto a minuto
   e, com esses acumulados, acho as viradas, a maior vantagem de cada lado, a janela de 10 minutos em que cada um mais cresceu
   e o momento em que o resultado ficou garantido. Tudo vira JSON pequeno em `docs/dados/`.
6. **Conferir com o resultado oficial** (`validar.py`). Os votos de todos os candidatos, os aptos e o comparecimento batem com o TSE.
   As viradas e o horário da definição batem com o que foi noticiado na noite.
7. **Medir os votos depois das 17h** (`logs_urna.py` e `pausa.py`). Cada urna tem um log com o horário de cada voto,
   publicado em `resultados.tse.jus.br/oficial/ele2026/arquivo-urna/3221/`. Baixei os logs de todas as 6.755 urnas de
   Salvador, Feira de Santana e Lauro de Freitas (onde a prorrogação foi pedida) e de uma amostra de 5 mil urnas do resto do país.
8. **Fazer o site** (`docs/`). HTML, CSS e JavaScript sem build, com gráficos do [ECharts](https://echarts.apache.org/).
   O site só lê os JSON e desenha; a análise fica toda no Python.

O detalhe de cada etapa, as armadilhas dos arquivos e as contas estão no [ESTUDO.md](ESTUDO.md).

## Votos depois das 17h no 2º turno

**Resultado:** em todas as urnas do país, **34.330 pessoas votaram depois das 17h**. Só **7.352 urnas** (1,48%) ficaram
abertas além das 17h45, ou seja, usaram de fato a prorrogação, e nelas entraram **5.052 votos** depois das 17h.
A vantagem de Lula foi de 4.430.191 votos. Mesmo pegando os 34.330 e passando todos de Lula para Flávio Bolsonaro,
Lula venceria por 4.361.531.

| Recorte | Urnas | Votos depois das 17h | % da vantagem de Lula |
|---|---:|---:|---:|
| Todas as urnas | 497.882 | 34.330 | 0,77% |
| Urnas que fecharam depois das 17h15 | 9.079 | 5.621 | 0,13% |
| Urnas que fecharam depois das 17h30 | 7.606 | 5.139 | 0,12% |
| Urnas que fecharam depois das 17h45 | 7.352 | 5.052 | 0,11% |

A diferença entre "35 mil" e "5 mil", que aparece nas notícias, é só de recorte: quase todo voto depois das 17h é de quem
já estava na fila, o que acontece em toda eleição, e essas urnas fecham poucos minutos depois.

### De onde vem o número do Brasil inteiro

Eu li os logs de todas as 6.755 urnas de Salvador, Feira de Santana e Lauro de Freitas (onde a prorrogação foi pedida) e
de uma amostra de 5 mil urnas do resto do país. O número do país inteiro vem do repositório
[apolinario/urnas-tardias](https://github.com/apolinario/urnas-tardias), que leu o log de todas as urnas com a mesma
fonte (o site de resultados do TSE) e o mesmo método. Antes de usar, cruzei urna por urna: nas 11.755 urnas que eu li,
**o número de votos depois das 17h e a classificação de urna estendida batem em todas**. Nas três cidades, os dois dão 1.994.

### Decisões de método (e quanto cada uma muda)

Nenhuma delas chega perto de mudar a conclusão. A maior diferença possível entre elas é de algumas centenas de votos,
contra uma vantagem de 4,4 milhões.

- **Horário do voto, não da chegada do boletim.** Para a linha do tempo da apuração uso a hora em que o boletim chegou
  ao TSE. Para "votou depois das 17h" uso a hora de cada voto no log da urna. São coisas diferentes: a pausa de 17h07 às
  19h foi na contagem, não na votação.
- **Fuso horário.** O log registra o relógio local da urna. No começo eu usei um fuso fixo por estado, e errei três urnas:
  Fernando de Noronha (UTC−2) e duas do oeste do Amazonas (UTC−5). Passei a descobrir o fuso de cada município pela hora em
  que as urnas abriram, porque toda urna abre às 8h de Brasília. Com isso a diferença para o apolinario zerou.
- **17:00:00 em ponto conta.** Conto votos às 17:00:00 ou depois. Contando só depois de 17:00:00, o total cai para 34.050
  (umas 280 a menos). É o que explica parte da diferença entre as contagens publicadas (34.050, 34.330, 35.521).
- **O que é "urna estendida".** Uma urna que fecha às 17h03 só atendeu a fila. Considero que usou a prorrogação se fechou
  depois das 17h45. Mudando o corte para 17h15 ou 17h30, o número vai de 5.052 para no máximo 5.621.
- **Exterior fora.** No exterior a votação vai até as 17h do horário local de cada cidade, que nas Américas cai depois das
  17h de Brasília sem ter nada a ver com a prorrogação.
- **Urnas trocadas entre os turnos.** Em cerca de 1% das urnas o log não traz o 1º turno (a urna foi substituída); elas
  ficam fora só da comparação entre turnos.
- **Seções não instaladas e nulo técnico.** O TSE conta 41 seções do exterior que não foram instaladas como "totalizadas";
  eu deixo de fora (não têm voto). No 1º turno, os 5.246 votos do nº 28 são nulos técnicos, como no resultado oficial.

## Como rodar

Só precisa de Python 3 (sem instalar nada) e uns 2 GB livres. Os dados brutos ficam em `dados/`, que não vai para o git.

```bash
python pipeline/rodar.py 2          # baixa, junta, analisa e confere o 2º turno
python pipeline/rodar.py 1          # o mesmo para o 1º turno
python pipeline/logs_urna.py        # logs das urnas (~1,6 GB, uns 15 min)
python pipeline/pausa.py            # análise da prorrogação
python -m http.server -d docs 8000  # abre em http://localhost:8000
```

Testes: `python -m unittest discover -s tests` e `node --test tests/calculos.test.mjs`.

## Como está organizado

```
pipeline/   scripts em Python (só biblioteca padrão)
tests/      testes do pipeline e das contas do site
docs/       o site e os JSON que ele lê (é a pasta publicada no GitHub Pages)
dados/      arquivos baixados e intermediários (fica só na máquina)
```
