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

4. Votos depois das 17h, contados no log de cada urna (logs_urna.py): todas as urnas das três cidades,
   uma amostra do resto do país e, para o Brasil inteiro, a contagem de todas as urnas publicada em
   github.com/apolinario/urnas-tardias (mesma fonte e mesmo método; conferido urna por urna).

Uso: python pipeline/pausa.py
"""
import csv
import json
import urllib.request

import analisar
import config

CIDADES = {"SALVADOR", "FEIRA DE SANTANA", "LAURO DE FREITAS"}
UF = "BA"
FIM_PAUSA = "2026-10-25T19:00:00"

# Contagem de todas as urnas do país, uma linha por urna: github.com/apolinario/urnas-tardias (secoes.csv)
URL_APOLINARIO = "https://raw.githubusercontent.com/apolinario/urnas-tardias/HEAD/secoes.csv"
ESTENDIDA = "17:45:00"  # urna "estendida": encerrou depois disso (Brasília), ou seja, usou a prorrogação
CORTES = ["17:00:00", "17:15:00", "17:30:00", "17:45:00"]


def seg(hora):
    h, m, s_ = map(int, hora.split(":"))
    return h * 3600 + m * 60 + s_


def brasil_inteiro(linhas):
    """Votos depois das 17h no Brasil (sem o exterior): em todas as urnas e só nas urnas estendidas."""
    r = {"urnas": 0, "votos_total": 0, "brasil": 0, "por_uf": {},
         "cortes": [{"corte": c[:5], "urnas": 0, "votos": 0} for c in CORTES]}
    for l in linhas:
        if l["uf"] == "ZZ":
            continue
        v = int(l["votos_apos_17h"])
        r["urnas"] += 1
        r["votos_total"] += int(l["votos_total"])
        r["brasil"] += v
        for c, corte in zip(r["cortes"], CORTES):
            if c["corte"] == "17:00" or l["encerramento_brt"] > corte:
                c["urnas"] += 1
                c["votos"] += v
        if l["encerramento_brt"] > ESTENDIDA:
            uf = r["por_uf"].setdefault(l["uf"], {"estendidas": 0, "votos": 0})
            uf["estendidas"] += 1
            uf["votos"] += v
    r["estendidas"] = r["cortes"][-1]["urnas"]
    r["votos_estendidas"] = r["cortes"][-1]["votos"]
    return r


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


def fusos(linhas):
    """Diferença (horas) entre o relógio local e Brasília, por município.

    Toda urna abre às 8h de Brasília; o horário de abertura mais comum no log das urnas do município diz o fuso.
    Só entram urnas que abriram na hora cheia (até 10 min depois): uma urna que abriu atrasada (9h25) não diz o fuso.
    Município sem nenhuma urna assim fica com o fuso mais comum do estado.
    """
    mun, uf = {}, {}
    for l in linhas:
        a = l["abertura_2t"]
        if not a or int(a[3:5]) >= 10:
            continue
        d = int(a[:2]) - 8
        for chave, destino in (((l["uf"], l["cd_municipio"]), mun), (l["uf"], uf)):
            c = destino.setdefault(chave, {})
            c[d] = c.get(d, 0) + 1

    def moda(c):
        return max(c, key=c.get)

    return {(l["uf"], l["cd_municipio"]): moda(mun.get((l["uf"], l["cd_municipio"])) or uf.get(l["uf"]) or {0: 1})
            for l in linhas}


FAIXAS = 15  # janelas de 10 min a partir das 17h; a última junta tudo a partir de 19h20


def resumo_logs(linhas):
    """Soma o que os logs das urnas mostram, por grupo (cidades da prorrogação e amostra do Brasil).

    Tudo em horário de Brasília. Conta voto às 17:00:00 ou depois (mesmo critério do apolinario/urnas-tardias).
    """
    linhas = list(linhas)
    fuso = fusos(linhas)
    grupos = {}
    for l in linhas:
        g = grupos.setdefault(l["grupo"], {
            "urnas": 0, "urnas_comparaveis": 0, "votos_2t": 0, "depois_2t": 0, "votos_1t": 0, "depois_1t": 0,
            "estendidas": 0, "votos_estendidas": 0, "ultimo_2t": "",
            "faixas_1t": [0] * FAIXAS, "faixas_2t": [0] * FAIXAS,
        })
        desloc = fuso.get((l["uf"], l["cd_municipio"]), 0) * 3600
        depois = {}
        for t in ("1", "2"):
            tarde = [seg(h) - desloc - 17 * 3600 for h in l[f"tarde_{t}t"].split(";") if h]
            tarde = [x for x in tarde if x >= 0]
            depois[t] = len(tarde)
            if t == "2" or int(l["votos_1t"]):
                for x in tarde:
                    g[f"faixas_{t}t"][min(x // 600, FAIXAS - 1)] += 1
            if t == "2" and tarde:
                m = 17 * 3600 + max(tarde)
                g["ultimo_2t"] = max(g["ultimo_2t"], f"{m // 3600:02d}:{m % 3600 // 60:02d}:{m % 60:02d}")
        g["urnas"] += 1
        g["votos_2t"] += int(l["votos_2t"])
        g["depois_2t"] += depois["2"]
        if l["encerramento_2t"] and seg(l["encerramento_2t"]) - desloc > seg(ESTENDIDA):
            g["estendidas"] += 1
            g["votos_estendidas"] += depois["2"]
        if int(l["votos_1t"]):  # urna trocada entre os turnos não tem o 1º turno no log
            g["urnas_comparaveis"] += 1
            g["votos_1t"] += int(l["votos_1t"])
            g["depois_1t"] += depois["1"]
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
    with open(config.PROCESSADOS / "logs_2026_2t.csv", encoding="utf-8", newline="") as arq:
        logs = resumo_logs(csv.DictReader(arq))
    resultado["logs"] = logs
    c = logs["cidades"]
    print(f"Logs, 3 cidades: {f(c['depois_2t'])} votos depois das 17h; {f(c['estendidas'])} urnas estendidas com "
          f"{f(c['votos_estendidas'])} deles. Amostra: {f(logs['amostra_brasil']['depois_2t'])}")

    arq = config.BRUTOS / "2026" / "apolinario" / "secoes.csv"
    if not arq.exists():
        arq.parent.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(URL_APOLINARIO, timeout=120) as r:
            arq.write_bytes(r.read())
    with open(arq, encoding="utf-8", newline="") as a_:
        resultado["brasil_apos_17h"] = brasil_inteiro(csv.DictReader(a_))
    bra = resultado["brasil_apos_17h"]
    print(f"Brasil inteiro: {f(bra['brasil'])} votos depois das 17h em {f(bra['urnas'])} urnas; "
          f"{f(bra['estendidas'])} urnas estendidas com {f(bra['votos_estendidas'])} votos depois das 17h")

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
