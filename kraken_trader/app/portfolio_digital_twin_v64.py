"""v64 digital twin for the complete portfolio execution path.
It produces an auditable simulation only; no exchange/private endpoint is called.
"""
from dataclasses import dataclass

@dataclass(frozen=True)
class TwinStep:
    step: str
    currency: str
    notional_eur: float
    cost_eur: float
    detail: str

class PortfolioDigitalTwinV64:
    def __init__(self, trading_fee_bps=40.0, fx_fee_bps=10.0, slippage_bps=10.0):
        self.trading_fee_bps=float(trading_fee_bps);self.fx_fee_bps=float(fx_fee_bps);self.slippage_bps=float(slippage_bps)

    def simulate(self, portfolio_eur, actions, eurusd=None, available_currencies=('EUR',)):
        total=max(0.0,float(portfolio_eur));fx=float(eurusd or 0.0);available={str(x).upper() for x in available_currencies};steps=[];total_cost=0.0
        if total<=0:return {'status':'INVALID_PORTFOLIO','steps':[],'total_cost_eur':0.0,'net_notional_eur':0.0}
        for action in actions or []:
            notional=min(total,max(0.0,float(action.get('notional_eur',0))));
            if notional<=0:continue
            currency=str(action.get('currency','EUR')).upper();trade_cost=notional*(self.trading_fee_bps+self.slippage_bps)/10000.0
            if currency=='USD' and 'USD' not in available:
                if fx<=0:return {'status':'MISSING_EURUSD','steps':steps,'total_cost_eur':round(total_cost,8),'net_notional_eur':round(sum(s.notional_eur for s in steps),8)}
                fx_cost=notional*self.fx_fee_bps/10000.0
                steps.append(TwinStep('EUR_TO_USD','EUR',notional,fx_cost,f'EUR/USD {fx:g}: EUR wird vor dem Produktkauf in USD umgewandelt'))
                total_cost+=fx_cost
            steps.append(TwinStep('BUY_OR_SELL_ASSET',currency,notional,trade_cost,f'Handelsgebühr + Slippage; Route={currency}'))
            total_cost+=trade_cost
        return {'status':'SIMULATED','steps':[s.__dict__ for s in steps],'total_cost_eur':round(total_cost,8),'net_notional_eur':round(sum(s.notional_eur for s in steps if s.step=='BUY_OR_SELL_ASSET'),8),'cost_pct_of_portfolio':round(100*total_cost/total,8)}
