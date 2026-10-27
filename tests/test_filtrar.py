import csv
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "pipeline"))
import filtrar  # noqa: E402

CABECALHO = [
    "DT_GERACAO", "ANO_ELEICAO", "NR_TURNO", "SG_UF", "CD_MUNICIPIO", "NM_MUNICIPIO",
    "NR_ZONA", "NR_SECAO", "CD_CARGO_PERGUNTA", "DS_CARGO_PERGUNTA", "NR_PARTIDO",
    "SG_PARTIDO", "DT_BU_RECEBIDO", "QT_APTOS", "QT_COMPARECIMENTO", "QT_ABSTENCOES",
    "CD_TIPO_VOTAVEL", "DS_TIPO_VOTAVEL", "NR_VOTAVEL", "NM_VOTAVEL", "QT_VOTOS",
]


def linha(uf, mun, nome_mun, zona, secao, cargo, ds_cargo, recebido, aptos, comp, tipo, nr, nome, votos, partido="#NULO#"):
    ds_tipo = {"1": "Nominal", "2": "Branco", "3": "Nulo"}[tipo]
    return ["26/10/2026", "2026", "2", uf, mun, nome_mun, zona, secao, cargo, ds_cargo, "-1", partido,
            recebido, str(aptos), str(comp), str(aptos - comp), tipo, ds_tipo, nr, nome, str(votos)]


def criar_zip(pasta, linhas):
    csv_path = Path(pasta) / "bweb_2t_XX.csv"
    with open(csv_path, "w", encoding="latin-1", newline="") as f:
        w = csv.writer(f, delimiter=";", quoting=csv.QUOTE_ALL)
        w.writerow(CABECALHO)
        w.writerows(linhas)
    zip_path = Path(pasta) / "bweb_2t_XX.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(csv_path, csv_path.name)
        z.writestr("leiame.pdf", b"%PDF")
    return zip_path


SP = ("SP", "71072", "SÃO PAULO", "1", "10")
RR = ("RR", "03018", "BOA VISTA", "1", "5")
LINHAS = [
    linha(*SP, "1", "Presidente", "2026-10-25 17:05:10", 300, 250, "1", "13", "LULA", 100, "PT"),
    linha(*SP, "1", "Presidente", "25/10/2026 17:05:10", 300, 250, "1", "22", "FLÁVIO BOLSONARO", 120, "PL"),
    linha(*SP, "1", "Presidente", "25/10/2026 17:05:10", 300, 250, "2", "95", "Branco", 10),
    linha(*SP, "1", "Presidente", "25/10/2026 17:05:10", 300, 250, "3", "96", "Nulo", 20),
    linha(*SP, "3", "Governador", "25/10/2026 17:05:10", 300, 250, "1", "10", "FULANO", 200, "AA"),
    linha(*RR, "1", "Presidente", "#NULO#", 200, 150, "1", "13", "LULA", 70, "PT"),
    linha(*RR, "1", "Presidente", "#NULO#", 200, 150, "1", "22", "FLÁVIO BOLSONARO", 80, "PL"),
]


class TestSecoesDoZip(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.urnas, self.candidatos = filtrar.secoes_do_zip(criar_zip(self.tmp.name, LINHAS))

    def tearDown(self):
        self.tmp.cleanup()

    def test_uma_urna_por_secao_so_com_presidente(self):
        self.assertEqual(len(self.urnas), 2)
        sp = next(u for u in self.urnas if u["uf"] == "SP")
        self.assertEqual(sp["votos"], {"13": 100, "22": 120, "brancos": 10, "nulos": 20})

    def test_campos_da_urna(self):
        sp = next(u for u in self.urnas if u["uf"] == "SP")
        self.assertEqual(sp["municipio"], "SÃO PAULO")
        self.assertEqual((sp["cd_municipio"], sp["zona"], sp["secao"]), ("71072", "1", "10"))
        self.assertEqual((sp["aptos"], sp["comparecimento"], sp["abstencoes"]), (300, 250, 50))
        self.assertEqual(sp["recebido"], "2026-10-25T17:05:10")

    def test_urna_sem_horario_fica_com_none(self):
        rr = next(u for u in self.urnas if u["uf"] == "RR")
        self.assertIsNone(rr["recebido"])

    def test_candidatos_com_nome_e_partido(self):
        self.assertEqual(self.candidatos, {
            "13": {"nome": "LULA", "partido": "PT"},
            "22": {"nome": "FLÁVIO BOLSONARO", "partido": "PL"},
        })


class TestGravar(unittest.TestCase):
    def test_csv_largo_com_uma_coluna_por_votavel(self):
        with tempfile.TemporaryDirectory() as tmp:
            urnas, _ = filtrar.secoes_do_zip(criar_zip(tmp, LINHAS))
            destino = Path(tmp) / "secoes.csv"
            filtrar.gravar(urnas, destino, ["13", "22", "brancos", "nulos"])
            with open(destino, encoding="utf-8", newline="") as f:
                linhas = list(csv.DictReader(f))
        self.assertEqual(len(linhas), 2)
        rr = next(r for r in linhas if r["uf"] == "RR")
        self.assertEqual(rr["recebido"], "")
        self.assertEqual((rr["votos_13"], rr["votos_22"], rr["brancos"], rr["nulos"]), ("70", "80", "0", "0"))


if __name__ == "__main__":
    unittest.main()
