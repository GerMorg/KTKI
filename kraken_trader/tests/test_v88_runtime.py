import ast
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app"


class V88RuntimeTests(unittest.TestCase):
    def test_active_runtime_is_v88(self):
        run_sh = (ROOT / "run.sh").read_text(encoding="utf-8")
        self.assertIn("v90_main:app", run_sh)
        self.assertNotIn("v87_main:app", run_sh)

    def test_v88_entrypoint_keeps_v87_diagnostics(self):
        source = (APP / "v88_main.py").read_text(encoding="utf-8")
        self.assertIn("import v87_main as base", source)
        self.assertIn('"/v88-health"', source)
        ast.parse(source, filename="v88_main.py")

    def test_v87_daily_submission_evidence_is_retained(self):
        source = (APP / "v87_main.py").read_text(encoding="utf-8")
        self.assertIn("DAILY_SUBMISSION_LIMIT", source)
        self.assertIn("private_execution_events", source)
        self.assertIn("Keine eingereichten Live-Aufträge heute.", source)
        self.assertIn("SUBMITTED", source)

    def test_version_metadata_is_v88(self):
        self.assertIn("0.1.0-dev.90", (APP / "version.py").read_text(encoding="utf-8"))
        self.assertIn("version: 0.1.0-dev.90", (ROOT / "config.yaml").read_text(encoding="utf-8"))
        self.assertIn("version: 0.1.0-dev.90", (ROOT.parent / "repository.yaml").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
