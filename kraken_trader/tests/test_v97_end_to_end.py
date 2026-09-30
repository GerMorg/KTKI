import tempfile
import unittest
from decimal import Decimal
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))

from db import DB
from decision_engine_v97 import DecisionEngineV97
from decision_pipeline_v97 import CanonicalDecisionPlannerV97
from decision_runtime_v97 import DecisionRuntimeV97


class V97EndToEndTests(unittest.TestCase):
    def test_new_risk_needs_directional_edge_evidence(self):
        f=tempfile.NamedTemporaryFile(suffix=".db",delete=False);f.close()
        db=DB(f.name);db.init()
        try:
            db.set("decision_min_edge_samples","10")
            engine=DecisionEngineV97(db)
            row={"symbol":"BTC/EUR","signal":"BUY","score":90,"momentum_pct":2,"trend_pct":1,
                 "volatility_pct":2,"buy_threshold":70}
            health={"risk_state":"OK","directions":{"UP":{
                "samples":2,"mean_edge_after_costs_pct":4,"historical_roundtrip_cost_pct":1
            }},"quality_score_by_direction":{"UP":90}}
            cfg={"decision_max_position_pct":10,"decision_cash_reserve_pct":20,
                 "decision_volatility_reference_pct":2,"decision_full_size_edge_pct":2}
            d=engine.build(row,health,1000,0,.5,"BULL",cfg)
            self.assertFalse(d["economic_gate_passed"])
            self.assertEqual(Decimal(d["target_exposure_eur"]),Decimal("0"))
        finally:
            Path(f.name).unlink(missing_ok=True)

    def test_planner_hash_is_environment_independent(self):
        f=tempfile.NamedTemporaryFile(suffix=".db",delete=False);f.close()
        db=DB(f.name);db.init()
        try:
            stamp="2026-09-30T18:00:00+00:00"
            db.upsert_live_price({"symbol":"BTC/EUR","last":"100000","bid":"99900","ask":"100100",
                                  "change_pct":"0","received_at":stamp})
            with db.con() as c:
                c.executescript("""
                CREATE TABLE scanner_results(
                    symbol TEXT PRIMARY KEY,scanned_at TEXT,score TEXT,signal TEXT,
                    momentum_pct TEXT,volatility_pct TEXT,trend_pct TEXT,spread_pct TEXT,
                    volume_quote TEXT,data_points INTEGER,quality TEXT,reasons_json TEXT,news_score TEXT);
                CREATE TABLE market_universe(
                    symbol TEXT PRIMARY KEY,canonical_id TEXT,asset_class TEXT,category TEXT,
                    base_asset TEXT,quote_asset TEXT,source_key TEXT,ordermin TEXT,costmin TEXT);
                """)
                c.execute("INSERT INTO market_universe VALUES(?,?,?,?,?,?,?,?,?)",
                          ("BTC/EUR","btc","currency","crypto_spot","BTC","EUR","BTC/EUR","0","0"))
                c.execute("INSERT INTO scanner_results VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
                          ("BTC/EUR",stamp,"90","BUY","2","2","1","0.1","1",50,"VALID","[]","0"))
            db.set("decision_max_scanner_age_minutes","120")
            planner=CanonicalDecisionPlannerV97(db)
            paper=planner.build(1000,{"BTC/EUR":0},"PAPER")
            real=planner.build(1000,{"BTC/EUR":0},"REAL")
            self.assertEqual(paper["plan_hash"],real["plan_hash"])
            self.assertEqual(paper["decisions"],real["decisions"])
        finally:
            Path(f.name).unlink(missing_ok=True)

    def test_shared_runtime_preparation_reuses_context(self):
        f=tempfile.NamedTemporaryFile(suffix=".db",delete=False);f.close()
        db=DB(f.name);db.init()
        calls={"market":0,"forecast":0}
        def market():
            calls["market"]+=1
            return 3
        def forecasts():
            calls["forecast"]+=1
            return 4
        try:
            db.set("decision_shared_context_reuse_seconds","10")
            runtime=DecisionRuntimeV97(db,market,forecasts)
            first=runtime.prepare(force=True)
            second=runtime.prepare()
            self.assertEqual(calls,{"market":1,"forecast":1})
            self.assertFalse(first["reused"])
            self.assertTrue(second["reused"])
            self.assertEqual(second["market_refresh_count"],3)
            self.assertEqual(second["forecasts_evaluated"],4)
        finally:
            Path(f.name).unlink(missing_ok=True)

    def test_runtime_entrypoint_is_v97(self):
        run=Path(__file__).resolve().parents[2] / "run.sh"
        self.assertIn("v97_main:app",run.read_text(encoding="utf-8"))

    def test_active_v97_gui_contains_portfolio_and_learning_routes(self):
        runtime=(Path(__file__).resolve().parents[1] / "app" / "v97_main.py").read_text(encoding="utf-8")
        self.assertIn('def portfolio_v97',runtime)
        self.assertIn('def lernen_v97',runtime)
        self.assertIn('_v97_chart',runtime)
        self.assertIn('news_learning',runtime)

    def test_portfolio_budget_reserves_cash(self):
        engine=DecisionEngineV97(None)
        rows=[
            {"symbol":"A/EUR","signal":"BUY","score":100,"momentum_pct":2,"trend_pct":1,
             "volatility_pct":2,"buy_threshold":70,"expected_edge_pct":"4","family":"crypto_spot"},
            {"symbol":"B/EUR","signal":"BUY","score":95,"momentum_pct":2,"trend_pct":1,
             "volatility_pct":2,"buy_threshold":70,"expected_edge_pct":"3","family":"crypto_spot"},
        ]
        cfg={"decision_max_position_pct":50,"decision_cash_reserve_pct":20,
             "decision_volatility_reference_pct":2,"decision_full_size_edge_pct":2}
        decisions=engine.target_rows(
            rows,{"crypto_spot":{"quality_score":100,"quality_score_by_direction":{"UP":100}}},
            1000,{"A/EUR":0,"B/EUR":0},cfg,
            {"crypto_spot":{"regime":"BULL"}},{"A/EUR":.2,"B/EUR":.2})
        total=sum(abs(Decimal(x["target_exposure_eur"])) for x in decisions)
        self.assertLessEqual(total,Decimal("800.000001"))


if __name__=="__main__":
    unittest.main()
