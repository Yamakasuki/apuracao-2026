import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "pipeline"))
import logs_urna  # noqa: E402

LOG = "\n".join([
    "04/10/2026 16:59:59\tINFO\t1\tVOTA\tO voto do eleitor foi computado\tX",
    "04/10/2026 17:00:00\tINFO\t1\tVOTA\tO voto do eleitor foi computado\tX",
    "04/10/2026 17:20:10\tINFO\t1\tVOTA\tO voto do eleitor foi computado\tX",
    "25/10/2026 10:00:00\tINFO\t1\tVOTA\tVoto confirmado para [Presidente]\tX",
    "25/10/2026 10:00:01\tINFO\t1\tVOTA\tO voto do eleitor foi computado\tX",
    "25/10/2026 18:45:00\tINFO\t1\tVOTA\tO voto do eleitor foi computado\tX",
    "25/10/2026 18:50:00\tINFO\t1\tVOTA\tProcedimento de encerramento confirmado\tX",
]).encode("latin-1")


class TestLog(unittest.TestCase):
    def test_conta_votos_e_os_depois_do_fechamento_por_turno(self):
        r = logs_urna.contar(LOG, fechamento=17)
        self.assertEqual({k: r["1"][k] for k in ("votos", "depois", "ultimo")}, {"votos": 3, "depois": 2, "ultimo": "17:20:10"})
        self.assertEqual({k: r["2"][k] for k in ("votos", "depois", "ultimo")}, {"votos": 2, "depois": 1, "ultimo": "18:45:00"})

    def test_faixas_de_10_min_depois_do_fechamento(self):
        r = logs_urna.contar(LOG, fechamento=17)
        self.assertEqual(r["1"]["faixas"][:3], [1, 0, 1])
        self.assertEqual(r["2"]["faixas"][10], 1)  # 18:45 = 105 min depois

    def test_fuso_do_estado(self):
        # no AM a urna fecha às 16h locais (17h de Brasília)
        self.assertEqual(logs_urna.contar(LOG, fechamento=16)["2"]["depois"], 1)
        self.assertEqual(logs_urna.FECHAMENTO_LOCAL.get("AM"), 16)
        self.assertEqual(logs_urna.FECHAMENTO_LOCAL.get("AC"), 15)

    def test_log_sem_o_primeiro_turno(self):
        r = logs_urna.contar(LOG.split(b"\n", 3)[3], fechamento=17)
        self.assertEqual(r["1"]["votos"], 0)
        self.assertIsNone(r["1"]["ultimo"])


if __name__ == "__main__":
    unittest.main()
