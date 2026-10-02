from __future__ import annotations
from decimal import Decimal
import time
from .models import OrderIntent,OrderState,Blocker,ErrorCode,Instrument,MarketSnapshot
class ExecutionPolicy:
    def __init__(self,config=None): self.config=config
    def choose(self,snapshot,edge,urgency,fill_probability):
        spread=snapshot.spread
        if spread<=Decimal("0.0008") and edge>spread*3:return "post_only"
        if spread<=Decimal("0.003") and edge>spread*2:return "limit"
        if urgency>Decimal("0.8") and edge>spread*4:return "marketable_limit"
        return "market"
class OrderSpamGuard:
    def __init__(self,db,cooldown_seconds=30):self.db,self.cooldown=db,int(cooldown_seconds)
    def allowed(self,intent,decision_hash):
        live=self.db.rows("SELECT * FROM orders WHERE symbol=? AND state IN ('INTENT_CREATED','PRECHECK_PASSED','SUBMITTING','ACKNOWLEDGED','LIVE','PARTIALLY_FILLED') ORDER BY id DESC LIMIT 20",(intent.symbol,))
        if live:return False,Blocker.BLOCKED_ORDER_LIMIT.value
        recent=self.db.rows("SELECT * FROM orders WHERE symbol=? AND created_at>? ORDER BY created_at DESC LIMIT 20",(intent.symbol,time.time()-self.cooldown))
        if recent:return False,Blocker.BLOCKED_ORDER_LIMIT.value
        prior=self.db.rows("SELECT digest FROM decisions WHERE symbol=? ORDER BY created_at DESC LIMIT 5",(intent.symbol,))
        if prior and prior[0].get("digest")==decision_hash:return False,ErrorCode.DUPLICATE_ORDER_RISK.value
        return True,""
class KrakenExecutor:
    def __init__(self,db,venue,config):self.db,self.venue,self.c=db,venue,config
    def submit(self,intent,instrument,live=False):
        if not live:return {"status":"PAPER_ONLY","client_order_id":intent.client_order_id}
        if self.c.kill_switch or not self.c.trading_enabled or not self.c.live_enabled:raise PermissionError(Blocker.SAFE_STOP.value)
        try:
            if instrument.product_type=="spot":
                params={"pair":instrument.altname or instrument.instrument_id,"type":intent.side,
                        "ordertype":"market" if intent.order_type=="market" else "limit","volume":str(intent.volume),
                        "cl_ord_id":intent.client_order_id}
                if intent.price and params["ordertype"]=="limit":params["price"]=str(intent.price)
                if intent.order_type=="post_only":params["oflags"]="post"
                if intent.margin:params["leverage"]=str(intent.leverage)
                if intent.reduce_only:params["reduce_only"]="true"
                result=self.venue.spot.add_order(**params);oid=result.get("txid",[None])[0] if isinstance(result.get("txid"),list) else result.get("txid","")
            else:
                params={"orderType":"mkt" if intent.order_type=="market" else ("post" if intent.order_type=="post_only" else "lmt"),
                        "symbol":instrument.instrument_id,"side":intent.side,"size":str(intent.volume),"cliOrdId":intent.client_order_id,
                        "reduceOnly":bool(intent.reduce_only)}
                if intent.price and params["orderType"] in ("lmt","post"):params["limitPrice"]=str(intent.price)
                result=self.venue.futures.send_order(**params);oid=str((result.get("sendStatus") or {}).get("order_id") or "")
            self.db.update_order(intent.client_order_id,OrderState.ACKNOWLEDGED.value,str(oid),details=result)
            return {"status":"ACKNOWLEDGED","kraken_order_id":str(oid),"client_order_id":intent.client_order_id}
        except Exception as exc:
            ambiguous=bool(getattr(exc,"ambiguous",False));state=OrderState.UNKNOWN_RECONCILING.value if ambiguous else OrderState.REJECTED.value
            self.db.update_order(intent.client_order_id,state,error_code=ErrorCode.NETWORK_AMBIGUITY.value if ambiguous else getattr(exc,"code",ErrorCode.API_ERROR.value),details={"error":type(exc).__name__})
            if ambiguous:return {"status":state,"client_order_id":intent.client_order_id,"error_code":ErrorCode.NETWORK_AMBIGUITY.value}
            raise
    def reconcile(self,client_order_id,kraken_order_id,instrument):
        try:
            if instrument.product_type=="spot":
                if kraken_order_id:
                    raw=self.venue.spot.query_orders(kraken_order_id)
                    order=raw.get(kraken_order_id) or next(iter(raw.values()),None)
                else:order=None
                if not order:
                    for group_name,raw in (("open",self.venue.spot.open_orders()),("closed",self.venue.spot.closed_orders())):
                        for oid,o in (raw.get(group_name) or {}).items():
                            if str(o.get("cl_ord_id") or o.get("userref") or "")==client_order_id or oid==kraken_order_id:order=dict(o,txid=oid);break
                        if order:break
            else:
                raw=self.venue.futures.orders();order=None
                items=(raw.get("orders") if isinstance(raw,dict) else None) or []
                for o in items:
                    if str(o.get("cliOrdId") or o.get("clientOrderId") or "")==client_order_id or str(o.get("order_id"))==str(kraken_order_id):order=o;break
            if not order:return {"status":OrderState.UNKNOWN_RECONCILING.value}
            status=str(order.get("status","unknown")).lower()
            mapping={"open":"LIVE","pending":"ACKNOWLEDGED","placed":"LIVE","partiallyfilled":"PARTIALLY_FILLED","closed":"FILLED","filled":"FILLED","canceled":"CANCELED","cancelled":"CANCELED","expired":"EXPIRED"}
            state=mapping.get(status,OrderState.UNKNOWN_RECONCILING.value);self.db.update_order(client_order_id,state,kraken_order_id,details=order);return {"status":state,"order":order}
        except Exception as exc:return {"status":OrderState.UNKNOWN_RECONCILING.value,"error":type(exc).__name__}
class PreTrade:
    def __init__(self,db,config):self.db,self.c=db,config
    def check(self,intent,instrument,snapshot,portfolio,orders_today):
        checks=[
            ("portfolio_consistent",bool(portfolio.get("consistent",False)),portfolio.get("consistent"),True),
            ("market_data",snapshot is not None,"fresh",True),
            ("system",not self.c.kill_switch,self.c.kill_switch,False),
            ("trading_enabled",self.c.trading_enabled,self.c.trading_enabled,True),
            ("live_enabled",self.c.live_enabled,self.c.live_enabled,True),
            ("orders_today",orders_today<self.c.max_orders_per_day,orders_today,self.c.max_orders_per_day),
            ("market_order_policy",intent.order_type!="market" or self.c.allow_market_orders,intent.order_type,self.c.allow_market_orders)]
        for name,ok,actual,required in checks:self.db.save_check(intent.decision_id,name,ok,actual,required)
        failed=next((name for name,ok,_,_ in checks if not ok),None)
        if failed=="portfolio_consistent": return False,Blocker.BLOCKED_RECONCILIATION.value
        if failed=="market_data": return False,Blocker.BLOCKED_MARKET_DATA.value
        if failed=="orders_today": return False,Blocker.BLOCKED_ORDER_LIMIT.value
        if failed=="market_order_policy": return False,Blocker.BLOCKED_STRATEGY.value
        return (True,"") if not failed else (False,Blocker.BLOCKED_RISK.value)
