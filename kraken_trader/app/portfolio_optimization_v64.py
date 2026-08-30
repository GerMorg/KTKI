"""v64 portfolio optimization: risk, costs, turnover and FX-aware rebalance planning.

This module is deliberately side-effect free. It computes target weights and a
rebalancing plan but never submits an exchange order.
"""
import math
from dataclasses import dataclass

@dataclass(frozen=True)
class Route:
    currency: str
    fx_required: bool
    fx_fee_pct: float
    trading_fee_pct: float
    slippage_pct: float
    total_cost_pct: float

class PortfolioOptimizerV64:
    def __init__(self, cash_reserve_pct=20.0, max_position_pct=25.0,
                 no_trade_band_pct=2.0, min_trade_eur=20.0, max_trade_eur=250.0,
                 fee_bps=40.0, fx_fee_bps=10.0, slippage_bps=10.0):
        self.cash_reserve_pct=max(0.0,min(95.0,float(cash_reserve_pct)))
        self.max_position_pct=max(0.0,min(100.0,float(max_position_pct)))
        self.no_trade_band_pct=max(0.0,float(no_trade_band_pct))
        self.min_trade_eur=max(0.0,float(min_trade_eur))
        self.max_trade_eur=max(self.min_trade_eur,float(max_trade_eur))
        self.fee_bps=max(0.0,float(fee_bps));self.fx_fee_bps=max(0.0,float(fx_fee_bps));self.slippage_bps=max(0.0,float(slippage_bps))

    @staticmethod
    def _clean_scores(scores):
        return {str(k):max(0.0,float(v)) for k,v in dict(scores or {}).items() if math.isfinite(float(v)) and float(v)>0}

    def target_weights(self, scores, covariance=None, risk_aversion=1.0):
        scores=self._clean_scores(scores)
        investable=max(0.0,100.0-self.cash_reserve_pct)
        if not scores or investable<=0:return {'EUR':100.0}
        # Start from risk-adjusted scores. Diagonal risk is accepted as either
        # variance or volatility; off-diagonal covariance reduces concentration.
        risk={k:1.0 for k in scores}
        cov=covariance or {}
        for k in scores:
            diagonal=cov.get(k,{}).get(k,1.0) if isinstance(cov.get(k,{}),dict) else 1.0
            risk[k]=max(1e-9,float(diagonal))
        raw={k:(v/(risk[k]**max(0.0,float(risk_aversion)))) for k,v in scores.items()}
        total=sum(raw.values()) or 1.0
        weights={k:min(self.max_position_pct,investable*v/total) for k,v in raw.items()}
        used=sum(weights.values())
        if used<investable:
            # redistribute unused capacity without breaching max position.
            for _ in range(len(weights)+1):
                room={k:self.max_position_pct-w for k,w in weights.items() if self.max_position_pct-w>1e-9}
                if not room:break
                add=min(investable-used,sum(room.values()))
                base=sum(raw[k] for k in room) or float(len(room))
                for k in room:weights[k]+=add*(raw[k]/base)
                used=sum(weights.values())
                if add<=1e-9:break
        weights={k:round(v,10) for k,v in weights.items() if v>1e-8}
        weights['EUR']=round(max(0.0,100.0-sum(weights.values())),10)
        return weights

    def route(self, product_currency, available_currencies=None, market_costs=None):
        currency=str(product_currency or 'EUR').upper();available={str(x).upper() for x in (available_currencies or ['EUR'])};costs=market_costs or {}
        if currency in available:
            fx=0.0;fx_required=False
        elif currency=='USD' or currency not in available:
            fx=self.fx_fee_bps/100.0;fx_required=True
        else:fx=0.0;fx_required=False
        trade=float(costs.get(currency+'_fee_bps',self.fee_bps))/100.0
        slip=float(costs.get(currency+'_slippage_bps',self.slippage_bps))/100.0
        return Route(currency,fx_required,fx,trade,slip,fx+trade+slip)

    def rebalance_plan(self, current_weights, target_weights, portfolio_eur, currencies=None, route_costs=None):
        total=max(0.0,float(portfolio_eur));current={str(k):float(v) for k,v in dict(current_weights or {}).items()};target={str(k):float(v) for k,v in dict(target_weights or {}).items()}
        symbols=set(current)|set(target);plan=[]
        for symbol in sorted(symbols):
            delta=target.get(symbol,0.0)-current.get(symbol,0.0)
            if symbol=='EUR':continue
            notional=abs(delta)/100.0*total
            if abs(delta)<self.no_trade_band_pct or notional<self.min_trade_eur:continue
            notional=min(notional,self.max_trade_eur)
            direction='BUY' if delta>0 else 'SELL'
            currency=(currencies or {}).get(symbol,'EUR')
            route=self.route(currency,available_currencies=['EUR'],market_costs=(route_costs or {}).get(symbol,{}))
            plan.append({'symbol':symbol,'action':direction,'notional_eur':round(notional,2),'weight_delta_pct':round(delta,6),'route':route.currency,'fx_required':route.fx_required,'fx_fee_pct':round(route.fx_fee_pct,6),'trading_fee_pct':round(route.trading_fee_pct,6),'slippage_pct':round(route.slippage_pct,6),'estimated_cost_eur':round(notional*route.total_cost_pct/100.0,2)})
        return sorted(plan,key=lambda x:(x['action']!='SELL',-x['notional_eur'],x['symbol']))

    @staticmethod
    def turnover(plan, portfolio_eur):
        total=max(0.0,float(portfolio_eur));return sum(float(x.get('notional_eur',0)) for x in plan)/total if total else 0.0

    @staticmethod
    def rebalance_value(current_weights,target_weights,portfolio_eur,plan):
        before=sum(abs(float(target_weights.get(k,0))-float(current_weights.get(k,0))) for k in set(current_weights)|set(target_weights))
        executed=sum(float(x.get('notional_eur',0)) for x in plan)
        after=max(0.0,before-100.0*executed/max(1.0,float(portfolio_eur)))
        return {'distance_before_pct_points':before,'executed_notional_eur':executed,'distance_after_lower_bound_pct_points':after,'turnover':PortfolioOptimizerV64.turnover(plan,portfolio_eur)}
