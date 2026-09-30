"""v95 Paper execution adapter.

All candidate, cost, target and economic decisions come from DecisionEngineV95.
This adapter only simulates the resulting Kraken fill and account effect.
"""

from decimal import Decimal
from paper_engine import PaperEngine, configure_engine
from model_health import ModelHealth
from strategy_profiles import family_for_category
from execution_confidence import execution_confidence, choose_execution
from market_regime import family_regime
from decision_context_v95 import ticker_map, scanner_candidates, routes_for_symbol, alternatives, decision_costs
from decision_engine_v95 import DecisionEngineV95

D=lambda x:Decimal(str(x or 0))


class PaperEngineV95(PaperEngine):
    def _existing_execution(self, symbol, margin_enabled, max_leverage):
        rows=self.db.rows('SELECT leverage FROM paper_position_risk WHERE symbol=? LIMIT 1',(symbol,))
        if rows:
            lev=max(1,int(float(rows[0].get('leverage') or 1)))
            return {'mode':'MARGIN' if margin_enabled and lev>1 else 'SPOT','leverage':min(lev,max_leverage),'reason':'EXISTING_POSITION_ROUTING'}
        return {'mode':'SPOT','leverage':1,'reason':'EXISTING_SPOT_POSITION_ROUTING'}

    def _current_exposure_by_symbol(self):
        out={}
        for p in self.positions():
            try:
                price=self.price(p['symbol'])
                if price:
                    out[p['symbol']]=D(p['quantity'])*D(price['last'])
            except Exception:
                continue
        return out

    def _current_for_canonical(self,symbol,current):
        cid_rows=self.db.rows('SELECT canonical_id FROM market_universe WHERE symbol=? LIMIT 1',(symbol,))
        cid=cid_rows[0]['canonical_id'] if cid_rows else symbol
        total=D(0)
        for held,exposure in current.items():
            rows=self.db.rows('SELECT canonical_id FROM market_universe WHERE symbol=? LIMIT 1',(held,))
            held_cid=rows[0]['canonical_id'] if rows else held
            if held_cid==cid: total+=D(exposure)
        return total

    def _execution_symbol(self,route_context,side):
        side_ctx=route_context.get('buy' if side=='BUY' else 'sell') or {}
        return (side_ctx.get('market') or {}).get('symbol')

    def run(self):
        self.consolidate_canonical_positions()
        active=self.db.value('automation_enabled','false').lower()=='true'
        cash,pv,total,missing=self.equity()
        cfg={
            'max_position_pct':D(self.db.value('decision_max_position_pct','5')),
            'cash_reserve_pct':D(self.db.value('decision_cash_reserve_pct','20')),
            'minimum_score':D(self.db.value('decision_minimum_score','70')),
            'min_trade_eur':D(self.db.value('decision_min_trade_eur','20')),
            'volatility_reference_pct':D(self.db.value('decision_volatility_reference_pct','2')),
        }
        families=('crypto_spot','xstocks','forex')
        health=ModelHealth(self.db)
        health_by={f:health.evaluate(f,require_long_horizon=False,max_drawdown_pct=float(self.db.value('decision_max_drawdown_pct','-25'))) for f in families}
        regimes={f:family_regime(self.db,f) for f in families}
        candidates=scanner_candidates(self.db, max_age_minutes=int(float(self.db.value('decision_max_scanner_age_minutes','120'))))

        tickers=ticker_map(self.db, int(float(self.db.value('decision_market_data_max_age_seconds','120'))))
        enriched=[]
        for row in candidates:
            row=dict(row)
            route=routes_for_symbol(
                self.db,row['symbol'],tickers,
                *decision_costs(self.db),
            )
            if route.get('status')!='VALID':
                continue
            row['route_context']=route
            row['roundtrip_cost_pct']=route['roundtrip_cost_pct']
            family=row.get('family') or family_for_category(row.get('category') or 'crypto_spot')
            row['family']=family
            profile=self.db.rows(
                'SELECT parameters_json FROM parameter_family_versions WHERE family=? AND status=\'ACTIVE\' ORDER BY version DESC LIMIT 1',
                (family,),
            )
            params={}
            if profile:
                try: import json; params=json.loads(profile[0]['parameters_json'])
                except Exception: params={}
            row['buy_threshold']=params.get('buy_threshold',cfg['minimum_score'])
            row['avoid_threshold']=params.get('avoid_threshold',35)
            enriched.append(row)

        current=self._current_exposure_by_symbol()
        current_by={row['symbol']:self._current_for_canonical(row['symbol'],current) for row in enriched}
        route_costs={row['symbol']:D(row['roundtrip_cost_pct']) for row in enriched}
        engine=DecisionEngineV95(self.db)
        enriched_symbols={x['symbol'] for x in enriched}
        for held_symbol, exposure in current.items():
            if held_symbol in enriched_symbols: continue
            route=routes_for_symbol(
                self.db,held_symbol,tickers,
                *decision_costs(self.db),
            )
            enriched.append({
                'symbol':held_symbol,'direction':'FLAT','signal':'HOLD','family':'crypto_spot',
                'score':0,'quality':'VALID','volatility_pct':0,'momentum_pct':0,'trend_pct':0,'news_score':0,
                'buy_threshold':cfg['minimum_score'],'avoid_threshold':35,
                'route_context':route,
                'roundtrip_cost_pct':route.get('roundtrip_cost_pct') if route.get('roundtrip_cost_pct') is not None else D(999),
            })
            current_by[held_symbol]=exposure
            route_costs[held_symbol]=D(enriched[-1]['roundtrip_cost_pct'])

        decisions=engine.target_rows(
            enriched,health_by,total,current_by,cfg,regimes,route_costs,allow_short=False
        )

        margin_enabled=self.db.value('paper_leverage_enabled','false').lower()=='true'
        max_leverage=int(float(self.db.value('paper_max_leverage','3')))
        results=[]
        for decision in sorted(decisions,key=lambda x:abs(D(x['rebalance_delta_eur'])),reverse=True):
            delta=D(decision['rebalance_delta_eur'])
            if abs(delta)<D(self.db.value('decision_min_trade_eur','20')):
                continue
            if abs(delta)/max(D(1),total)*100<D(self.db.value('decision_no_trade_band_pct','2')):
                continue
            if not decision['economic_gate_passed']:
                continue

            side='BUY' if delta>0 else 'SELL'
            row=next((x for x in enriched if x['symbol']==decision['symbol']),None)
            if not row:
                # Existing holding. Use its actual paper symbol for an explicit exit.
                row={'symbol':decision['symbol'],'family':'crypto_spot','route_context':routes_for_symbol(
                    self.db,decision['symbol'],tickers,self.db.value('paper_fee_bps','40'),
                    self.db.value('paper_fx_fee_bps','10'),self.db.value('paper_slippage_bps','10')),
                }
            route_ctx=row.get('route_context') or {}
            execution_symbol=self._execution_symbol(route_ctx,side)
            if not execution_symbol:
                results.append({'symbol':decision['symbol'],'action':'HOLD','executed':False,'reason':'NO_VALID_EXECUTION_ROUTE','decision':decision})
                continue

            family=row.get('family','crypto_spot')
            h=health_by.get(family,{})
            is_exit=D(decision.get('target_exposure_eur'))==0 and D(decision.get('current_exposure_eur'))>0
            reducing=abs(D(decision.get('target_exposure_eur')))<abs(D(decision.get('current_exposure_eur'))) and D(decision.get('target_exposure_eur'))*D(decision.get('current_exposure_eur'))>=0
            if reducing:
                ex=self._existing_execution(execution_symbol,margin_enabled,max_leverage)
                conf=execution_confidence(decision.get('score',0),h,None,regime=decision.get('regime','NEUTRAL'),direction='UP' if side=='BUY' else 'DOWN')
                ex={**ex,'confidence':str(conf)}
            else:
                cal=health.margin_calibration(family,'UP' if side=='BUY' else 'DOWN',24,20) if margin_enabled else {'status':'READY','direction':'SPOT'}
                conf=execution_confidence(
                    decision.get('score',0),h,cal if cal.get('status')=='READY' else None,
                    regime=decision.get('regime','NEUTRAL'),direction='UP' if side=='BUY' else 'DOWN',
                )
                ex=choose_execution(conf,margin_enabled,max_leverage,65,78,86,93,97,calibration=cal if cal.get('status')=='READY' else None)
            if ex['mode']=='BLOCKED':
                results.append({'symbol':decision['symbol'],'action':'HOLD','executed':False,'reason':ex['reason'],'decision':decision})
                continue

            # Canonical target exposure is not collateral. When margin is used,
            # only the collateral required to create that notional is sent to
            # PaperEngine.execute(); Real sends the full notional with leverage.
            notional_gap=abs(delta)
            gross_for_paper=notional_gap/D(ex['leverage']) if side=='BUY' and D(ex['leverage'])>1 else notional_gap
            decision=dict(decision,execution_symbol=execution_symbol,execution_mode=ex['mode'],execution_leverage=str(ex['leverage']),execution_confidence=str(conf))
            if active:
                try:
                    if not reducing:
                        allowed,reason=self.stability_gate(decision['symbol'],side,max(D(0),D(decision.get('expected_edge_after_costs_pct') or 0))*notional_gap/100)
                    else:
                        allowed,reason=True,'RISK_REDUCTION'
                    if not allowed:
                        results.append({'symbol':decision['symbol'],'action':'HOLD','executed':False,'reason':reason,'decision':decision})
                        continue
                    decision['leverage']=int(ex['leverage'])
                    tid=self.execute(execution_symbol,side,gross_for_paper,'v95 canonical rebalance',decision)
                    self.mark_turnover(execution_symbol,side)
                    results.append({'symbol':decision['symbol'],'execution_symbol':execution_symbol,'action':side,'executed':True,'trade_id':tid,'decision':decision})
                except Exception as exc:
                    results.append({'symbol':decision['symbol'],'execution_symbol':execution_symbol,'action':side,'executed':False,'reason':str(exc),'decision':decision})
            else:
                results.append({'symbol':decision['symbol'],'execution_symbol':execution_symbol,'action':side,'executed':False,'reason':'AUTOMATION_DISABLED','decision':decision})

        self.snapshot()
        self.db.audit('PAPER_V95_CANONICAL_DECISION',str({
            'decisions':len(decisions),
            'executed':sum(1 for x in results if x.get('executed')),
        }))
        return {'status':'COMPLETED','decisions':decisions,'actions':results,'model_health':health_by,'regimes':regimes}


def configure_v95_engine(engine):
    configure_engine(engine)
