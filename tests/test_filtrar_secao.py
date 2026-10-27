import csv
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "pipeline"))
import filtrar_secao  # noqa: E402


def zip_csv(caminho, nome, cabecalho, linhas):
    with zipfile.ZipFile(caminho, "w", zipfile.ZIP_DEFLATED) as z:
        texto = [";".join(f'"{c}"' for c in cabecalho)] + [";".join(f'"{c}"' for c in l) for l in linhas]
        z.writestr(nome, "\r\n".join(texto).encode("latin-1"))


class TestFiltrarSecao(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        p = Path(self.tmp.name)
        self.votos, self.detalhe, self.cand = p / "v.zip", p / "d.zip", p / "c.zip"
        cab_v = ["NR_TURNO", "SG_UF", "CD_MUNICIPIO", "NM_MUNICIPIO", "NR_ZONA", "NR_SECAO", "NR_VOTAVEL", "QT_VOTOS"]
        zip_csv(self.votos, "votacao_secao_2026_BR.csv", cab_v, [
            ["2", "SP", "71072", "SÃO PAULO", "1", "10", "13", "100"],
            ["1", "SP", "71072", "SÃO PAULO", "1", "10", "13", "999"],
            ["2", "RR", "03018", "BOA VISTA", "1", "5", "22", "80"],
            ["2", "SP", "71072", "SÃO PAULO", "1", "10", "22", "120"],
            ["2", "SP", "71072", "SÃO PAULO", "1", "10", "95", "10"],
            ["2", "SP", "71072", "SÃO PAULO", "1", "10", "96", "20"],
        ])
        cab_d = ["NR_TURNO", "SG_UF", "CD_MUNICIPIO", "NM_MUNICIPIO", "NR_ZONA", "NR_SECAO", "QT_APTOS",
                 "QT_COMPARECIMENTO", "QT_ABSTENCOES", "DT_RECEBIMENTO_BU_HOR_TSE", "ST_SECAO_INSTALADA"]
        zip_csv(self.detalhe, "detalhe_votacao_secao_2026_BR.csv", cab_d, [
            ["2", "SP", "71072", "SÃO PAULO", "1", "10", "300", "250", "50", "25/10/2026 17:05:10", "Sim"],
            ["2", "RR", "03018", "BOA VISTA", "1", "5", "200", "80", "120", "#NULO#", "Sim"],
            ["2", "RR", "03018", "BOA VISTA", "1", "6", "200", "0", "200", "#NULO#", "Não"],
            ["1", "SP", "71072", "SÃO PAULO", "1", "10", "300", "260", "40", "04/10/2026 17:30:00", "Sim"],
        ])
        cab_c = ["NR_TURNO", "DS_CARGO", "NR_CANDIDATO", "NM_URNA_CANDIDATO", "SG_PARTIDO", "DS_SIT_TOT_TURNO"]
        zip_csv(self.cand, "consulta_cand_2026_BR.csv", cab_c, [
            ["1", "PRESIDENTE", "13", "LULA", "PT", "2º TURNO"],
            ["2", "PRESIDENTE", "22", "FLAVIO BOLSONARO", "PL", "NÃO ELEITO"],
            ["2", "PRESIDENTE", "13", "LULA", "PT", "ELEITO"],
            ["1", "PRESIDENTE", "28", "PABLO MARÇAL", "PRTB", "#NULO"],
            ["1", "PRESIDENTE", "28", "LEONARDO AVALANCHE", "PRTB", "NÃO ELEITO"],
            ["1", "GOVERNADOR", "13", "FULANO", "PT", "ELEITO"],
        ])
        self.urnas = filtrar_secao.urnas(self.votos, self.detalhe, 2)

    def tearDown(self):
        self.tmp.cleanup()

    def test_junta_votos_e_horario_so_do_turno(self):
        sp = next(u for u in self.urnas if u["uf"] == "SP")
        self.assertEqual(sp["votos"], {"13": 100, "22": 120, "brancos": 10, "nulos": 20})
        self.assertEqual(sp["recebido"], "2026-10-25T17:05:10")
        self.assertEqual((sp["aptos"], sp["comparecimento"], sp["abstencoes"]), (300, 250, 50))
        self.assertEqual(sp["municipio"], "SÃO PAULO")

    def test_secao_nao_instalada_fica_de_fora(self):
        self.assertEqual(len(self.urnas), 2)
        rr = next(u for u in self.urnas if u["uf"] == "RR")
        self.assertIsNone(rr["recebido"])
        self.assertEqual(rr["votos"], {"22": 80})

    def test_candidatos_com_nome_de_urna(self):
        c = filtrar_secao.candidatos(self.cand, 1)
        self.assertEqual(c, {"13": {"nome": "LULA", "partido": "PT"}, "28": {"nome": "LEONARDO AVALANCHE", "partido": "PRTB"}})


if __name__ == "__main__":
    unittest.main()
