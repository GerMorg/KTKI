from decimal import Decimal
from pathlib import Path
import re,tempfile

from autonomous_trader.config import Config,ABSOLUTE_CAPS
from autonomous_trader.db import Database
from autonomous_trader.execution import KrakenExecutor,PreTrade,OrderSpamGuard
from autonomous_trader.kraken import KrakenAPIError,SpotClient,FuturesClient
from autonomous_trader.learning import Learner
from autonomous_trader.models import Decision,DecisionAction,Instrument,OrderIntent,OrderState,Signal
from autonomous_trader.risk import RiskEngine

def config(**kw):
    base=dict(start_capital_eur=Decimal("50"),news_enabled=False,gemini_enabled=False,max_leverage=Decimal("5"),
              max_margin_pct=Decimal("25"),max_position_risk_pct=Decimal("2"),cash_reserve_pct=Decimal("20"),
              max_gross_exposure_pct=Decimal("100"),max_net_exposure_pct=Decimal("75"),
              daily_loss_limit_pct=Decimal("5"),max_drawdown_pct=Decimal("15"),max_slippage_pct=Decimal("0.75"))
    base.update(kw);return Config(**base)

def test_immutable_caps_and_50_eur_sizing():
    c=config();assert c.minimum_confidence==Decimal("0.55");assert ABSOLUTE_CAPS["max_leverage"]==Decimal("10")
    r=RiskEngine(c);signal=Signal("BTC/EUR","long",Decimal("0.8"),Decimal("0.2"),Decimal("0.03"),Decimal("0.8"),Decimal("0.2"),"TREND_UP",
                                  features={"realized_volatility":"0.03","downside_volatility":"0.02"})
    size,block=r.size(signal,{"equity":"50","gross_exposure":"0","net_exposure":"0"},Decimal("2"))
    assert not block and Decimal("0")<size<=Decimal("40")

def test_client_order_id_is_kraken_compatible_uuid():
    intent=OrderIntent("c","d","BTC/EUR","buy",Decimal("0.001"),"limit",Decimal("90000"),Decimal("1"),False,False,"s","m","h")
    assert re.fullmatch(r"[0-9a-f-]{36}",intent.client_order_id)
    assert len(intent.client_order_id)==36

def test_spot_and_futures_signatures_have_expected_shape():
    assert len(SpotClient.sign("/0/private/AddOrder",{"nonce":"1","pair":"XXBTZEUR","type":"buy"},"c2VjcmV0"))>40
    assert len(FuturesClient.authent("/api/v3/sendorder",{"symbol":"PI_XBTUSD","orderType":"lmt","side":"buy","size":"1"},"c2VjcmV0"))>40

def test_db_reconstructs_decision_and_order_state():
    with tempfile.TemporaryDirectory() as d:
        db=Database(str(Path(d)/"x.sqlite3"))
        dec=Decision("cyc","BTC/EUR",DecisionAction.NO_POSITION,"buy",Decimal("0"),Decimal("0"),Decimal("0"),Decimal("0"),Decimal("0.5"),Decimal("0.5"),Decimal("1"),False)
        db.save_decision(dec);db.event("info","TEST","UNIT",cycle_id="cyc")
        assert db.one("SELECT id FROM decisions WHERE id=?",(dec.decision_id,))
        assert db.one("SELECT id FROM app_events WHERE cycle_id='cyc'")

def test_ambiguous_order_never_retries_and_enters_reconciliation_state():
    class Spot:
        def add_order(self,**_): raise KrakenAPIError("timeout",ambiguous=True,code="NETWORK_AMBIGUITY")
    class Venue: spot=Spot()
    with tempfile.TemporaryDirectory() as d:
        db=Database(str(Path(d)/"x.sqlite3"));c=config(trading_enabled=True,live_enabled=True,kill_switch=False)
        executor=KrakenExecutor(db,Venue(),c)
        i=Instrument("kraken","spot","BTC/EUR","XXBTZEUR","XXBTZEUR","BTC","EUR","online","spot",False,False)
        intent=OrderIntent("c","d","BTC/EUR","buy",Decimal("0.001"),"limit",Decimal("90000"),Decimal("1"),False,False,"s","m",c.hash())
        db.save_order(intent,OrderState.INTENT_CREATED.value)
        result=executor.submit(intent,i,live=True)
        assert result["status"]==OrderState.UNKNOWN_RECONCILING.value
        assert db.one("SELECT state FROM orders WHERE client_order_id=?",(intent.client_order_id,))["state"]==OrderState.UNKNOWN_RECONCILING.value

def test_order_spam_guard_blocks_live_or_recent_orders():
    with tempfile.TemporaryDirectory() as d:
        db=Database(str(Path(d)/"x.sqlite3"));intent=OrderIntent("c","d","BTC/EUR","buy",Decimal("0.001"),"limit",Decimal("1"),Decimal("1"),False,False,"s","m","h")
        db.save_order(intent,OrderState.PRECHECK_PASSED.value)
        assert OrderSpamGuard(db).allowed(intent,"different")[0] is False

def test_learning_validation_uses_multiple_windows_and_can_rollback():
    with tempfile.TemporaryDirectory() as d:
        db=Database(str(Path(d)/"x.sqlite3"));c=config(auto_promotion=True);l=Learner(db,c)
        metrics=l.validate_candidate([[0.01]*10,[0.005]*10,[0.008]*10])
        assert metrics["passed"] and len(metrics["windows"])==3 and metrics["walk_forward"] and metrics["oos"]
        l.register_candidate("ensemble-v2","ensemble-v1",metrics)
        with db.tx() as con:
            con.execute("UPDATE model_versions SET status='ACTIVE' WHERE version='ensemble-v2'")
            con.execute("INSERT OR IGNORE INTO model_versions VALUES('ensemble-v1',NULL,'immutable','BASELINE','{}',?,?)",(0,"initial"))
        assert l.rollback()=="ensemble-v1"

def test_pretrade_requires_portfolio_consistency_and_market_policy():
    with tempfile.TemporaryDirectory() as d:
        db=Database(str(Path(d)/"x.sqlite3"));c=config()
        p=PreTrade(db,c);i=Instrument("kraken","spot","BTC/EUR","id","id","BTC","EUR","online")
        intent=OrderIntent("c","d","BTC/EUR","buy",Decimal("0.001"),"market",Decimal("1"),Decimal("1"),False,False,"s","m",c.hash())
        ok,reason=p.check(intent,i,object(),{"consistent":False},0)
        assert not ok and reason=="BLOCKED_RECONCILIATION"
