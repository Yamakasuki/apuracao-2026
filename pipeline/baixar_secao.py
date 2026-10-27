"""Passo 1 (fonte principal): baixa os três arquivos nacionais do TSE usados pelo filtrar_secao.py.

Uso: python pipeline/baixar_secao.py
"""
import baixar
import config

BASE = "https://cdn.tse.jus.br/estatistica/sead/odsele/"
ARQUIVOS = [
    "votacao_secao/votacao_secao_2026_BR.zip",                 # votos por seção (~240 MB)
    "detalhe_votacao_secao/detalhe_votacao_secao_2026.zip",    # horário, aptos e comparecimento por seção (~235 MB)
    "consulta_cand/consulta_cand_2026.zip",                    # nome de urna e partido (~3 MB)
]


def main():
    pasta = config.BRUTOS / "2026" / "secao"
    pasta.mkdir(parents=True, exist_ok=True)
    for caminho in ARQUIVOS:
        baixar.baixar(BASE + caminho, pasta / caminho.rsplit("/", 1)[-1])


if __name__ == "__main__":
    main()
