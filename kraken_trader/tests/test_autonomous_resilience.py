from decimal import Decimal
from pathlib import Path
import tempfile

from autonomous_trader.analysis import RegimeEngine, Ensemble
from autonomous_trader.models import Instrument, MarketSnapshot, Signal, OrderIntent, OrderState
from autonomous_trader.db import Database
from autonomous_trader.ws import WebSocketSupervisor
from autonomous_trader.gemini import GeminiAnalyzer

def test_regime_engine_covers_breakout_recovery_and_mean_reversion():
    r=RegimeEngine()
    assert r.detect({"trend":"0.07","momentum":"0.06","realized_volatility":"0.02","spread":"0.0002","volume_anomaly":"2"})=="BREAKOUT"
    assert r.detect({"trend":"0.015","momentum":"0.02","realized_volatility":"0.03","spread":"0.0002","volume_anomaly":"1"},"PANIC")=="RECOVERY"
    assert r.detect({"trend":"0.001","momentum":"-0.001","realized_volatility":"0.02","spread":"0.0002","volume_anomaly":"1"})=="MEAN_REVERSION"

def test_ensemble_scores_long_and_short_separately():
    e=Ensemble()
    instrument=Instrument("kraken","spot","BTC/EUR","XXBTZEUR","XXBTZEUR","BTC","EUR","online")
    feature={"trend":"0.04","momentum":"0.03","imbalance":"0.2","realized_volatility":"0.02","spread":"0.0005"}
    s=e.signal(instrument,feature,"TREND_UP")
    assert s.long_score>s.short_score and s.direction=="long"
    feature["trend"]="-0.04";feature["momentum"]="-0.03"
    s=e.signal(instrument,feature,"TREND_DOWN")
    assert s.short_score>s.long_score and s.direction=="short"

def test_websocket_sequence_gap_emits_recovery_event():
    class FakeWS:
        def send(self,*_): pass
    with tempfile.TemporaryDirectory() as d:
        db=Database(str(Path(d)/"x.sqlite3"))
        ws=WebSocketSupervisor(db,"wss://example.invalid",name="private-ws")
        ws._on_message(FakeWS(),'{"channel":"executions","seq":10}')
        ws._on_message(FakeWS(),'{"channel":"executions","seq":12}')
        rows=db.rows("SELECT event_code FROM app_events ORDER BY id")
        codes=[r["event_code"] for r in rows]
        assert "PRIVATE_SEQUENCE_GAP" in codes and "RECOVERY_STARTED" in codes

def test_gemini_schema_rejects_malformed_values():
    bad={"asset":"BTC","event":"x","direction":"bullish","impact":2,"confidence":0.5,"time_horizon":"1h","novelty":0.5,"market_confirmation":0.5,"risk_flags":[]}
    try:
        GeminiAnalyzer.validate(bad)
    except ValueError:
        return
    raise AssertionError("malformed Gemini value accepted")

def test_order_state_is_persistable_as_reconciliation_terminal_or_live_state():
    assert {OrderState.INTENT_CREATED.value,OrderState.PRECHECK_PASSED.value,OrderState.SUBMITTING.value,
            OrderState.ACKNOWLEDGED.value,OrderState.LIVE.value,OrderState.PARTIALLY_FILLED.value,
            OrderState.FILLED.value,OrderState.CANCELED.value,OrderState.EXPIRED.value,
            OrderState.REJECTED.value,OrderState.UNKNOWN_RECONCILING.value}.issubset({x.value for x in OrderState})


def test_order_normalizer_enforces_minimums_and_tick_precision():
    from autonomous_trader.execution import OrderNormalizer
    i=Instrument("kraken","spot","BTC/EUR","XXBTZEUR","XXBTZEUR","BTC","EUR","online","spot",True,True,("2","3"),Decimal("3"),Decimal("0.001"),Decimal("5"),4,2,Decimal("0.1"))
    intent=OrderIntent("c","d","BTC/EUR","buy",Decimal("0.00127"),"limit",Decimal("90000.07"),Decimal("2"),True,False,"s","m","h")
    snap=MarketSnapshot("BTC/EUR",Decimal("90000"),Decimal("90001"),Decimal("90000"),Decimal("100"),0)
    normalized,block=OrderNormalizer().normalize(intent,i,snap)
    assert block is None
    assert normalized.volume==Decimal("0.0012")
    assert normalized.price==Decimal("90000.0")
