"""v65 autonomous portfolio decision engine and deterministic digital twin.

The module is deliberately side-effect free: it creates an auditable portfolio
plan and simulates it. It never calls an exchange or places an order.
"""
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional

@dataclass(frozen=True)
class AssetView:
    symbol: str
    score: float
    expected_return_pct: float
    volatility_pct: float
    currency: str = "EUR"

@dataclass(frozen=True)
class Holding:
    symbol: str
    value_eur: float
    currency: str = "EUR"

@dataclass(frozen=True)
class DecisionPolicy:
    cash_reserve_pct: float = 20.0
    max_position_pct: float = 5.0
    no_trade_band_pct: float = 2.0
    minimum_score: float = 70.0
    min_trade_eur: float = 20.0
    max_trade_eur: float = 50.0
    max_actions: int = 1
    fx_fee_bps: float = 10.0
    trading_fee_bps: float = 40.0
    slippage_bps: float = 10.0

class AutonomousPortfolioEngine:
    """Turn validated model outputs into bounded, auditable rebalance plans."""
    def __init__(self, policy: DecisionPolicy = None):
        self.policy = policy or DecisionPolicy()
    def _eligible(self, a: AssetView) -> bool:
        return a.score >= self.policy.minimum_score and a.expected_return_pct > 0 and a.volatility_pct >= 0 and str(a.currency).upper() in {"EUR", "USD"}
    def target_weights(self, assets: List[AssetView]) -> Dict[str, float]:
        eligible = [a for a in assets if self._eligible(a)]
        budget = max(0.0, 100.0 - self.policy.cash_reserve_pct)
        cap = max(0.0, self.policy.max_position_pct)
        if not eligible or budget <= 0 or cap <= 0: return {}
        raw = {a.symbol: max(0.0, a.expected_return_pct) / (1.0 + a.volatility_pct / 100.0) for a in eligible}
        if sum(raw.values()) <= 0: return {}
        weights, remaining, pool = {}, budget, list(raw)
        while pool and remaining > 1e-10:
            pool_raw = sum(raw[s] for s in pool)
            proposed = {s: remaining * raw[s] / pool_raw for s in pool}
            over = [s for s in pool if proposed[s] > cap + 1e-10]
            if not over:
                weights.update(proposed); break
            for s in over:
                weights[s] = cap; remaining -= cap; pool.remove(s)
        return {s: round(w, 8) for s, w in weights.items() if w > 1e-10}
    def rebalance(self, total_eur: float, holdings: List[Holding], assets: List[AssetView]) -> Dict:
        total = float(total_eur)
        if total <= 0: return {"status":"INVALID_PORTFOLIO","total_eur":total,"actions":[],"action_count":0}
        current = {h.symbol: max(0.0, float(h.value_eur)) / total * 100.0 for h in holdings}
        targets = self.target_weights(assets); asset_map = {a.symbol:a for a in assets}; actions=[]
        for symbol in sorted(set(current)|set(targets)):
            delta = targets.get(symbol,0.0)-current.get(symbol,0.0)
            if abs(delta) < self.policy.no_trade_band_pct: continue
            amount = abs(delta)/100.0*total
            if amount < self.policy.min_trade_eur: continue
            amount=min(amount,self.policy.max_trade_eur); asset=asset_map.get(symbol); currency=str(asset.currency).upper() if asset else 'EUR'
            actions.append({'symbol':symbol,'side':'BUY' if delta>0 else 'SELL','currency':currency,'target_weight_pct':round(targets.get(symbol,0.0),8),'current_weight_pct':round(current.get(symbol,0.0),8),'delta_pct':round(delta,8),'notional_eur':round(amount,8)})
        actions.sort(key=lambda x:(-abs(x['delta_pct']),x['symbol'])); actions=actions[:max(0,int(self.policy.max_actions))]
        for a in actions:a['estimated_trading_cost_eur']=round(a['notional_eur']*(self.policy.trading_fee_bps+self.policy.slippage_bps)/10000.0,8)
        return {'status':'PLAN_READY','total_eur':total,'cash_reserve_pct':self.policy.cash_reserve_pct,'current_weights_pct':current,'target_weights_pct':targets,'assets':[asdict(a) for a in assets],'actions':actions,'action_count':len(actions)}

