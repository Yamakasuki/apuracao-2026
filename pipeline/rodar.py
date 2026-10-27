"""Roda o pipeline inteiro para um turno de 2026: baixar -> juntar -> analisar -> validar.

Uso: python pipeline/rodar.py 2
"""
import sys

import analisar
import baixar_secao
import filtrar_secao
import validar

turno = int(sys.argv[1])
print("1. Baixando os arquivos do TSE")
baixar_secao.main()
print(f"2. Juntando votos e horário por seção ({turno}º turno)")
filtrar_secao.main(turno)
print("3. Montando a linha do tempo e os resumos")
analisar.main(2026, turno)
print("4. Conferindo com o resultado oficial")
validar.main(2026, turno)
