import json
from decimal import Decimal, ROUND_DOWN
from db import now
from portfolio_allocator import PortfolioAllocator
D=lambda x:Decimal(str(x or 0))
class PaperEngine:
 def __init__(self,db,start_eur=1000,fee_bps=40,slippage_bps=10,max_position_pct=10,trade_eur=25):
  self.db=db;self.start=D(start_eur);self.fee=D(fee_bps)/10000;self.slip=D(slippage_bps)/10000;self.maxpct=D(max_position_pct)/100;self.trade_eur=D(trade_eur);self.ensure()
 def ensure(self):
  with self.db.con() as c:
   c.executescript("""CREATE TABLE IF NOT EXISTS paper_accounts(id INTEGER PRIMARY KEY CHECK(id=1),cash_eur TEXT NOT NULL,initial_eur TEXT NOT NULL,updated_at TEXT NOT NULL);CREATE TABLE IF NOT EXISTS paper_positions(symbol TEXT PRIMARY KEY,quantity TEXT NOT NULL,avg_cost_eur TEXT NOT NULL,updated_at TEXT NOT NULL);CREATE TABLE IF NOT EXISTS paper_trades(id INTEGER PRIMARY KEY AUTOINCREMENT,created_at TEXT NOT NULL,symbol TEXT NOT NULL,side TEXT NOT NULL,quantity TEXT NOT NULL,market_price TEXT NOT NULL,execution_price TEXT NOT NULL,gross_eur TEXT NOT NULL,fee_eur TEXT NOT NULL,slippage_eur TEXT NOT NULL,net_eur TEXT NOT NULL,reason TEXT NOT NULL,decision_json TEXT NOT NULL);CREATE TABLE IF NOT EXISTS paper_decisions(id INTEGER PRIMARY KEY AUTOINCREMENT,created_at TEXT NOT NULL,symbol TEXT NOT NULL,action TEXT NOT NULL,score TEXT NOT NULL,reason TEXT NOT NULL,data_quality TEXT NOT NULL,executed INTEGER NOT NULL,trade_id INTEGER);CREATE TABLE IF NOT EXISTS paper_snapshots(id INTEGER PRIMARY KEY AUTOINCREMENT,created_at TEXT NOT NULL,cash_eur TEXT NOT NULL,positions_eur TEXT NOT NULL,total_eur TEXT NOT NULL,realized_fees_eur TEXT NOT NULL,quality TEXT NOT NULL);CREATE TABLE IF NOT EXISTS research_watchlist(symbol TEXT PRIMARY KEY,category TEXT NOT NULL,prefilter_score TEXT NOT NULL,status TEXT NOT NULL,selected_at TEXT NOT NULL,run_id INTEGER NOT NULL,reasons_json TEXT NOT NULL);""")
   c.executescript("""CREATE TABLE IF NOT EXISTS paper_position_risk(symbol TEXT PRIMARY KEY,leverage INTEGER NOT NULL,borrowed_eur TEXT NOT NULL,updated_at TEXT NOT NULL);CREATE TABLE IF NOT EXISTS product_trade_state(canonical_id TEXT PRIMARY KEY,last_buy_at TEXT,last_sell_at TEXT,confirm_action TEXT,confirm_count INTEGER NOT NULL DEFAULT 0,updated_at TEXT NOT NULL);CREATE TABLE IF NOT EXISTS daily_turnover(day TEXT PRIMARY KEY,turnovers INTEGER NOT NULL);CREATE TABLE IF NOT EXISTS allocation_plans(id INTEGER PRIMARY KEY AUTOINCREMENT,created_at TEXT NOT NULL,symbol TEXT NOT NULL,confidence TEXT NOT NULL,target_pct TEXT NOT NULL,target_exposure_eur TEXT NOT NULL,leverage INTEGER NOT NULL,current_exposure_eur TEXT NOT NULL,action TEXT NOT NULL,reason TEXT NOT NULL);""")
   c.execute('INSERT OR IGNORE INTO paper_accounts VALUES(1,?,?,?)',(str(self.start),str(self.start),now()))
 def account(self):return self.db.rows('SELECT * FROM paper_accounts WHERE id=1')[0]
 def positions(self):return self.db.rows('SELECT * FROM paper_positions ORDER BY symbol')
 def price(self,symbol):
  r=self.db.rows('SELECT last,change_pct,received_at FROM live_prices WHERE symbol=?',(symbol,))
  if not r:return None
  out=dict(r[0])
  if symbol.endswith('/USD'):
   fx=self.db.rows("SELECT last FROM live_prices WHERE symbol='EUR/USD'")
   if not fx or D(fx[0]['last'])<=0:return None
   out['last']=str(D(out['last'])/D(fx[0]['last']))
  return out
 def scanner(self,symbol):
  try:
   r=self.db.rows('SELECT * FROM scanner_results WHERE symbol=?',(symbol,));return r[0] if r else None
  except Exception:return None
 def equity(self):
  cash=D(self.account()['cash_eur']);pv=D(0);missing=[]
  for p in self.positions():
   x=self.price(p['symbol'])
   if not x:missing.append(p['symbol']);continue
   pv+=D(p['quantity'])*D(x['last'])
  debt=sum((D(x['borrowed_eur']) for x in self.db.rows('SELECT borrowed_eur FROM paper_position_risk')),D(0))
  return cash,pv,cash+pv-debt,missing
 def snapshot(self):
  cash,pv,total,missing=self.equity();fees=self.db.rows("SELECT COALESCE(SUM(CAST(fee_eur AS REAL)),0) v FROM paper_trades")[0]['v']
  with self.db.con() as c:c.execute('INSERT INTO paper_snapshots(created_at,cash_eur,positions_eur,total_eur,realized_fees_eur,quality) VALUES(?,?,?,?,?,?)',(now(),str(cash),str(pv),str(total),str(fees),'INCOMPLETE' if missing else 'VALID'))
 def execute(self,symbol,side,gross,reason,decision):
  x=self.price(symbol)
  if not x:raise ValueError('Kein Livepreis')
  market=D(x['last']);gross=D(gross);cash,pv,total,_=self.equity();pos=next((p for p in self.positions() if p['symbol']==symbol),None);oldqty=D(pos['quantity']) if pos else D(0);oldcost=D(pos['avg_cost_eur']) if pos else D(0);risk=self.db.rows('SELECT * FROM paper_position_risk WHERE symbol=?',(symbol,));olddebt=D(risk[0]['borrowed_eur']) if risk else D(0)
  quote_usd=symbol.endswith('/USD');fx_fee=fx_spread_cost=D(0)
  if quote_usd:
   fx=self.db.rows("SELECT bid,ask,last FROM live_prices WHERE symbol='EUR/USD'")
   if not fx:raise ValueError('EUR/USD fehlt für FX-Ausführung')
   fb=D(fx[0].get('bid') or fx[0].get('last'));fa=D(fx[0].get('ask') or fx[0].get('last'));fm=(fb+fa)/2
   fx_spread_rate=((fa-fb)/fm/2) if fm else D(0);fx_fee_rate=D(self.db.value('paper_fx_fee_bps','10'))/10000
  if side=='BUY':
   lev=max(1,int(decision.get('leverage',1)));collateral=min(gross,cash/(1+self.fee*lev));notional=collateral*lev;execp=market*(1+self.slip);qty=(notional/execp).quantize(Decimal('0.00000001'),rounding=ROUND_DOWN);notional=qty*execp;fee=notional*self.fee;fx_fee=notional*fx_fee_rate if quote_usd else D(0);fx_spread_cost=notional*fx_spread_rate if quote_usd else D(0);net=collateral+fee+fx_fee+fx_spread_cost
   if qty<=0 or net>cash:raise ValueError('Nicht genügend Paper-Cash')
   newqty=oldqty+qty;avg=((oldqty*oldcost)+notional)/newqty;newcash=cash-net;newdebt=olddebt+max(D(0),notional-collateral)
  else:
   lev=int(risk[0]['leverage']) if risk else 1;qty=min(oldqty,(gross/(market*(1-self.slip))).quantize(Decimal('0.00000001'),rounding=ROUND_DOWN));execp=market*(1-self.slip);notional=qty*execp;fee=notional*self.fee;fx_fee=notional*fx_fee_rate if quote_usd else D(0);fx_spread_cost=notional*fx_spread_rate if quote_usd else D(0);fee+=fx_fee+fx_spread_cost
   if qty<=0:raise ValueError('Keine Paper-Position')
   share=qty/oldqty if oldqty else D(1);repay=olddebt*share;net=notional-fee-repay;newqty=oldqty-qty;avg=oldcost;newcash=cash+net;newdebt=max(D(0),olddebt-repay);gross=notional
  rules=self.db.rows('SELECT ordermin,costmin,lot_decimals,pair_decimals,asset_class,category FROM market_universe WHERE symbol=? LIMIT 1',(symbol,))
  rule=rules[0] if rules else {};ordermin=D(rule.get('ordermin'));costmin=D(rule.get('costmin'))
  if side=='BUY' and ordermin>0 and qty<ordermin:raise ValueError(f'Mindestmenge {ordermin} unterschritten')
  if side=='BUY' and costmin>0 and notional<costmin:raise ValueError(f'Mindestkosten {costmin} unterschritten')
  decision=dict(decision,asset_class=rule.get('asset_class'),category=rule.get('category'),ordermin=str(ordermin),costmin=str(costmin),quote_currency=('USD' if symbol.endswith('/USD') else 'EUR'))
  slip=abs(execp-market)*qty
  decision=dict(decision,fx_conversion_required=quote_usd,fx_fee_eur=str(fx_fee),fx_spread_eur=str(fx_spread_cost),product_spread_slippage_eur=str(slip),trade_fee_eur=str(notional*self.fee),leverage=lev,borrowed_before_eur=str(olddebt),borrowed_after_eur=str(newdebt))
  with self.db.con() as c:
   c.execute('UPDATE paper_accounts SET cash_eur=?,updated_at=? WHERE id=1',(str(newcash),now()))
   if newqty>0:
    c.execute('INSERT OR REPLACE INTO paper_positions VALUES(?,?,?,?)',(symbol,str(newqty),str(avg),now()));c.execute('INSERT OR REPLACE INTO paper_position_risk VALUES(?,?,?,?)',(symbol,lev,str(newdebt),now()))
   else:c.execute('DELETE FROM paper_positions WHERE symbol=?',(symbol,));c.execute('DELETE FROM paper_position_risk WHERE symbol=?',(symbol,))
   cur=c.execute('INSERT INTO paper_trades(created_at,symbol,side,quantity,market_price,execution_price,gross_eur,fee_eur,slippage_eur,net_eur,reason,decision_json) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',(now(),symbol,side,str(qty),str(market),str(execp),str(gross),str(fee),str(slip),str(net),reason,json.dumps(decision,sort_keys=True)));tid=cur.lastrowid
  self.snapshot();return tid
 def canonical_id(self,symbol):
  r=self.db.rows('SELECT canonical_id FROM market_universe WHERE symbol=? LIMIT 1',(symbol,));return (r[0].get('canonical_id') if r else None) or symbol
 def stability_gate(self,symbol,action,improvement_after_costs=D(0)):
  from datetime import datetime,timezone,timedelta
  cid=self.canonical_id(symbol);today=datetime.now(timezone.utc).date().isoformat();limit=int(float(self.db.value('paper_max_turnovers_per_day','2')));used=self.db.rows('SELECT turnovers FROM daily_turnover WHERE day=?',(today,));
  if used and int(used[0]['turnovers'])>=limit:return False,'Tägliches Umschichtungslimit erreicht'
  st=self.db.rows('SELECT * FROM product_trade_state WHERE canonical_id=?',(cid,));hold_h=float(self.db.value('paper_min_hold_hours','24'));cool_h=float(self.db.value('paper_cooldown_hours','12'));need=int(float(self.db.value('paper_confirmation_runs','2')))
  if st:
   row=st[0];anchor=row.get('last_buy_at') if action=='SELL' else row.get('last_sell_at');hours=hold_h if action=='SELL' else cool_h
   if anchor and datetime.now(timezone.utc)-datetime.fromisoformat(anchor)<timedelta(hours=hours):return False,('Mindesthaltedauer aktiv' if action=='SELL' else 'Wiederkauf-Cooldown aktiv')
  previous=st[0].get('confirm_action') if st else None;count=(int(st[0].get('confirm_count') or 0)+1) if previous==action else 1
  with self.db.con() as c:c.execute('INSERT INTO product_trade_state(canonical_id,confirm_action,confirm_count,updated_at) VALUES(?,?,?,?) ON CONFLICT(canonical_id) DO UPDATE SET confirm_action=excluded.confirm_action,confirm_count=excluded.confirm_count,updated_at=excluded.updated_at',(cid,action,count,now()))
  if count<need:return False,f'Bestätigung {count}/{need}'
  if improvement_after_costs<=0:return False,'Keine positive Mindestverbesserung nach vollständigen Kosten'
  return True,'Stabilitätsregeln erfüllt'
 def mark_turnover(self,symbol,action):
  from datetime import datetime,timezone
  cid=self.canonical_id(symbol);today=datetime.now(timezone.utc).date().isoformat();field='last_buy_at' if action=='BUY' else 'last_sell_at'
  with self.db.con() as c:
   c.execute(f'INSERT INTO product_trade_state(canonical_id,{field},confirm_action,confirm_count,updated_at) VALUES(?,?,NULL,0,?) ON CONFLICT(canonical_id) DO UPDATE SET {field}=excluded.{field},confirm_action=NULL,confirm_count=0,updated_at=excluded.updated_at',(cid,now(),now()));c.execute('INSERT INTO daily_turnover VALUES(?,1) ON CONFLICT(day) DO UPDATE SET turnovers=turnovers+1',(today,))
 def run(self):
  active=self.db.value('automation_enabled','false')=='true';cash,pv,total,missing=self.equity();allocator=PortfolioAllocator(self.db);plans=allocator.plans(total);results=[];min_trade=D(self.db.value('paper_min_transfer_eur','20'));edge_min=D(self.db.value('paper_rebalance_edge_pct','8'))/100
  current={p['symbol']:D(p['quantity'])*D(self.price(p['symbol'])['last']) for p in self.positions() if self.price(p['symbol'])};rank={p['symbol']:D(p['confidence']) for p in plans};best=max(rank.values(),default=D(0))
  # Cost-aware funding: reduce materially weaker positions only when the confidence edge exceeds the configured band.
  for symbol,value in sorted(current.items(),key=lambda x:rank.get(x[0],D(0))):
   conf=rank.get(symbol,D(0));gap=best-conf
   if active and value>=min_trade and gap>=edge_min:
    costs=value*(self.fee+self.slip)*2
    if value*gap>costs:
     allowed,gate_reason=self.stability_gate(symbol,'SELL',value*gap-costs)
     if not allowed:
      results.append({'symbol':symbol,'action':'HOLD','executed':False,'reason':gate_reason});continue
     decision={'symbol':symbol,'confidence':str(conf),'better_confidence':str(best),'edge':str(gap),'estimated_roundtrip_cost_eur':str(costs),'leverage':1,'action':'SELL'};reason='Kostenbewusste Umschichtung: erwarteter Konfidenzvorteil über Transferkosten'
     try:tid=self.execute(symbol,'SELL',value,reason,decision);executed=1;self.mark_turnover(symbol,'SELL')
     except ValueError as exc:tid=None;executed=0;reason+='; '+str(exc)
     with self.db.con() as c:c.execute('INSERT INTO paper_decisions VALUES(NULL,?,?,?,?,?,?,?,?)',(now(),symbol,'SELL',str(conf*100),reason,'LIVE',executed,tid))
     results.append(decision|{'executed':bool(executed),'reason':reason})
  cash,pv,total,missing=self.equity()
  for plan in plans:
   symbol=plan['symbol'];target=D(plan['target_exposure_eur']);value=current.get(symbol,D(0));gap=max(D(0),target-value);lev=int(plan['leverage']);collateral=gap/lev if lev else gap;action='BUY' if gap>=min_trade else 'HOLD';reason='Dynamisches Zielgewicht aus kalibrierbarem Score, Volatilität und Portfoliolimit' if action=='BUY' else 'No-Trade-Band oder Zielgewicht erreicht';tid=None;executed=0
   with self.db.con() as c:c.execute('INSERT INTO allocation_plans VALUES(NULL,?,?,?,?,?,?,?,?,?)',(now(),symbol,plan['confidence'],plan['target_pct'],plan['target_exposure_eur'],lev,str(value),action,reason))
   if active and action=='BUY' and D(plan['confidence'])>0:
    estimated=gap*D(plan['confidence'])-gap*(self.fee+self.slip)*2
    allowed,gate_reason=self.stability_gate(symbol,'BUY',estimated)
    if not allowed:reason+='; '+gate_reason
    try:
     if not allowed:raise ValueError(gate_reason)
     tid=self.execute(symbol,'BUY',min(collateral,D(self.db.value('paper_max_transfer_eur','250'))),reason,plan|{'action':'BUY'});executed=1;self.mark_turnover(symbol,'BUY')
    except ValueError as exc:reason+='; '+str(exc)
   with self.db.con() as c:c.execute('INSERT INTO paper_decisions VALUES(NULL,?,?,?,?,?,?,?,?)',(now(),symbol,action,str(D(plan['confidence'])*100),reason,'LIVE',executed,tid))
   results.append(plan|{'action':action,'executed':bool(executed),'reason':reason})
  self.snapshot();self.db.audit('PAPER_PORTFOLIO_OPTIMIZER_RUN',json.dumps({'plans':len(plans),'executed':sum(1 for x in results if x['executed']),'automation_enabled':active}));return results
def configure_engine(engine):
 def value(key,default):
  rows=engine.db.rows('SELECT value FROM settings WHERE key=?',(key,));return rows[0]['value'] if rows else default
 engine.fee=D(value('paper_fee_bps',40))/10000
 engine.slip=D(value('paper_slippage_bps',10))/10000
 engine.maxpct=D(value('paper_max_position_pct',10))/100
 engine.trade_eur=D(value('paper_trade_eur',25))
 return engine
