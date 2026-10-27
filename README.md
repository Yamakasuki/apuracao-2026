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

## Votos depois das 17h no 2º turno: de onde vem o número do Brasil inteiro

Eu li os logs das três cidades da Bahia e de uma amostra. Quem leu **todas as 499.207 urnas** foi o repositório
[furtado0x/eleicoes-2026-votos-apos-17h](https://github.com/furtado0x/eleicoes-2026-votos-apos-17h). Ele usou a mesma
fonte (log, boletim de urna e assinaturas de cada urna no site do TSE) e chegou a **34.050 votos depois das 17h no Brasil**,
mais 10.865 no exterior. O site usa esse arquivo para o gráfico do Brasil inteiro.

Cruzei urna por urna com o que eu tinha lido: das 11.755 urnas, 11.742 dão exatamente o mesmo número. As diferenças
são votos às 17:00:00 em ponto (eu contava, ele não) e o oeste do Amazonas, que é UTC−5.

Por que uns falam em ~35 mil e outros em ~5 mil: dos 34.050 votos, 28.721 foram entre 17h00 e 17h05, o fim da fila de quem
já estava no local, o que acontece em toda eleição. Depois das 17h05 foram 5.329. A CNN contou 34.330 e o g1 35.521;
a diferença entre eles é de método.

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
