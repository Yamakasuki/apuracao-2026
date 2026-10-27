"""Passo 3: monta a linha do tempo da apuração e os resumos que o site lê.

Entrada: dados/processados/secoes_<ano>_<t>t.csv (saída do filtrar.py)
Saída:   docs/dados/<ano>-<t>t/resumo.json, linha_do_tempo.json e municipios.json

Uso: python pipeline/analisar.py 2026 2
"""
import csv
import json
import sys
from collections import Counter
from datetime import datetime, timedelta

import config

LARGURA_RITMO = 10  # minutos por janela no gráfico de ritmo


def ler(caminho):
    """Lê o CSV do filtrar.py de volta para o formato de urna (votos por votável)."""
    urnas = []
    with open(caminho, encoding="utf-8", newline="") as f:
        for linha in csv.DictReader(f):
            votos = {}
            for coluna, valor in linha.items():
                if coluna.startswith("votos_"):
                    votos[coluna[6:]] = int(valor)
                elif coluna in ("brancos", "nulos"):
                    votos[coluna] = int(valor)
            urnas.append({
                "uf": linha["uf"], "cd_municipio": linha["cd_municipio"], "municipio": linha["municipio"],
                "recebido": linha["recebido"] or None, "aptos": int(linha["aptos"]),
                "comparecimento": int(linha["comparecimento"]), "abstencoes": int(linha["abstencoes"]),
                "votos": votos,
            })
    return urnas


