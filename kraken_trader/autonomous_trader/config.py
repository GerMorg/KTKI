from __future__ import annotations
from dataclasses import dataclass, asdict
from decimal import Decimal
import hashlib, json, os

ABSOLUTE_CAPS={"max_leverage":Decimal("10"),"max_margin_pct":Decimal("50"),"max_gross_exposure_pct":Decimal("200"),
"max_net_exposure_pct":Decimal("150"),"max_position_risk_pct":Decimal("10"),"max_positions":20,"daily_loss_limit_pct":Decimal("25"),
"max_drawdown_pct":Decimal("35"),"cash_reserve_pct_min":Decimal("5"),"max_orders_per_day":100,"max_slippage_pct":Decimal("3")}

@dataclass(frozen=True)
class Config:
    kraken_api_key:str=""; kraken_api_secret:str=""; gemini_api_key:str=""; gemini_model:str="gemini-3.8-flash"
    news_enabled:bool=True; gemini_enabled:bool=True; trading_enabled:bool=False; live_enabled:bool=False; kill_switch:bool=True
    discovery_interval_seconds:int=300; data_freshness_seconds:int=120; minimum_liquidity_eur:Decimal=Decimal("25"); max_spread_pct:Decimal=Decimal("1.5")
    minimum_expected_edge_pct:Decimal=Decimal("0.20"); minimum_confidence:Decimal=Decimal("0.55"); recalibration_interval_minutes:int=60
    max_position_risk_pct:Decimal=Decimal("2"); max_gross_exposure_pct:Decimal=Decimal("100"); max_net_exposure_pct:Decimal=Decimal("75")
    max_margin_pct:Decimal=Decimal("25"); max_leverage:Decimal=Decimal("5"); max_positions:int=10
    daily_loss_limit_pct:Decimal=Decimal("5"); max_drawdown_pct:Decimal=Decimal("15"); cash_reserve_pct:Decimal=Decimal("20")
    max_slippage_pct:Decimal=Decimal("0.75"); order_timeout_seconds:int=10; max_reprices:int=2; max_orders_per_day:int=20; allow_market_orders:bool=False; taker_fee_pct:Decimal=Decimal("0.40"); maker_fee_pct:Decimal=Decimal("0.25")
    learning_enabled:bool=True; auto_calibration:bool=True; auto_promotion:bool=False
    news_horizon_hours:tuple[int,...]=(1,24,168); deep_scan_limit:int=50; history_lookback:int=200; start_capital_eur:Decimal=Decimal("50")

    @classmethod
    def load(cls,path="/data/options.json"):
        data={}
        try:
            with open(path,encoding="utf-8") as fh:data=json.load(fh) or {}
        except FileNotFoundError: pass
        except Exception as exc: raise ValueError(f"config read failed: {type(exc).__name__}") from exc
        def b(k,d):return bool(data.get(k,d))
        def i(k,d,lo,hi):return max(lo,min(hi,int(data.get(k,d))))
        def D(k,d,lo=None,hi=None):
            v=Decimal(str(data.get(k,d)))
            if lo is not None:v=max(Decimal(str(lo)),v)
            if hi is not None:v=min(Decimal(str(hi)),v)
            return v
        return cls(
            kraken_api_key=str(data.get("kraken_api_key") or os.getenv("KRAKEN_API_KEY","")),
            kraken_api_secret=str(data.get("kraken_api_secret") or os.getenv("KRAKEN_API_SECRET","")),
            gemini_api_key=str(data.get("gemini_api_key") or os.getenv("GEMINI_API_KEY","")),
            gemini_model=str(data.get("gemini_model","gemini-3.8-flash")),
            news_enabled=b("news_enabled",True),gemini_enabled=b("gemini_enabled",True),
            trading_enabled=b("trading_enabled",False),live_enabled=b("live_enabled",False),kill_switch=b("kill_switch",True),
            discovery_interval_seconds=i("discovery_interval_seconds",300,30,86400),data_freshness_seconds=i("data_freshness_seconds",120,10,900),
            minimum_liquidity_eur=D("minimum_liquidity_eur",25,0,100000000),max_spread_pct=D("max_spread_pct",1.5,Decimal("0.01"),20),
            minimum_expected_edge_pct=D("minimum_expected_edge_pct",0.20,0,50),minimum_confidence=D("minimum_confidence",0.55,0,1),
            recalibration_interval_minutes=i("recalibration_interval_minutes",60,5,10080),
            max_position_risk_pct=D("max_position_risk_pct",2,Decimal("0.1"),ABSOLUTE_CAPS["max_position_risk_pct"]),
            max_gross_exposure_pct=D("max_gross_exposure_pct",100,10,ABSOLUTE_CAPS["max_gross_exposure_pct"]),
            max_net_exposure_pct=D("max_net_exposure_pct",75,5,ABSOLUTE_CAPS["max_net_exposure_pct"]),
            max_margin_pct=D("max_margin_pct",25,1,ABSOLUTE_CAPS["max_margin_pct"]),
            max_leverage=D("max_leverage",5,1,ABSOLUTE_CAPS["max_leverage"]),
            max_positions=i("max_positions",10,1,ABSOLUTE_CAPS["max_positions"]),
            daily_loss_limit_pct=D("daily_loss_limit_pct",5,Decimal("0.1"),ABSOLUTE_CAPS["daily_loss_limit_pct"]),
            max_drawdown_pct=D("max_drawdown_pct",15,Decimal("0.5"),ABSOLUTE_CAPS["max_drawdown_pct"]),
            cash_reserve_pct=D("cash_reserve_pct",20,ABSOLUTE_CAPS["cash_reserve_pct_min"],95),
            max_slippage_pct=D("max_slippage_pct",0.75,0,ABSOLUTE_CAPS["max_slippage_pct"]),
            order_timeout_seconds=i("order_timeout_seconds",10,2,120),max_reprices=i("max_reprices",2,0,10),
            max_orders_per_day=i("max_orders_per_day",20,1,ABSOLUTE_CAPS["max_orders_per_day"]),allow_market_orders=b("allow_market_orders",False),taker_fee_pct=D("taker_fee_pct",0.40,0,2),maker_fee_pct=D("maker_fee_pct",0.25,0,2),
            learning_enabled=b("learning_enabled",True),auto_calibration=b("auto_calibration",True),auto_promotion=b("auto_promotion",False),
            deep_scan_limit=i("deep_scan_limit",50,5,200),history_lookback=i("history_lookback",200,50,2000),
            start_capital_eur=D("start_capital_eur",50,0,100000000))
    def validate(self):
        if self.live_enabled and self.kill_switch: raise ValueError("live_enabled requires kill_switch=false")
        if self.live_enabled and not self.trading_enabled: raise ValueError("live_enabled requires trading_enabled=true")
        pairs=[("max_leverage",self.max_leverage),("max_margin_pct",self.max_margin_pct),("max_gross_exposure_pct",self.max_gross_exposure_pct),
               ("max_net_exposure_pct",self.max_net_exposure_pct),("max_position_risk_pct",self.max_position_risk_pct),("daily_loss_limit_pct",self.daily_loss_limit_pct),
               ("max_drawdown_pct",self.max_drawdown_pct),("max_slippage_pct",self.max_slippage_pct)]
        for k,v in pairs:
            if v>ABSOLUTE_CAPS[k]: raise ValueError(f"{k} exceeds immutable cap")
        if self.max_positions>ABSOLUTE_CAPS["max_positions"] or self.max_orders_per_day>ABSOLUTE_CAPS["max_orders_per_day"]: raise ValueError("count cap exceeded")
        if self.cash_reserve_pct<ABSOLUTE_CAPS["cash_reserve_pct_min"]: raise ValueError("cash reserve below immutable cap")
    def hash(self):
        return hashlib.sha256(json.dumps(asdict(self),sort_keys=True,default=str).encode()).hexdigest()
