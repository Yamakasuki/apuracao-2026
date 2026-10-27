import sys
import unittest
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "pipeline"))
import analisar  # noqa: E402

INICIO = datetime(2026, 10, 25, 17, 0)


def urna(uf, minuto, aptos=100, **votos):
    s = {"13": 0, "22": 0, "brancos": 0, "nulos": 0}
    s.update({k.lstrip("v"): v for k, v in votos.items()})
    return {"uf": uf, "minuto": minuto, "aptos": aptos, "s": s}


class TestMinuto(unittest.TestCase):
    def test_minutos_desde_as_17h(self):
        self.assertEqual(analisar.minuto("2026-10-25T17:05:10", INICIO), 5)
        self.assertEqual(analisar.minuto("2026-10-25T19:00:59", INICIO), 120)

    def test_bu_antes_das_17h_entra_no_minuto_zero(self):
        self.assertEqual(analisar.minuto("2026-10-25T09:30:00", INICIO), 0)

    def test_sem_horario(self):
        self.assertIsNone(analisar.minuto(None, INICIO))


class TestAgrupar(unittest.TestCase):
    def test_demais_candidatos_viram_outros(self):
        votos = {"13": 10, "22": 5, "12": 3, "15": 2, "brancos": 1, "nulos": 4}
        self.assertEqual(analisar.agrupar(votos, ["13", "22"], com_outros=True),
                         {"13": 10, "22": 5, "outros": 5, "brancos": 1, "nulos": 4})

    def test_segundo_turno_sem_outros(self):
        self.assertEqual(analisar.agrupar({"13": 1, "nulos": 2}, ["13", "22"], com_outros=False),
                         {"13": 1, "22": 0, "brancos": 0, "nulos": 2})


class TestLinhaDoTempo(unittest.TestCase):
    def setUp(self):
        urnas = [
            urna("SP", 0, v13=10, v22=5),
            urna("SP", 2, v13=1, v22=20),
            urna("RJ", 2, v13=3, v22=3),
            urna("RJ", None, v13=100),
        ]
        self.lt = analisar.linha_do_tempo(urnas, ["13", "22", "brancos", "nulos"])

    def test_so_minutos_com_urna_nova(self):
        self.assertEqual(self.lt["minutos"], [0, 2])

    def test_brasil_acumula_todas_as_ufs(self):
        br = self.lt["locais"]["BR"]
        self.assertEqual(br["13"], [10, 14])
        self.assertEqual(br["22"], [5, 28])
        self.assertEqual(br["secoes"], [1, 3])
        self.assertEqual(br["aptos"], [100, 300])

    def test_cada_uf_tem_a_propria_serie(self):
        self.assertEqual(self.lt["locais"]["SP"]["13"], [10, 11])
        self.assertEqual(self.lt["locais"]["RJ"]["13"], [0, 3])

    def test_urna_sem_horario_fica_fora(self):
        self.assertEqual(self.lt["locais"]["RJ"]["secoes"], [0, 1])


class TestRitmo(unittest.TestCase):
    def test_votos_por_janela_de_10_min(self):
        self.assertEqual(analisar.ritmo([0, 5, 12, 25], [10, 15, 30, 31], 10, 3), [15, 15, 1])

    def test_janela_vazia_e_zero(self):
        self.assertEqual(analisar.ritmo([0, 25], [10, 31], 10, 3), [10, 0, 21])


class TestEventos(unittest.TestCase):
    def test_virada_picos_e_definido(self):
        a = [10, 20, 30, 60, 100]
        b = [20, 40, 50, 55, 60]
        aptos = [50, 100, 150, 200, 250]
        ev = analisar.eventos(a, b, aptos, 260)
        self.assertEqual(ev["viradas"], [{"i": 3, "lider": "a"}])
        self.assertEqual(ev["pico"], {"a": 4, "b": 1})
        self.assertEqual(ev["definido"], 4)

    def test_empate_nao_e_virada(self):
        self.assertEqual(analisar.eventos([5, 5, 8], [0, 5, 5], [1, 2, 3], 9)["viradas"], [])
        self.assertEqual(analisar.eventos([5, 5, 5], [0, 5, 7], [1, 2, 3], 9)["viradas"], [{"i": 2, "lider": "b"}])

    def test_lado_sem_voto_nao_quebra(self):
        ev = analisar.eventos([3, 7], [0, 0], [10, 20], 20)
        self.assertEqual(ev["pico"], {"a": 1, "b": None})
        self.assertEqual(ev["viradas"], [])

    def test_serie_vazia(self):
        self.assertEqual(analisar.eventos([], [], [], 0), {"viradas": [], "pico": {"a": None, "b": None}, "definido": None})


class TestGerar(unittest.TestCase):
    def setUp(self):
        def bruta(uf, mun, recebido, aptos, comp, **votos):
            return {"uf": uf, "cd_municipio": mun, "municipio": f"CIDADE {mun}", "zona": "1", "secao": "1",
                    "recebido": recebido, "aptos": aptos, "comparecimento": comp, "abstencoes": aptos - comp,
                    "votos": {k.lstrip("v"): v for k, v in votos.items()}}
        urnas = [
            bruta("SP", "1", "2026-10-25T17:01:00", 100, 90, v13=30, v22=50, vbrancos=5, vnulos=5),
            bruta("BA", "2", "2026-10-25T17:31:00", 100, 80, v13=60, v22=10, vbrancos=4, vnulos=6),
            bruta("ZZ", "3", "2026-10-25T12:00:00", 10, 5, v13=2, v22=3),
            bruta("BA", "2", None, 50, 40, v13=30, v22=10),
        ]
        candidatos = {"13": {"nome": "LULA", "partido": "PT"}, "22": {"nome": "FULANO", "partido": "PL"}}
        self.resumo, self.linha, self.municipios = analisar.gerar(urnas, candidatos, 2026, 2)

    def test_resumo_com_totais_e_candidatos_em_ordem(self):
        self.assertEqual([c["numero"] for c in self.resumo["candidatos"]], ["13", "22"])
        self.assertEqual(self.resumo["candidatos"][0]["votos"], 122)
        br = self.resumo["totais"]["BR"]
        self.assertEqual((br["secoes"], br["aptos"], br["comparecimento"]), (4, 260, 215))
        self.assertEqual(self.resumo["secoes_sem_horario"], 1)
        self.assertEqual(self.resumo["series"], ["13", "22", "brancos", "nulos"])

    def test_linha_do_tempo_com_eventos_por_local(self):
        self.assertEqual(self.linha["minutos"], [0, 1, 31])
        br = self.linha["locais"]["BR"]
        self.assertEqual(br["13"], [2, 32, 92])
        self.assertEqual(br["eventos"]["viradas"], [{"i": 2, "lider": "13"}])
        self.assertEqual(br["eventos"]["pico"], {"13": 2, "22": 1})
        self.assertNotIn("aptos", br)

    def test_municipios(self):
        self.assertEqual(self.municipios["colunas"][:5], ["uf", "codigo", "nome", "aptos", "comparecimento"])
        ba = next(l for l in self.municipios["linhas"] if l[0] == "BA")
        self.assertEqual(ba[1:5], ["2", "CIDADE 2", 150, 120])


if __name__ == "__main__":
    unittest.main()
