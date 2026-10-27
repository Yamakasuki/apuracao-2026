"""Passo 2: lê os zips do boletim de urna (bweb) sem descompactar no disco e guarda só o
cargo Presidente, uma linha por urna (seção), num CSV bem menor que o original.

Uso: python pipeline/filtrar.py 2026 2
"""
import csv
import json
import sys
import time
import zipfile
from datetime import datetime

import config

COLUNAS = ["uf", "cd_municipio", "municipio", "zona", "secao", "recebido",
           "aptos", "comparecimento", "abstencoes"]


def horario(texto):
    """'2026-10-25 17:05:10' (2026) ou '25/10/2022 17:05:10' (2022) -> ISO; vazio ou #NULO# -> None."""
    for formato in config.FORMATOS_DATA_HORA:
        try:
            return datetime.strptime(texto, formato).isoformat()
        except ValueError:
            pass
    return None


def votavel(nr):
    if nr == config.BRANCO:
        return "brancos"
    if nr == config.NULO:
        return "nulos"
    return nr


def secoes_do_zip(caminho):
    """Devolve (urnas, candidatos). Cada urna traz os votos de Presidente somados por votável."""
    urnas = {}
    candidatos = {}
    with zipfile.ZipFile(caminho) as z:
        nome = next(n for n in z.namelist() if n.lower().endswith(".csv"))
        with z.open(nome) as f:
            cabecalho = next(csv.reader([next(f).decode("latin-1")], delimiter=";"))
            i = {coluna: n for n, coluna in enumerate(cabecalho)}
            for bruta in f:
                if config.ATALHO_PRESIDENTE not in bruta:
                    continue
                campos = next(csv.reader([bruta.decode("latin-1")], delimiter=";"))
                if campos[i["CD_CARGO_PERGUNTA"]] != config.CARGO_PRESIDENTE:
                    continue
                chave = (campos[i["SG_UF"]], campos[i["CD_MUNICIPIO"]], campos[i["NR_ZONA"]], campos[i["NR_SECAO"]])
                urna = urnas.get(chave)
                if urna is None:
                    urna = urnas[chave] = {
                        "uf": chave[0], "cd_municipio": chave[1], "municipio": campos[i["NM_MUNICIPIO"]],
                        "zona": chave[2], "secao": chave[3],
                        "recebido": horario(campos[i["DT_BU_RECEBIDO"]]),
                        "aptos": int(campos[i["QT_APTOS"]]),
                        "comparecimento": int(campos[i["QT_COMPARECIMENTO"]]),
                        "abstencoes": int(campos[i["QT_ABSTENCOES"]]),
                        "votos": {},
                    }
                v = votavel(campos[i["NR_VOTAVEL"]])
                urna["votos"][v] = urna["votos"].get(v, 0) + int(campos[i["QT_VOTOS"]])
                if v not in ("brancos", "nulos"):
                    candidatos.setdefault(v, {"nome": campos[i["NM_VOTAVEL"]], "partido": campos[i["SG_PARTIDO"]]})
    return list(urnas.values()), candidatos


def gravar(urnas, destino, votaveis):
    """CSV largo: uma coluna por votável (votos_13, votos_22, ..., brancos, nulos)."""
    destino.parent.mkdir(parents=True, exist_ok=True)
    nomes = [v if v in ("brancos", "nulos") else f"votos_{v}" for v in votaveis]
    with open(destino, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(COLUNAS + nomes)
        for u in urnas:
            w.writerow(["" if u[c] is None else u[c] for c in COLUNAS] + [u["votos"].get(v, 0) for v in votaveis])


def main(ano, turno):
    pasta = config.BRUTOS / str(ano) / f"{turno}t"
    zips = sorted(pasta.glob("*.zip"))
    if not zips:
        sys.exit(f"Nenhum zip em {pasta}. Baixe antes os arquivos do boletim de urna.")
    urnas, candidatos = [], {}
    for z in zips:
        inicio = time.perf_counter()
        u, c = secoes_do_zip(z)
        urnas += u
        for nr, dados in c.items():
            candidatos.setdefault(nr, dados)
        print(f"{z.name}: {len(u):,} urnas ({time.perf_counter() - inicio:.1f} s)")
    if not urnas:
        sys.exit("Nenhuma linha de Presidente. Confira DS_CARGO_PERGUNTA no CSV e o ATALHO_PRESIDENTE do config.py.")
    total = {}
    for u in urnas:
        for v, q in u["votos"].items():
            total[v] = total.get(v, 0) + q
    votaveis = sorted(candidatos, key=lambda nr: -total.get(nr, 0)) + ["brancos", "nulos"]
    destino = config.PROCESSADOS / f"secoes_{ano}_{turno}t.csv"
    gravar(urnas, destino, votaveis)
    with open(config.PROCESSADOS / f"candidatos_{ano}_{turno}t.json", "w", encoding="utf-8") as f:
        json.dump(candidatos, f, ensure_ascii=False, indent=2)
    print(f"{len(urnas):,} urnas gravadas em {destino}")


if __name__ == "__main__":
    main(int(sys.argv[1]), int(sys.argv[2]))
