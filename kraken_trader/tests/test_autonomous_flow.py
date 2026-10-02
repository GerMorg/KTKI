from decimal import Decimal
from pathlib import Path
import tempfile

from autonomous_trader.config import Config
from autonomous_trader.db import Database
from autonomous_trader.runtime import TradingAuthority
from autonomous_trader.models import Stage

class FakeSpot:
    def status(self): return {"status":"online"}
    def get_api_key_info(self): return {"permissions":["query-funds","query-open-trades","query-closed-trades"]}
    def asset_pairs(self,*_):
        return {
          "XXBTZEUR":{"wsname":"BTC/EUR","altname":"XXBTZEUR","base":"BTC","quote":"EUR","status":"online","ordermin":"0.0001","costmin":"0.5",
                      "pair_decimals":1,"lot_decimals":4,"leverage_buy":["2:1","3:1"],"leverage_sell":["2:1","3:1"]},
          "XETHZEUR":{"wsname":"ETH/EUR","altname":"XETHZEUR","base":"ETH","quote":"EUR","status":"online","ordermin":"0.001","costmin":"0.5",
                      "pair_decimals":1,"lot_decimals":3}
        }
    def ticker(self,pair=""):
        return {"XXBTZEUR":{"b":["90000"],"a":["90010"],"c":["90005"],"v":["100"]},
                "XETHZEUR":{"b":["3000"],"a":["3001"],"c":["3000.5"],"v":["100"]}}
    def ohlc(self,*args,**kwargs):
        pair=str(args[0]) if args else "XXBTZEUR"
        return {pair:[[0,0,89500,90500,90000,90000,10,1]]*40}
    def balance(self): return {"ZEUR":"50"}
    def trade_balance(self,*_): return {"e":"50","mf":"50","m":"0","n":"0","ml":"999999"}
    def open_positions(self): return {}
    def open_orders(self): return {"open":{}}
    def closed_orders(self): return {"closed":{}}
    def query_orders(self,*_): return {}

class FakeFutures:
    def instruments(self): return {"instruments":[]}
    def tickers(self): return {"tickers":[]}

class FakeVenue:
    def __init__(self): self.spot=FakeSpot();self.futures=FakeFutures()
    def system_status(self): return self.spot.status()
    def auth_info(self): return self.spot.get_api_key_info()
    def discover(self):
        out=[]
        for key,p in self.spot.asset_pairs("currency").items():
            lev=list(p.get("leverage_buy",[]))
            out.append({"venue":"kraken","product_type":"spot","symbol":p["wsname"],"instrument_id":key,"altname":p["altname"],
                        "base":p["base"],"quote":p["quote"],"status":p["status"],"contract_type":"spot","margin":bool(lev),"long_short":bool(lev),
                        "leverage_levels":lev,"max_leverage":"3","order_min":p["ordermin"],"cost_min":p["costmin"],
                        "lot_precision":p["lot_decimals"],"price_precision":p["pair_decimals"],"metadata":p})
        return out

def test_startup_discovers_dynamic_market_and_runs_full_cycle():
    with tempfile.TemporaryDirectory() as d:
        c=Config(kraken_api_key="x",kraken_api_secret="y",trading_enabled=False,live_enabled=False,kill_switch=True,
                 news_enabled=False,gemini_enabled=False,start_capital_eur=Decimal("50"),deep_scan_limit=5)
        db=Database(str(Path(d)/"trader.sqlite3"));rt=TradingAuthority(c,db,FakeVenue())
        assert rt.startup() and rt.stage==Stage.READY
        assert set(x["symbol"] for x in db.rows("SELECT symbol FROM instrument_metadata"))=={"BTC/EUR","ETH/EUR"}
        result=rt.run_cycle()
        assert result["status"]=="COMPLETE" and result["decisions"]>0 and result["blocked"]>0
        assert db.one("SELECT COUNT(*) AS n FROM cycles")["n"]==1
        assert db.one("SELECT COUNT(*) AS n FROM decisions")["n"]==result["decisions"]
        assert db.one("SELECT COUNT(*) AS n FROM learning_events")["n"]>=1
        assert db.one("SELECT COUNT(*) AS n FROM calibration_history")["n"]==0

def test_paper_mode_never_calls_order_sender():
    class ExplodingExecutor:
        def submit(self,*_a,**_k): raise AssertionError("paper cycle must not use live executor")
    with tempfile.TemporaryDirectory() as d:
        c=Config(kraken_api_key="x",kraken_api_secret="y",trading_enabled=False,live_enabled=False,kill_switch=True,news_enabled=False,gemini_enabled=False,start_capital_eur=Decimal("50"))
        rt=TradingAuthority(c,Database(str(Path(d)/"x.sqlite3")),FakeVenue());assert rt.startup()
        rt.executor=ExplodingExecutor()
        result=rt.run_cycle()
        assert result["status"]=="COMPLETE"


def test_no_credentials_portfolio_uses_safe_zero_risk_metrics():
    with tempfile.TemporaryDirectory() as d:
        c=Config(trading_enabled=False,live_enabled=False,kill_switch=True,news_enabled=False,gemini_enabled=False,start_capital_eur=Decimal("50"))
        rt=TradingAuthority(c,Database(str(Path(d)/"x.sqlite3")),FakeVenue())
        p=rt.portfolio_snapshot()
        assert p["equity"]=="50" and p["daily_loss_pct"]=="0" and p["drawdown_pct"]=="0"


def test_portfolio_current_position_is_reconciled_into_signed_notional():
    with tempfile.TemporaryDirectory() as d:
        c=Config(kraken_api_key="x",kraken_api_secret="y",trading_enabled=False,live_enabled=False,kill_switch=True,news_enabled=False,gemini_enabled=False,start_capital_eur=Decimal("50"))
        rt=TradingAuthority(c,Database(str(Path(d)/"x.sqlite3")),FakeVenue())
        rt.registry.sync(rt.venue.discover())
        p={"positions":[{"symbol":"BTC/EUR","base":"BTC","side":"short","notional_eur":"10"}]}
        instrument=rt.registry.by_symbol("BTC/EUR")
        assert rt._current_notional(p,instrument)==Decimal("-10")