def minuto(recebido, inicio):
    """Minutos desde o início da divulgação; o que chegou antes conta no minuto 0."""
    if recebido is None:
        return None
    return max(0, int((datetime.fromisoformat(recebido) - inicio).total_seconds() // 60))


def agrupar(votos, principais, com_outros):
    """Votos de uma urna nas séries do site: os dois principais, outros, brancos e nulos."""
    s = {nr: votos.get(nr, 0) for nr in principais}
    if com_outros:
        s["outros"] = sum(v for k, v in votos.items() if k not in principais and k not in ("brancos", "nulos"))
    s["brancos"] = votos.get("brancos", 0)
    s["nulos"] = votos.get("nulos", 0)
    return s


def linha_do_tempo(urnas, series):
    """Acumulados por minuto (só os minutos em que chegou urna), para o Brasil e cada UF."""
    minutos = sorted({u["minuto"] for u in urnas if u["minuto"] is not None})
    pos = {m: i for i, m in enumerate(minutos)}
    locais = {}
    for u in urnas:
        for local in ("BR", u["uf"]):
            if local not in locais:
                locais[local] = {c: [0] * len(minutos) for c in ["secoes", "aptos"] + series}
        if u["minuto"] is None:
            continue
        i = pos[u["minuto"]]
        for local in ("BR", u["uf"]):
            dados = locais[local]
            dados["secoes"][i] += 1
            dados["aptos"][i] += u["aptos"]
            for s in series:
                dados[s][i] += u["s"][s]
    for dados in locais.values():
        for lista in dados.values():
            for i in range(1, len(lista)):
                lista[i] += lista[i - 1]
    return {"minutos": minutos, "locais": locais}


def ritmo(minutos, acumulado, largura, n):
    """Quanto entrou em cada janela de `largura` minutos: [0, largura), [largura, 2*largura), ..."""
    saida, anterior, j = [], 0, -1
    for k in range(n):
        while j + 1 < len(minutos) and minutos[j + 1] < (k + 1) * largura:
            j += 1
        atual = acumulado[j] if j >= 0 else 0
        saida.append(atual - anterior)
        anterior = atual
    return saida


def eventos(a, b, aptos, aptos_total):
    """Viradas, maior vantagem de cada lado e o momento em que o resultado ficou garantido.

    a, b e aptos são acumulados alinhados com os minutos. "Definido" é o primeiro momento em que a
    vantagem passa dos aptos das urnas que ainda faltam: nem com todos votando no outro dá para virar.
    """
    vantagem = [x - y for x, y in zip(a, b)]
    viradas, lider = [], None
    for i, v in enumerate(vantagem):
        agora = "a" if v > 0 else "b" if v < 0 else lider
        if lider is not None and agora != lider:
            viradas.append({"i": i, "lider": agora})
        lider = agora
    i_max = max(range(len(vantagem)), key=vantagem.__getitem__, default=None)
    i_min = min(range(len(vantagem)), key=vantagem.__getitem__, default=None)
    return {
        "viradas": viradas,
        "pico": {
            "a": i_max if i_max is not None and vantagem[i_max] > 0 else None,
            "b": i_min if i_min is not None and vantagem[i_min] < 0 else None,
        },
        "definido": next((i for i, v in enumerate(vantagem) if abs(v) > aptos_total - aptos[i]), None),
    }


def arrancadas(r, a, b):
    """Janela em que cada lado mais ganhou vantagem (votos dele menos os do outro)."""
    liquido = [x - y for x, y in zip(r[a], r[b])]
    k_a = max(range(len(liquido)), key=liquido.__getitem__, default=None)
    k_b = min(range(len(liquido)), key=liquido.__getitem__, default=None)
    return {
        a: {"janela": k_a, "liquido": liquido[k_a]} if k_a is not None and liquido[k_a] > 0 else None,
        b: {"janela": k_b, "liquido": -liquido[k_b]} if k_b is not None and liquido[k_b] < 0 else None,
    }


def puxadores(locais, k, a, b, para_a, quantos=3):
    """UFs que mais contribuíram para a vantagem de um lado na janela k."""
    contrib = []
    for uf, dados in locais.items():
        if uf == "BR":
            continue
        liquido = dados["ritmo"][a][k] - dados["ritmo"][b][k]
        if not para_a:
            liquido = -liquido
        if liquido > 0:
            contrib.append([uf, liquido])
    return sorted(contrib, key=lambda x: -x[1])[:quantos]


def somar(destino, chave, u):
    t = destino.setdefault(chave, Counter())
    t["secoes"] += 1
    for c in ("aptos", "comparecimento", "abstencoes"):
        t[c] += u[c]
    t.update(u["s"])


def gerar(brutas, candidatos, ano, turno):
    """Devolve (resumo, linha_do_tempo, municipios), prontos para virar JSON."""
    inicio = datetime.fromisoformat(f"{config.DATAS[(ano, turno)]}T{config.INICIO_DIVULGACAO}")
    total = Counter()
    for u in brutas:
        total.update(u["votos"])
    numeros = sorted(candidatos, key=lambda nr: -total[nr])
    principais = numeros[:2]
    com_outros = len(numeros) > 2
    series = principais + (["outros"] if com_outros else []) + ["brancos", "nulos"]

    urnas, totais, municipios = [], {}, {}
    for b in brutas:
        u = {"uf": b["uf"], "minuto": minuto(b["recebido"], inicio), "aptos": b["aptos"],
             "comparecimento": b["comparecimento"], "abstencoes": b["abstencoes"],
             "s": agrupar(b["votos"], principais, com_outros)}
        urnas.append(u)
        somar(totais, "BR", u)
        somar(totais, b["uf"], u)
        somar(municipios, (b["uf"], b["cd_municipio"], b["municipio"]), u)

    lt = linha_do_tempo(urnas, series)
    minutos = lt["minutos"]
    secoes_br = lt["locais"]["BR"]["secoes"]
    # o eixo do site abre até 99,9% das urnas; a cauda (urnas que chegam bem depois) fica no zoom
    i99 = next((i for i, s in enumerate(secoes_br) if s >= 0.999 * secoes_br[-1]), None) if minutos else None
    minuto_99 = minutos[i99] if i99 is not None else 0
    n = minuto_99 // LARGURA_RITMO + 1
    a, b = principais
    for local, dados in lt["locais"].items():
        dados["ritmo"] = {s: ritmo(minutos, dados[s], LARGURA_RITMO, n) for s in ["secoes"] + series}
        ev = eventos(dados[a], dados[b], dados.pop("aptos"), totais[local]["aptos"])
        dados["eventos"] = {
            "viradas": [{"i": v["i"], "lider": a if v["lider"] == "a" else b} for v in ev["viradas"]],
            "pico": {a: ev["pico"]["a"], b: ev["pico"]["b"]},
            "definido": ev["definido"],
            "arrancada": arrancadas(dados["ritmo"], a, b),
        }
    for nr, arr in lt["locais"]["BR"]["eventos"]["arrancada"].items():
        if arr:
            arr["ufs"] = puxadores(lt["locais"], arr["janela"], a, b, nr == a)

    resumo = {
        "ano": ano, "turno": turno, "data": config.DATAS[(ano, turno)], "inicio": inicio.isoformat(),
        "candidatos": [{"numero": nr, **candidatos[nr], "votos": total[nr]} for nr in numeros],
        "principais": principais, "series": series,
        "totais": {local: dict(t) for local, t in totais.items()},
        "secoes_sem_horario": sum(1 for u in urnas if u["minuto"] is None),
        "gerado_em": datetime.now().isoformat(timespec="seconds"),
    }
    linha = {"inicio": inicio.isoformat(), "minutos": minutos, "minuto_99": minuto_99,
             "largura_ritmo": LARGURA_RITMO, "series": series, "principais": principais,
             "locais": lt["locais"]}
    colunas = ["uf", "codigo", "nome", "aptos", "comparecimento"] + series
    linhas = [[uf, cod, nome] + [t[c] for c in colunas[3:]] for (uf, cod, nome), t in sorted(municipios.items())]
    return resumo, linha, {"colunas": colunas, "linhas": linhas}


def fmt(n):
    return f"{n:,}".replace(",", ".")


def imprimir_destaques(resumo, linha):
    inicio = datetime.fromisoformat(linha["inicio"])
    a, b = linha["principais"]
    nome = {c["numero"]: c["nome"] for c in resumo["candidatos"]}
    br, minutos = linha["locais"]["BR"], linha["minutos"]
    validos = sum(c["votos"] for c in resumo["candidatos"])

    def momento(i):
        quando = inicio + timedelta(minutes=minutos[i])
        return f"{quando:%d/%m %H:%M} ({100 * br['secoes'][i] / br['secoes'][-1]:.1f}% das urnas)"

    print("\nResultado:")
    for c in resumo["candidatos"]:
        print(f"  {c['nome']} ({c['partido']}): {fmt(c['votos'])} votos ({100 * c['votos'] / validos:.2f}% dos válidos)")
    print("Apuração (Brasil):")
    for v in br["eventos"]["viradas"]:
        print(f"  Virada: {nome[v['lider']]} passa à frente em {momento(v['i'])}")
    for nr, i in br["eventos"]["pico"].items():
        if i is not None:
            print(f"  Maior vantagem de {nome[nr]}: {fmt(abs(br[a][i] - br[b][i]))} votos em {momento(i)}")
    if br["eventos"]["definido"] is not None:
        print(f"  Resultado garantido em {momento(br['eventos']['definido'])}")
    for nr, arr in br["eventos"]["arrancada"].items():
        if arr:
            de = inicio + timedelta(minutes=arr["janela"] * linha["largura_ritmo"])
            ate = de + timedelta(minutes=linha["largura_ritmo"])
            ufs = ", ".join(uf for uf, _ in arr["ufs"])
            print(f"  Maior arrancada de {nome[nr]}: +{fmt(arr['liquido'])} de vantagem entre "
                  f"{de:%H:%M} e {ate:%H:%M} (puxada por {ufs})")
    if resumo["secoes_sem_horario"]:
        print(f"  {fmt(resumo['secoes_sem_horario'])} urnas sem horário de recebimento (fora da linha do tempo)")


def atualizar_indice(ano, turno):
    """docs/dados/eleicoes.json lista as eleições já processadas (é o que o seletor do site mostra)."""
    caminho = config.SITE_DADOS / "eleicoes.json"
    lista = json.loads(caminho.read_text(encoding="utf-8")) if caminho.exists() else []
    lista = [e for e in lista if e["id"] != f"{ano}-{turno}t"]
    lista.append({"id": f"{ano}-{turno}t", "ano": ano, "turno": turno, "data": config.DATAS[(ano, turno)]})
    lista.sort(key=lambda e: (-e["ano"], -e["turno"]))
    caminho.write_text(json.dumps(lista, ensure_ascii=False, indent=2), encoding="utf-8")


def main(ano, turno):
    with open(config.PROCESSADOS / f"candidatos_{ano}_{turno}t.json", encoding="utf-8") as f:
        candidatos = json.load(f)
    resumo, linha, municipios = gerar(ler(config.PROCESSADOS / f"secoes_{ano}_{turno}t.csv"), candidatos, ano, turno)
    pasta = config.SITE_DADOS / f"{ano}-{turno}t"
    pasta.mkdir(parents=True, exist_ok=True)
    for nome, dados in (("resumo", resumo), ("linha_do_tempo", linha), ("municipios", municipios)):
        caminho = pasta / f"{nome}.json"
        caminho.write_text(json.dumps(dados, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        print(f"{caminho.relative_to(config.RAIZ)}: {caminho.stat().st_size / 1024:,.0f} KB")
    atualizar_indice(ano, turno)
    imprimir_destaques(resumo, linha)


if __name__ == "__main__":
    main(int(sys.argv[1]), int(sys.argv[2]))
