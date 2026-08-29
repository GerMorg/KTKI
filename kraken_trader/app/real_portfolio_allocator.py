import json,secrets,threading
from decimal import Decimal,InvalidOperation
from db import now
from decision_matrix import DecisionMatrix
from execution_router import choose_route
from model_health import ModelHealth
from portfolio_target import build_targets
from strategy_profiles import active_profile,family_for_category
D=lambda x:Decimal(str(x or 0))
def _bool(db,key,default='false'):return db.value(key,default).lower()=='true'
def safe_json(value):return json.dumps(value,sort_keys=True,default=str)
class RealPortfolioAllocator:
 def __init__(self,db,trade_engine):self.db=db;self.trade_engine=trade_engine;self.lock=threading.Lock();self.ensure()
 def ensure(self):
  with self.db.con() as c:c.executescript("CREATE TABLE IF NOT EXISTS real_allocation_runs(id INTEGER PRIMARY KEY AUTOINCREMENT,created_at TEXT NOT NULL,finished_at TEXT,status TEXT NOT NULL,automatic INTEGER NOT NULL,settings_json TEXT NOT NULL,details_json TEXT NOT NULL,error TEXT);CREATE TABLE IF NOT EXISTS real_allocation_actions(id INTEGER PRIMARY KEY AUTOINCREMENT,run_id INTEGER NOT NULL,created_at TEXT NOT NULL,symbol TEXT NOT NULL,side TEXT NOT NULL,current_eur TEXT NOT NULL,target_eur TEXT NOT NULL,difference_eur TEXT NOT NULL,status TEXT NOT NULL,decision_json TEXT NOT NULL,order_intent_id TEXT,error TEXT);CREATE TABLE IF NOT EXISTS real_balance_snapshots(id INTEGER PRIMARY KEY AUTOINCREMENT,created_at TEXT NOT NULL,asset TEXT NOT NULL,amount TEXT NOT NULL,source TEXT NOT NULL);")
 def settings(self):
  def num(k,d,lo=None,hi=None):
   try:v=D(self.db.value(k,str(d)))
   except (InvalidOperation,ValueError):v=D(d)
   if lo is not None:v=max(D(lo),v)
   if hi is not None:v=min(D(hi),v)
   return v
  return {'enabled':_bool(self.db,'real_balancing_enabled'),'automatic_execution':_bool(self.db,'real_balancing_execute_enabled'),'interval_minutes':int(num('real_balancing_interval_minutes',60,5,1440)),'max_position_pct':num('real_balancing_max_position_pct',5,.1,100),'cash_reserve_pct':num('real_balancing_cash_reserve_pct',20,0,100),'min_trade_eur':num('real_balancing_min_trade_eur',20,0),'max_trade_eur':num('real_balancing_max_trade_eur',50,.01),'no_trade_band_pct':num('real_balancing_no_trade_band_pct',2,0,100),'max_actions_per_run':int(num('real_balancing_max_actions_per_run',1,1,100)),'max_actions_per_day':int(num('real_balancing_max_actions_per_day',2,1,100)),'cooldown_hours':num('real_balancing_cooldown_hours',24,0,720),'minimum_score':num('real_balancing_minimum_score',70,0,100),'allowed_symbols':[x.strip().upper() for x in self.db.value('real_allowed_symbols','').split(',') if x.strip()],'dry_run':_bool(self.db,'real_balancing_dry_run','true'),'limit_offset_pct':num('real_balancing_limit_offset_pct',.2,0,10)}
 def balances(self):return self.db.rows('SELECT asset,balance FROM private_balances ORDER BY asset')
 @staticmethod
 def _asset(code):return str(code or '').upper().replace('XBT','BTC').replace('Z','').replace('X','')
 def _tickers(self):return {x['symbol']:{'b':[x['bid'] or x['last']],'a':[x['ask'] or x['last']],'c':[x['last']]} for x in self.db.rows('SELECT symbol,last,bid,ask FROM live_prices')}
 def _current_eur(self):
  tickers=self._tickers();fx=tickers.get('EUR/USD');fx_mid=D((fx or {}).get('c',[0])[0]);out={};total=D(0)
  for b in self.balances():
   asset=self._asset(b['asset']);amount=D(b['balance']);value=D(0)
   if asset=='EUR':value=amount
   elif asset=='USD' and fx_mid>0:value=amount/fx_mid
   else:
    direct=tickers.get(asset+'/EUR');usd=tickers.get(asset+'/USD')
    if direct:value=amount*D(direct['c'][0])
    elif usd and fx_mid>0:value=amount*D(usd['c'][0])/fx_mid
   out[asset]=value;total+=value
   with self.db.con() as c:c.execute('INSERT INTO real_balance_snapshots(created_at,asset,amount,source) VALUES(?,?,?,?)',(now(),asset,str(amount),'PRIVATE_BALANCE'))
  return out,total
 def _refresh_private_balances(self):
  if not hasattr(self.trade_engine,'client') or not hasattr(self.trade_engine.client,'balance'):return False
  data=self.trade_engine.client.balance() or {}
  if not isinstance(data,dict):return False
  with self.db.con() as c:
   for asset,balance in data.items():c.execute('INSERT OR REPLACE INTO private_balances(asset,balance,wallets_json,sequence,received_at) VALUES(?,?,?,?,?)',(asset,str(balance),'[]',None,now()))
  return True
 def _alternatives(self,symbol):
  try:rows=self.db.rows('SELECT canonical_id FROM market_universe WHERE symbol=? LIMIT 1',(symbol,))
  except Exception:rows=[]
  cid=rows[0]['canonical_id'] if rows else symbol
  try:alts=self.db.rows("SELECT symbol,asset_class,category,base_asset,quote_asset,source_key,ordermin,costmin FROM market_universe WHERE canonical_id=? AND quote_asset IN ('EUR','USD')",(cid,))
  except Exception:alts=[]
  if alts:return [dict(x) for x in alts]
  base,quote=(symbol.split('/',1)+['EUR'])[:2] if '/' in symbol else (symbol,'EUR')
  return [{'symbol':symbol,'asset_class':'crypto','category':'crypto_spot','base_asset':base,'quote_asset':quote,'source_key':symbol,'ordermin':'0','costmin':'0'}]
 def _candidates(self,cfg):
  tickers=self._tickers();out=[]
  try:cols={x['name'] for x in self.db.rows('PRAGMA table_info(scanner_results)')}
  except Exception:cols=set()
  vol_expr='s.volatility_pct' if 'volatility_pct' in cols else '0 AS volatility_pct'
  rows=self.db.rows(f"SELECT s.symbol,s.score,{vol_expr},s.signal,s.quality FROM scanner_results s WHERE s.quality='VALID' AND s.signal='BUY' AND CAST(s.score AS REAL)>=? ORDER BY CAST(s.score AS REAL) DESC",(str(cfg['minimum_score']),))
  for row in rows:
   if cfg['allowed_symbols'] and row['symbol'].upper() not in cfg['allowed_symbols']:continue
   alts=self._alternatives(row['symbol'])
   try:catrows=self.db.rows('SELECT category FROM market_universe WHERE symbol=? LIMIT 1',(row['symbol'],))
   except Exception:catrows=[]
   category=catrows[0]['category'] if catrows else 'crypto_spot';family=family_for_category(category)
   try:version,params=active_profile(self.db,family)
   except Exception:version,params=1,{'buy_threshold':cfg['minimum_score']}
   selected,route=choose_route(alts,tickers,100,self.db.value('real_fee_bps',self.db.value('paper_fee_bps','40')),self.db.value('real_fx_fee_bps',self.db.value('paper_fx_fee_bps','10')),self.db.value('real_slippage_bps',self.db.value('paper_slippage_bps','10')),'buy')
   if not selected:continue
   out.append({'symbol':row['symbol'],'score':row['score'],'volatility_pct':row['volatility_pct'] or 0,'roundtrip_cost_pct':str(route['selected']['total_cost_pct'] if route.get('selected') else 999),'buy_threshold':params.get('buy_threshold',cfg['minimum_score']),'family':family,'model_version':version})
  return out
 def _volume(self,symbol,trade_eur,side,route):
  rows=self.db.rows('SELECT ask,bid,last FROM live_prices WHERE symbol=? LIMIT 1',(symbol,));r=rows[0] if rows else {};price=D(r['ask' if side=='buy' else 'bid'] or r['last'])
  if price<=0:raise ValueError('Kein Ausführungspreis')
  quote=str(route.get('selected',{}).get('quote_currency') or 'EUR')
  if quote=='USD':
   fx=self.db.rows("SELECT bid,ask,last FROM live_prices WHERE symbol='EUR/USD' LIMIT 1");rate=D((fx[0]['bid' if side=='buy' else 'ask'] or fx[0]['last']) if fx else 0)
   if rate<=0:raise ValueError('EUR/USD fehlt')
   return D(trade_eur)*rate/price,price
  return D(trade_eur)/price,price
 def run(self,automatic=False,approval_token=None):
  if not self.lock.acquire(False):return {'status':'BUSY'}
  cfg=self.settings();rid=None
  try:
   if automatic and not cfg['enabled']:return {'status':'DISABLED'}
   current,total=self._current_eur();payload={k:(str(v) if isinstance(v,Decimal) else v) for k,v in cfg.items()};tickers=self._tickers();health=ModelHealth(self.db);health_by_family={family:health.evaluate(family) for family in ('crypto_spot','xstocks','forex')};candidates=self._candidates(cfg);targets=build_targets(candidates,total,cfg['cash_reserve_pct'],cfg['max_position_pct'],cfg['minimum_score'],cfg['min_trade_eur'])
   with self.db.con() as con:cur=con.execute('INSERT INTO real_allocation_runs(created_at,status,automatic,settings_json,details_json) VALUES(?,?,?,?,?)',(now(),'RUNNING',1 if automatic else 0,safe_json(payload),'{}'));rid=cur.lastrowid
   actions=[];today=self.db.rows("SELECT COUNT(*) n FROM real_allocation_actions WHERE status='SUBMITTED' AND date(created_at)=date('now')")[0]['n'];room=max(0,cfg['max_actions_per_day']-int(today))
   for target in targets[:min(cfg['max_actions_per_run'],room)]:
    symbol=target['symbol'];asset=self._asset(symbol.split('/')[0]);present=D(current.get(asset,0));target_eur=D(target['target_exposure_eur']);diff=target_eur-present
    if total<=0 or abs(diff)/total*100<cfg['no_trade_band_pct'] or abs(diff)<cfg['min_trade_eur']:continue
    side='buy' if diff>0 else 'sell';trade_eur=min(abs(diff),cfg['max_trade_eur']);alts=self._alternatives(symbol);selected,route=choose_route(alts,tickers,trade_eur,self.db.value('real_fee_bps',self.db.value('paper_fee_bps','40')),self.db.value('real_fx_fee_bps',self.db.value('paper_fx_fee_bps','10')),self.db.value('real_slippage_bps',self.db.value('paper_slippage_bps','10')),side)
    if not selected:continue
    family=next((x['family'] for x in candidates if x['symbol']==symbol),'crypto_spot');h=health_by_family.get(family,{'status':'NOT_READY'});raw_edge=D(health.expected_edge_pct(family,24) or 0);cost_pct=D(route['selected']['total_cost_pct'] if route.get('selected') else 999);edge_after_cost=raw_edge-cost_pct;quote=str(selected.get('quote_asset') or 'EUR').upper();usd_balance=sum((D(x['balance']) for x in self.balances() if self._asset(x['asset'])=='USD'),D(0));fx_ok=True;funding={'required':False}
    if side=='buy' and quote=='USD':
     fx=self.db.rows("SELECT bid,ask,last FROM live_prices WHERE symbol='EUR/USD' LIMIT 1")
     if not fx:fx_ok=False
     else:
      bid=D(fx[0]['bid'] or fx[0]['last']);needed_usd=trade_eur*bid*(1+D(self.db.value('real_fee_bps','40'))/10000+D(self.db.value('real_slippage_bps','10'))/10000);needed_eur=needed_usd/bid;funding={'required':usd_balance<needed_usd,'needed_usd':str(needed_usd),'needed_eur':str(needed_eur),'available_usd':str(usd_balance)}
    volume,price=self._volume(selected['symbol'],trade_eur,side,route);meta=next((x for x in alts if x.get('symbol')==selected['symbol']),{});order_ok=(not meta.get('ordermin') or volume>=D(meta.get('ordermin'))) and (not meta.get('costmin') or volume*price>=D(meta.get('costmin')));risk_ok=target_eur<=total*cfg['max_position_pct']/100 and target_eur<=total*(1-cfg['cash_reserve_pct']/100)
    ctx={'canonical_id':symbol,'confirmation_count':1,'confirmation_required':1,'minimum_hold_ok':True,'cooldown_ok':True,'daily_limit_ok':True,'improvement_after_costs':str(max(D(0),edge_after_cost)*trade_eur/100),'tax_loss_ok':True,'data_fresh':True,'model_health_ok':h.get('status')=='READY','model_health_details':h,'route_cost_ok':route.get('status')=='VALID','route_cost_details':route,'quote_funding_ok':fx_ok,'quote_funding_details':funding,'portfolio_risk_ok':risk_ok,'portfolio_risk_details':{'target_eur':str(target_eur),'total_eur':str(total)},'order_constraints_ok':order_ok,'order_constraints_details':{'volume':str(volume),'price':str(price),'ordermin':meta.get('ordermin'),'costmin':meta.get('costmin')},'real_trading_enabled':self.trade_engine.enabled(),'real_kill_switch_clear':self.db.value('real_kill_switch','true').lower()!='true','real_limits_ok':trade_eur<=cfg['max_trade_eur'],'real_balance_ok':True}
    decision=DecisionMatrix(self.db).evaluate(symbol,side.upper(),ctx,'REAL');status='BLOCKED';intent=None;secret=self.db.value('real_balancing_automation_secret','');execute=automatic and cfg['automatic_execution'] and not cfg['dry_run'] and decision['allowed']
    if automatic and cfg['dry_run']:status='DRY_RUN'
    elif automatic and cfg['automatic_execution'] and not self.db.value('real_balancing_automation_secret_hash',''):status='BLOCKED_AUTOMATION_SECRET'
    elif execute and funding['required']:
     funding_result=self.trade_engine.convert_eur_to_usd(funding['needed_eur'],secret,approval_token,False);funding['result']=funding_result
     if funding_result.get('status') in ('SUBMITTED','VALIDATED'):
      self._refresh_private_balances();usd_after=sum((D(x['balance']) for x in self.balances() if self._asset(x['asset'])=='USD'),D(0));funding['available_usd_after']=str(usd_after);funding['confirmed']=usd_after>=D(funding['needed_usd'])
      if not funding['confirmed']:status='FUNDING_RECHECK_FAILED'
      else:
       volume,price=self._volume(selected['symbol'],trade_eur,side,route);result=self.trade_engine.submit(selected['symbol'],side,str(volume),'limit',str(price),secrets.token_hex(16),approval_token,False,secret);status=result['status'];intent=result.get('client_order_id')
     else:status='FUNDING_FAILED'
    elif execute:
     result=self.trade_engine.submit(selected['symbol'],side,str(volume),'limit',str(price),secrets.token_hex(16),approval_token,False,secret);status=result['status'];intent=result.get('client_order_id')
    elif decision['allowed']:status='DRY_RUN' if cfg['dry_run'] or automatic else 'PROPOSED'
    with self.db.con() as con:con.execute('INSERT INTO real_allocation_actions(run_id,created_at,symbol,side,current_eur,target_eur,difference_eur,status,decision_json,order_intent_id,error) VALUES(?,?,?,?,?,?,?,?,?,?,?)',(rid,now(),symbol,side,str(present),str(target_eur),str(diff),status,safe_json({'decision':decision,'route':route,'funding':funding,'model_health':h}),intent,None))
    actions.append({'symbol':symbol,'side':side,'trade_eur':str(trade_eur),'status':status,'route':selected['symbol'],'quote':quote,'funding':funding})
   final='COMPLETED' if all(x['status'] not in ('FAILED','FUNDING_FAILED','FUNDING_RECHECK_FAILED') for x in actions) else 'PARTIAL'
   with self.db.con() as con:con.execute('UPDATE real_allocation_runs SET finished_at=?,status=?,details_json=? WHERE id=?',(now(),final,safe_json({'total_eur':str(total),'actions':actions,'model_health':health_by_family}),rid))
   self.db.audit('REAL_BALANCING_RUN',safe_json({'run_id':rid,'status':final,'automatic':automatic,'actions':len(actions)}),'warning' if automatic else 'info','REAL');return {'status':final,'run_id':rid,'total_eur':str(total),'actions':actions,'settings':payload,'model_health':health_by_family}
  except Exception as exc:
   if rid:
    with self.db.con() as con:con.execute('UPDATE real_allocation_runs SET finished_at=?,status=?,error=? WHERE id=?',(now(),'FAILED',type(exc).__name__+': '+str(exc),rid))
   self.db.audit('REAL_BALANCING_FAILED',type(exc).__name__+': '+str(exc),'error','REAL');return {'status':'FAILED','error':type(exc).__name__}
  finally:self.lock.release()
