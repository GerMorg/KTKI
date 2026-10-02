from __future__ import annotations
from decimal import Decimal
import math
from .models import Signal
def clamp(x,lo=Decimal("0"),hi=Decimal("1")):return max(lo,min(hi,x))
class FeatureEngine:
    def __init__(self,venue,lookback=200):self.venue,self.lookback=venue,int(lookback)
    def features(self,instrument,snapshot):
        out={"returns":None,"momentum":None,"trend":None,"ema_slope":None,"sma_slope":None,"atr":None,"realized_volatility":None,
             "downside_volatility":None,"volume_anomaly":None,"spread":str(snapshot.spread),"depth_bid":str(snapshot.depth_bid),
             "depth_ask":str(snapshot.depth_ask),"imbalance":str(snapshot.imbalance),"liquidity":str(snapshot.volume*snapshot.last),
             "market_impact":None,"relative_strength":None,"correlation":None,"btc_regime":None,"funding":str(instrument.funding),
             "basis":None,"open_interest":None,"liquidations":None}
        if instrument.product_type!="spot":return out
        try:
            raw=self.venue.spot.ohlc(instrument.altname or instrument.symbol,60)
            rows=list(raw.get(instrument.altname) or raw.get(instrument.symbol) or raw.get(instrument.instrument_id) or [])[-self.lookback:]
            closes=[Decimal(str(x[4])) for x in rows if len(x)>5 and Decimal(str(x[4]))>0]
            if len(closes)<30:return out
            n=min(20,len(closes)-1);ret=closes[-1]/closes[-1-n]-1;out["returns"]=str(ret);out["momentum"]=str(ret)
            fast=sum(closes[-10:])/Decimal("10");slow=sum(closes[-30:])/Decimal("30");trend=fast/slow-1
            out["trend"]=str(trend);out["ema_slope"]=str(trend);out["sma_slope"]=str(trend)
            rets=[float(closes[j]/closes[j-1]-1) for j in range(1,len(closes))];mu=sum(rets)/len(rets);var=sum((x-mu)**2 for x in rets)/max(1,len(rets)-1)
            out["realized_volatility"]=str(Decimal(str(math.sqrt(var)*math.sqrt(24))));down=[x for x in rets if x<0]
            out["downside_volatility"]=str(Decimal(str(math.sqrt(sum(x*x for x in down)/max(1,len(down)))))
            trs=[abs(float(Decimal(str(x[2]))-Decimal(str(x[3]))) for x in rows[-20:] if len(x)>3]
            if trs:out["atr"]=str(sum(Decimal(str(x)) for x in trs)/Decimal(len(trs)))
            vols=[Decimal(str(x[6])) for x in rows if len(x)>6]
            if len(vols)>=20 and vols[-1]>0:
                avg=sum(vols[:-1])/Decimal(max(1,len(vols)-1));out["volume_anomaly"]=str(vols[-1]/avg if avg else Decimal("1"))
        except Exception:pass
        return out
class RegimeEngine:
    def detect(self,features):
        trend=Decimal(str(features.get("trend") or 0));vol=Decimal(str(features.get("realized_volatility") or 0));spread=Decimal(str(features.get("spread") or 0))
        if spread>Decimal("0.015"):return "LIQUIDITY_STRESS"
        if vol>Decimal("0.08") and trend<Decimal("-0.03"):return "PANIC"
        if vol>Decimal("0.08"):return "HIGH_VOLATILITY"
        if trend>Decimal("0.02"):return "TREND_UP"
        if trend<Decimal("-0.02"):return "TREND_DOWN"
        if vol<Decimal("0.01"):return "LOW_VOLATILITY"
        return "RANGE"
class Ensemble:
    def __init__(self,news_weight=Decimal("0.12"),gemini_weight=Decimal("0.08")):self.news_weight,self.gemini_weight=news_weight,gemini_weight
    def signal(self,instrument,features,regime,news_effect=Decimal("0"),gemini_effect=Decimal("0"),model_version="ensemble-v1"):
        mom=Decimal(str(features.get("momentum") or 0));trend=Decimal(str(features.get("trend") or 0));imb=Decimal(str(features.get("imbalance") or 0));vol=Decimal(str(features.get("realized_volatility") or 0));spread=Decimal(str(features.get("spread") or 0))
        long_score=clamp(Decimal("0.5")+mom*3+trend*2+imb*Decimal("0.25")+news_effect*self.news_weight+gemini_effect*self.gemini_weight)
        short_score=clamp(Decimal("0.5")-mom*3-trend*2-imb*Decimal("0.25")-news_effect*self.news_weight-gemini_effect*self.gemini_weight)
        conf=clamp(Decimal("1")-vol*3-spread*2);expected=(long_score-short_score)*max(Decimal("0.01"),Decimal("0.5")-vol)
        direction="long" if long_score>=short_score else "short"
        return Signal(instrument.symbol,direction,long_score,short_score,expected,conf,Decimal("1")-conf,regime,
                      ["momentum","trend","orderbook","news","gemini"],features,model_version)
