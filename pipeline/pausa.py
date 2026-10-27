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
import csv
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


def resumo_logs(linhas):
    """Soma o que os logs das urnas contaram, por grupo (cidades da prorrogação e amostra do Brasil).

    O 1º turno serve de base: comparamos só urnas cujo log tem os dois turnos, e a diferença de votos
    depois do fechamento entre os turnos é o que a prorrogação (e a fila) acrescentou.
    """
    grupos = {}
    for l in linhas:
        g = grupos.setdefault(l["grupo"], {
            "urnas": 0, "urnas_comparaveis": 0, "votos_2t": 0, "depois_2t": 0,
            "votos_1t": 0, "depois_1t": 0, "depois_2t_comparaveis": 0, "votos_2t_comparaveis": 0,
            "urnas_depois_18h_2t": 0, "urnas_depois_18h_1t": 0, "ultimo_2t": "", "faixas_1t": None, "faixas_2t": None,
        })
        g["urnas"] += 1
        g["votos_2t"] += int(l["votos_2t"])
        g["depois_2t"] += int(l["depois_2t"])
        g["ultimo_2t"] = max(g["ultimo_2t"], l["ultimo_2t"] or "")
        if int(l["votos_1t"]) == 0:
            continue  # urna trocada entre os turnos: o log não tem o 1º turno para comparar
        g["urnas_comparaveis"] += 1
        g["votos_1t"] += int(l["votos_1t"])
        g["depois_1t"] += int(l["depois_1t"])
        g["votos_2t_comparaveis"] += int(l["votos_2t"])
        g["depois_2t_comparaveis"] += int(l["depois_2t"])
        for t in ("1t", "2t"):
            faixas = [int(x) for x in l[f"faixas_{t}"].split()]
            g[f"faixas_{t}"] = [a + b for a, b in zip(g[f"faixas_{t}"] or [0] * len(faixas), faixas)]
            if sum(faixas[6:]):
                g[f"urnas_depois_18h_{t}"] += 1
    for g in grupos.values():
        g["a_mais"] = g["depois_2t_comparaveis"] - g["depois_1t"]
    return grupos


def main():
    u1 = analisar.ler(config.PROCESSADOS / "secoes_2026_1t.csv")
    u2 = analisar.ler(config.PROCESSADOS / "secoes_2026_2t.csv")
    f = analisar.fmt
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
    arq_logs = config.PROCESSADOS / "logs_2026_2t.csv"
    if arq_logs.exists():
        with open(arq_logs, encoding="utf-8", newline="") as arq:
            logs = resumo_logs(csv.DictReader(arq))
        amostra = logs["amostra_brasil"]
        # extrapola a amostra para o resto do país (proporção de votos depois do fechamento em cada turno)
        votos_resto = g2["brasil"]["comparecimento"] - g2["cidades"]["comparecimento"]
        taxa_2t = amostra["depois_2t_comparaveis"] / amostra["votos_2t_comparaveis"]
        taxa_1t = amostra["depois_1t"] / amostra["votos_1t"]
        logs["estimativa_resto_brasil"] = {
            "votos": votos_resto,
            "depois_2t": round(taxa_2t * votos_resto),
            "a_mais": round((taxa_2t - taxa_1t) * votos_resto),
        }
        resultado["logs"] = logs
        c = logs["cidades"]
        print(f"Logs, 3 cidades: {f(c['depois_2t'])} votos depois das 17h no 2º turno "
              f"({100 * c['depois_2t'] / c['votos_2t']:.2f}% dos votos); nas mesmas urnas, 1º turno: {f(c['depois_1t'])}; "
              f"a mais: {f(c['a_mais'])}")
        e = logs["estimativa_resto_brasil"]
        print(f"Resto do Brasil (amostra): ~{f(e['depois_2t'])} votos depois do fechamento; a mais que no 1º turno: ~{f(e['a_mais'])}")

    destino = config.SITE_DADOS / "2026-2t" / "pausa.json"
    destino.write_text(json.dumps(resultado, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Comparecimento nas cidades: {100 * taxa(g1['cidades']):.2f}% -> {100 * taxa(g2['cidades']):.2f}%; "
          f"resto do Brasil: {100 * taxa(g1['resto_br']):.2f}% -> {100 * taxa(g2['resto_br']):.2f}%")
    print(f"Eleitores a mais além da tendência: {f(extra)} ({100 * extra / margem:.1f}% da vantagem de Lula)")
    for c in resultado["cenarios"]:
        print(f"  {c['id']}: Lula {'+' if c['margem'] > 0 else ''}{f(c['margem'])}")
    print(f"Gravado em {destino}")


if __name__ == "__main__":
    main()
