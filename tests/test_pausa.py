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


def log(grupo, uf, mun, abertura, v1, tarde1, v2, tarde2, encerramento="17:02:00"):
    return {"grupo": grupo, "uf": uf, "cd_municipio": mun, "votos_1t": str(v1), "tarde_1t": tarde1,
            "abertura_2t": abertura, "encerramento_2t": encerramento, "votos_2t": str(v2), "tarde_2t": tarde2}


class TestResumoLogs(unittest.TestCase):
    def test_fuso_do_municipio_pela_abertura(self):
        # duas urnas do mesmo município abrem às 07h locais: o relógio local está 1h atrás de Brasília
        linhas = [log("amostra", "AM", "1", "07:00:01", 10, "", 10, "16:00:00;16:30:00", encerramento="16:50:00"),
                  log("amostra", "AM", "1", "07:00:05", 10, "", 10, "15:59:59", encerramento="16:02:00")]
        self.assertEqual(pausa.fusos(linhas), {("AM", "1"): -1})
        g = pausa.resumo_logs(linhas)["amostra"]
        self.assertEqual(g["depois_2t"], 2)  # 17:00:00 e 17:30:00 de Brasília
        self.assertEqual((g["estendidas"], g["votos_estendidas"]), (1, 2))  # fechou às 17h50 de Brasília
        self.assertEqual(g["faixas_2t"][:4], [1, 0, 0, 1])
        self.assertEqual(g["ultimo_2t"], "17:30:00")

    def test_urna_trocada_fica_fora_so_da_comparacao(self):
        linhas = [log("cidades", "BA", "2", "08:00:01", 300, "17:10:00", 310, "17:01:00"),
                  log("cidades", "BA", "2", "08:00:02", 0, "", 200, "17:03:00")]
        g = pausa.resumo_logs(linhas)["cidades"]
        self.assertEqual((g["urnas"], g["urnas_comparaveis"]), (2, 1))
        self.assertEqual((g["depois_2t"], g["depois_1t"]), (2, 1))


class TestFusos(unittest.TestCase):
    def test_urna_que_abriu_atrasada_nao_define_o_fuso(self):
        linhas = [log("x", "PR", "9", "09:25:07", 1, "", 1, ""),     # única urna do município, abriu atrasada
                  log("x", "PR", "8", "08:00:01", 1, "", 1, ""),
                  log("x", "PR", "7", "08:02:00", 1, "", 1, "")]
        self.assertEqual(pausa.fusos(linhas)[("PR", "9")], 0)  # cai no fuso mais comum do estado


class TestBrasilInteiro(unittest.TestCase):
    def test_todas_as_urnas_e_so_as_estendidas(self):
        def linha(uf, enc, v):
            return {"uf": uf, "encerramento_brt": enc, "votos_apos_17h": str(v), "votos_total": "300"}
        linhas = [linha("SP", "17:01:00", 5), linha("RJ", "17:20:00", 2), linha("RJ", "18:59:00", 3), linha("ZZ", "21:00:00", 9)]
        r = pausa.brasil_inteiro(linhas)
        self.assertEqual((r["urnas"], r["brasil"]), (3, 10))
        self.assertEqual((r["estendidas"], r["votos_estendidas"]), (1, 3))
        self.assertEqual([c["votos"] for c in r["cortes"]], [10, 5, 3, 3])
        self.assertEqual(r["por_uf"], {"RJ": {"estendidas": 1, "votos": 3}})


if __name__ == "__main__":
    unittest.main()
