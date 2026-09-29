import ast
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app"


class V87RuntimeTests(unittest.TestCase):
    def test_active_runtime_is_v88(self):
        run_sh = (ROOT / "run.sh").read_text(encoding="utf-8")
        self.assertIn("v89_main:app", run_sh)
        self.assertNotIn("v87_main:app", run_sh)

    def test_v87_entrypoint_keeps_v86_baseline_and_exposes_health(self):
        source = (APP / "v87_main.py").read_text(encoding="utf-8")
        self.assertIn("import v86_main as base", source)
        self.assertIn('"/v87-health"', source)
        self.assertIn("blockers", source)
        self.assertIn("blocked_decisions", source)
        ast.parse(source, filename="v87_main.py")

    def test_real_trade_gui_is_replaced_with_diagnostic_view(self):
        source = (APP / "v87_main.py").read_text(encoding="utf-8")
        self.assertIn('app.view_functions["real_trade.view"]', source)
        self.assertIn("Blockierte Kandidaten / Regelprüfungen", source)
        self.assertIn("DAILY_SUBMISSION_LIMIT", source)
        self.assertIn("private_execution_events", source)
        self.assertIn("SUBMITTED", source)

    def test_decision_matrix_persists_blocking_reasons(self):
        source = (APP / "decision_matrix.py").read_text(encoding="utf-8")
        self.assertIn("decision_rule_evaluations", source)
        self.assertIn("blocker=next", source)
        self.assertIn("Tägliches Umschichtungslimit erreicht", source)

    def test_version_metadata_is_v88(self):
        self.assertIn("0.1.0-dev.89", (APP / "version.py").read_text(encoding="utf-8"))
        self.assertIn("version: 0.1.0-dev.89", (ROOT / "config.yaml").read_text(encoding="utf-8"))
        self.assertIn("version: 0.1.0-dev.89", (ROOT.parent / "repository.yaml").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
