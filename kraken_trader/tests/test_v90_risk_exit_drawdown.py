import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app"


class V92RiskExitDrawdownTests(unittest.TestCase):
    def _db(self):
        from db import DB
        handle = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        handle.close()
        db = DB(handle.name)
        db.init()
        return db, handle.name

    def test_configurable_max_drawdown_controls_health_gate(self):
        import sys
        sys.path.insert(0, str(APP))
        from model_health import ModelHealth

        db, path = self._db()
        try:
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
                values = [10.0, -15.0, 10.0]
                for i, value in enumerate(values, 1):
                    c.execute(
                        "INSERT INTO research_forecasts VALUES(?,?,?,?,?)",
                        (i, "crypto_spot", 24, "UP", json.dumps({"estimated_roundtrip_cost_pct": 0.0})),
                    )
                    c.execute(
                        "INSERT INTO forecast_evaluations VALUES(?,?,?)",
                        (i, str(value), 1),
                    )
            health = ModelHealth(db)
            strict = health.evaluate("crypto_spot", min_samples=3, max_drawdown_pct=-10, require_long_horizon=False)
            relaxed = health.evaluate("crypto_spot", min_samples=3, max_drawdown_pct=-30, require_long_horizon=False)
            self.assertEqual(strict["status"], "READY")
            self.assertEqual(relaxed["status"], "READY")
            self.assertAlmostEqual(strict["horizons"]["24"]["max_drawdown_pct"], -13.6363636364, places=6)
            self.assertEqual(strict["risk_state"], "CAUTION")
        finally:
            Path(path).unlink(missing_ok=True)

    def test_exit_risk_override_does_not_disable_other_real_safety_gates(self):
        import sys
        sys.path.insert(0, str(APP))
        from decision_matrix import DecisionMatrix

        db, path = self._db()
        try:
            matrix = DecisionMatrix(db)
            context = {
                "canonical_id": "BTC/EUR",
                "confirmation_count": 1,
                "confirmation_required": 1,
                "minimum_hold_ok": True,
                "cooldown_ok": True,
                "daily_limit_ok": True,
                "improvement_after_costs": "-5",
                "tax_loss_ok": True,
                "data_fresh": True,
                "exit_risk_override": True,
                "model_health_ok": False,
                "model_health_details": {"status": "NOT_READY"},
                "route_cost_ok": True,
                "quote_funding_ok": True,
                "portfolio_risk_ok": True,
                "order_constraints_ok": True,
                "real_trading_enabled": True,
                "real_kill_switch_clear": True,
                "real_limits_ok": True,
                "real_balance_ok": True,
            }
            decision = matrix.evaluate("BTC/EUR", "SELL", context, "REAL")
            self.assertTrue(decision["allowed"])
            self.assertTrue(all(x["passed"] for x in decision["checks"]))
            keys = {x["rule_key"]: x for x in decision["checks"]}
            self.assertTrue(keys["MODEL_HEALTH"]["passed"])
            self.assertTrue(keys["POSITIVE_AFTER_COSTS"]["passed"])
        finally:
            Path(path).unlink(missing_ok=True)

    def test_v91_runtime_exposes_risk_configuration(self):
        run_sh = (ROOT / "run.sh").read_text(encoding="utf-8")
        version = (APP / "version.py").read_text(encoding="utf-8")
        config = (ROOT / "config.yaml").read_text(encoding="utf-8")
        runtime = (APP / "v95_main.py").read_text(encoding="utf-8")
        self.assertIn("v95_main:app", run_sh)
        self.assertIn("0.1.0-dev.95", version)
        self.assertIn("real_balancing_max_drawdown_pct", config)
        self.assertIn('h168', runtime.lower())
        self.assertIn('margin', runtime)
        self.assertIn("existing_position_exit", runtime)


if __name__ == "__main__":
    unittest.main()
