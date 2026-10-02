from __future__ import annotations
from decimal import Decimal
from .models import Blocker,Signal,Instrument,dec
class RiskEngine:
    def __init__(self,config):self.c=config
    def margin_safe(self,p):
        level=dec(p.get("margin_level"),Decimal("999999")); 
        if p.get("margin_danger") or (level>0 and level<Decimal("150")):return False,Blocker.BLOCKED_MARGIN.value
        return True,""
    def select_leverage(self,signal:Signal,instrument:Instrument,portfolio):
        if not instrument.margin or instrument.max_leverage<=1:return Decimal("1"),None
        raw=Decimal("1")+max(Decimal("0"),signal.expected_return*20)*signal.confidence
        if signal.uncertainty>Decimal("0.5"):raw=Decimal("1")
        if dec(portfolio.get("drawdown_pct"))>self.c.max_drawdown_pct/2:raw=min(raw,Decimal("2"))
        allowed=[Decimal("1")]
        for level in instrument.leverage_levels:
            try:
                x=Decimal(str(level))
                if x>0 and x<=self.c.max_leverage and x<=instrument.max_leverage:allowed.append(x)
            except Exception:continue
        if signal.direction=="short" and instrument.product_type=="spot" and instrument.margin:
            allowed=[x for x in allowed if x>1] or allowed
            raw=max(raw,Decimal("2"))
        candidates=[x for x in allowed if x<=raw]
        return (max(candidates) if candidates else min(allowed)),None
    def size(self,signal:Signal,portfolio,leverage):
        equity=dec(portfolio.get("equity"))
        if equity<=0:return Decimal("0"),Blocker.BLOCKED_POSITION_SIZE.value
        vol=dec(signal.features.get("realized_volatility"),Decimal("0.03"));down=dec(signal.features.get("downside_volatility"),vol)
        risk_per_eur=max(Decimal("0.005"),vol,down);budget=equity*self.c.max_position_risk_pct/100
        notional=budget/risk_per_eur*max(Decimal("0.25"),signal.confidence)*max(Decimal("1"),leverage)
        notional=min(notional,equity*self.c.max_gross_exposure_pct/100-dec(portfolio.get("gross_exposure")),
                     equity*self.c.max_net_exposure_pct/100-abs(dec(portfolio.get("net_exposure"))),
                     max(Decimal("0"),equity*(1-self.c.cash_reserve_pct/100)))
        return (notional,None) if notional>0 else (Decimal("0"),Blocker.BLOCKED_PORTFOLIO.value)
    def check(self,signal,instrument,portfolio,target,leverage,existing_positions,orders_today):
        blocked=None
        margin_ok,mb=self.margin_safe(portfolio)
        if not margin_ok and signal.direction in ("long","short"):blocked=mb
        if signal.confidence<self.c.minimum_confidence:blocked=Blocker.BLOCKED_STRATEGY.value
        if signal.expected_return*100<self.c.minimum_expected_edge_pct:blocked=Blocker.BLOCKED_EXPECTED_EDGE.value
        if dec(portfolio.get("daily_loss_pct"))>=self.c.daily_loss_limit_pct or dec(portfolio.get("drawdown_pct"))>=self.c.max_drawdown_pct:blocked=Blocker.CIRCUIT_BREAKER.value
        if orders_today>=self.c.max_orders_per_day:blocked=Blocker.BLOCKED_ORDER_LIMIT.value
        if len(existing_positions)>=self.c.max_positions and target>0:blocked=Blocker.BLOCKED_PORTFOLIO.value
        if signal.direction=="short" and not instrument.long_short:blocked=Blocker.BLOCKED_LEVERAGE.value
        if signal.direction=="short" and instrument.product_type=="spot" and instrument.margin and leverage<Decimal("2"):blocked=Blocker.BLOCKED_LEVERAGE.value
        return blocked
