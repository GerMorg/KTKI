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
        self.breaker=CircuitBreaker(self.db);self.stage=Stage.BOOT;self.health={};self.last_decision=None;self.regime_memory={};self._cycle_lock=threading.Lock()
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
            try:
                info=self.venue.auth_info()
                permissions={str(x).lower() for x in (info.get("permissions") or [])}
                required={"query-funds","query-open-trades","query-closed-trades"}
                if self.c.live_enabled: required.update({"modify-trades","close-trades","create-ws-token"})
                missing=sorted(required-permissions)
                private_ok=not missing
                if missing:
                    self.db.event("error","KRAKEN_PERMISSION_MISSING",self.stage.value,message="missing spot permissions",details={"missing":missing})
                if self.c.live_enabled:
                    try:
                        fut=self.venue.futures.check_key()
                        general=str(((fut.get("permissions") or {}).get("general") or "")).upper()
                        if general and general!="FULL_ACCESS":
                            self.db.event("error","KRAKEN_PERMISSION_MISSING",self.stage.value,message="futures key is not FULL_ACCESS")
                            self.health["derivatives_tradeable"]=False
                        else:self.health["derivatives_tradeable"]=True
                    except Exception as exc:
                        self.health["derivatives_tradeable"]=False
                        self.db.event("warning","DERIVATIVES_AUTH_UNAVAILABLE",self.stage.value,message=type(exc).__name__)
                else:self.health["derivatives_tradeable"]=True
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
        ready=bool(public_ok and bool(instruments) and market_ok and self.health.get("history_ok",False) and portfolio.get("consistent",False) and (not self.c.trading_enabled or private_ok) and not self.breaker.active)
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
        symbol=f"{a}/USD";snap=self.market.get(symbol)
        if snap:
            fx=self.market.get("EUR/USD")
            if fx and fx.last>0:return amt*snap.last/fx.last
        for pair in ("USD/EUR","USDT/EUR","USDC/EUR"):
            fx=self.market.get(pair)
            if fx and fx.last>0 and a in ("USD","USDT","USDC"):return amt*fx.last
        return Decimal("0")
    def _futures_snapshot(self):
        result={"equity":Decimal("0"),"available_margin":Decimal("0"),"used_margin":Decimal("0"),
                "gross_exposure":Decimal("0"),"net_exposure":Decimal("0"),"realized_pnl":Decimal("0"),
                "unrealized_pnl":Decimal("0"),"margin_level":Decimal("999999"),"positions":[],"consistent":True,"details":{}}
        if not hasattr(self.venue.futures,"accounts"): return result
        accounts=self.venue.futures.accounts() or {}
        accounts=accounts.get("accounts",accounts) if isinstance(accounts,dict) else {}
        flex=accounts.get("flex",{}) if isinstance(accounts,dict) else {}
        def D(v):
            try:return Decimal(str(v or 0))
            except Exception:return Decimal("0")
        equity_usd=D(flex.get("marginEquity") or flex.get("portfolioValue") or flex.get("balanceValue"))
        avail_usd=D(flex.get("availableMargin"))
        used_usd=D(flex.get("initialMarginWithOrders") or flex.get("initialMargin"))
        maint_usd=D(flex.get("maintenanceMargin"))
        result["equity"]=self._asset_eur("USD",equity_usd)
        result["available_margin"]=self._asset_eur("USD",avail_usd)
        result["used_margin"]=self._asset_eur("USD",used_usd)
        result["realized_pnl"]=self._asset_eur("USD",D(flex.get("pnl")))
        result["unrealized_pnl"]=self._asset_eur("USD",D(flex.get("totalUnrealized") or flex.get("totalUnrealizedAsMargin")))
        if maint_usd>0 and equity_usd>0: result["margin_level"]=equity_usd/maint_usd*100
        try: raw=self.venue.futures.open_positions() or {}
        except Exception as exc:
            result["consistent"]=False;result["details"]["positions_error"]=type(exc).__name__;raw={}
        pos=raw.get("openPositions") or raw.get("openpositions") or raw.get("positions") or raw
        if isinstance(pos,dict): pos=list(pos.values())
        for p in pos if isinstance(pos,list) else []:
            if not isinstance(p,dict):continue
            symbol=str(p.get("symbol") or p.get("instrument") or "")
            instrument=self.registry.by_symbol(symbol)
            if not instrument:continue
            size=D(p.get("size") or p.get("quantity") or p.get("qty"))
            snap=self.market.get(symbol)
            mark=D(p.get("markPrice") or p.get("mark_price") or p.get("price") or (snap.last if snap else 0))
            if size==0 or mark<=0:continue
            csize=instrument.contract_size if instrument.contract_size>0 else Decimal("1")
            ctype=instrument.contract_type.lower()
            quote_value=abs(size)*csize if "inverse" in ctype else abs(size)*csize*mark
            eur=self._asset_eur(instrument.quote or "USD",quote_value)
            side=str(p.get("side") or "").lower()
            sign=Decimal("-1") if side in ("short","sell") else Decimal("1")
            result["gross_exposure"]+=eur;result["net_exposure"]+=sign*eur
            result["positions"].append({"symbol":symbol,"base":instrument.base,"side":"short" if sign<0 else "long",
                                        "quantity":str(size),"notional_eur":str(eur),"mark_price":str(mark),
                                        "leverage":str(p.get("leverage") or 1),"margin":str(p.get("initialMargin") or 0),
                                        "product_type":"derivative"})
        result["details"]={"flex":flex,"position_count":len(result["positions"])}
        return result

    def portfolio_snapshot(self):
        if not (self.c.kraken_api_key and self.c.kraken_api_secret):
            p={"consistent":True,"equity":str(self.c.start_capital_eur),"cash":str(self.c.start_capital_eur),"available_margin":str(self.c.start_capital_eur),"used_margin":"0","gross_exposure":"0","net_exposure":"0","realized_pnl":"0","unrealized_pnl":"0","daily_pnl":"0","daily_loss_pct":"0","drawdown_pct":"0","margin_level":"999999","positions":[]}
            return p
        try:
            balances=self.venue.spot.balance();self._cache_private_balances(balances)
            spot_equity=sum((self._asset_eur(k,v) for k,v in balances.items()),Decimal("0"))
            derivatives=self._futures_snapshot()
            equity=spot_equity+derivatives["equity"]
            eur_cash=sum((Decimal(str(v)) for k,v in balances.items() if str(k).upper() in ("EUR","ZEUR")),Decimal("0"))
            margin=self.venue.spot.trade_balance("ZEUR")
            open_margin=self.venue.spot.open_positions()
            spot_positions=[]
            for k,v in balances.items():
                asset=str(k).upper().replace("XBT","BTC");value=self._asset_eur(asset,v)
                if value>0 and asset not in ("EUR","ZEUR"):
                    match=next((x for x in self.registry.instruments.values() if x.product_type=="spot" and x.base.upper()==asset),None)
                    spot_positions.append({"symbol":match.symbol if match else f"{asset}/EUR","base":asset,"side":"long","quantity":str(v),"eur_value":str(value),"notional_eur":str(value),"product_type":"spot"})
            if isinstance(open_margin,dict):
                margin_items=open_margin.get("open") or open_margin.get("positions") or open_margin
                if isinstance(margin_items,dict):
                    for mid,p in margin_items.items():
                        if not isinstance(p,dict):continue
                        symbol=str(p.get("pair") or p.get("symbol") or "")
                        inst=self.registry.by_symbol(symbol)
                        qty=Decimal(str(p.get("vol") or p.get("volume") or p.get("qty") or 0))
                        px=Decimal(str(p.get("price") or p.get("mark_price") or 0))
                        if not inst or qty<=0 or px<=0:continue
                        value=self._asset_eur(inst.quote,qty*px)
                        raw_side=str(p.get("type") or p.get("side") or "").lower()
                        side="short" if raw_side in ("sell","short") else "long"
                        spot_positions.append({"symbol":inst.symbol,"base":inst.base,"side":side,"quantity":str(qty),"eur_value":str(value),"notional_eur":str(value),"product_type":"spot_margin","position_id":str(mid),"margin":True})
            history=self.db.rows("SELECT ts,equity FROM portfolio_snapshots WHERE equity IS NOT NULL ORDER BY ts ASC")
            gross=sum((Decimal(x["notional_eur"]) for x in spot_positions),Decimal("0"))+derivatives["gross_exposure"]
            net=sum((Decimal(x["notional_eur"]) for x in spot_positions),Decimal("0"))+derivatives["net_exposure"]
            available_margin=Decimal(str(margin.get("mf") or eur_cash))+derivatives["available_margin"]
            used_margin=Decimal(str(margin.get("m") or 0))+derivatives["used_margin"]
            realized=Decimal(str(margin.get("e") or 0))+derivatives["realized_pnl"]
            unrealized=Decimal(str(margin.get("n") or 0))+derivatives["unrealized_pnl"]
            margin_levels=[x for x in (Decimal(str(margin.get("ml") or "999999")),derivatives["margin_level"]) if x>0]
            margin_level=min(margin_levels) if margin_levels else Decimal("999999")
            positions=spot_positions+derivatives["positions"]
            peak=max((Decimal(str(x["equity"])) for x in history),default=equity)
            today_start=time.time()-86400
            day_rows=[x for x in history if float(x["ts"])>=today_start]
            day_base=Decimal(str(day_rows[0]["equity"])) if day_rows else equity
            drawdown_pct=max(Decimal("0"),(peak-equity)/peak*100) if peak>0 else Decimal("0")
            daily_loss_pct=max(Decimal("0"),(day_base-equity)/day_base*100) if day_base>0 else Decimal("0")
            with self.db.tx() as c:
                c.execute("INSERT INTO portfolio_snapshots(cycle_id,ts,equity,cash,available_margin,used_margin,gross_exposure,net_exposure,realized_pnl,unrealized_pnl,daily_pnl,drawdown,quality,details_json) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                          ("",time.time(),str(equity),str(eur_cash),str(available_margin),str(used_margin),str(gross),str(net),str(realized),str(unrealized),str(-equity*daily_loss_pct/100),str(drawdown_pct),"VALID" if derivatives["consistent"] else "INCONSISTENT",json.dumps({"balances":list(balances.keys()),"margin_positions":list((open_margin or {}).keys()) if isinstance(open_margin,dict) else [],"derivatives":derivatives["details"]},default=str)))
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
            quote_value=s.last*s.volume
            liquidity=self._asset_eur(i.quote,quote_value) if i.quote.upper() not in ("EUR","ZEUR") else quote_value
            if liquidity<self.c.minimum_liquidity_eur:continue
            if s.spread*100>self.c.max_spread_pct:continue
            out.append((i,s))
        return out
    def _sync_exchange_fills(self):
        if not (self.c.kraken_api_key and self.c.kraken_api_secret):return 0
        try:
            raw=self.venue.spot.trades_history() or {}
            trades=raw.get("trades") or {}
            saved=0
            for trade_id,t in trades.items():
                if not isinstance(t,dict):continue
                with self.db.tx() as con:
                    before=con.total_changes
                    con.execute("INSERT OR IGNORE INTO fills(client_order_id,kraken_trade_id,ts,price,volume,fee,fee_currency,side,details_json) VALUES(?,?,?,?,?,?,?,?,?)",
                                (str(t.get("cl_ord_id") or ""),str(trade_id),float(t.get("time") or time.time()),
                                 str(t.get("price") or "0"),str(t.get("vol") or "0"),str(t.get("fee") or "0"),str(t.get("fee_currency") or ""),
                                 str(t.get("type") or ""),json.dumps(t,sort_keys=True,default=str)))
                    saved+=con.total_changes-before
            if saved:self.db.event("info","FILL_HISTORY_SYNC","OUTCOME_TRACKING",message=f"fills={saved}")
            return saved
        except Exception as exc:
            self.db.error("PRIVATE_DATA_STALE","OUTCOME_TRACKING",message=type(exc).__name__);return 0

    def _current_notional(self,portfolio,instrument):
        total=Decimal("0")
        for p in portfolio.get("positions",[]):
            same_symbol=p.get("symbol")==instrument.symbol
            same_base=instrument.product_type=="spot" and str(p.get("base","")).upper()==instrument.base.upper()
            if not (same_symbol or same_base):continue
            value=Decimal(str(p.get("notional_eur") or p.get("eur_value") or 0))
            total += -value if str(p.get("side","")).lower()=="short" else value
        return total

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
            self.set_stage(Stage.CYCLE_START,cycle);self.set_stage(Stage.MARKET_DISCOVERY,cycle)
            self.registry.sync(self.venue.discover())
            eligible=self.registry.eligible()
            self.set_stage(Stage.MARKET_FILTER,cycle)
            self.set_stage(Stage.MARKET_SNAPSHOT,cycle);self.market.snapshot_all(eligible,cycle_id=cycle)
            fast=self._fast_filter(eligible)
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
                f=self.features.features(i,s);reg=self.regimes.detect(f,self.regime_memory.get(i.symbol,"UNKNOWN"));self.regime_memory[i.symbol]=reg;news_effect=Decimal(str(self.news.effect_for_symbol(i.symbol)));gem_effect=self._gemini_effect(i.symbol)
                sig=self.ensemble.signal(i,f,reg,news_effect,gem_effect);signals.append((i,s,f,reg,sig))
            self.set_stage(Stage.REGIME_DETECTION,cycle);self.set_stage(Stage.SIGNAL_EVALUATION,cycle)
            for i,s,f,reg,sig in signals[:self.c.deep_scan_limit]:
                for horizon in self.c.news_horizon_hours:self.learning.record_prediction(cycle,sig,horizon,s.last,Decimal("0"))
                roundtrip=s.spread*2+(self.c.taker_fee_pct/100)*2+(self.c.max_slippage_pct/100)+(abs(Decimal(str(i.funding)))*Decimal("2") if i.product_type=="derivative" else Decimal("0"))
                net_edge=sig.expected_return-roundtrip;self.set_stage(Stage.COST_ESTIMATION,cycle);self.set_stage(Stage.EXPECTED_EDGE,cycle)
                self.set_stage(Stage.PORTFOLIO_TARGET,cycle);lev,_=self.risk.select_leverage(sig,i,portfolio);target,_=self.risk.size(sig,portfolio,lev)
                current_notional=self._current_notional(portfolio,i)
                opposite=current_notional<0 if sig.direction=="long" else current_notional>0
                exit_position= current_notional!=0 and (opposite or net_edge<=0)
                if exit_position:
                    target=Decimal("0")
                    lev=Decimal("1")
                    action=DecisionAction.CLOSE_SHORT if current_notional<0 else DecisionAction.CLOSE_LONG
                    side="buy" if current_notional<0 else "sell"
                elif sig.direction=="long":
                    action=DecisionAction.OPEN_LONG if current_notional==0 else (DecisionAction.INCREASE_LONG if target>current_notional else DecisionAction.REDUCE_LONG if target>0 else DecisionAction.CLOSE_LONG)
                    side="sell" if action in (DecisionAction.REDUCE_LONG,DecisionAction.CLOSE_LONG) else "buy"
                else:
                    action=DecisionAction.OPEN_SHORT if current_notional==0 else (DecisionAction.INCREASE_SHORT if abs(target)>abs(current_notional) else DecisionAction.REDUCE_SHORT if target>0 else DecisionAction.CLOSE_SHORT)
                    side="buy" if action in (DecisionAction.REDUCE_SHORT,DecisionAction.CLOSE_SHORT) else "sell"
                self.set_stage(Stage.LEVERAGE_SELECTION,cycle);self.set_stage(Stage.MARGIN_CHECK,cycle);self.set_stage(Stage.RISK_CHECK,cycle)
                blocker=None if exit_position else self.risk.check(sig,i,portfolio,target,lev,portfolio.get("positions",[]),self._orders_today())
                if not exit_position and net_edge*100<self.c.minimum_expected_edge_pct:blocker=Blocker.BLOCKED_EXPECTED_EDGE.value
                status="BLOCKED" if blocker else "NO_ACTION";d=Decision(cycle,i.symbol,action,side,target,current_notional,target-current_notional,net_edge,sig.confidence,sig.uncertainty,lev,lev>1,status,blocker or "",config_hash=self.c.hash(),evidence={"regime":reg,"news_effect":str(self.news.effect_for_symbol(i.symbol)),"gemini_effect":str(self._gemini_effect(i.symbol)),"roundtrip_cost":str(roundtrip),"features":f,"news_status":news_result.get("status")})
                self.db.save_decision(d);details["decisions"]+=1;self.last_decision=d
                if blocker:details["blocked"]+=1;self.learning.learn_event(cycle,d.decision_id,{"status":"NO_TRADE","blocker":blocker,"expected_edge":str(net_edge)});continue
                px=s.ask if side=="buy" else s.bid
                delta_notional=abs(target-current_notional)
                volume=delta_notional/px if px>0 else Decimal("0")
                order_type=self.policy.choose(s,net_edge,Decimal("0.5"),Decimal("0.5"));intent=OrderIntent(cycle,d.decision_id,i.symbol,side,volume,order_type,px,lev,lev>1,action in (DecisionAction.REDUCE_LONG,DecisionAction.REDUCE_SHORT,DecisionAction.CLOSE_LONG,DecisionAction.CLOSE_SHORT),d.strategy_version,d.model_version,d.config_hash)
                intent,normalizer_blocker=self.executor.normalizer.normalize(intent,i,s)
                if normalizer_blocker:
                    d.status="BLOCKED";d.blocker=normalizer_blocker;self.db.save_decision(d);details["blocked"]+=1
                    self.learning.learn_event(cycle,d.decision_id,{"status":"NO_TRADE","blocker":normalizer_blocker,"stage":"ORDER_NORMALIZATION"});continue
                d.intent_id=intent.intent_id;self.db.save_decision(d);self.db.save_order(intent,OrderState.INTENT_CREATED.value)
                allowed,reason=self.guard.allowed(intent,d.digest())
                if not allowed:self.db.update_order(intent.client_order_id,OrderState.REJECTED.value,error_code=reason);continue
                self.db.save_order(intent,OrderState.PRECHECK_PASSED.value);self.set_stage(Stage.PRETRADE_CHECK,cycle)
                okay,reason=self.pretrade.check(intent,i,s,portfolio,self._orders_today())
                if not okay:self.db.update_order(intent.client_order_id,OrderState.REJECTED.value,error_code=reason);details["blocked"]+=1;continue
                self.set_stage(Stage.ORDER_SUBMITTING,cycle);self.db.update_order(intent.client_order_id,OrderState.SUBMITTING.value)
                result=self.executor.submit(intent,i,live=self.c.live_enabled);details["orders"]+=1 if result.get("status")=="ACKNOWLEDGED" else 0
                self.set_stage(Stage.RECONCILIATION,cycle)
                if result.get("status")=="UNKNOWN_RECONCILING":
                    self.breaker.trip(Blocker.BLOCKED_RECONCILIATION.value,cycle)
                elif result.get("status")=="ACKNOWLEDGED":
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
