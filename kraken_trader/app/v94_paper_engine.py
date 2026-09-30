"""v94 Paper adapter.

It consumes the exact same DecisionEngineV94 output as Real.  Fills are simulated
only after the decision has been made; no paper-specific signal/target logic is
allowed here.
"""
from decimal import Decimal
from paper_engine import PaperEngine
from model_health import ModelHealth
from strategy_profiles import family_for_category
from market_regime import family_regime
from execution_router import choose_route
from decision_engine_v94 import DecisionEngineV94
from execution_confidence import execution_confidence,choose_execution

D=lambda x:Decimal(str(x or 0))

class PaperEngineV94(PaperEngine):
    def run(self):
        self.consolidate_canonical_positions()
        active=self.db.value('automation_enabled','false')=='true'
        cash,pv,total,missing=self.equity()
        cfg={'max_position_pct':D(self.db.value('paper_max_position_pct','10')),
             'cash_reserve_pct':D(self.db.value('paper_cash_reserve_pct','20')),
             'minimum_score':D(self.db.value('paper_buy_score_threshold','62')),
             'min_trade_eur':D(self.db.value('paper_min_transfer_eur','20'))}
        health=ModelHealth(self.db);families=('crypto_spot','xstocks','forex')
        hb={f:health.evaluate(f,require_long_horizon=False) for f in families}
        rb={f:family_regime(self.db,f) for f in families}
        cols={x['name'] for x in self.db.rows('PRAGMA table_info(scanner_results)')}
        news_expr='s.news_score' if 'news_score' in cols else '0 AS news_score'
        rows=self.db.rows(f"SELECT s.symbol,s.score,s.volatility_pct,s.momentum_pct,s.trend_pct,s.signal,s.quality,{news_expr} FROM scanner_results s WHERE s.quality='VALID' AND s.signal IN ('BUY','AVOID')")
        candidates=[];tickers={x['symbol']:{'b':[x['bid'] or x['last']],'a':[x['ask'] or x['last']],'c':[x['last']]} for x in self.db.rows('SELECT symbol,last,bid,ask FROM live_prices')}
        for r in rows:
            symbol=r['symbol'];cat=self.db.rows('SELECT category FROM market_universe WHERE symbol=? LIMIT 1',(symbol,));family=family_for_category(cat[0]['category'] if cat else 'crypto_spot')
            side='buy' if r['signal']=='BUY' else 'sell'
            alts=self.db.rows("SELECT symbol,asset_class,category,base_asset,quote_asset,source_key,ordermin,costmin FROM market_universe WHERE canonical_id=(SELECT canonical_id FROM market_universe WHERE symbol=? LIMIT 1) AND quote_asset IN ('EUR','USD')",(symbol,))
            selected,route=choose_route(alts,tickers,100,self.db.value('paper_fee_bps','40'),self.db.value('paper_fx_fee_bps','10'),self.db.value('paper_slippage_bps','10'),side)
            if selected and route.get('status')=='VALID':
                candidates.append({'symbol':symbol,'score':r['score'],'volatility_pct':r['volatility_pct'] or 0,'momentum_pct':r['momentum_pct'] or 0,'trend_pct':r['trend_pct'] or 0,'news_score':r['news_score'] or 0,'signal':r['signal'],'family':family,'buy_threshold':cfg['minimum_score'],'roundtrip_cost_pct':route['selected']['total_cost_pct'],'selected':selected,'route':route})
        current={}
        for p in self.positions():
            current[p['symbol']]=D(p['quantity'])*D(self.price(p['symbol'])['last'])
        engine=DecisionEngineV94(self.db)
        current_by={c['symbol']:current.get(c['symbol'],D(0)) for c in candidates}
        decisions=engine.target_rows(candidates,hb,total,current_by,cfg,rb,{c['symbol']:D(c['roundtrip_cost_pct']) for c in candidates})
        # Paper v94 currently models spot/margin long fills; it does not invent
        # a short position. An existing long can still be reduced to zero.
        for d in decisions:
            if d['direction']=='SHORT' and D(d['current_exposure_eur'])==0:
                d['target_exposure_eur']='0';d['rebalance_delta_eur']='0';d['action']='HOLD';d['economic_gate_passed']=False
        # Held positions with no current thesis are explicit zero targets.
        for p in self.positions():
            if p['symbol'] not in current_by:
                decisions.append({'symbol':p['symbol'],'direction':'FLAT','action':'SELL','current_exposure_eur':str(current.get(p['symbol'],0)),'target_exposure_eur':'0','rebalance_delta_eur':str(-current.get(p['symbol'],0)),'economic_gate_passed':True,'expected_edge_after_costs_pct':'0','score':'0','quality_score':'0','regime':'NEUTRAL'})
        results=[]
        margin_enabled=self.db.value('paper_leverage_enabled','false')=='true'
        max_leverage=int(float(self.db.value('paper_max_leverage','3')))
        for d in sorted(decisions,key=lambda x:abs(D(x['rebalance_delta_eur'])),reverse=True):
            delta=D(d['rebalance_delta_eur'])
            if abs(delta)<cfg['min_trade_eur']:continue
            if not d['economic_gate_passed']:continue
            side='BUY' if delta>0 else 'SELL'
            family=next((x['family'] for x in candidates if x['symbol']==d['symbol']),'crypto_spot')
            h=hb.get(family,{})
            cal=health.margin_calibration(family,'UP' if side=='BUY' else 'DOWN',24,20) if margin_enabled else {'status':'READY','direction':'SPOT'}
            conf=execution_confidence(d.get('score',0),h,cal if cal.get('status')=='READY' else None,regime=d.get('regime','NEUTRAL'),direction='UP' if side=='BUY' else 'DOWN')
            ex=choose_execution(conf,margin_enabled,max_leverage,65,78,86,93,97,calibration=cal if cal.get('status')=='READY' else None)
            if ex['mode']=='BLOCKED':
                results.append({'symbol':d['symbol'],'action':'HOLD','executed':False,'reason':ex['reason'],'decision':d});continue
            d['execution_confidence']=str(conf);d['execution_mode']=ex['mode'];d['execution_leverage']=str(ex['leverage'])
            if active:
                allowed,reason=self.stability_gate(d['symbol'],side,max(D(0),D(d['expected_edge_after_costs_pct']))*abs(delta)/100)
                if not allowed:
                    results.append({'symbol':d['symbol'],'action':'HOLD','executed':False,'reason':reason,'decision':d});continue
                try:
                    d['leverage']=int(ex['leverage'])
                    tid=self.execute(d['symbol'],side,abs(delta), 'v94 canonical rebalance',d)
                    self.mark_turnover(d['symbol'],side);results.append({'symbol':d['symbol'],'action':side,'executed':True,'trade_id':tid,'decision':d})
                except Exception as exc:
                    results.append({'symbol':d['symbol'],'action':side,'executed':False,'reason':str(exc),'decision':d})
            else:
                results.append({'symbol':d['symbol'],'action':side,'executed':False,'reason':'AUTOMATION_DISABLED','decision':d})
        self.snapshot()
        self.db.audit('PAPER_V94_CANONICAL_DECISION',str({'decisions':len(decisions),'executed':sum(x.get('executed',False) for x in results)}))
        return {'status':'COMPLETED','decisions':decisions,'actions':results,'model_health':hb,'regimes':rb}
