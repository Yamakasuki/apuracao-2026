"""Configurações do pipeline: pastas, endereços do TSE e códigos do boletim de urna."""
import os
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent

# Dados brutos e intermediários ficam fora do git (ver .gitignore).
# Dá para apontar para outro disco com a variável de ambiente APURACAO_DADOS.
DADOS = Path(os.environ.get("APURACAO_DADOS", RAIZ / "dados"))
BRUTOS = DADOS / "brutos"
PROCESSADOS = DADOS / "processados"

# O que o site lê (vai para o git, por isso precisa ser pequeno).
SITE_DADOS = RAIZ / "docs" / "dados"

# Portal de Dados Abertos do TSE (é um CKAN: a API lista os arquivos de cada conjunto).
CKAN = "https://dadosabertos.tse.jus.br/api/3/action/package_show?id={}"
DATASET_BU = "resultados-{ano}-boletim-de-urna"

# Boletim de urna (bweb)
CARGO_PRESIDENTE = "1"
ATALHO_PRESIDENTE = b'"Presidente"'  # só linhas com esse texto são decodificadas (bem mais rápido)
# Candidatos cujos votos o TSE contou como "nulo técnico" (não entram nos válidos).
# 2026, 1º turno: o nº 28 (PRTB) aparece nos dados por seção, mas o resultado oficial soma os votos dele aos nulos.
NULOS_TECNICOS = {(2026, 1): {"28"}}
BRANCO = "95"
NULO = "96"
# DT_BU_RECEBIDO está no horário de Brasília (conferido: em RR chega >= 65 min depois da emissão local).
FORMATOS_DATA_HORA = ("%Y-%m-%d %H:%M:%S", "%d/%m/%Y %H:%M:%S")

# A divulgação começa às 17h de Brasília, quando fecham as últimas urnas do país.
INICIO_DIVULGACAO = "17:00"
DATAS = {
    (2022, 1): "2022-10-02",
    (2022, 2): "2022-10-30",
    (2026, 1): "2026-10-04",
    (2026, 2): "2026-10-25",
}
