"""v81 real-execution coordinator with repaired live allocation/rebalancing."""
import hashlib,json,secrets
from decimal import Decimal
from automation_v67 import AutomationControllerV67
from controlled_learning import ControlledLearning
from news_learning import NewsLearning
from real_portfolio_allocator import RealPortfolioAllocator
from model_health import ModelHealth
from decision_matrix import DecisionMatrix
from execution_router import choose_route
from strategy_profiles import active_profile,family_for_category
D=lambda x:Decimal(str(x or 0))
REAL_DEFAULTS={'real_trading_enabled':'false','real_kill_switch':'true','real_fee_bps':'40','real_fx_fee_bps':'10','real_slippage_bps':'10','real_max_price_deviation_pct':'1','real_allow_fx_conversion':'true','real_max_order_volume':'0','real_max_order_notional_eur':'0','real_allowed_symbols':'','real_allow_market_orders':'false','real_max_orders_per_day':'2','real_max_fx_orders_per_day':'2','real_balancing_enabled':'false','real_balancing_execute_enabled':'false','real_balancing_dry_run':'true','real_balancing_interval_minutes':'60','real_balancing_max_position_pct':'5','real_balancing_cash_reserve_pct':'20','real_balancing_min_trade_eur':'20','real_balancing_max_trade_eur':'50','real_balancing_no_trade_band_pct':'2','real_balancing_max_actions_per_run':'1','real_balancing_max_actions_per_day':'2','real_balancing_cooldown_hours':'24','real_balancing_minimum_score':'70','real_balancing_limit_offset_pct':'.2','real_balancing_automation_secret':'','real_balancing_automation_secret_hash':''}
def install_real_settings(db,options=None):
 options=options or {}
 for key,default in REAL_DEFAULTS.items():
  if not db.rows('SELECT value FROM settings WHERE key=?',(key,)):db.set_setting(key,options.get(key,default))
 secret=str(db.value('real_balancing_automation_secret','') or '');hashed=str(db.value('real_balancing_automation_secret_hash','') or '')
 if secret and not hashed:
  db.set_setting('real_balancing_automation_secret_hash',hashlib.sha256(secret.encode()).hexdigest());db.audit('REAL_AUTOMATION_SECRET_HASH_INITIALIZED','Configured automation secret hashed','warning','REAL')
