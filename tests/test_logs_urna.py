import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "pipeline"))
import logs_urna  # noqa: E402

LOG = "\n".join([
    "Inicio\tlinha sem data no começo",
    "04/10/2026 08:00:01\tINFO\t1\tVOTA\tUrna pronta para receber votos\tX",
    "04/10/2026 16:59:59\tINFO\t1\tVOTA\tO voto do eleitor foi computado\tX",
    "04/10/2026 17:20:10\tINFO\t1\tVOTA\tO voto do eleitor foi computado\tX",
    "04/10/2026 17:30:00\tINFO\t1\tVOTA\tProcedimento de encerramento confirmado\tX",
    "25/10/2026 08:00:02\tINFO\t1\tVOTA\tUrna pronta para receber votos\tX",
    "25/10/2026 10:00:01\tINFO\t1\tVOTA\tO voto do eleitor foi computado\tX",
    "25/10/2026 18:45:00\tINFO\t1\tVOTA\tO voto do eleitor foi computado\tX",
    "25/10/2026 18:50:00\tINFO\t1\tVOTA\tProcedimento de encerramento confirmado\tX",
]).encode("latin-1")


class TestLog(unittest.TestCase):
    def test_fatos_de_cada_turno(self):
        r = logs_urna.contar(LOG)
        self.assertEqual(r["1"], {"votos": 2, "abertura": "08:00:01", "encerramento": "17:30:00",
                                  "tarde": ["16:59:59", "17:20:10"]})
        self.assertEqual(r["2"], {"votos": 2, "abertura": "08:00:02", "encerramento": "18:50:00", "tarde": ["18:45:00"]})

    def test_log_sem_o_primeiro_turno(self):
        r = logs_urna.contar(LOG.split(b"\n", 4)[4])
        self.assertEqual(r["1"]["votos"], 0)
        self.assertIsNone(r["1"]["abertura"])


if __name__ == "__main__":
    unittest.main()
