"""v91 real-margin coordinator: gated leveraged long/short execution and risk exits."""
import json,secrets
from decimal import Decimal
from decision_matrix import DecisionMatrix
from model_health import ModelHealth
from real_autonomous_v81 import RealPortfolioAllocatorV81
from execution_confidence import execution_confidence,short_execution
from market_regime import family_regime

D=lambda x:Decimal(str(x or 0))

class RealPortfolioAllocatorV91(RealPortfolioAllocatorV81):
 def _margin_positions(self):
  try:return self.db.rows("SELECT * FROM real_margin_positions ORDER BY id")
  except Exception:return []

 def _scanner_short_candidates(self,cfg):
  rows=self.db.rows("SELECT s.symbol,s.score,s.momentum_pct,s.trend_pct,s.spread_pct FROM scanner_results s JOIN market_universe u ON u.symbol=s.symbol WHERE s.quality='VALID' AND s.signal='AVOID' AND CAST(COALESCE(s.momentum_pct,0) AS REAL)<0 AND CAST(COALESCE(s.trend_pct,0) AS REAL)<0 AND u.leverage_sell_json NOT IN ('','[]') ORDER BY CAST(s.score AS REAL) ASC")
  out=[]
  for row in rows:
   symbol=str(row['symbol']).upper()
   if cfg['allowed_symbols'] and symbol not in cfg['allowed_symbols']:continue
   alts=self._alternatives(symbol)
   selected,route=__import__('execution_router').choose_route(alts,self._tickers(),cfg['min_trade_eur'],self.db.value('real_fee_bps',self.db.value('paper_fee_bps','40')),self.db.value('real_fx_fee_bps','10'),self.db.value('real_slippage_bps','10'),'sell')
   if selected and route.get('status')=='VALID':out.append({'symbol':symbol,'score':row['score'],'family':self._family(symbol),'selected':selected,'route':route})
  return out

 def _family(self,symbol):
  row=self.db.rows('SELECT category FROM market_universe WHERE symbol=? LIMIT 1',(symbol,))
  from strategy_profiles import family_for_category
  return family_for_category(row[0]['category'] if row else 'crypto_spot')

 def _decision(self,symbol,side,calibration,route,cfg,reduce_only=False):
  return DecisionMatrix(self.db).evaluate(symbol,side,{'canonical_id':symbol,'confirmation_count':1,'confirmation_required':1,'minimum_hold_ok':True,'cooldown_ok':True,'daily_limit_ok':True,'improvement_after_costs':'1','tax_loss_ok':True,'data_fresh':True,'exit_risk_override':bool(reduce_only),'model_health_ok':calibration.get('status')=='READY','model_health_details':calibration,'route_cost_ok':route.get('status')=='VALID','route_cost_details':route,'quote_funding_ok':True,'quote_funding_details':{},'portfolio_risk_ok':True,'portfolio_risk_details':{},'order_constraints_ok':True,'order_constraints_details':{},'real_trading_enabled':self.trade_engine.enabled(),'real_kill_switch_clear':self.db.value('real_kill_switch','true').lower()!='true','real_limits_ok':True,'real_balance_ok':True},'REAL')

 def _risk_exit_margin_positions(self,cfg,result):
  if not cfg['margin_enabled']:return result
  try:self.trade_engine.refresh_margin_state()
  except Exception:return result
  health=ModelHealth(self.db);actions=list(result.get('actions') or []);capacity=max(0,cfg['max_actions_per_run']-sum(1 for x in actions if str(x.get('status','')).upper()=='SUBMITTED'))
  if capacity<=0:return result
  for pos in self._margin_positions():
   if capacity<=0:break
   symbol=str(pos['symbol']).upper();scan=self.db.rows('SELECT signal,momentum_pct,trend_pct,quality FROM scanner_results WHERE symbol=? LIMIT 1',(symbol,))
   if not scan:continue
   current_side=str(pos['side']).lower();should_close=(current_side=='buy' and scan[0]['signal']!='BUY') or (current_side=='sell' and not (scan[0]['signal']=='AVOID' and D(scan[0].get('momentum_pct'))<0 and D(scan[0].get('trend_pct'))<0))
   if not should_close:continue
   side='sell' if current_side=='buy' else 'buy';alts=self._alternatives(symbol);selected,route=__import__('execution_router').choose_route(alts,self._tickers(),cfg['min_trade_eur'],self.db.value('real_fee_bps','40'),self.db.value('real_fx_fee_bps','10'),self.db.value('real_slippage_bps','10'),side)
   if not selected or route.get('status')!='VALID':continue
   vol=D(pos['volume']);price=D(self._tickers().get(symbol,{}).get('b',[0])[0] if side=='sell' else self._tickers().get(symbol,{}).get('a',[0])[0])
   if price<=0:continue
   lev=D(pos.get('leverage') or cfg['margin_default_leverage']);cal={'status':'READY','direction':'EXIT','reason':'Existing margin position follows dedicated reduce-only risk exit'}
   decision=self._decision(symbol,side,cal,route,cfg,True)
   if not decision['allowed']:continue
   try:out=self.trade_engine.submit(symbol,side,str(vol),'limit',str(price),secrets.token_hex(16),None,False,self.db.value('real_balancing_automation_secret',''),leverage=lev,margin=True,reduce_only=True);status=out.get('status','FAILED');intent=out.get('client_order_id')
   except Exception as exc:status='FAILED';intent=None
   actions.append({'symbol':symbol,'side':side,'trade_eur':str(min(cfg['max_trade_eur'],vol*price)),'status':status,'margin':True,'leverage':str(lev),'reduce_only':True,'reason':'MARGIN_RISK_EXIT','order_intent_id':intent});capacity-=status=='SUBMITTED'
  result=dict(result);result['actions']=actions;result['margin_risk_exits']=[x for x in actions if x.get('reason')=='MARGIN_RISK_EXIT'];return result

 def run(self,automatic=False,approval_token=None):
  result=super().run(automatic=automatic,approval_token=approval_token)
  if not automatic or not isinstance(result,dict):return result
  cfg=self.settings()
  result=self._risk_exit_margin_positions(cfg,result)
  if not cfg['margin_enabled'] or not cfg['margin_allow_shorts'] or cfg['dry_run'] or not cfg['automatic_execution']:return result
  if sum(1 for x in result.get('actions',[]) if str(x.get('status','')).upper()=='SUBMITTED')>=cfg['max_actions_per_run']:return result
  candidates=self._scanner_short_candidates(cfg)
  if not candidates:return result
  health=ModelHealth(self.db);total=self._current_eur()[1];selected_candidate=candidates[0];symbol=selected_candidate['symbol'];family=selected_candidate['family'];cal=health.margin_calibration(family,'DOWN',24,20,cfg['max_drawdown_pct']);family_health=health.evaluate(family,require_long_horizon=False,max_drawdown_pct=cfg['max_drawdown_pct']);regime=family_regime(self.db,family).get('regime','NEUTRAL');directional_score=max(D(0),D(100)-D(selected_candidate.get('score',0)));confidence=execution_confidence(directional_score,family_health,cal,regime=regime,direction='DOWN');execution=short_execution(confidence,cal,cfg['margin_max_leverage'],cfg['confidence_short_min'],cfg['confidence_margin_2x'],cfg['confidence_margin_3x'],cfg['confidence_margin_4x'],cfg['confidence_margin_5x'])
  if execution['mode']!='MARGIN':
   result=dict(result);result['margin_short']={'symbol':symbol,'status':'BLOCKED','execution_confidence':str(confidence),'reason':execution['reason'],'calibration':cal,'regime':regime};return result
  trade_eur=min(cfg['max_trade_eur'],max(cfg['min_trade_eur'],total*cfg['max_position_pct']/100))
  selected=selected_candidate['selected'];route=selected_candidate['route'];price=D(self._tickers()[selected['symbol']]['b'][0]);volume=trade_eur/price if price>0 else D(0)
  if volume<=0:return result
  decision=self._decision(symbol,'SELL',cal,route,cfg,False)
  if not decision['allowed']:return result
  try:out=self.trade_engine.submit(selected['symbol'],'sell',str(volume),'limit',str(price),secrets.token_hex(16),approval_token,False,self.db.value('real_balancing_automation_secret',''),leverage=execution['leverage'],margin=True,reduce_only=False);status=out.get('status','FAILED');intent=out.get('client_order_id')
  except Exception as exc:status='FAILED';intent=None
  result=dict(result);result['actions']=list(result.get('actions') or [])+[{'symbol':symbol,'side':'sell','trade_eur':str(trade_eur),'status':status,'margin':True,'leverage':str(execution['leverage']),'reduce_only':False,'reason':'MARGIN_SHORT_OPEN','execution_confidence':str(confidence),'execution_reason':execution['reason'],'blockers':[],'calibration':cal,'regime':regime,'directional_score':str(directional_score),'order_intent_id':intent}];result['margin_short']=result['actions'][-1]
  return result
