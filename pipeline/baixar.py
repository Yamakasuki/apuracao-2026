"""Passo 1: baixa os zips do boletim de urna (bweb) de um turno, um por UF.

A lista de arquivos vem da API do Portal de Dados Abertos do TSE (CKAN), então não é
preciso saber de antemão o nome de cada zip (o TSE põe data e hora de geração no nome).

Uso: python pipeline/baixar.py 2026 2
"""
import json
import random
import sys
import time
import urllib.request

import config


def listar(ano, turno):
    """[(nome, url)] dos zips bweb do turno, pela API CKAN."""
    with urllib.request.urlopen(config.CKAN.format(config.DATASET_BU.format(ano=ano)), timeout=60) as r:
        pacote = json.load(r)["result"]
    marca = f"bweb_{turno}t_"
    arquivos = []
    for recurso in pacote["resources"]:
        url = recurso["url"]
        nome = url.rsplit("/", 1)[-1]
        if nome.startswith(marca) and nome.endswith(".zip"):
            arquivos.append((nome, url))
    return sorted(arquivos)


def baixar(url, destino, tentativas=5):
    """Tenta de novo se a conexão cair (o CDN do TSE às vezes derruba downloads longos)."""
    for n in range(1, tentativas + 1):
        try:
            return baixar_uma_vez(url, destino)
        except OSError as e:
            print(f"\n  falhou ({e}); tentativa {n} de {tentativas}")
            time.sleep(5 * n)
    sys.exit(f"Não consegui baixar {url}")


def baixar_uma_vez(url, destino):
    """Baixa para destino.part e renomeia no fim; pula se já existe com o mesmo tamanho.

    O ?cb= aleatório evita que o CDN entregue uma versão antiga em cache.
    """
    with urllib.request.urlopen(f"{url}?cb={random.randrange(10**9)}", timeout=120) as r:
        tamanho = int(r.headers.get("Content-Length", 0))
        if destino.exists() and destino.stat().st_size == tamanho:
            print(f"  já baixado: {destino.name}")
            return
        parcial = destino.with_suffix(".part")
        feito = 0
        with open(parcial, "wb") as f:
            while bloco := r.read(1 << 20):
                f.write(bloco)
                feito += len(bloco)
                if tamanho:
                    print(f"\r  {destino.name}: {feito / 2**20:,.0f} de {tamanho / 2**20:,.0f} MB", end="", flush=True)
        print()
    parcial.replace(destino)


def main(ano, turno):
    pasta = config.BRUTOS / str(ano) / f"{turno}t"
    pasta.mkdir(parents=True, exist_ok=True)
    arquivos = listar(ano, turno)
    if not arquivos:
        sys.exit(f"O TSE ainda não publicou o bweb do {turno}º turno de {ano}.")
    print(f"{len(arquivos)} arquivos em {pasta}")
    for nome, url in arquivos:
        baixar(url, pasta / nome)


if __name__ == "__main__":
    main(int(sys.argv[1]), int(sys.argv[2]))
