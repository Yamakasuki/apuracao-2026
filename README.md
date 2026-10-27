# Apuração 2026 · Presidente

Peguei os dados abertos do TSE da eleição para Presidente de 2026 e refiz a apuração minuto a minuto.
O site mostra quem liderou em cada momento, quando teve virada, o maior pico de vantagem de cada lado,
em que horário cada um mais cresceu e de quais estados e cidades vieram os votos.

A ideia principal foi estudar o caminho inteiro dos dados: de onde baixar, como processar arquivos
grandes sem descompactar tudo e como transformar isso numa visualização. O passo a passo detalhado
está no [ESTUDO.md](ESTUDO.md).

## De onde vêm os dados

Tudo vem do [Portal de Dados Abertos do TSE](https://dadosabertos.tse.jus.br/dataset/resultados-2026), conjunto "Resultados 2026":

| Arquivo | O que tem | Tamanho |
|---|---|---|
| [votacao_secao_2026_BR.zip](https://cdn.tse.jus.br/estatistica/sead/odsele/votacao_secao/votacao_secao_2026_BR.zip) | votos de cada candidato a Presidente em cada seção, nos dois turnos | ~240 MB |
| [detalhe_votacao_secao_2026.zip](https://cdn.tse.jus.br/estatistica/sead/odsele/detalhe_votacao_secao/detalhe_votacao_secao_2026.zip) | por seção: aptos, comparecimento, brancos, nulos e **o horário em que o boletim chegou ao TSE** | ~235 MB |

O horário de chegada de cada boletim (`DT_RECEBIMENTO_BU_HOR_TSE`) é o que permite refazer a apuração:
ordenando as seções por esse horário e somando os votos, dá para ver o placar em qualquer momento da noite.

Também existe o [boletim de urna (bweb)](https://dadosabertos.tse.jus.br/dataset/resultados-2026-boletim-de-urna),
que junta voto e horário num arquivo só por estado. O do 1º turno tem 5 GB; o do 2º turno ainda não tinha
sido publicado quando fiz isso. O pipeline também lê esse formato (`filtrar.py`).

O mapa usa a [malha de estados do IBGE](https://servicodados.ibge.gov.br/api/docs/malhas?versao=3).

## Como rodar

Só precisa de Python 3 (sem instalar nada) e uns 2 GB livres. Os dados brutos ficam em `dados/`, que não vai para o git.

```bash
python pipeline/rodar.py 2     # baixa, processa e gera os dados do 2º turno
python pipeline/rodar.py 1     # o mesmo para o 1º turno
python -m http.server -d docs 8000
```

Depois é só abrir http://localhost:8000.

Cada etapa também roda separada:

```bash
python pipeline/baixar_secao.py          # 1. baixa os dois zips do TSE
python pipeline/filtrar_secao.py 2       # 2. junta votos + horário, uma linha por seção
python pipeline/analisar.py 2026 2       # 3. linha do tempo, eventos e resumos -> docs/dados/
python pipeline/validar.py 2026 2        # 4. confere os totais com o resultado oficial
```

Testes: `python -m unittest discover -s tests` e `node --test tests/calculos.test.mjs`.

## Como está organizado

```
pipeline/   scripts em Python (só biblioteca padrão)
tests/      testes do pipeline e das contas do site
docs/       o site (HTML, CSS e JS) e os JSON que ele lê; é a pasta publicada no GitHub Pages
dados/      arquivos baixados e intermediários (fica só na máquina)
```

Para publicar: Settings → Pages → Deploy from a branch → `main` / `docs`.
