import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "pipeline"))
import pausa  # noqa: E402


def urna(uf, municipio, aptos, comp, a=0, b=0, recebido="2026-10-25T20:00:00"):
    return {"uf": uf, "municipio": municipio, "aptos": aptos, "comparecimento": comp,
            "recebido": recebido, "votos": {"13": a, "22": b}}


class TestPausa(unittest.TestCase):
    def test_grupos_somam_aptos_comparecimento_e_margem(self):
        urnas = [urna("BA", "SALVADOR", 100, 90, 60, 20), urna("BA", "ILHEUS", 100, 80, 50, 25),
                 urna("SP", "SANTOS", 200, 160, 70, 80)]
        g = pausa.grupos(urnas, {"SALVADOR"}, "BA", "13", "22")
        self.assertEqual(g["cidades"], {"secoes": 1, "aptos": 100, "comparecimento": 90, "margem": 40})
        self.assertEqual(g["resto_uf"]["margem"], 25)
        self.assertEqual(g["resto_br"]["margem"], -10)
        self.assertEqual(g["brasil"]["margem"], 55)

    def test_eleitores_a_mais_alem_da_tendencia(self):
        # cidades: 80% -> 90% (+10 pontos); resto do país: 70% -> 72% (+2 pontos); 1.000 aptos
        t1 = {"cidades": {"aptos": 1000, "comparecimento": 800}, "resto_br": {"aptos": 1000, "comparecimento": 700}}
        t2 = {"cidades": {"aptos": 1000, "comparecimento": 900}, "resto_br": {"aptos": 1000, "comparecimento": 720}}
        self.assertEqual(pausa.excesso(t1, t2), 80)

    def test_excesso_nunca_negativo(self):
        t1 = {"cidades": {"aptos": 10, "comparecimento": 9}, "resto_br": {"aptos": 10, "comparecimento": 5}}
        t2 = {"cidades": {"aptos": 10, "comparecimento": 9}, "resto_br": {"aptos": 10, "comparecimento": 9}}
        self.assertEqual(pausa.excesso(t1, t2), 0)

    def test_antes_e_depois_da_pausa(self):
        urnas = [urna("ZZ", "LISBOA", 10, 5, 3, 2, "2026-10-25T17:06:00"),
                 urna("SP", "SANTOS", 10, 8, 4, 4, "2026-10-25T19:30:00")]
        r = pausa.recebidas_antes(urnas, "2026-10-25T19:00:00")
        self.assertEqual(r, {"secoes": 1, "votos": 5, "total_secoes": 2, "total_votos": 13})


if __name__ == "__main__":
    unittest.main()
