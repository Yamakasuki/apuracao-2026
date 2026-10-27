"""A pausa de 25/10 mudou o resultado? Testes simples com os dados por seção dos dois turnos.

Contexto: o STF prorrogou a votação até 19h nas seções ainda abertas, a pedido da coligação de Lula,
alegando falta de transporte em Salvador, Feira de Santana e Lauro de Freitas (BA). O TSE suspendeu a
totalização das 17h07 às 19h. O argumento de quem perdeu é que os votos desse período decidiram a eleição.

Testes:
1. Quantos boletins já tinham chegado antes da pausa (a pausa atrasou a contagem de quase tudo, mas a
   ordem de chegada não muda a soma).
2. Quanto o comparecimento das três cidades subiu do 1º para o 2º turno, além da alta do resto do país.
   Isso dá um teto de "eleitores a mais" que a prorrogação pode ter trazido.
3. Cenários extremos: tirar todos esses eleitores a mais, todas as urnas das três cidades, ou a Bahia inteira.

Limite: sem o horário de encerramento de cada urna (está no boletim de urna do 2º turno, ainda não publicado),
não dá para contar exatamente quantos votos foram dados depois das 17h.

Uso: python pipeline/pausa.py
"""
import json

import analisar
import config

CIDADES = {"SALVADOR", "FEIRA DE SANTANA", "LAURO DE FREITAS"}
UF = "BA"
FIM_PAUSA = "2026-10-25T19:00:00"


def grupos(urnas, cidades, uf, a, b):
    """Soma aptos, comparecimento e margem (a - b) em: cidades, resto da UF, resto do Brasil e Brasil."""
    saida = {g: {"secoes": 0, "aptos": 0, "comparecimento": 0, "margem": 0}
             for g in ("cidades", "resto_uf", "resto_br", "brasil")}
    for u in urnas:
        if u["uf"] == uf:
            g = "cidades" if u["municipio"] in cidades else "resto_uf"
        else:
            g = "resto_br"
        for chave in (g, "brasil"):
            s = saida[chave]
            s["secoes"] += 1
            s["aptos"] += u["aptos"]
            s["comparecimento"] += u["comparecimento"]
            s["margem"] += u["votos"].get(a, 0) - u["votos"].get(b, 0)
    return saida


def taxa(g):
    return g["comparecimento"] / g["aptos"]


def excesso(t1, t2):
    """Eleitores a mais nas cidades no 2º turno, além da alta que o resto do país teve."""
    alta_cidades = taxa(t2["cidades"]) - taxa(t1["cidades"])
    alta_resto = taxa(t2["resto_br"]) - taxa(t1["resto_br"])
    return max(0, round((alta_cidades - alta_resto) * t2["cidades"]["aptos"]))


def recebidas_antes(urnas, limite):
    """Boletins (e votos) que já tinham chegado ao TSE antes do fim da pausa."""
    antes = [u for u in urnas if u["recebido"] and u["recebido"] < limite]
    return {"secoes": len(antes), "votos": sum(u["comparecimento"] for u in antes),
            "total_secoes": len(urnas), "total_votos": sum(u["comparecimento"] for u in urnas)}


def main():
    u1 = analisar.ler(config.PROCESSADOS / "secoes_2026_1t.csv")
    u2 = analisar.ler(config.PROCESSADOS / "secoes_2026_2t.csv")
    a, b = "13", "22"
    g1, g2 = grupos(u1, CIDADES, UF, a, b), grupos(u2, CIDADES, UF, a, b)
    extra = excesso(g1, g2)
    margem = g2["brasil"]["margem"]
    resultado = {
        "cidades": sorted(CIDADES), "uf": UF, "a": a, "b": b,
        "turno1": g1, "turno2": g2,
        "antes_da_pausa": recebidas_antes(u2, FIM_PAUSA),
        "excesso": extra,
        "cenarios": [
            {"id": "oficial", "margem": margem},
            {"id": "sem_excesso_todos_para_a", "margem": margem - extra},
            {"id": "excesso_todos_para_b", "margem": margem - 2 * extra},
            {"id": "sem_cidades", "margem": margem - g2["cidades"]["margem"]},
            {"id": "sem_uf", "margem": g2["resto_br"]["margem"]},
        ],
    }
    destino = config.SITE_DADOS / "2026-2t" / "pausa.json"
    destino.write_text(json.dumps(resultado, ensure_ascii=False, indent=1), encoding="utf-8")
    f = analisar.fmt
    print(f"Comparecimento nas cidades: {100 * taxa(g1['cidades']):.2f}% -> {100 * taxa(g2['cidades']):.2f}%; "
          f"resto do Brasil: {100 * taxa(g1['resto_br']):.2f}% -> {100 * taxa(g2['resto_br']):.2f}%")
    print(f"Eleitores a mais além da tendência: {f(extra)} ({100 * extra / margem:.1f}% da vantagem de Lula)")
    for c in resultado["cenarios"]:
        print(f"  {c['id']}: Lula {'+' if c['margem'] > 0 else ''}{f(c['margem'])}")
    print(f"Gravado em {destino}")


if __name__ == "__main__":
    main()
