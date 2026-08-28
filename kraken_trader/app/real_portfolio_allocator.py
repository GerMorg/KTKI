import json,secrets,threading
from datetime import datetime,timezone
from decimal import Decimal,InvalidOperation
from db import now
from decision_matrix import DecisionMatrix
D=lambda x:Decimal(str(x or 0))

def _bool(db,key,default='false'):return db.value(key,default).lower()=='true'
class RealPortfolioAllocator:
 def __init__(self,db,trade_engine):self.db=db;self.trade_engine=trade_engine;self.lock=threading.Lock();self.ensure()
 def ensure(self):
  with self.db.con() as c:c.executescript("""
  CREATE TABLE IF NOT EXISTS real_allocation_runs(id INTEGER PRIMARY KEY AUTOINCREMENT,created_at TEXT NOT NULL,finished_at TEXT,status TEXT NOT NULL,automatic INTEGER NOT NULL,settings_json TEXT NOT NULL,details_json TEXT NOT NULL,error TEXT);
  CREATE TABLE IF NOT EXISTS real_allocation_actions(id INTEGER PRIMARY KEY AUTOINCREMENT,run_id INTEGER NOT NULL,created_at TEXT NOT NULL,symbol TEXT NOT NULL,side TEXT NOT NULL,current_eur TEXT NOT NULL,target_eur TEXT NOT NULL,difference_eur TEXT NOT NULL,status TEXT NOT NULL,decision_json TEXT NOT NULL,order_intent_id TEXT,error TEXT);
  CREATE TABLE IF NOT EXISTS real_balance_snapshots(id INTEGER PRIMARY KEY AUTOINCREMENT,created_at TEXT NOT NULL,asset TEXT NOT NULL,amount TEXT NOT NULL,source TEXT NOT NULL);
  """)
 def settings(self):
  def num(k,d,lo=None,hi=None):
   try:v=D(self.db.value(k,str(d)))
   except (InvalidOperation,ValueError):v=D(d)
   if lo is not None:v=max(D(lo),v)
   if hi is not None:v=min(D(hi),v)
   return v
  return {'enabled':_bool(self.db,'real_balancing_enabled'),'automatic_execution':_bool(self.db,'real_balancing_execute_enabled'),
   'interval_minutes':int(num('real_balancing_interval_minutes',60,5,1440)),'max_position_pct':num('real_balancing_max_position_pct',5,.1,100),
   'cash_reserve_pct':num('real_balancing_cash_reserve_pct',20,0,100),'min_trade_eur':num('real_balancing_min_trade_eur',20,0),
   'max_trade_eur':num('real_balancing_max_trade_eur',50,.01),'no_trade_band_pct':num('real_balancing_no_trade_band_pct',2,0,100),
   'max_actions_per_run':int(num('real_balancing_max_actions_per_run',1,1,100)),'max_actions_per_day':int(num('real_balancing_max_actions_per_day',2,1,100)),
   'cooldown_hours':num('real_balancing_cooldown_hours',24,0,720),'minimum_score':num('real_balancing_minimum_score',70,0,100),
   'allowed_symbols':[x.strip().upper() for x in self.db.value('real_allowed_symbols','').split(',') if x.strip()],
   'dry_run':_bool(self.db,'real_balancing_dry_run','true'),'limit_offset_pct':num('real_balancing_limit_offset_pct',.2,0,10)}
 def balances(self):return self.db.rows('SELECT asset,balance FROM private_balances ORDER BY asset')
 def _current_eur(self):
  out={};total=D(0)
  for b in self.balances():
   asset=str(b['asset']).replace('XBT','BTC');amount=D(b['balance']);
   if asset in ('EUR','ZEUR'):value=amount
   else:
    rows=self.db.rows('SELECT last FROM live_prices WHERE symbol=?', (asset+'/EUR',));value=amount*D(rows[0]['last']) if rows else D(0)
   out[asset]=value;total+=value
  return out,total
 def _candidates(self,settings):
  try:rows=self.db.rows("SELECT s.symbol,s.score,p.last,p.ask,p.bid FROM scanner_results s JOIN live_prices p ON p.symbol=s.symbol WHERE s.quality='VALID' AND s.signal='BUY' AND CAST(s.score AS REAL)>=? ORDER BY CAST(s.score AS REAL) DESC",(str(settings['minimum_score']),))
  except Exception:rows=[]
  return [x for x in rows if not settings['allowed_symbols'] or x['symbol'].upper() in settings['allowed_symbols']]
 def run(self,automatic=False,approval_token=None):
  if not self.lock.acquire(False):return {'status':'BUSY'}
  cfg=self.settings();rid=None
  try:
   if automatic and not cfg['enabled']:return {'status':'DISABLED'}
   current,total=self._current_eur();payload={k:(str(v) if isinstance(v,Decimal) else v) for k,v in cfg.items()}
   with self.db.con() as c:cur=c.execute('INSERT INTO real_allocation_runs(created_at,status,automatic,settings_json,details_json) VALUES(?,?,?,?,?)',(now(),'RUNNING',1 if automatic else 0,json.dumps(payload,sort_keys=True),'{}'));rid=cur.lastrowid
   investable=total*(D(1)-cfg['cash_reserve_pct']/100);actions=[];today=self.db.rows("SELECT COUNT(*) n FROM real_allocation_actions WHERE status='SUBMITTED' AND date(created_at)=date('now')")[0]['n']
   room=max(0,cfg['max_actions_per_day']-int(today))
   for row in self._candidates(cfg):
    if len(actions)>=min(cfg['max_actions_per_run'],room):break
    symbol=row['symbol'];asset=symbol.split('/')[0].replace('XBT','BTC');target=min(investable*cfg['max_position_pct']/100,investable);present=current.get(asset,D(0));diff=target-present
    if total and abs(diff)/total*100<cfg['no_trade_band_pct'] or abs(diff)<cfg['min_trade_eur']:continue
    side='buy' if diff>0 else 'sell';trade_eur=min(abs(diff),cfg['max_trade_eur']);price=D(row.get('ask') if side=='buy' else row.get('bid') or row.get('last'))
    if price<=0:continue
    volume=trade_eur/price;ctx={'confirmation_count':1,'confirmation_required':1,'improvement_after_costs':trade_eur,'data_fresh':True,'real_trading_enabled':self.trade_engine.enabled(),'real_kill_switch_clear':self.db.value('real_kill_switch','true').lower()!='true','real_limits_ok':trade_eur<=cfg['max_trade_eur'],'real_balance_ok':bool(self.balances())}
    decision=DecisionMatrix(self.db).evaluate(symbol,side.upper(),ctx,'REAL');status='BLOCKED';intent=None;error=None
    execute=automatic and cfg['automatic_execution'] and not cfg['dry_run'] and decision['allowed']
    if execute:
     # Automatic balancing has no reusable UI token. It requires a separate automation secret matching a stored hash.
     secret=self.db.value('real_balancing_automation_secret','');armed=self.db.value('real_balancing_automation_secret_hash','')
     import hashlib,hmac
     if not secret or not armed or not hmac.compare_digest(hashlib.sha256(secret.encode()).hexdigest(),armed):status='BLOCKED_AUTOMATION_SECRET'
     else:
      try:
       result=self.trade_engine.submit(symbol,side,str(volume),'limit',str(price),secrets.token_hex(16),approval_token=None,validate_only=False,automation_secret=secret);status=result['status'];intent=result['client_order_id']
      except Exception as exc:status='FAILED';error=type(exc).__name__+': '+str(exc)
    elif decision['allowed']:status='DRY_RUN' if cfg['dry_run'] or automatic else 'PROPOSED'
    with self.db.con() as c:c.execute('INSERT INTO real_allocation_actions(run_id,created_at,symbol,side,current_eur,target_eur,difference_eur,status,decision_json,order_intent_id,error) VALUES(?,?,?,?,?,?,?,?,?,?,?)',(rid,now(),symbol,side,str(present),str(target),str(diff),status,json.dumps(decision,sort_keys=True),intent,error))
    actions.append({'symbol':symbol,'side':side,'trade_eur':str(trade_eur),'status':status,'error':error})
   final='COMPLETED' if all(x['status'] not in ('FAILED',) for x in actions) else 'PARTIAL'
   with self.db.con() as c:c.execute('UPDATE real_allocation_runs SET finished_at=?,status=?,details_json=? WHERE id=?',(now(),final,json.dumps({'total_eur':str(total),'actions':actions},sort_keys=True),rid))
   self.db.audit('REAL_BALANCING_RUN',json.dumps({'run_id':rid,'status':final,'automatic':automatic,'actions':len(actions)}),'warning' if automatic else 'info','REAL');return {'status':final,'run_id':rid,'total_eur':str(total),'actions':actions,'settings':payload}
  except Exception as exc:
   if rid:
    with self.db.con() as c:c.execute('UPDATE real_allocation_runs SET finished_at=?,status=?,error=? WHERE id=?',(now(),'FAILED',type(exc).__name__+': '+str(exc),rid))
   self.db.audit('REAL_BALANCING_FAILED',type(exc).__name__+': '+str(exc),'error','REAL');return {'status':'FAILED','error':type(exc).__name__}
  finally:self.lock.release()
