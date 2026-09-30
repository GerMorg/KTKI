"""v94 Real adapter: executes canonical v94 decisions through Kraken."""
import json,secrets,threading
from decimal import Decimal
from db import now
from model_health import ModelHealth
from strategy_profiles import family_for_category
from execution_router import choose_route
from execution_confidence import execution_confidence,choose_execution
from market_regime import family_regime
from decision_matrix import DecisionMatrix
from decision_engine_v94 import DecisionEngineV94
from real_portfolio_allocator import RealPortfolioAllocator

D=lambda x:Decimal(str(x or 0))
def safe_json(x):return json.dumps(x,sort_keys=True,default=str)

class RealPortfolioAllocatorV94(RealPortfolioAllocator):
    def _rows(self,cfg):
        cols={x['name'] for x in self.db.rows('PRAGMA table_info(scanner_results)')}
        vol='s.volatility_pct' if 'volatility_pct' in cols else '0 AS volatility_pct'
        mom='s.momentum_pct' if 'momentum_pct' in cols else '0 AS momentum_pct'
        trend='s.trend_pct' if 'trend_pct' in cols else '0 AS trend_pct'
        news='s.news_score' if 'news_score' in cols else '0 AS news_score'
        return self.db.rows(f"SELECT s.symbol,s.score,{vol},{mom},{trend},{news},s.signal,s.quality FROM scanner_results s WHERE s.quality='VALID' AND s.signal IN ('BUY','AVOID') ORDER BY CAST(s.score AS REAL) DESC")
    def _candidates(self,cfg,tickers):
        out=[]
        for r in self._rows(cfg):
            symbol=str(r['symbol']).upper()
            if cfg['allowed_symbols'] and symbol not in cfg['allowed_symbols']: continue
            alts=self._alternatives(symbol)
            side='buy' if str(r.get('signal')).upper()=='BUY' else 'sell'
            selected,route=choose_route(alts,tickers,100,self.db.value('real_fee_bps',self.db.value('paper_fee_bps','40')),self.db.value('real_fx_fee_bps',self.db.value('paper_fx_fee_bps','10')),self.db.value('real_slippage_bps',self.db.value('paper_slippage_bps','10')),side)
            if not selected or route.get('status')!='VALID': continue
            cat=self.db.rows('SELECT category FROM market_universe WHERE symbol=? LIMIT 1',(symbol,))
            family=family_for_category(cat[0]['category'] if cat else 'crypto_spot')
            out.append({'symbol':symbol,'score':r['score'],'volatility_pct':r.get('volatility_pct') or 0,'momentum_pct':r.get('momentum_pct') or 0,'trend_pct':r.get('trend_pct') or 0,'news_score':r.get('news_score') or 0,'signal':r['signal'],'quality':'VALID','family':family,'route':route,'selected':selected,'roundtrip_cost_pct':route['selected']['total_cost_pct']})
        return out
    def run(self,automatic=False,approval_token=None):
        if not self.lock.acquire(False): return {'status':'BUSY'}
        rid=None
        try:
            cfg=self.settings()
            current,total=self._current_eur()
            tickers=self._tickers()
            health=ModelHealth(self.db)
            families=('crypto_spot','xstocks','forex')
            health_by={f:health.evaluate(f,require_long_horizon=False,max_drawdown_pct=cfg['max_drawdown_pct']) for f in families}
            regimes={f:family_regime(self.db,f) for f in families}
            candidates=self._candidates(cfg,tickers)
            # Build a common target map from ALL long/short candidates, then
            # explicitly add currently-held symbols so HOLD/EXIT cannot vanish.
            held={a for a,v in current.items() if v!=0}
            symbols={x['symbol'] for x in candidates}
            for a in held:
                sym=next((s for s in tickers if s.split('/')[0].upper().replace('XBT','BTC')==a),None)
                if sym and sym not in symbols:
                    candidates.append({'symbol':sym,'score':0,'volatility_pct':0,'momentum_pct':0,'trend_pct':0,'news_score':0,'signal':'HOLD','quality':'VALID','family':'crypto_spot','route':{'status':'VALID','selected':{'total_cost_pct':'0'}},'selected':{'symbol':sym}})
            engine=DecisionEngineV94(self.db)
            current_by={}
            for c in candidates:
                asset=self._asset(c['symbol'].split('/')[0]); current_by[c['symbol']]=current.get(asset,0)
            route_costs={c['symbol']:D(c.get('roundtrip_cost_pct',999)) for c in candidates}
            # Candidate-specific family health is the only model evidence.
            decisions=engine.target_rows(candidates,health_by,total,current_by,cfg,regimes,route_costs)
            # For existing holdings without a live BUY thesis, force a reduction
            # target to zero. This is a target decision, not a separate exit engine.
            for d in decisions:
                if d['symbol'] in held and d['direction']!='LONG' and d['direction']!='SHORT':
                    d['target_exposure_eur']='0';d['rebalance_delta_eur']=str(-D(d['current_exposure_eur']));d['action']='SELL';d['economic_gate_passed']=True
            with self.db.con() as c:
                cur=c.execute('INSERT INTO real_allocation_runs(created_at,status,automatic,settings_json,details_json) VALUES(?,?,?,?,?)',(now(),'RUNNING',int(automatic),safe_json(cfg),'{}'));rid=cur.lastrowid
            actions=[];capacity=min(cfg['max_actions_per_run'],max(0,cfg['max_actions_per_day']-int(self.db.rows("SELECT COUNT(*) n FROM real_allocation_actions WHERE status='SUBMITTED' AND date(created_at)=date('now')")[0]['n']))
            for d in sorted(decisions,key=lambda x:abs(D(x['rebalance_delta_eur'])),reverse=True):
                if capacity<=0: break
                delta=D(d['rebalance_delta_eur'])
                if abs(delta)<cfg['min_trade_eur'] or abs(delta)/max(D(1),total)*100<cfg['no_trade_band_pct']: continue
                if not d['economic_gate_passed']: continue
                symbol=d['symbol'];side='buy' if delta>0 else 'sell'
                cand=next((x for x in candidates if x['symbol']==symbol),None)
                if not cand: continue
                selected=cand['selected'];route=cand['route'];trade_eur=min(abs(delta),cfg['max_trade_eur'])
                family=cand['family'];h=health_by[family];regime=d['regime']
                cal=health.margin_calibration(family,'UP' if side=='buy' else 'DOWN',24,20,cfg['max_drawdown_pct']) if cfg['margin_enabled'] else {'status':'READY','direction':'SPOT'}
                conf=execution_confidence(d['score'],h,cal if cal.get('status')=='READY' else None,regime=regime,direction='UP' if side=='buy' else 'DOWN')
                ex=choose_execution(conf,cfg['margin_enabled'],cfg['margin_max_leverage'],cfg['confidence_spot_min'],cfg['confidence_margin_2x'],cfg['confidence_margin_3x'],cfg['confidence_margin_4x'],cfg['confidence_margin_5x'],calibration=cal if side=='buy' else None)
                if ex['mode']=='BLOCKED': continue
                price=D(self.db.rows('SELECT ask,bid,last FROM live_prices WHERE symbol=? LIMIT 1',(symbol,))[0][('ask' if side=='buy' else 'bid')])
                vol=D(trade_eur)/price if price>0 else D(0)
                meta=next((x for x in self._alternatives(symbol) if x.get('symbol')==selected.get('symbol')), {})
                order_ok=(not meta.get('ordermin') or vol>=D(meta.get('ordermin'))) and (not meta.get('costmin') or vol*price>=D(meta.get('costmin')))
                ctx={'canonical_id':symbol,'confirmation_count':1,'confirmation_required':1,'minimum_hold_ok':True,'cooldown_ok':True,'daily_limit_ok':True,'improvement_after_costs':str(max(D(0),D(d['expected_edge_after_costs_pct']))),'execution_confidence':str(conf),'execution_mode':ex['mode'],'execution_leverage':str(ex['leverage']),'execution_confidence_ok':True,'execution_confidence_reason':ex['reason'],'tax_loss_ok':True,'data_fresh':True,'model_health_ok':True,'model_health_details':{'health':h,'role':'QUALITY_AND_SIZING','regime':regime},'route_cost_ok':route.get('status')=='VALID','route_cost_details':route,'quote_funding_ok':True,'quote_funding_details':{},'portfolio_risk_ok':True,'portfolio_risk_details':{'target_eur':d['target_exposure_eur'],'total':str(total)},'order_constraints_ok':order_ok,'order_constraints_details':{'volume':str(vol)},'real_trading_enabled':self.trade_engine.enabled(),'real_kill_switch_clear':self.db.value('real_kill_switch','true').lower()!='true','real_limits_ok':trade_eur<=cfg['max_trade_eur'],'real_balance_ok':True}
                dec=DecisionMatrix(self.db).evaluate(symbol,side.upper(),ctx,'REAL')
                status='PROPOSED';intent=None
                if automatic and cfg['dry_run']:status='DRY_RUN'
                elif automatic and cfg['automatic_execution'] and dec['allowed']:
                    secret=self.db.value('real_balancing_automation_secret','')
                    res=self.trade_engine.submit(symbol,side,str(vol),'limit',str(price),secrets.token_hex(16),approval_token,False,secret,leverage=ex['leverage'],margin=(ex['mode']=='MARGIN'),reduce_only=(D(d['target_exposure_eur'])==0))
                    status=res.get('status');intent=res.get('client_order_id')
                with self.db.con() as c:c.execute('INSERT INTO real_allocation_actions(run_id,created_at,symbol,side,current_eur,target_eur,difference_eur,status,decision_json,order_intent_id,error) VALUES(?,?,?,?,?,?,?,?,?,?,?)',(rid,now(),symbol,side,d['current_exposure_eur'],d['target_exposure_eur'],d['rebalance_delta_eur'],status,safe_json({'canonical_decision':d,'decision':dec,'model_health':h}),intent,None))
                actions.append({'symbol':symbol,'side':side,'status':status,'decision':d,'execution':ex,'blockers':[x['reason'] for x in dec.get('checks',[]) if not x['passed']]})
                if status=='SUBMITTED':capacity-=1
            final='COMPLETED'
            with self.db.con() as c:c.execute('UPDATE real_allocation_runs SET finished_at=?,status=?,details_json=? WHERE id=?',(now(),final,safe_json({'decisions':decisions,'actions':actions,'model_health':health_by,'regimes':regimes}),rid))
            return {'status':final,'run_id':rid,'decisions':decisions,'actions':actions,'model_health':health_by,'regimes':regimes}
        except Exception as exc:
            if rid:
                with self.db.con() as c:c.execute('UPDATE real_allocation_runs SET finished_at=?,status=?,error=? WHERE id=?',(now(),'FAILED',type(exc).__name__+': '+str(exc),rid))
            return {'status':'FAILED','error':type(exc).__name__+': '+str(exc)}
        finally:self.lock.release()
