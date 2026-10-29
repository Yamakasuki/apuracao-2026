"""Lê o log de cada urna: abertura, encerramento e horário de cada voto da tarde, nos dois turnos.

O log da urna (arquivo .jez, que é um 7z) registra cada voto com data e hora ("O voto do eleitor foi
computado"). A urna é a mesma nos dois turnos e o log é cumulativo, então o mesmo arquivo traz os dois turnos.
Os horários estão no relógio local da urna; a conversão para Brasília é feita no pausa.py.

Os arquivos ficam em resultados.tse.jus.br/oficial/ele2026/arquivo-urna/3221/... (uma seção por pedido).
Grupos: todas as urnas de Salvador, Feira de Santana e Lauro de Freitas + amostra aleatória do resto do país.

Uso: python pipeline/logs_urna.py
"""
import csv
import json
import random
import subprocess
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor

import config
import pausa

BASE = "https://resultados.tse.jus.br/oficial/ele2026/arquivo-urna/3221/dados/{uf}/{mun}/{zona}/{secao}/"
DATAS = {"04/10/2026": "1", "25/10/2026": "2"}
TARDE = "13:00:00"  # guarda os votos a partir daqui (hora local): cobre 17h de Brasília em qualquer fuso do país
AMOSTRA = 5000
TAR = r"C:\Windows\System32\tar.exe"  # o tar do Windows 10/11 abre 7z
COLUNAS = ["uf", "cd_municipio", "municipio", "zona", "secao", "grupo"] + [
    f"{c}_{t}t" for t in ("1", "2") for c in ("votos", "abertura", "encerramento", "tarde")]


def contar(log):
    """Por turno: total de votos, abertura, encerramento e horários (locais) dos votos da tarde."""
    r = {t: {"votos": 0, "abertura": None, "encerramento": None, "tarde": []} for t in DATAS.values()}
    for linha in log.split(b"\n"):
        if linha[2:3] != b"/" or linha[10:11] != b" ":  # só linhas que começam com "dd/mm/aaaa hh:mm:ss"
            continue
        data, hora = linha[:19].decode("latin-1").split(" ")
        turno = DATAS.get(data)
        if not turno:
            continue
        t = r[turno]
        if b"O voto do eleitor foi computado" in linha:
            t["votos"] += 1
            if hora >= TARDE:
                t["tarde"].append(hora)
        elif b"Urna pronta para receber votos" in linha and t["abertura"] is None:
            t["abertura"] = hora
        elif b"Procedimento de encerramento confirmado" in linha:
            t["encerramento"] = hora
    return r


def baixar(url):
    for _ in range(4):
        try:
            with urllib.request.urlopen(url, timeout=60) as resp:
                return resp.read()
        except OSError:
            continue
    raise OSError(f"falhou: {url}")


def log_da_secao(u, pasta):
    """Baixa (uma vez) e lê o log de uma seção. Devolve a linha do CSV de saída."""
    ids = {"uf": u["uf"].lower(), "mun": u["cd_municipio"].zfill(5), "zona": u["zona"].zfill(4), "secao": u["secao"].zfill(4)}
    arquivo = pasta / f"{ids['uf']}{ids['mun']}{ids['zona']}{ids['secao']}.jez"
    if not arquivo.exists():
        base = BASE.format(**ids)
        aux = json.loads(baixar(base + f"p003221-{ids['uf']}-m{ids['mun']}-z{ids['zona']}-s{ids['secao']}-aux.json"))
        h = aux["hashes"][0]
        nome = next(a["nm"] for a in h["arq"] if a["tp"] == "log")
        parcial = arquivo.with_suffix(".part")
        parcial.write_bytes(baixar(base + f"{h['hash']}/{nome}"))
        parcial.replace(arquivo)
    log = subprocess.run([TAR, "-xOf", str(arquivo)], capture_output=True, check=True).stdout
    r = contar(log)
    return [u["uf"], u["cd_municipio"], u["municipio"], u["zona"], u["secao"], u["grupo"]] + [
        ";".join(r[t][c]) if c == "tarde" else ("" if r[t][c] is None else r[t][c])
        for t in ("1", "2") for c in ("votos", "abertura", "encerramento", "tarde")]


def escolher(urnas):
    cidades = [dict(u, grupo="cidades") for u in urnas if u["uf"] == pausa.UF and u["municipio"] in pausa.CIDADES]
    resto = [u for u in urnas if u["uf"] != "ZZ" and not (u["uf"] == pausa.UF and u["municipio"] in pausa.CIDADES)]
    amostra = [dict(u, grupo="amostra_brasil") for u in random.Random(2026).sample(resto, AMOSTRA)]
    return cidades + amostra


def main():
    with open(config.PROCESSADOS / "secoes_2026_2t.csv", encoding="utf-8", newline="") as f:
        urnas = list(csv.DictReader(f))
    escolhidas = escolher(urnas)
    pasta = config.BRUTOS / "2026" / "logs"
    pasta.mkdir(parents=True, exist_ok=True)
    linhas, falhas = [], 0
    with ThreadPoolExecutor(max_workers=32) as ex:
        futuros = [ex.submit(log_da_secao, u, pasta) for u in escolhidas]
        for n, f in enumerate(futuros, 1):
            try:
                linhas.append(f.result())
            except Exception as e:  # noqa: BLE001 - uma seção ruim não pode parar as outras
                falhas += 1
                print(f"\n  {e}", file=sys.stderr)
            if n % 200 == 0:
                print(f"\r{n} de {len(futuros)} urnas", end="", flush=True)
    destino = config.PROCESSADOS / "logs_2026_2t.csv"
    with open(destino, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(COLUNAS)
        w.writerows(linhas)
    print(f"\n{len(linhas)} urnas lidas, {falhas} falhas -> {destino}")


if __name__ == "__main__":
    main()
