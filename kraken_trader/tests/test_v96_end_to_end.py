import json
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"app"))

from db import DB
from decision_engine_v96 import DecisionEngineV96
from execution_plan_v96 import build_execution_intent
from order_math_v96 import volume_for_eur, order_constraints
from trade_guard_v96 import TradeGuardV96
from decision_pipeline_v96 import CanonicalDecisionPlannerV96


class V96EndToEndTests(unittest.TestCase):
    def test_new_risk_requires_positive_edge_after_current_roundtrip_cost(self):
        e=DecisionEngineV96(None)
        row={"symbol":"BTC/EUR","signal":"BUY","score":90,"momentum_pct":2,"trend_pct":1,"volatility_pct":2,"buy_threshold":70}
        cfg={"decision_minimum_score":70,"decision_max_position_pct":5,"decision_cash_reserve_pct":20,
             "decision_volatility_reference_pct":2,"decision_full_size_edge_pct":2,
             "decision_max_trade_eur":250}
        d=e.build(row,{"quality_score":80,"quality_score_by_direction":{"UP":80}},
                  1000,0,1.1,"BULL",cfg)
        self.assertFalse(d["economic_gate_passed"])
        self.assertEqual(Decimal(d["target_exposure_eur"]),Decimal("0"))

    def test_positive_net_edge_drives_target_size(self):
        e=DecisionEngineV96(None)
        row={"symbol":"BTC/EUR","signal":"BUY","score":90,"momentum_pct":2,"trend_pct":1,"volatility_pct":2,"buy_threshold":70,
             "expected_edge_pct":"2.0"}
        cfg={"decision_minimum_score":70,"decision_max_position_pct":10,"decision_cash_reserve_pct":20,
             "decision_volatility_reference_pct":2,"decision_full_size_edge_pct":2,"decision_max_trade_eur":250}
        d=e.build(row,{"quality_score":80,"quality_score_by_direction":{"UP":80}},
                  1000,0,.5,"BULL",cfg)
        self.assertTrue(d["economic_gate_passed"])
        self.assertEqual(Decimal(d["expected_edge_after_costs_pct"]),Decimal("1.5"))
        self.assertGreater(Decimal(d["target_exposure_eur"]),Decimal("0"))

    def test_avoid_is_flat_without_explicit_short_permission(self):
        e=DecisionEngineV96(None)
        row={"symbol":"BTC/EUR","signal":"AVOID","score":20,"momentum_pct":-2,"trend_pct":-1,"volatility_pct":2}
        cfg={"decision_minimum_score":70,"decision_max_position_pct":5,"decision_cash_reserve_pct":20,
             "decision_volatility_reference_pct":2,"decision_full_size_edge_pct":2}
        d=e.build(row,{},1000,100,.2,"BEAR",cfg)
        self.assertEqual(d["direction"],"FLAT")
        self.assertEqual(d["action"],"SELL")
        self.assertEqual(Decimal(d["target_exposure_eur"]),Decimal("0"))

    def test_hold_is_capped_by_portfolio_position_limit(self):
        e=DecisionEngineV96(None)
        row={"symbol":"BTC/EUR","signal":"HOLD","score":50,"momentum_pct":0,"trend_pct":0,"volatility_pct":2}
        cfg={"decision_max_position_pct":5,"decision_cash_reserve_pct":20}
        d=e.build(row,{},1000,100,.2,"NEUTRAL",cfg)
        self.assertEqual(Decimal(d["target_exposure_eur"]),Decimal("40"))
        self.assertEqual(d["action"],"SELL")

    def test_risk_reduction_is_allowed_without_positive_entry_edge(self):
        e=DecisionEngineV96(None)
        row={"symbol":"BTC/EUR","signal":"BUY","score":75,"momentum_pct":1,"trend_pct":.1,"volatility_pct":2,"buy_threshold":70}
        cfg={"decision_minimum_score":70,"decision_max_position_pct":5,"decision_cash_reserve_pct":20,
             "decision_volatility_reference_pct":2,"decision_full_size_edge_pct":2}
        d=e.build(row,{},1000,50,.2,"BEAR",cfg,existing=True)
        self.assertEqual(d["action"],"SELL")
        self.assertTrue(d["economic_gate_passed"])

    def test_short_entry_requires_explicit_capability(self):
        e=DecisionEngineV96(None)
        row={"symbol":"BTC/EUR","signal":"AVOID","score":10,"momentum_pct":-3,"trend_pct":-2,"volatility_pct":2,
             "avoid_threshold":35,"expected_edge_pct":"2"}
        cfg={"decision_max_position_pct":5,"decision_cash_reserve_pct":20,"decision_volatility_reference_pct":2,
             "decision_full_size_edge_pct":2,"decision_max_trade_eur":250}
        d=e.build(row,{},1000,0,.2,"BEAR",cfg,allow_short=True)
        self.assertEqual(d["direction"],"SHORT")
        self.assertLess(Decimal(d["target_exposure_eur"]),Decimal("0"))
        intent=build_execution_intent(
            d,{"status":"VALID","buy":{},"sell":{}},
            {},{"decision_max_leverage":3,"decision_confidence_spot_min":65,
            "decision_confidence_margin_2x":78,"decision_confidence_margin_3x":86,
            "decision_confidence_margin_4x":93,"decision_confidence_margin_5x":97,
            "decision_max_trade_eur":250},"REAL",margin_capable=False,short_capable=False)
        self.assertEqual(intent["status"],"BLOCKED")
        self.assertEqual(intent["reason"],"NO_VALID_EXECUTION_ROUTE")

    def test_order_math_uses_side_aware_fx(self):
        tickers={
            "BTC/USD":{"b":["99000"],"a":["100000"],"c":["99500"]},
            "EUR/USD":{"b":["1.10"],"a":["1.11"],"c":["1.105"]},
        }
        v_buy,p_buy,q_buy=volume_for_eur(tickers,"BTC/USD","BUY",100)
        v_sell,p_sell,q_sell=volume_for_eur(tickers,"BTC/USD","SELL",100)
        self.assertEqual(q_buy,"USD")
        self.assertGreater(v_buy,Decimal("0"))
        self.assertGreater(v_sell,Decimal("0"))
        self.assertNotEqual(v_buy,v_sell)

    def test_common_trade_guard_is_environment_scoped(self):
        f=tempfile.NamedTemporaryFile(suffix=".db",delete=False);f.close()
        db=DB(f.name);db.init()
        try:
            paper=TradeGuardV96(db,"PAPER")
            real=TradeGuardV96(db,"REAL")
            p=paper.check("BTC/EUR","BUY")
            r=real.check("BTC/EUR","BUY")
            self.assertEqual(p["confirmation_count"],1)
            self.assertEqual(r["confirmation_count"],1)
        finally:
            Path(f.name).unlink(missing_ok=True)

    def _plan_db(self):
        f=tempfile.NamedTemporaryFile(suffix=".db",delete=False);f.close()
        db=DB(f.name);db.init()
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
        return f,db

    def test_paper_and_real_planner_use_same_plan_hash_for_same_inputs(self):
        f,db=self._plan_db()
        try:
            nowv="2026-09-30T18:00:00+00:00"
            db.set("decision_max_scanner_age_minutes",120)
            db.upsert_live_price({"symbol":"BTC/EUR","last":"100000","bid":"99900","ask":"100100","change_pct":"0","received_at":nowv})
            with db.con() as c:
                c.execute("INSERT INTO market_universe VALUES(?,?,?,?,?,?,?,?,?)",
                          ("BTC/EUR","btc","currency","crypto_spot","BTC","EUR","BTC/EUR","0","0"))
                c.execute("INSERT INTO scanner_results VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
                          ("BTC/EUR",nowv,"90","BUY","2","2","1","0.1","1",50,"VALID","[]","0"))
            planner=CanonicalDecisionPlannerV96(db)
            # No forecast evidence means no new risk; that is intentional and still
            # must produce identical planning inputs/hash in both environments.
            p=planner.build(1000,{"BTC/EUR":0},"PAPER")
            r=planner.build(1000,{"BTC/EUR":0},"REAL")
            self.assertEqual(p["plan_hash"],r["plan_hash"])
            self.assertEqual(p["decisions"],r["decisions"])
        finally:
            Path(f.name).unlink(missing_ok=True)

    def test_portfolio_normalization_never_exceeds_budget(self):
        e=DecisionEngineV96(None)
        rows=[]
        for symbol in ("A/EUR","B/EUR","C/EUR"):
            rows.append({"symbol":symbol,"signal":"BUY","score":100,"momentum_pct":2,"trend_pct":1,
                         "volatility_pct":2,"buy_threshold":70,"expected_edge_pct":"4","family":"crypto_spot"})
        cfg={"decision_minimum_score":70,"decision_max_position_pct":50,"decision_cash_reserve_pct":20,
             "decision_volatility_reference_pct":2,"decision_full_size_edge_pct":2}
        ds=e.target_rows(rows,{"crypto_spot":{"quality_score":100,"quality_score_by_direction":{"UP":100}}},
                         1000,{x:0 for x in ("A/EUR","B/EUR","C/EUR")},cfg,
                         {"crypto_spot":{"regime":"BULL"}},{x:.2 for x in ("A/EUR","B/EUR","C/EUR")})
        total=sum(abs(Decimal(x["target_exposure_eur"])) for x in ds)
        self.assertLessEqual(total,Decimal("800.000001"))

if __name__=="__main__":
    unittest.main()
