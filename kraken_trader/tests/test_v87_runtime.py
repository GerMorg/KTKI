import ast
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app"


class V87RuntimeTests(unittest.TestCase):
    def test_decision_matrix_persists_blocking_reasons(self):
        source = (APP / "decision_matrix.py").read_text(encoding="utf-8")
        self.assertIn("decision_rule_evaluations", source)
        self.assertIn("blocker=next", source)
        self.assertIn("Tägliches Umschichtungslimit erreicht", source)

if __name__ == "__main__":
    unittest.main()
