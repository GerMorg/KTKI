import tempfile
import unittest
from decimal import Decimal
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"app"))

from db import DB
from decision_engine_v98 import DecisionEngineV98
from decision_pipeline_v98 import CanonicalDecisionPlannerV98
from decision_runtime_v98 import DecisionRuntimeV98
from decision_context_v98 import alternatives, routes_for_symbol
from real_trade import RealTradeEngine
from trade_thresholds_v98 import trade_thresholds


class DummyClient:
    def balance(self): return {}
    def add_order(self, **kwargs): return {"txid":["TEST"],"descr":kwargs}


class V98RealOrderPathTests(unittest.TestCase):
    def db(self):
        f=tempfile.NamedTemporaryFile(suffix=".db",delete=False);f.close()
        db=DB(f.name);db.init()
        return f,db

    def test_xstock_symbol_case_is_preserved_for_routes(self):
        f,db=self.db()
        try:
            with db.con() as c:
                c.execute("""CREATE TABLE market_universe(
                    symbol TEXT,asset_class TEXT,category TEXT,base_asset TEXT,
                    quote_asset TEXT,source_key TEXT,ordermin TEXT,costmin TEXT,
                    canonical_id TEXT)""")
                c.execute("INSERT INTO market_universe VALUES(?,?,?,?,?,?,?,?,?)",
                          ("TSLAx/USD","tokenized_asset","xstocks","TSLAx","USD","TSLAx/USD","0.01","0.1","xstock:TSLAX"))
            alts=alternatives(db,"TSLAX/USD")
            self.assertEqual(alts[0]["symbol"],"TSLAx/USD")
            routes=routes_for_symbol(
                db,"TSLAX/USD",
                {"TSLAx/USD":{"b":["355.75"],"a":["355.81"],"c":["355.89"]},
                 "EUR/USD":{"b":["1.12872"],"a":["1.12878"],"c":["1.12872"]}},
                40,10,10,
            )
            self.assertEqual(routes["status"],"VALID")
            self.assertEqual(routes["buy"]["market"]["symbol"],"TSLAx/USD")
        finally:
            Path(f.name).unlink(missing_ok=True)

    def test_real_engine_resolves_uppercase_xstock_input(self):
        f,db=self.db()
        try:
            with db.con() as c:
                c.execute("""CREATE TABLE market_universe(
                    symbol TEXT,asset_class TEXT,category TEXT,base_asset TEXT,
                    quote_asset TEXT,source_key TEXT,ordermin TEXT,costmin TEXT)""")
                c.execute("INSERT INTO market_universe VALUES(?,?,?,?,?,?,?,?)",
                          ("TSLAx/USD","tokenized_asset","xstocks","TSLAx","USD","TSLAx/USD","0.01","0.1"))
                c.execute("""CREATE TABLE IF NOT EXISTS live_prices(
                    symbol TEXT,last TEXT,bid TEXT,ask TEXT,received_at TEXT)""")
                c.execute("INSERT INTO live_prices(symbol,last,bid,ask,change_pct,received_at) VALUES(?,?,?,?,?,?)",
                          ("TSLAx/USD","355.89","355.75","355.81","0","2026-10-01T14:00:00+00:00"))
            engine=RealTradeEngine(db,DummyClient())
            self.assertEqual(engine._resolve_symbol("TSLAX/USD"),"TSLAx/USD")
            self.assertEqual(engine._pair("TSLAX/USD")["symbol"],"TSLAx/USD")
        finally:
            Path(f.name).unlink(missing_ok=True)

    def test_directional_up_evidence_survives_weak_family_status(self):
        f,db=self.db()
        try:
            db.set("decision_min_edge_samples","10")
            engine=DecisionEngineV98(db)
            row={"symbol":"MEGA/USD","signal":"BUY","score":"81.5667",
                 "momentum_pct":"8.011735","trend_pct":"4.55011",
                 "volatility_pct":"7.271433","buy_threshold":"65",
                 "family":"crypto_spot"}
            health={"status":"WEAK","risk_state":"WEAK",
                    "directions":{"UP":{"samples":275,"mean_edge_after_costs_pct":0.6205,
                                         "historical_roundtrip_cost_pct":1.7914,
                                         "worst_sample_pct":-46.24}},
                    "quality_score_by_direction":{"UP":62.65}}
            cfg={"decision_max_position_pct":10,"decision_cash_reserve_pct":20,
                 "decision_volatility_reference_pct":2,"decision_full_size_edge_pct":2,
                 "decision_max_drawdown_pct":-50}
            d=engine.build(row,health,46.194649,0,1.247923,"BULL",cfg)
            self.assertTrue(d["economic_gate_passed"])
            self.assertEqual(d["direction"],"LONG")
            self.assertGreater(Decimal(d["target_exposure_eur"]),Decimal("0"))
            self.assertGreater(Decimal(d["expected_edge_after_costs_pct"]),Decimal("0"))
        finally:
            Path(f.name).unlink(missing_ok=True)

    def test_entry_minimum_is_capped_by_small_account_position_limit(self):
        result=trade_thresholds(Decimal("2.20"),Decimal("0"),Decimal("46.194649"),Decimal("5"),Decimal("2"),Decimal("5"))
        self.assertTrue(result["allowed"])
        self.assertAlmostEqual(float(result["minimum_eur"]),46.194649*0.05,places=8)

    def test_entry_is_not_blocked_by_portfolio_percentage_hysteresis(self):
        self.assertTrue(trade_thresholds(Decimal("10"),Decimal("0"),Decimal("1000"),Decimal("5"),Decimal("2"),Decimal("5"))["allowed"])
        self.assertFalse(trade_thresholds(Decimal("0.10"),Decimal("10"),Decimal("1000"),Decimal("0.1"),Decimal("2"),Decimal("5"))["allowed"])

    def test_positive_edge_can_reach_small_account_entry_floor(self):
        f,db=self.db()
        try:
            db.set("decision_min_edge_samples","10")
            e=DecisionEngineV98(db)
            row={"symbol":"AAVE/EUR","signal":"BUY","score":"72","momentum_pct":"4",
                 "trend_pct":"3","volatility_pct":"3","buy_threshold":"65","family":"crypto_spot"}
            health={"risk_state":"WEAK","directions":{"UP":{"samples":30,"mean_edge_after_costs_pct":2.0,
                      "historical_roundtrip_cost_pct":1.0,"worst_sample_pct":-10}},
                    "quality_score_by_direction":{"UP":70}}
            cfg={"decision_min_edge_samples":10,"decision_max_position_pct":5,
                 "decision_cash_reserve_pct":20,"decision_volatility_reference_pct":2,
                 "decision_full_size_edge_pct":2,"decision_max_drawdown_pct":-25,
                 "decision_min_trade_eur":5}
            d=e.build(row,health,46.194649,0,1.0,"BULL",cfg)
            self.assertGreaterEqual(Decimal(d["target_exposure_eur"]),Decimal("2.30973245"))
            self.assertGreater(Decimal(d["expected_edge_after_costs_pct"]),0)
        finally:
            Path(f.name).unlink(missing_ok=True)

    def test_planner_hash_is_environment_independent(self):
        f,db=self.db()
        try:
            stamp="2026-10-01T14:00:00+00:00"
            db.upsert_live_price({"symbol":"BTC/EUR","last":"100000","bid":"99900","ask":"100100","change_pct":"0","received_at":stamp})
            with db.con() as c:
                c.executescript("""CREATE TABLE scanner_results(
                    symbol TEXT PRIMARY KEY,scanned_at TEXT,score TEXT,signal TEXT,momentum_pct TEXT,
                    volatility_pct TEXT,trend_pct TEXT,spread_pct TEXT,volume_quote TEXT,data_points INTEGER,
                    quality TEXT,reasons_json TEXT,news_score TEXT);
                CREATE TABLE market_universe(
                    symbol TEXT,asset_class TEXT,category TEXT,base_asset TEXT,quote_asset TEXT,
                    source_key TEXT,ordermin TEXT,costmin TEXT,canonical_id TEXT);""")
                c.execute("INSERT INTO market_universe VALUES(?,?,?,?,?,?,?,?,?)",
                          ("BTC/EUR","currency","crypto_spot","BTC","EUR","BTC/EUR","0","0","btc"))
                c.execute("INSERT INTO scanner_results VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
                          ("BTC/EUR",stamp,"90","BUY","2","2","1","0.1","1",50,"VALID","[]","0"))
            db.set("decision_max_scanner_age_minutes","120")
            planner=CanonicalDecisionPlannerV98(db)
            p=planner.build(1000,{"BTC/EUR":0},"PAPER")
            r=planner.build(1000,{"BTC/EUR":0},"REAL")
            self.assertEqual(p["plan_hash"],r["plan_hash"])
            self.assertEqual(p["decisions"],r["decisions"])
        finally:
            Path(f.name).unlink(missing_ok=True)

    def test_runtime_entrypoint_is_v98(self):
        self.assertIn("v98_main:app",(ROOT/"run.sh").read_text(encoding="utf-8"))
        self.assertIn("v98_main:app",(ROOT.parents[0]/"run.sh").read_text(encoding="utf-8"))

    def test_shared_runtime_preparation_reuses_context(self):
        f,db=self.db();calls={"market":0,"forecast":0}
        def market(): calls["market"]+=1;return 2
        def forecasts(): calls["forecast"]+=1;return 3
        try:
            db.set("decision_shared_context_reuse_seconds","10")
            rt=DecisionRuntimeV98(db,market,forecasts)
            self.assertFalse(rt.prepare(force=True)["reused"])
            self.assertTrue(rt.prepare()["reused"])
            self.assertEqual(calls,{"market":1,"forecast":1})
        finally:
            Path(f.name).unlink(missing_ok=True)


if __name__=="__main__":
    unittest.main()
