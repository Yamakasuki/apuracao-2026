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


class TestResumoLogs(unittest.TestCase):
    def test_compara_so_urnas_com_os_dois_turnos(self):
        def linha(grupo, v1, d1, v2, d2, f1="0 0 0 0 0 0 0", f2="0 0 0 0 0 0 0"):
            return {"grupo": grupo, "votos_1t": str(v1), "depois_1t": str(d1), "votos_2t": str(v2), "depois_2t": str(d2),
                    "ultimo_2t": "18:10:00", "faixas_1t": f1, "faixas_2t": f2}
        linhas = [linha("cidades", 300, 5, 310, 40, "5 0 0 0 0 0 0", "10 10 10 0 0 0 10"),
                  linha("cidades", 0, 0, 200, 30)]  # urna trocada: não entra na comparação
        g = pausa.resumo_logs(linhas)["cidades"]
        self.assertEqual((g["urnas"], g["urnas_comparaveis"]), (2, 1))
        self.assertEqual((g["depois_2t"], g["depois_1t"], g["a_mais"]), (70, 5, 35))
        self.assertEqual(g["faixas_2t"], [10, 10, 10, 0, 0, 0, 10])
        self.assertEqual((g["urnas_depois_18h_2t"], g["urnas_depois_18h_1t"]), (1, 0))


class TestFaixasBrasil(unittest.TestCase):
    def test_converte_fuso_e_separa_exterior(self):
        linhas = [
            {"uf": "sp", "delta_h": "0.0", "log_horarios_apos_corte": "170000;170001;170630"},   # 17:00:00 não conta
            {"uf": "am", "delta_h": "-1.0", "log_horarios_apos_corte": "160200;155900"},          # 17:02 e 16:59 de Brasília
            {"uf": "zz", "delta_h": "-4.0", "log_horarios_apos_corte": "130500"},                 # 17:05 de Brasília
            {"uf": "rj", "delta_h": "", "log_horarios_apos_corte": "191500"},                     # cai na última janela
        ]
        r = pausa.faixas_brasil(linhas)
        self.assertEqual((r["brasil"], r["exterior"]), (4, 1))
        self.assertEqual(r["faixas"][:2], [2, 1])
        self.assertEqual(r["faixas"][-1], 1)


if __name__ == "__main__":
    unittest.main()
