"""v94 canonical decision engine shared by Paper and Real.

Only the execution adapter is allowed to differ after this module.  The engine
turns the same market/news/model evidence into a target exposure and an order
intent.  It deliberately separates signal conviction, model quality, economic
edge and portfolio/risk constraints.
"""
from decimal import Decimal
D=lambda x: Decimal(str(x or 0))

class DecisionEngineV94:
    def __init__(self, db):
        self.db=db

    @staticmethod
    def direction(signal):
        s=str(signal or '').upper()
        if s in ('BUY','UP','LONG'): return 'LONG'
        if s in ('AVOID','SELL','DOWN','SHORT'): return 'SHORT'
        return 'FLAT'

    @staticmethod
    def regime_factor(regime,direction):
        r=str(regime or 'NEUTRAL').upper()
        if direction=='LONG':
            return {'BULL':D('1.0'),'NEUTRAL':D('.75'),'MIXED':D('.55'),'BEAR':D('.25')}.get(r,D('.5'))
        if direction=='SHORT':
            return {'BEAR':D('1.0'),'NEUTRAL':D('.75'),'MIXED':D('.55'),'BULL':D('.25')}.get(r,D('.5'))
        return D(0)

    def _symbol_edge(self,symbol,direction,limit=30):
        if not self.db or not symbol:return None
        want='UP' if direction=='LONG' else 'DOWN'
        try:
            rows=self.db.rows("SELECT f.direction,e.actual_return_pct,f.features_json FROM research_forecasts f JOIN forecast_evaluations e ON e.forecast_id=f.id WHERE f.symbol=? AND f.horizon_hours=24 AND f.direction=? ORDER BY f.id DESC LIMIT ?",(symbol,want,int(limit)))
        except Exception:return None
        vals=[]
        import json
        for r in rows:
            try:features=json.loads(r.get('features_json') or '{}')
            except Exception:features={}
            actual=D(r.get('actual_return_pct'))
            cost=D(features.get('estimated_roundtrip_cost_pct'))
            vals.append(actual-cost if want=='UP' else -actual-cost)
        return sum(vals)/D(len(vals)) if vals else None

    def news_score(self,row):
        for k in ('news_score','news_impact_score','news_relevance_score'):
            if k in row and row.get(k) not in (None,''):
                try:return D(row.get(k))
                except Exception:pass
        return D(0)

    def candidate_edge(self,row,health,route_cost_pct,direction):
        # Scanner score is conviction, not expected return.  The only economic
        # gate is an explicit forecast edge after the current route costs.
        raw=D(row.get('expected_edge_pct',row.get('forecast_edge_pct',0)))
        if raw==0:
            symbol_edge=self._symbol_edge(row.get('symbol'),direction)
            if symbol_edge is not None:
                raw=symbol_edge
            elif direction=='LONG':
                raw=D(health.get('horizons',{}).get('24',{}).get('expected_up_edge_raw_pct',0) or 0)
                if raw==0: raw=D(health.get('expected_edge_after_costs_pct',0) or 0)
            elif direction=='SHORT':
                raw=D(health.get('horizons',{}).get('24',{}).get('expected_down_edge_raw_pct',0) or 0)
                if raw==0: raw=D(health.get('directions',{}).get('DOWN',{}).get('net_return_pct',0) or 0)
        news=self.news_score(row)
        # News is an input to the decision, never a standalone order trigger.
        news_adj=max(D('-2'),min(D(2),news/100))
        gross=raw+news_adj
        return gross-D(route_cost_pct)

    def build(self,row,health,total,current_eur,route_cost_pct,regime,config,existing=False):
        direction=self.direction(row.get('signal'))
        score=D(row.get('score'))
        quality=D(health.get('quality_score',50) or 50)
        regime_factor=self.regime_factor(regime,direction)
        volatility=max(D('.25'),abs(D(row.get('volatility_pct') or 0)))
        edge_after_cost=self.candidate_edge(row,health,D(route_cost_pct),direction)
        quality_factor=D('.65')+D('.35')*max(D(0),min(D(100),quality))/100
        conviction=max(D(0),score-D(row.get('buy_threshold',config.get('minimum_score',70))))
        sizing=conviction/volatility/(D(1)+max(D(0),D(route_cost_pct)))*quality_factor*regime_factor if direction!='FLAT' else D(0)
        max_position=D(config.get('max_position_pct',5))/100
        reserve=D(config.get('cash_reserve_pct',20))/100
        budget=max(D(0),D(total)*(1-reserve))
        raw_target=min(D(budget)*max_position, D(budget)*sizing) if direction=='LONG' else D(0)
        # Shorts use the same sizing function but are represented as negative exposure.
        if direction=='SHORT':
            raw_target=-min(D(budget)*max_position,D(budget)*sizing)
        current=D(current_eur)
        delta=raw_target-current
        # Existing positions are never silently dropped: a missing/invalid BUY
        # signal produces an explicit HOLD/EXIT target in the caller.
        action='HOLD'
        if direction=='LONG' and raw_target>0: action='BUY' if delta>0 else ('SELL' if delta<0 else 'HOLD')
        elif direction=='SHORT': action='SELL' if delta<0 else ('BUY' if delta>0 else 'HOLD')
        elif existing and current>0: action='SELL'
        elif existing and current<0: action='BUY'
        else: action='HOLD'
        return {
            'symbol':row.get('symbol'),'direction':direction,'signal':row.get('signal'),
            'score':str(score),'quality_score':str(quality),'regime':regime,
            'regime_factor':str(regime_factor),'volatility_pct':str(volatility),
            'roundtrip_cost_pct':str(route_cost_pct),'expected_edge_after_costs_pct':str(edge_after_cost),
            'news_score':str(self.news_score(row)),'target_exposure_eur':str(raw_target),
            'current_exposure_eur':str(current),'rebalance_delta_eur':str(delta),
            'action':action,'economic_gate_passed':edge_after_cost>0 or (existing and action in ('SELL','BUY')),
            'quality_role':'SIZING_AND_CONFIDENCE','paper_real_decision_hash_inputs':{
                'score':str(score),'quality':str(quality),'regime':regime,
                'edge_after_costs':str(edge_after_cost),'target':str(raw_target),
                'current':str(current),'action':action},
        }

    def valid_entry(self,decision):
        return decision['action'] in ('BUY','SELL') and decision['economic_gate_passed'] and D(decision['rebalance_delta_eur'])!=0

    def target_rows(self, rows, health_by_family, total, current_by_symbol, config, regime_by_family, route_costs):
        out=[]
        for row in rows:
            family=row.get('family','crypto_spot')
            health=health_by_family.get(family,{})
            regime=regime_by_family.get(family,{}).get('regime','NEUTRAL')
            d=self.build(row,health,total,current_by_symbol.get(row.get('symbol'),0),route_costs.get(row.get('symbol'),999),regime,config,row.get('symbol') in current_by_symbol)
            out.append(d)
        return out
