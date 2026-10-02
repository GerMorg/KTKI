from __future__ import annotations
from decimal import Decimal
import json,time,threading
from .config import Config
from .db import Database
from .models import Stage,Blocker,DecisionAction,Decision,OrderIntent,OrderState,new_id
from .kraken import KrakenVenue,KrakenAPIError
from .market import InstrumentRegistry,MarketData
from .news import NewsEngine
from .gemini import GeminiAnalyzer
from .analysis import FeatureEngine,RegimeEngine,Ensemble
from .risk import RiskEngine
from .execution import KrakenExecutor,ExecutionPolicy,OrderSpamGuard,PreTrade
from .learning import Learner
from .sensors import SensorPublisher
from .history import HistoryEngine

class CircuitBreaker:
    def __init__(self,db):self.db=db;self.active=False;self.reason=""
    def trip(self,reason,cycle_id=""):
        self.active=True;self.reason=reason;self.db.event("error","CIRCUIT_BREAKER","RISK_CHECK",cycle_id=cycle_id,message=reason)
        self.db.event("warning","SAFE_STOP","RISK_CHECK",cycle_id=cycle_id,message="NO NEW RISK")
    def recover(self):
        self.active=False;self.reason="";self.db.event("info","RECOVERY_COMPLETED","HEALTH_CHECK",message="circuit breaker recovered")

