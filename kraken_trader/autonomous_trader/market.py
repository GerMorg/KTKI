from __future__ import annotations
from dataclasses import asdict
from decimal import Decimal
import json,time
from .models import Instrument,MarketSnapshot

ONLINE={"online","post_only","limit_only","true","1","tradable"}

class InstrumentRegistry:
    def __init__(self,db): self.db=db; self.instruments={}
    def sync(self,raw):
        self.instruments={}
        for r in raw:
            try:
                i=Instrument(
                    venue=r["venue"],product_type=r["product_type"],symbol=r["symbol"],instrument_id=r["instrument_id"],altname=r.get("altname",""),
                    base=r.get("base",""),quote=r.get("quote",""),status=str(r.get("status","unknown")).lower(),contract_type=r.get("contract_type","spot"),
                    margin=bool(r.get("margin")),long_short=bool(r.get("long_short")),leverage_levels=tuple(r.get("leverage_levels") or ()),
                    max_leverage=Decimal(str(r.get("max_leverage",1))),order_min=Decimal(str(r.get("order_min",0))),cost_min=Decimal(str(r.get("cost_min",0))),
                    lot_precision=int(r.get("lot_precision",8)),price_precision=int(r.get("price_precision",8)),tick_size=Decimal(str(r.get("tick_size",0))),
                    position_limit_long=Decimal(str(r.get("position_limit_long",0))),position_limit_short=Decimal(str(r.get("position_limit_short",0))),
                    margin_class=str(r.get("margin_class","")),collateral=str(r.get("collateral","")),funding=Decimal(str(r.get("funding",0))),
                    fee_model=str(r.get("fee_model","")),updated_at=time.time(),metadata=r.get("metadata") or {})
                self.instruments[i.instrument_id]=i
                with self.db.tx() as c:
                    c.execute("INSERT OR REPLACE INTO instrument_metadata VALUES(?,?,?,?,?,?,?,?,?,?)",
                              (i.instrument_id,i.venue,i.product_type,i.symbol,i.altname,i.base,i.quote,i.status,
                               json.dumps(asdict(i),sort_keys=True,default=str),i.updated_at))
            except Exception as exc:
                self.db.error("DATA_ERROR","INSTRUMENT_SYNC",message=f"instrument invalid: {type(exc).__name__}")
        return self.instruments
    def eligible(self):
        return sorted((i for i in self.instruments.values() if i.status in ONLINE and i.base and i.quote and i.symbol),
                      key=lambda x:(x.product_type,x.symbol))
    def by_symbol(self,symbol):
        s=str(symbol or "").upper()
        return next((i for i in self.instruments.values() if i.symbol.upper()==s or i.altname.upper()==s),None)

class MarketData:
    def __init__(self,db,venue,freshness=120):
        self.db,self.venue,self.freshness=db,venue,int(freshness);self.cache={}
    @staticmethod
    def _find(mapping,instrument):
        if not isinstance(mapping,dict): return None
        for key in (instrument.altname,instrument.symbol,instrument.instrument_id):
            if key in mapping and isinstance(mapping[key],dict): return mapping[key]
        normalized={"".join(ch for ch in str(k).upper() if ch.isalnum()):v for k,v in mapping.items()}
        wanted="".join(ch for ch in str(instrument.altname or instrument.symbol).upper() if ch.isalnum())
        return normalized.get(wanted)
    def snapshot_all(self,instruments,cycle_id=""):
        spot={}
        try: spot=self.venue.spot.ticker("")
        except Exception as exc: self.db.error("API_ERROR","MARKET_SNAPSHOT",cycle_id=cycle_id,message=type(exc).__name__)
        futures=[]
        try: futures=(self.venue.futures.tickers() or {}).get("tickers",[])
        except Exception as exc: self.db.event("warning","DERIVATIVES_TICKER_DEGRADED","MARKET_SNAPSHOT",cycle_id=cycle_id,message=type(exc).__name__)
        now=time.time();count=0
        for i in instruments:
            item=self._find(spot,i) if i.product_type=="spot" else next((x for x in futures if str(x.get("symbol") or x.get("instrument"))==i.symbol),None)
            if not item: continue
            def d(*keys):
                for k in keys:
                    value=item.get(k)
                    if value in (None,""): continue
                    if isinstance(value,(list,tuple)):
                        value=value[0] if value else None
                    if value in (None,""): continue
                    try:return Decimal(str(value))
                    except Exception:continue
                return Decimal("0")
            bid,ask,last=d("bid","b"),d("ask","a"),d("last","c","markPrice","lastPrice")
            if last<=0: continue
            bid=bid or last;ask=ask or last
            depth_bid,depth_ask=d("bidSize","bid_size","bestBidSize"),d("askSize","ask_size","bestAskSize")
            imbalance=(depth_bid-depth_ask)/(depth_bid+depth_ask) if depth_bid+depth_ask>0 else Decimal("0")
            snap=MarketSnapshot(i.symbol,bid,ask,last,d("volume","volume24h","vol24h","v","vol"),now,depth_bid,depth_ask,imbalance)
            self.cache[i.symbol]=snap;count+=1
            with self.db.tx() as c:
                c.execute("INSERT INTO market_snapshots(cycle_id,symbol,ts,bid,ask,last,volume,depth_bid,depth_ask,imbalance,features_json) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                          (cycle_id,i.symbol,now,str(bid),str(ask),str(last),str(snap.volume),str(depth_bid),str(depth_ask),str(imbalance),"{}"))
        return count
    def get(self,symbol):
        s=self.cache.get(symbol)
        return s if s and time.time()-s.timestamp<=self.freshness else None
