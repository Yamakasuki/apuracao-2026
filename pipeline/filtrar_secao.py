"""Passo 2 (fonte principal): junta dois arquivos nacionais do TSE numa linha por urna.

- votacao_secao_2026_BR.csv: votos de cada candidato a Presidente em cada seção (os dois turnos).
- detalhe_votacao_secao_2026_BR.csv: por seção, aptos, comparecimento e o horário em que o
  boletim chegou ao TSE (DT_RECEBIMENTO_BU_HOR_TSE, horário de Brasília).

A saída tem o mesmo formato do filtrar.py (bweb), então o analisar.py serve para as duas fontes.

Uso: python pipeline/filtrar_secao.py 2
"""
import csv
import io
import json
import sys
import zipfile

import config
import filtrar

ARQ_VOTOS = "votacao_secao_2026_BR.zip"
ARQ_DETALHE = "detalhe_votacao_secao_2026.zip"
ARQ_CANDIDATOS = "consulta_cand_2026.zip"


def ler_csv(caminho_zip, nome):
    """Linhas (dicts) de um CSV latin-1 com ';' dentro de um zip, lidas em streaming."""
    with zipfile.ZipFile(caminho_zip) as z, z.open(nome) as f:
        yield from csv.DictReader(io.TextIOWrapper(f, encoding="latin-1", newline=""), delimiter=";")


def chave(l):
    return (l["SG_UF"], l["CD_MUNICIPIO"], l["NR_ZONA"], l["NR_SECAO"])


def urnas(arq_votos, arq_detalhe, turno):
    turno = str(turno)
    secoes = {}
    for l in ler_csv(arq_detalhe, "detalhe_votacao_secao_2026_BR.csv"):
        if l["NR_TURNO"] != turno or l["ST_SECAO_INSTALADA"] == "Não":
            continue
        secoes[chave(l)] = {
            "uf": l["SG_UF"], "cd_municipio": l["CD_MUNICIPIO"], "municipio": l["NM_MUNICIPIO"],
            "zona": l["NR_ZONA"], "secao": l["NR_SECAO"],
            "recebido": filtrar.horario(l["DT_RECEBIMENTO_BU_HOR_TSE"]),
            "aptos": int(l["QT_APTOS"]), "comparecimento": int(l["QT_COMPARECIMENTO"]),
            "abstencoes": int(l["QT_ABSTENCOES"]), "votos": {},
        }
    sem_detalhe = 0
    for l in ler_csv(arq_votos, "votacao_secao_2026_BR.csv"):
        if l["NR_TURNO"] != turno:
            continue
        urna = secoes.get(chave(l))
        if urna is None:
            sem_detalhe += 1
            continue
        v = filtrar.votavel(l["NR_VOTAVEL"])
        urna["votos"][v] = urna["votos"].get(v, 0) + int(l["QT_VOTOS"])
    if sem_detalhe:
        print(f"aviso: {sem_detalhe} linhas de voto sem seção correspondente no detalhe")
    return list(secoes.values())


def candidatos(arq, turno):
    """Nome de urna e partido de cada candidato a Presidente no turno."""
    saida = {}
    for l in ler_csv(arq, "consulta_cand_2026_BR.csv"):
        if l["NR_TURNO"] == str(turno) and l["DS_CARGO"].upper() == "PRESIDENTE":
            # candidato substituído aparece duas vezes; fica o que foi para a urna
            if l["NR_CANDIDATO"] not in saida or not l["DS_SIT_TOT_TURNO"].startswith("#"):
                saida[l["NR_CANDIDATO"]] = {"nome": l["NM_URNA_CANDIDATO"], "partido": l["SG_PARTIDO"]}
    return saida


def main(turno):
    pasta = config.BRUTOS / "2026" / "secao"
    lista = urnas(pasta / ARQ_VOTOS, pasta / ARQ_DETALHE, turno)
    cand = candidatos(pasta / ARQ_CANDIDATOS, turno)
    for nr in config.NULOS_TECNICOS.get((2026, turno), ()):
        for u in lista:
            if nr in u["votos"]:
                u["votos"]["nulos"] = u["votos"].get("nulos", 0) + u["votos"].pop(nr)
    total = {}
    for u in lista:
        for v, q in u["votos"].items():
            total[v] = total.get(v, 0) + q
    cand = {nr: c for nr, c in cand.items() if total.get(nr)}
    votaveis = sorted(cand, key=lambda nr: -total[nr]) + ["brancos", "nulos"]
    destino = config.PROCESSADOS / f"secoes_2026_{turno}t.csv"
    filtrar.gravar(lista, destino, votaveis)
    (config.PROCESSADOS / f"candidatos_2026_{turno}t.json").write_text(
        json.dumps(cand, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{len(lista):,} urnas gravadas em {destino}")


if __name__ == "__main__":
    main(int(sys.argv[1]))
