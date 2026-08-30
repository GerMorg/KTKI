"""v64 digital twin. Simulates the complete currency/execution cost path without orders."""
from dataclasses import dataclass
@dataclass(frozen=True)
class TwinStep:
 step:str;currency:str;notional_eur:float;cost_eur:float;detail:str
class PortfolioDigitalTwinV64:
 def __init__(self,trading_fee_bps=40,fx_fee_bps=10,slippage_bps=10):self.trading_fee_bps=float(trading_fee_bps);self.fx_fee_bps=float(fx_fee_bps);self.slippage_bps=float(slippage_bps)
 def simulate(self,portfolio_eur,actions,eurusd=None,available_currencies=('EUR',)):
  total=max(0,float(portfolio_eur));fx=float(eurusd or 0);available={str(x).upper() for x in available_currencies};steps=[];cost=0
  if total<=0:return {'status':'INVALID_PORTFOLIO','steps':[],'total_cost_eur':0.0,'net_notional_eur':0.0}
  for action in actions or []:
   n=min(total,max(0,float(action.get('notional_eur',0))))
   if n<=0:continue
   currency=str(action.get('currency','EUR')).upper();trade=n*(self.trading_fee_bps+self.slippage_bps)/10000
   if currency=='USD' and 'USD' not in available:
    if fx<=0:return {'status':'MISSING_EURUSD','steps':[s.__dict__ for s in steps],'total_cost_eur':round(cost,8),'net_notional_eur':round(sum(s.notional_eur for s in steps if s.step=='BUY_OR_SELL_ASSET'),8)}
    fx_cost=n*self.fx_fee_bps/10000;steps.append(TwinStep('EUR_TO_USD','EUR',n,fx_cost,f'EUR/USD {fx:g}: EUR wird vor dem Produktkauf in USD umgewandelt'));cost+=fx_cost
   steps.append(TwinStep('BUY_OR_SELL_ASSET',currency,n,trade,f'Handelsgebühr + Slippage; Route={currency}'));cost+=trade
  return {'status':'SIMULATED','steps':[s.__dict__ for s in steps],'total_cost_eur':round(cost,8),'net_notional_eur':round(sum(s.notional_eur for s in steps if s.step=='BUY_OR_SELL_ASSET'),8),'cost_pct_of_portfolio':round(100*cost/total,8)}
