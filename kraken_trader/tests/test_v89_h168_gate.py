import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app"


class V89H168GateTests(unittest.TestCase):
    def _db(self):
        from db import DB
        handle = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        handle.close()
        db = DB(handle.name)
        db.init()
        with db.con() as c:
            c.executescript("""
                CREATE TABLE research_forecasts(
                    id INTEGER PRIMARY KEY,
                    family TEXT NOT NULL,
                    horizon_hours INTEGER NOT NULL,
                    direction TEXT NOT NULL,
                    features_json TEXT NOT NULL
                );
                CREATE TABLE forecast_evaluations(
                    forecast_id INTEGER PRIMARY KEY,
                    actual_return_pct TEXT NOT NULL,
                    direction_correct INTEGER NOT NULL
                );
            """)
            for i in range(1, 21):
                c.execute(
                    "INSERT INTO research_forecasts VALUES(?,?,?,?,?)",
                    (i, "crypto_spot", 24, "UP", json.dumps({"estimated_roundtrip_cost_pct": 0.1})),
                )
                c.execute(
                    "INSERT INTO forecast_evaluations VALUES(?,?,?)",
                    (i, "1.0", 1),
                )
        return db, handle.name

    def test_h168_is_advisory_for_real_execution(self):
        import sys
        sys.path.insert(0, str(APP))
        from model_health import ModelHealth

        db, path = self._db()
        try:
            health = ModelHealth(db)
            execution = health.evaluate("crypto_spot", require_long_horizon=False)
            self.assertEqual(execution["status"], "READY")
            self.assertEqual(execution["execution_gate"], "H24_ONLY")
            self.assertFalse(execution["h168_advisory_ready"])
            self.assertEqual(execution["horizons"]["168"]["samples"], 0)

            general = health.evaluate("crypto_spot", require_long_horizon=True)
            self.assertEqual(general["status"], "READY")
        finally:
            Path(path).unlink(missing_ok=True)

    def test_v90_runtime_and_version_are_active(self):
        run_sh = (ROOT / "run.sh").read_text(encoding="utf-8")
        version = (APP / "version.py").read_text(encoding="utf-8")
        config = (ROOT / "config.yaml").read_text(encoding="utf-8")
        repository = (ROOT.parent / "repository.yaml").read_text(encoding="utf-8")
        runtime = (APP / "v97_main.py").read_text(encoding="utf-8")
        self.assertIn("v97_main:app", run_sh)
        self.assertNotIn("v89_main:app", run_sh)
        self.assertIn("0.1.0-dev.97", version)
        self.assertIn("version: 0.1.0-dev.97", config)
        self.assertIn("version: 0.1.0-dev.97", repository)
        self.assertIn('H24', runtime)


if __name__ == "__main__":
    unittest.main()
