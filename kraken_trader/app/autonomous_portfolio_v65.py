"""v65 autonomous portfolio decision engine and deterministic digital twin.
No exchange/order calls are made here. The engine produces an auditable plan only.
"""
from dataclasses import dataclass,asdict
from typing import Dict,List,Optional

@dataclass(frozen=True)
class AssetView:
    symbol:str
    score:float
    expected_return_pct:float
    volatility_pct:float
    currency:str='EUR'

@dataclass(frozen=True)
class Holding:
    symbol:str
    value_eur:float
    currency:str='EUR'

@dataclass(frozen=True)
class DecisionPolicy:
    cash_reserve_pct:float=20.0
    max_position_pct:float=5.0
    no_trade_band_pct:float=2.0
    minimum_score:float=70.0
    min_trade_eur:float=20.0
    max_trade_eur:float=50.0
    max_actions:int=1
    fx_fee_bps:float=10.0
    trading_fee_bps:float=40.0
    slippage_bps:float=10.0

class AutonomousPortfolioEngine:
    """Converts model outputs into a bounded target portfolio and dry-run actions."""
    def __init__(self,policy:DecisionPolicy=None):self.policy=policy or DecisionPolicy()
    def _eligible(self,a):return a.score>=self.policy.minimum_score and a.expected_return_pct>0 and a.volatility_pct>=0
    def target_weights(self,assets:List[AssetView])->Dict[str,float]:
        eligible=[a for a in assets if self._eligible(a)]
        budget=max(0.,100.-self.policy.cash_reserve_pct)
        if not eligible or budget<=0:return {}
        # Reward expected return while penalising volatility; score is a quality gate,
        # not a substitute for risk.
        raw={a.symbol:max(0.,a.expected_return_pct)/(1.+a.volatility_pct/100.) for a in eligible}
        total=sum(raw.values())
        if total<=0:return {}
        weights={s:budget*v/total for s,v in raw.items()}
        cap=self.policy.max_position_pct
        # Water-fill capped weights so the portfolio never silently exceeds limits.
        fixed={};remaining=budget;pool=list(weights)
        while pool:
            proposed={s:remaining*raw[s]/sum(raw[x] for x in pool) for s in pool}
            over=[s for s in pool if proposed[s]>cap]
            if not over:
                fixed.update(proposed);break
            for s in over:fixed[s]=cap;remaining-=cap;pool.remove(s)
            if remaining<=0:break
        return {s:round(w,8) for s,w in fixed.items() if w>0}
    def rebalance(self,total_eur:float,holdings:List[Holding],assets:List[AssetView])->Dict:
        current={h.symbol:(h.value_eur/total_eur*100 if total_eur>0 else 0.) for h in holdings}
        targets=self.target_weights(assets);symbols=sorted(set(current)|set(targets));actions=[]
        for s in symbols:
            delta=targets.get(s,0.)-current.get(s,0.)
            if abs(delta)<self.policy.no_trade_band_pct:continue
            amount=abs(delta)/100.*total_eur
            if amount<self.policy.min_trade_eur:continue
            amount=min(amount,self.policy.max_trade_eur)
            actions.append({'symbol':s,'side':'BUY' if delta>0 else 'SELL','target_weight_pct':targets.get(s,0.),'current_weight_pct':current.get(s,0.),'delta_pct':delta,'notional_eur':round(amount,8)})
        actions.sort(key=lambda x:abs(x['delta_pct']),reverse=True);actions=actions[:max(0,self.policy.max_actions)]
        for a in actions:a['estimated_trading_cost_eur']=a['notional_eur']*(self.policy.trading_fee_bps+self.policy.slippage_bps)/10000.
        return {'total_eur':total_eur,'cash_reserve_pct':self.policy.cash_reserve_pct,'current_weights_pct':current,'target_weights_pct':targets,'actions':actions,'action_count':len(actions)}

class DigitalTwin:
    """Replays a proposed plan including currency conversion and all configured costs."""
    def __init__(self,policy:DecisionPolicy=None):self.policy=policy or DecisionPolicy()
    def execute(self,plan:Dict,eur_balance:float,usd_balance:float=0.,fx_rate_eur_per_usd:Optional[float]=None)->Dict:
        if fx_rate_eur_per_usd is not None and fx_rate_eur_per_usd<=0:raise ValueError('fx_rate_eur_per_usd must be positive')
        fx_cost=trade_cost=0.;remaining_eur=float(eur_balance);remaining_usd=float(usd_balance);events=[]
        for a in plan.get('actions',[]):
            amount=float(a['notional_eur']);cost=amount*(self.policy.trading_fee_bps+self.policy.slippage_bps)/10000.;trade_cost+=cost
            if a['side']!='BUY':events.append({'symbol':a['symbol'],'side':a['side'],'notional_eur':amount,'trade_cost_eur':cost});continue
            currency=next((x.get('currency') for x in plan.get('assets',[]) if x.get('symbol')==a['symbol']),'EUR')
            if currency=='USD':
                if fx_rate_eur_per_usd is None:return {'status':'BLOCKED_FX_RATE_MISSING','events':events,'trade_cost_eur':trade_cost,'fx_cost_eur':fx_cost}
                usd_needed=amount/fx_rate_eur_per_usd;fx=usd_needed*self.policy.fx_fee_bps/10000.;total_eur=amount+fx
                if remaining_eur<total_eur:return {'status':'BLOCKED_INSUFFICIENT_EUR_FOR_FX','events':events,'trade_cost_eur':trade_cost,'fx_cost_eur':fx_cost}
                remaining_eur-=total_eur;remaining_usd+=usd_needed;fx_cost+=fx;events.append({'symbol':a['symbol'],'side':'BUY','currency':'USD','eur_funding':amount,'usd_acquired':usd_needed,'fx_cost_eur':fx,'trade_cost_eur':cost})
            else:
                if remaining_eur<amount+cost:return {'status':'BLOCKED_INSUFFICIENT_EUR','events':events,'trade_cost_eur':trade_cost,'fx_cost_eur':fx_cost}
                remaining_eur-=amount+cost;events.append({'symbol':a['symbol'],'side':'BUY','currency':'EUR','notional_eur':amount,'trade_cost_eur':cost})
        return {'status':'SIMULATED','events':events,'remaining_eur':round(remaining_eur,8),'remaining_usd':round(remaining_usd,8),'trade_cost_eur':round(trade_cost,8),'fx_cost_eur':round(fx_cost,8),'total_cost_eur':round(trade_cost+fx_cost,8)}
    @staticmethod
    def serializable(obj):
        if hasattr(obj,'__dataclass_fields__'):return asdict(obj)
        return obj