class DigitalTwin:
    """Replay a plan including EUR/USD funding and all configured costs."""
    def __init__(self, policy: DecisionPolicy = None): self.policy=policy or DecisionPolicy()
    def execute(self, plan: Dict, eur_balance: float, usd_balance: float=0.0, fx_rate_eur_per_usd: Optional[float]=None) -> Dict:
        if not isinstance(plan,dict): raise TypeError('plan must be a dictionary')
        if fx_rate_eur_per_usd is not None and fx_rate_eur_per_usd<=0: raise ValueError('fx_rate_eur_per_usd must be positive')
        remaining_eur=float(eur_balance); remaining_usd=float(usd_balance); trade_cost=0.0; fx_cost=0.0; events=[]
        for action in plan.get('actions') or []:
            if not isinstance(action,dict): return {'status':'BLOCKED_INVALID_ACTION','events':events}
            amount=float(action.get('notional_eur',0.0))
            if amount<=0: continue
            side=str(action.get('side','BUY')).upper(); currency=str(action.get('currency','EUR')).upper()
            trading_cost=amount*(self.policy.trading_fee_bps+self.policy.slippage_bps)/10000.0
            if side=='SELL':
                trade_cost+=trading_cost; events.append({'symbol':action.get('symbol'),'side':'SELL','currency':currency,'notional_eur':amount,'trade_cost_eur':trading_cost}); continue
            if side!='BUY': return {'status':'BLOCKED_INVALID_SIDE','events':events}
            if currency=='USD':
                if fx_rate_eur_per_usd is None: return {'status':'BLOCKED_FX_RATE_MISSING','events':events,'trade_cost_eur':round(trade_cost,8),'fx_cost_eur':round(fx_cost,8)}
                usd_needed=amount/float(fx_rate_eur_per_usd); fx=usd_needed*self.policy.fx_fee_bps/10000.0; total_eur=amount+fx
                if remaining_eur<total_eur: return {'status':'BLOCKED_INSUFFICIENT_EUR_FOR_FX','events':events,'trade_cost_eur':round(trade_cost,8),'fx_cost_eur':round(fx_cost,8)}
                remaining_eur-=total_eur; remaining_usd+=usd_needed; fx_cost+=fx; trade_cost+=trading_cost
                events.append({'symbol':action.get('symbol'),'side':'BUY','currency':'USD','eur_funding':amount,'usd_acquired':usd_needed,'fx_cost_eur':fx,'trade_cost_eur':trading_cost})
            elif currency=='EUR':
                if remaining_eur<amount+trading_cost: return {'status':'BLOCKED_INSUFFICIENT_EUR','events':events,'trade_cost_eur':round(trade_cost,8),'fx_cost_eur':round(fx_cost,8)}
                remaining_eur-=amount+trading_cost; trade_cost+=trading_cost; events.append({'symbol':action.get('symbol'),'side':'BUY','currency':'EUR','notional_eur':amount,'trade_cost_eur':trading_cost})
            else: return {'status':'BLOCKED_UNSUPPORTED_CURRENCY','events':events}
        return {'status':'SIMULATED','events':events,'remaining_eur':round(remaining_eur,8),'remaining_usd':round(remaining_usd,8),'trade_cost_eur':round(trade_cost,8),'fx_cost_eur':round(fx_cost,8),'total_cost_eur':round(trade_cost+fx_cost,8)}
    @staticmethod
    def serializable(obj):
        return asdict(obj) if hasattr(obj,'__dataclass_fields__') else obj