class RealPortfolioAllocatorV81(RealPortfolioAllocator):
 def _refresh_before_run(self):
  try:return bool(self._refresh_private_balances())
  except Exception as exc:self.db.audit('REAL_BALANCE_REFRESH_FAILED',type(exc).__name__+': '+str(exc)[:400],'error','REAL');return False
 def _held_symbols(self):
  rows=self.db.rows('SELECT asset,balance FROM private_balances ORDER BY asset');symbols=[]
  for row in rows:
   raw_asset=str(row.get('asset') or '').upper();asset=self._asset(raw_asset);amount=D(row.get('balance'))
   if amount<=0 or asset in ('EUR','USD'):continue
   bases=(raw_asset,asset,'X'+asset,'Z'+asset)
   pairs=self.db.rows("SELECT symbol FROM market_universe WHERE base_asset IN (?,?,?,?) AND quote_asset IN ('EUR','USD')",bases)
   for pair in pairs:
    symbol=str(pair['symbol']).upper()
    if symbol not in symbols:symbols.append(symbol)
  return symbols
 def _all_candidates(self,cfg):
  candidates=self._candidates(cfg);known={str(x['symbol']).upper() for x in candidates}
  for symbol in self._held_symbols():
   if cfg['allowed_symbols'] and symbol not in cfg['allowed_symbols']:continue
   if symbol in known:continue
   row=self.db.rows('SELECT category FROM market_universe WHERE symbol=? LIMIT 1',(symbol,));category=row[0]['category'] if row else 'crypto_spot';family=family_for_category(category)
   try:version,params=active_profile(self.db,family)
   except Exception:version,params=1,{'buy_threshold':cfg['minimum_score']}
   candidates.append({'symbol':symbol,'score':'0','volatility_pct':'0','roundtrip_cost_pct':'0','buy_threshold':params.get('buy_threshold',cfg['minimum_score']),'family':family,'model_version':version,'held_only':True})
  return candidates
 def _deterministic_id(self,run_id,symbol,side):return 'kt81-'+hashlib.sha256(f'v81:{run_id}:{symbol.upper()}:{side.lower()}'.encode()).hexdigest()[:24]
 def _daily_count(self):return int(self.db.rows("SELECT COUNT(*) n FROM real_trade_intents WHERE validate_only=0 AND status='SUBMITTED' AND date(created_at)=date('now')")[0]['n'])
 def _submit_live(self,selected,side,trade_eur,route,run_id,secret,approval_token):
  volume,price=self._volume(selected['symbol'],trade_eur,side,route);cid=self._deterministic_id(run_id,selected['symbol'],side)
  return self.trade_engine.submit(selected['symbol'],side,str(volume),'limit',str(price),cid,approval_token,False,secret)
 def run(self,automatic=False,approval_token=None):
  if automatic:self._refresh_before_run()
  result=super().run(automatic=automatic,approval_token=approval_token)
  if not automatic or not isinstance(result,dict) or result.get('status') in ('DISABLED','BUSY'):return result
  cfg=self.settings()
  if not cfg['enabled'] or cfg['dry_run'] or not cfg['automatic_execution']:return result
  secret=self.db.value('real_balancing_automation_secret','');secret_hash=self.db.value('real_balancing_automation_secret_hash','')
  if not secret_hash:return result
  candidates=self._all_candidates(cfg);active_symbols={str(x['symbol']).upper() for x in candidates if not x.get('held_only') and D(x.get('score'))>=D(cfg['minimum_score'])};held=self._held_symbols()
  reduction=[];room=min(max(0,cfg['max_actions_per_run']-len(result.get('actions') or [])),max(0,cfg['max_actions_per_day']-self._daily_count()))
  if room<=0:return result
  run_id=result.get('run_id') or secrets.token_hex(8);health=ModelHealth(self.db);tickers=self._tickers()
  for symbol in held:
   if room<=0 or symbol in active_symbols:continue
   alts=self._alternatives(symbol);selected,route=choose_route(alts,tickers,cfg['min_trade_eur'],self.db.value('real_fee_bps','40'),self.db.value('real_fx_fee_bps','10'),self.db.value('real_slippage_bps','10'),'sell')
   if not selected or route.get('status')!='VALID':continue
   asset=self._asset(symbol.split('/')[0]);current,total=self._current_eur();present=D(current.get(asset,0))
   if present<cfg['min_trade_eur']:continue
   trade_eur=min(present,cfg['max_trade_eur']);row=self.db.rows('SELECT category FROM market_universe WHERE symbol=? LIMIT 1',(symbol,));family=family_for_category(row[0]['category'] if row else 'crypto_spot');h=health.evaluate(family);raw_edge=D(health.expected_edge_pct(family,24) or 0);cost=D(route['selected']['total_cost_pct'])
   ctx={'canonical_id':symbol,'confirmation_count':1,'confirmation_required':1,'minimum_hold_ok':True,'cooldown_ok':True,'daily_limit_ok':True,'improvement_after_costs':str(max(D(0),raw_edge-cost)*trade_eur/100),'tax_loss_ok':True,'data_fresh':True,'model_health_ok':h.get('status')=='READY','model_health_details':h,'route_cost_ok':True,'route_cost_details':route,'quote_funding_ok':True,'quote_funding_details':{},'portfolio_risk_ok':True,'portfolio_risk_details':{'target_eur':'0','total_eur':str(total)},'order_constraints_ok':True,'order_constraints_details':{},'real_trading_enabled':self.trade_engine.enabled(),'real_kill_switch_clear':self.db.value('real_kill_switch','true').lower()!='true','real_limits_ok':trade_eur<=cfg['max_trade_eur'],'real_balance_ok':True}
   decision=DecisionMatrix(self.db).evaluate(symbol,'SELL',ctx,'REAL');status='BLOCKED';intent=None
   if decision['allowed']:
    try:out=self._submit_live(selected,'sell',trade_eur,route,run_id,secret,approval_token);status=out.get('status','FAILED');intent=out.get('client_order_id')
    except Exception as exc:status='FAILED';self.db.audit('REAL_REBALANCE_SELL_FAILED',json.dumps({'symbol':symbol,'error':type(exc).__name__}),'error','REAL')
   reduction.append({'symbol':symbol,'side':'sell','trade_eur':str(trade_eur),'status':status,'route':selected['symbol'],'order_intent_id':intent});room-=1
  if reduction:
   result=dict(result);result['actions']=list(result.get('actions') or [])+reduction;result['reduction_actions']=reduction
  return result
def replace_controller(base,allocator):
 old=getattr(base,'controller',None)
 if old is not None:
  try:old.stop()
  except Exception:pass
 controller=AutomationControllerV67(base.db,base.legacy.pipeline,base.legacy.news_prefilter,ControlledLearning(base.db),NewsLearning(base.db),base.legacy.run_paper_cycle,allocator);controller.start_background();base.controller=controller;base.legacy.controller=controller;return controller
