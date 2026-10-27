"""Passo 4: confere os totais do pipeline com o placar final do site de resultados do TSE.

O arquivo oficial (br-e<eleição>-ab.json) traz por UF as seções totalizadas, o eleitorado das
seções instaladas e o comparecimento. Se o pipeline juntou tudo certo, os números batem.

Uso: python pipeline/validar.py 2026 2
"""
import json
import sys
import urllib.request

import config

ELEICOES = {(2026, 1): "6257", (2026, 2): "6258"}
URL = "https://resultados.tse.jus.br/oficial/ele{ano}/{e}/dados/br/br-e{e:0>6}-ab.json"


def oficial(ano, turno):
    e = ELEICOES[(ano, turno)]
    with urllib.request.urlopen(URL.format(ano=ano, e=e), timeout=60) as r:
        dados = json.load(r)
    saida = {}
    for a in dados["abr"]:
        saida[a["cdabr"].upper()] = {
            "secoes": int(a["s"]["st"]), "aptos": int(a["e"]["esi"]), "comparecimento": int(a["e"]["c"]),
        }
    return saida


def votos_oficiais(ano, turno):
    """{número: votos} do arquivo final de Presidente (c0001) do Brasil."""
    e = ELEICOES[(ano, turno)]
    url = f"https://resultados.tse.jus.br/oficial/ele{ano}/{e}/dados/br/br-c0001-e{e:0>6}-u.json"
    with urllib.request.urlopen(url, timeout=60) as r:
        dados = json.load(r)
    return {c["n"]: int(c["vap"]) for agr in dados["carg"][0]["agr"] for par in agr["par"] for c in par["cand"]}


def comparar(nosso, deles):
    """Lista de (local, campo, nosso, oficial) que não batem."""
    diferencas = []
    for local, oficial_local in deles.items():
        for campo, valor in oficial_local.items():
            meu = nosso.get(local, {}).get(campo)
            if meu != valor:
                diferencas.append((local, campo, meu, valor))
    return diferencas


def main(ano, turno):
    resumo = json.loads((config.SITE_DADOS / f"{ano}-{turno}t" / "resumo.json").read_text(encoding="utf-8"))
    diferencas = comparar(resumo["totais"], oficial(ano, turno))
    if not diferencas:
        print(f"OK: urnas, aptos e comparecimento batem com o TSE nas {len(resumo['totais'])} abrangências.")
    for local, campo, meu, valor in diferencas:
        print(f"  {local} {campo}: pipeline {meu}, TSE {valor} (diferença {(meu or 0) - valor:+})")
    if diferencas:
        print("  (o TSE conta como totalizadas as seções não instaladas, que não têm voto; o pipeline as deixa de fora)")
    oficiais = votos_oficiais(ano, turno)
    for c in resumo["candidatos"]:
        ok = "ok" if oficiais.get(c["numero"]) == c["votos"] else f"DIFERENTE (TSE {oficiais.get(c['numero'])})"
        print(f"  {c['nome']}: {c['votos']:,} votos -> {ok}".replace(",", "."))


if __name__ == "__main__":
    main(int(sys.argv[1]), int(sys.argv[2]))
