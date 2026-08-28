import json
from datetime import datetime,timezone,timedelta
from decimal import Decimal
from db import now
D=lambda x:Decimal(str(x or 0))
class DecisionMatrix:
 def __init__(self,db):self.db=db;self.ensure()
 def ensure(self):
  with self.db.con() as c:c.executescript("""CREATE TABLE IF NOT EXISTS decision_rule_evaluations(id INTEGER PRIMARY KEY AUTOINCREMENT,created_at TEXT NOT NULL,symbol TEXT NOT NULL,canonical_id TEXT NOT NULL,action TEXT NOT NULL,rule_key TEXT NOT NULL,passed INTEGER NOT NULL,reason TEXT NOT NULL,details_json TEXT NOT NULL,decision_id INTEGER);""")
 def evaluate(self,symbol,action,context,trade_context='PAPER'):
  cid=context.get('canonical_id') or symbol;checks=[]
  def add(key,passed,reason,details=None):checks.append({'rule_key':key,'passed':bool(passed),'reason':reason,'details':details or {}})
  add('SIGNAL_CONFIRMED',context.get('confirmation_count',0)>=context.get('confirmation_required',1),f"Bestätigung {context.get('confirmation_count',0)}/{context.get('confirmation_required',1)}")
  add('MINIMUM_HOLD',context.get('minimum_hold_ok',True),'Mindesthaltedauer erfüllt' if context.get('minimum_hold_ok',True) else 'Mindesthaltedauer aktiv')
  add('COOLDOWN',context.get('cooldown_ok',True),'Cooldown beendet' if context.get('cooldown_ok',True) else 'Wiederkauf-Cooldown aktiv')
  add('DAILY_LIMIT',context.get('daily_limit_ok',True),'Tageslimit verfügbar' if context.get('daily_limit_ok',True) else 'Tägliches Umschichtungslimit erreicht')
  add('POSITIVE_AFTER_COSTS',D(context.get('improvement_after_costs'))>0,'Erwarteter Vorteil nach Kosten positiv' if D(context.get('improvement_after_costs'))>0 else 'Kein positiver Vorteil nach vollständigen Kosten',{'eur':str(context.get('improvement_after_costs',0))})
  add('TAX_AND_LOSS',context.get('tax_loss_ok',True),'Steuer- und Verlustwirkung akzeptabel' if context.get('tax_loss_ok',True) else 'Steuer- oder Verlustwirkung blockiert')
  add('DATA_FRESHNESS',context.get('data_fresh',False),'Daten vollständig und aktuell' if context.get('data_fresh',False) else 'Daten fehlen oder sind veraltet')
  if str(trade_context).upper()=='REAL':
   add('REAL_TRADING_ENABLED',context.get('real_trading_enabled',False),'Realhandel aktiviert' if context.get('real_trading_enabled',False) else 'Realhandel deaktiviert')
   add('REAL_KILL_SWITCH',context.get('real_kill_switch_clear',False),'Kill-Switch frei' if context.get('real_kill_switch_clear',False) else 'Kill-Switch aktiv')
   add('REAL_LIMITS',context.get('real_limits_ok',False),'Realhandelslimits eingehalten' if context.get('real_limits_ok',False) else 'Realhandelslimits blockieren')
   add('REAL_BALANCE',context.get('real_balance_ok',False),'Realer Saldo bestätigt' if context.get('real_balance_ok',False) else 'Realer Saldo fehlt')
  allowed=all(x['passed'] for x in checks);blocker=next((x['reason'] for x in checks if not x['passed']),'Alle Regeln erfüllt')
  with self.db.con() as c:
   for x in checks:c.execute('INSERT INTO decision_rule_evaluations(created_at,symbol,canonical_id,action,rule_key,passed,reason,details_json,decision_id) VALUES(?,?,?,?,?,?,?,?,?)',(now(),symbol,cid,action,x['rule_key'],1 if x['passed'] else 0,x['reason'],json.dumps(x['details'],sort_keys=True),context.get('decision_id')))
  return {'allowed':allowed,'blocker':blocker,'checks':checks}
 def recent(self):return self.db.rows('SELECT * FROM decision_rule_evaluations ORDER BY id DESC LIMIT 500')