class TradingAuthority:
    """The only component allowed to turn an approved decision into an order intent."""
    def __init__(self,config=None,db=None,venue=None):
        self.c=config or Config.load();self.c.validate();self.db=db or Database()
        self.venue=venue or KrakenVenue(self.c.kraken_api_key,self.c.kraken_api_secret)
        self.registry=InstrumentRegistry(self.db);self.market=MarketData(self.db,self.venue,self.c.data_freshness_seconds)
        self.news=NewsEngine(self.db,enabled=self.c.news_enabled);self.gemini=GeminiAnalyzer(self.db,self.c.gemini_api_key,self.c.gemini_model,self.c.gemini_enabled)
        self.features=FeatureEngine(self.venue,self.c.history_lookback,self.db);self.history=HistoryEngine(self.db,self.venue,self.c.history_lookback);self.regimes=RegimeEngine();self.ensemble=Ensemble()
        self.risk=RiskEngine(self.c);self.executor=KrakenExecutor(self.db,self.venue,self.c);self.policy=ExecutionPolicy(self.c)
        self.guard=OrderSpamGuard(self.db);self.pretrade=PreTrade(self.db,self.c);self.learning=Learner(self.db,self.c);self.sensors=SensorPublisher()
        self.breaker=CircuitBreaker(self.db);self.stage=Stage.BOOT;self.health={};self.last_decision=None;self._cycle_lock=threading.Lock()
    def set_stage(self,s,cycle_id=""):
        self.stage=s;self.db.event("info",s.value,s.value,cycle_id=cycle_id,message=s.value)
    def startup(self):
        self.set_stage(Stage.CONFIG_VALIDATING);self.c.validate()
        self.set_stage(Stage.KRAKEN_AUTH_CHECK)
        public_ok=private_ok=False
        try:
            status=self.venue.system_status()
            public_ok=str(status.get("status","online")).lower() in ("online","operational","post_only","online")
            if not public_ok:self.db.event("warning","KRAKEN_STATUS",self.stage.value,message=str(status.get("status","unknown")))
        except Exception as exc:self.db.error("API_ERROR",self.stage.value,message=type(exc).__name__)
        if self.c.kraken_api_key and self.c.kraken_api_secret:
            try:self.venue.auth_info();private_ok=True
            except KrakenAPIError as exc:self.db.error(getattr(exc,"code","AUTH_ERROR"),self.stage.value,message=type(exc).__name__)
            except Exception as exc:self.db.error("AUTH_ERROR",self.stage.value,message=type(exc).__name__)
        self.health.update(public_ok=public_ok,private_ok=private_ok)
        self.set_stage(Stage.PRODUCT_DISCOVERY)
        try:raw=self.venue.discover()
        except Exception as exc:raw=[];self.db.error("DATA_ERROR",self.stage.value,message=type(exc).__name__)
        self.set_stage(Stage.INSTRUMENT_SYNC);instruments=self.registry.sync(raw)
        self.set_stage(Stage.PUBLIC_DATA_CONNECT)
        eligible=self.registry.eligible()
        market_ok=False
        if eligible:
            try:market_ok=self.market.snapshot_all(eligible,cycle_id="BOOT")>0
            except Exception as exc:self.db.error("API_ERROR",self.stage.value,message=type(exc).__name__)
        self.health["market_ok"]=market_ok
        self.set_stage(Stage.HISTORY_BACKFILL)
        backfill=self.history.backfill(eligible[:min(len(eligible),self.c.deep_scan_limit)]) if market_ok else {"saved":0,"errors":1}
        self.health["history_ok"]=bool(backfill.get("saved") or not backfill.get("errors"))
        self.set_stage(Stage.PRIVATE_DATA_CONNECT);self.health["private_data_ok"]=private_ok
        self.set_stage(Stage.ACCOUNT_SYNC)
        portfolio=self.portfolio_snapshot()
        self.set_stage(Stage.PORTFOLIO_SYNC)
        if self.c.trading_enabled and not private_ok:
            self.breaker.trip(Blocker.BLOCKED_PRIVATE_DATA.value)
        self.set_stage(Stage.MODEL_INITIALIZATION);self.ensure_models()
        self.set_stage(Stage.HEALTH_CHECK)
        ready=bool(public_ok and bool(instruments) and market_ok and portfolio.get("consistent",False) and (not self.c.trading_enabled or private_ok) and not self.breaker.active)
        self.health["system_ready"]=ready;self.stage=Stage.READY if ready else Stage.HEALTH_CHECK;self.publish_sensors(portfolio)
        return ready
    def ensure_models(self):
        with self.db.tx() as c:
            c.execute("INSERT OR IGNORE INTO strategy_versions VALUES('strategy-v1',NULL,'immutable','ACTIVE','{}',?,?)",(time.time(),"initial"))
            c.execute("INSERT OR IGNORE INTO model_versions VALUES('ensemble-v1',NULL,'immutable','ACTIVE','{}',?,?)",(time.time(),"initial"))
    def _asset_eur(self,asset,amount):
        a=str(asset).upper().replace("XBT","BTC");amt=Decimal(str(amount))
        if a in ("EUR","ZEUR"):return amt
        symbol=f"{a}/EUR";snap=self.market.get(symbol)
        if snap:return amt*snap.last
        symbol=f"{a}/USD";snap=self.market.get(symbol);fx=self.market.get("EUR/USD")
        if snap and fx and fx.last>0:return amt*snap.last/fx.last
        return Decimal("0")
    def portfolio_snapshot(self):
        if not (self.c.kraken_api_key and self.c.kraken_api_secret):
            p={"consistent":True,"equity":str(self.c.start_capital_eur),"cash":str(self.c.start_capital_eur),"available_margin":str(self.c.start_capital_eur),"used_margin":"0","gross_exposure":"0","net_exposure":"0","realized_pnl":"0","unrealized_pnl":"0","daily_pnl":"0","drawdown_pct":"0","margin_level":"999999","positions":[]}
            return p
        try:
            balances=self.venue.spot.balance();self._cache_private_balances(balances)
            equity=sum((self._asset_eur(k,v) for k,v in balances.items()),Decimal("0"))
            eur_cash=sum((Decimal(str(v)) for k,v in balances.items() if str(k).upper() in ("EUR","ZEUR")),Decimal("0"))
            spot_positions=[]
            for k,v in balances.items():
                value=self._asset_eur(k,v)
                if value>0 and str(k).upper() not in ("EUR","ZEUR"):spot_positions.append({"asset":str(k),"quantity":str(v),"eur_value":str(value)})
            margin=self.venue.spot.trade_balance()
            open_margin=self.venue.spot.open_positions()
            with self.db.tx() as c:
                c.execute("INSERT INTO portfolio_snapshots(cycle_id,ts,equity,cash,available_margin,used_margin,gross_exposure,net_exposure,realized_pnl,unrealized_pnl,daily_pnl,drawdown,quality,details_json) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                          ("",time.time(),str(equity),str(eur_cash),str(margin.get("mf") or eur_cash),str(margin.get("m") or 0),str(sum((Decimal(x["eur_value"]) for x in spot_positions),Decimal("0"))),str(sum((Decimal(x["eur_value"]) for x in spot_positions),Decimal("0"))),
                           str(margin.get("e") or 0),str(margin.get("n") or 0),"0","0","VALID",json.dumps({"balances":list(balances.keys()),"margin_positions":list((open_margin or {}).keys())})))
            return {"consistent":True,"equity":str(equity),"cash":str(eur_cash),"available_margin":str(margin.get("mf") or eur_cash),"used_margin":str(margin.get("m") or 0),
                    "gross_exposure":str(sum((Decimal(x["eur_value"]) for x in spot_positions),Decimal("0"))),"net_exposure":str(sum((Decimal(x["eur_value"]) for x in spot_positions),Decimal("0"))),
                    "realized_pnl":str(margin.get("e") or 0),"unrealized_pnl":str(margin.get("n") or 0),"daily_pnl":"0","drawdown_pct":"0","margin_level":str(margin.get("ml") or "999999"),"positions":spot_positions,"margin_positions":open_margin}
        except Exception as exc:
            self.db.error("PRIVATE_DATA_STALE",Stage.PORTFOLIO_SYNC.value,message=type(exc).__name__);self.breaker.trip(Blocker.BLOCKED_PORTFOLIO.value)
            return {"consistent":False}
    def _cache_private_balances(self,balances):
        self.db.event("info","ACCOUNT_SYNC_COMPLETED","ACCOUNT_SYNC",message=f"assets={len(balances)}")
    def _fast_filter(self,instruments):
        out=[]
        for i in instruments:
            s=self.market.get(i.symbol)
            if not s or s.last<=0:continue
            liquidity=s.last*s.volume
            if liquidity<self.c.minimum_liquidity_eur:continue
            if s.spread*100>self.c.max_spread_pct:continue
            out.append((i,s))
        return out
    def _gemini_effect(self,symbol):
        rows=self.db.rows("SELECT direction,impact,confidence FROM gemini_analysis WHERE symbol=? ORDER BY created_at DESC LIMIT 10",(symbol,));effect=Decimal("0")
        for r in rows:
            x=Decimal(str(r.get("impact") or 0))*Decimal(str(r.get("confidence") or 0))
            effect += x if r.get("direction")=="bullish" else (-x if r.get("direction")=="bearish" else 0)
        return max(Decimal("-1"),min(Decimal("1"),effect))
    def run_cycle(self):
        if not self.health.get("system_ready",False) or self.breaker.active:return {"status":"SAFE_STOP","stage":self.stage.value,"reason":self.breaker.reason}
        if not self._cycle_lock.acquire(blocking=False):return {"status":"SKIPPED","reason":"CYCLE_ALREADY_RUNNING"}
        cycle=new_id("cycle");self.db.start_cycle(cycle);details={"cycle_id":cycle,"decisions":0,"orders":0,"blocked":0}
        try:
            self.set_stage(Stage.CYCLE_START,cycle);self.set_stage(Stage.MARKET_DISCOVERY,cycle);eligible=self.registry.eligible()
            self.set_stage(Stage.MARKET_FILTER,cycle);fast=self._fast_filter(eligible);self.set_stage(Stage.MARKET_SNAPSHOT,cycle)
            self.history.backfill([i for i,_ in fast[:self.c.deep_scan_limit]])
            self.set_stage(Stage.NEWS_ANALYSIS,cycle);news_result=self.news.collect();self.news.annotate([i for i,_ in fast[:self.c.deep_scan_limit]])
            self.set_stage(Stage.GEMINI_ANALYSIS,cycle)
            for n in self.news.recent(10):
                value=self.gemini.analyze(n)
                if isinstance(value,dict) and value.get("direction") in ("bullish","bearish","neutral"):
                    entity=str(value.get("asset") or "")
                    for i,_ in fast:
                        if entity and (entity.upper() in i.base.upper() or i.base.upper() in entity.upper()):
                            with self.db.tx() as c:c.execute("INSERT INTO gemini_analysis(news_id,symbol,event,direction,impact,confidence,time_horizon,novelty,market_confirmation,risk_flags_json,model_version,status,raw_json,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                                (n["id"],i.symbol,str(value.get("event","")),value["direction"],str(value["impact"]),str(value["confidence"]),str(value["time_horizon"]),str(value["novelty"]),str(value["market_confirmation"]),json.dumps(value.get("risk_flags",[])),self.c.gemini_model,"VALID",json.dumps(value,sort_keys=True),time.time()))
            portfolio=self.portfolio_snapshot();self.set_stage(Stage.FEATURE_CALCULATION,cycle);signals=[]
            for i,s in fast:
                f=self.features.features(i,s);reg=self.regimes.detect(f);news_effect=Decimal(str(self.news.effect_for_symbol(i.symbol)));gem_effect=self._gemini_effect(i.symbol)
                sig=self.ensemble.signal(i,f,reg,news_effect,gem_effect);signals.append((i,s,f,reg,sig))
            self.set_stage(Stage.REGIME_DETECTION,cycle);self.set_stage(Stage.SIGNAL_EVALUATION,cycle)
            for i,s,f,reg,sig in signals[:self.c.deep_scan_limit]:
                roundtrip=s.spread*2+(self.c.taker_fee_pct/100)*2+(self.c.max_slippage_pct/100)+(abs(Decimal(str(i.funding)))*Decimal("2") if i.product_type=="derivative" else Decimal("0"))
                net_edge=sig.expected_return-roundtrip;self.set_stage(Stage.COST_ESTIMATION,cycle);self.set_stage(Stage.EXPECTED_EDGE,cycle)
                self.set_stage(Stage.PORTFOLIO_TARGET,cycle);lev,_=self.risk.select_leverage(sig,i,portfolio);target,_=self.risk.size(sig,portfolio,lev)
                action=DecisionAction.OPEN_LONG if sig.direction=="long" else DecisionAction.OPEN_SHORT;side="buy" if sig.direction=="long" else "sell"
                self.set_stage(Stage.LEVERAGE_SELECTION,cycle);self.set_stage(Stage.MARGIN_CHECK,cycle);self.set_stage(Stage.RISK_CHECK,cycle)
                blocker=self.risk.check(sig,i,portfolio,target,lev,portfolio.get("positions",[]),self._orders_today())
                if net_edge*100<self.c.minimum_expected_edge_pct:blocker=Blocker.BLOCKED_EXPECTED_EDGE.value
                status="BLOCKED" if blocker else "NO_ACTION";d=Decision(cycle,i.symbol,action,side,target,Decimal("0"),target,net_edge,sig.confidence,sig.uncertainty,lev,lev>1,status,blocker or "",config_hash=self.c.hash(),evidence={"regime":reg,"news_effect":str(self.news.effect_for_symbol(i.symbol)),"gemini_effect":str(self._gemini_effect(i.symbol)),"roundtrip_cost":str(roundtrip),"features":f,"news_status":news_result.get("status")})
                self.db.save_decision(d);details["decisions"]+=1;self.last_decision=d
                if blocker:details["blocked"]+=1;self.learning.learn_event(cycle,d.decision_id,{"status":"NO_TRADE","blocker":blocker,"expected_edge":str(net_edge)});continue
                px=s.ask if side=="buy" else s.bid;volume=target/px if px>0 else Decimal("0")
                order_type=self.policy.choose(s,net_edge,Decimal("0.5"),Decimal("0.5"));intent=OrderIntent(cycle,d.decision_id,i.symbol,side,volume,order_type,px,lev,lev>1,False,d.strategy_version,d.model_version,d.config_hash)
                d.intent_id=intent.intent_id;self.db.save_decision(d);self.db.save_order(intent,OrderState.INTENT_CREATED.value)
                allowed,reason=self.guard.allowed(intent,d.digest())
                if not allowed:self.db.update_order(intent.client_order_id,OrderState.REJECTED.value,error_code=reason);continue
                self.db.save_order(intent,OrderState.PRECHECK_PASSED.value);self.set_stage(Stage.PRETRADE_CHECK,cycle)
                okay,reason=self.pretrade.check(intent,i,s,portfolio,self._orders_today())
                if not okay:self.db.update_order(intent.client_order_id,OrderState.REJECTED.value,error_code=reason);details["blocked"]+=1;continue
                self.set_stage(Stage.ORDER_SUBMITTING,cycle);self.db.update_order(intent.client_order_id,OrderState.SUBMITTING.value)
                result=self.executor.submit(intent,i,live=self.c.live_enabled);details["orders"]+=1 if result.get("status")=="ACKNOWLEDGED" else 0
                self.set_stage(Stage.RECONCILIATION,cycle)
                if result.get("status")=="ACKNOWLEDGED":
                    rec=self.executor.reconcile(intent.client_order_id,result.get("kraken_order_id",""),i)
                    if rec.get("status")==OrderState.UNKNOWN_RECONCILING.value:self.breaker.trip(Blocker.BLOCKED_RECONCILIATION.value,cycle)
            self.set_stage(Stage.PORTFOLIO_UPDATED,cycle);portfolio=self.portfolio_snapshot();self.set_stage(Stage.OUTCOME_TRACKING,cycle)
            self.learning.learn_event(cycle,"",{"news":news_result,"decisions":details["decisions"],"orders":details["orders"]});self.set_stage(Stage.LEARNING_EVENT,cycle)
            self.set_stage(Stage.CALIBRATION,cycle);self.learning.calibrate();self.set_stage(Stage.CYCLE_COMPLETE,cycle)
            self.db.finish_cycle(cycle,"COMPLETE",details);self.publish_sensors(portfolio,details);return {"status":"COMPLETE",**details}
        except Exception as exc:
            self.db.error("API_ERROR",self.stage.value,cycle_id=cycle,message=f"{type(exc).__name__}: {str(exc)[:250]}");self.db.finish_cycle(cycle,"FAILED",{"error":type(exc).__name__});self.publish_sensors({},{"status":"FAILED"});return {"status":"FAILED","cycle_id":cycle,"error":type(exc).__name__}
        finally:self._cycle_lock.release()
    def _orders_today(self):
        row=self.db.one("SELECT COUNT(*) AS n FROM orders WHERE created_at>=?",(time.time()-86400,));return int(row["n"]) if row else 0
    def publish_sensors(self,portfolio=None,details=None):
        p=portfolio or {}
        state={"trading_enabled":self.c.trading_enabled,"system_ready":self.health.get("system_ready",False),"market_data_healthy":self.health.get("market_ok",False),
        "private_data_healthy":self.health.get("private_data_ok",False),"portfolio_consistent":bool(p.get("consistent",False)),"model_ready":True,
        "news_healthy":True,"gemini_healthy":bool(self.c.gemini_api_key) if self.c.gemini_enabled else True,"circuit_breaker":self.breaker.active,
        "margin_safe":self.risk.margin_safe(p)[0],"portfolio_equity":p.get("equity","0"),"available_cash":p.get("cash","0"),"available_margin":p.get("available_margin","0"),
        "used_margin":p.get("used_margin","0"),"gross_exposure":p.get("gross_exposure","0"),"net_exposure":p.get("net_exposure","0"),
        "realized_pnl":p.get("realized_pnl","0"),"unrealized_pnl":p.get("unrealized_pnl","0"),"daily_pnl":p.get("daily_pnl","0"),"drawdown":p.get("drawdown_pct","0"),
        "open_positions":len(p.get("positions",[]) or []),"open_orders":len(self.db.rows("SELECT id FROM orders WHERE state IN ('LIVE','PARTIALLY_FILLED','ACKNOWLEDGED')")),
        "orders_today":self._orders_today(),"current_leverage":"1","average_slippage":"0","average_latency":"0","expected_edge":str(self.last_decision.expected_edge if self.last_decision else 0),
        "system_state":self.stage.value,"last_action":(details or {}).get("status",""),"last_symbol":self.last_decision.symbol if self.last_decision else "",
        "last_direction":self.last_decision.side if self.last_decision else "","last_blocker":self.last_decision.blocker if self.last_decision else "",
        "last_trade":"","active_strategy":"strategy-v1","active_model":"ensemble-v1","active_regime":self.last_decision.evidence.get("regime","") if self.last_decision else "",
        "last_news_event":"","gemini_status":"ready" if self.c.gemini_api_key else "unconfigured","learning_status":"enabled" if self.c.learning_enabled else "disabled"}
        return self.sensors.publish(state)
    def serve(self):
        if not self.startup():return 1
        while True:self.run_cycle();time.sleep(self.c.discovery_interval_seconds)

class Runtime:
    def run(self):return TradingAuthority().serve()
