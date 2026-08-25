import json
from decimal import Decimal, ROUND_DOWN
from db import now
D=lambda x:Decimal(str(x or 0))
class PaperEngine:
 def __init__(self,db,start_eur=1000,fee_bps=40,slippage_bps=10,max_position_pct=10,trade_eur=25):
  self.db=db;self.start=D(start_eur);self.fee=D(fee_bps)/10000;self.slip=D(slippage_bps)/10000;self.maxpct=D(max_position_pct)/100;self.trade_eur=D(trade_eur);self.ensure()
 def ensure(self):
  with self.db.con() as c:
   c.executescript("""CREATE TABLE IF NOT EXISTS paper_accounts(id INTEGER PRIMARY KEY CHECK(id=1),cash_eur TEXT NOT NULL,initial_eur TEXT NOT NULL,updated_at TEXT NOT NULL);CREATE TABLE IF NOT EXISTS paper_positions(symbol TEXT PRIMARY KEY,quantity TEXT NOT NULL,avg_cost_eur TEXT NOT NULL,updated_at TEXT NOT NULL);CREATE TABLE IF NOT EXISTS paper_trades(id INTEGER PRIMARY KEY AUTOINCREMENT,created_at TEXT NOT NULL,symbol TEXT NOT NULL,side TEXT NOT NULL,quantity TEXT NOT NULL,market_price TEXT NOT NULL,execution_price TEXT NOT NULL,gross_eur TEXT NOT NULL,fee_eur TEXT NOT NULL,slippage_eur TEXT NOT NULL,net_eur TEXT NOT NULL,reason TEXT NOT NULL,decision_json TEXT NOT NULL);CREATE TABLE IF NOT EXISTS paper_decisions(id INTEGER PRIMARY KEY AUTOINCREMENT,created_at TEXT NOT NULL,symbol TEXT NOT NULL,action TEXT NOT NULL,score TEXT NOT NULL,reason TEXT NOT NULL,data_quality TEXT NOT NULL,executed INTEGER NOT NULL,trade_id INTEGER);CREATE TABLE IF NOT EXISTS paper_snapshots(id INTEGER PRIMARY KEY AUTOINCREMENT,created_at TEXT NOT NULL,cash_eur TEXT NOT NULL,positions_eur TEXT NOT NULL,total_eur TEXT NOT NULL,realized_fees_eur TEXT NOT NULL,quality TEXT NOT NULL);CREATE TABLE IF NOT EXISTS research_watchlist(symbol TEXT PRIMARY KEY,category TEXT NOT NULL,prefilter_score TEXT NOT NULL,status TEXT NOT NULL,selected_at TEXT NOT NULL,run_id INTEGER NOT NULL,reasons_json TEXT NOT NULL);""")
   c.execute('INSERT OR IGNORE INTO paper_accounts VALUES(1,?,?,?)',(str(self.start),str(self.start),now()))
 def account(self):return self.db.rows('SELECT * FROM paper_accounts WHERE id=1')[0]
 def positions(self):return self.db.rows('SELECT * FROM paper_positions ORDER BY symbol')
 def price(self,symbol):
  r=self.db.rows('SELECT last,change_pct,received_at FROM live_prices WHERE symbol=?',(symbol,));return r[0] if r else None
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
  return cash,pv,cash+pv,missing
 def snapshot(self):
  cash,pv,total,missing=self.equity();fees=self.db.rows("SELECT COALESCE(SUM(CAST(fee_eur AS REAL)),0) v FROM paper_trades")[0]['v']
  with self.db.con() as c:c.execute('INSERT INTO paper_snapshots(created_at,cash_eur,positions_eur,total_eur,realized_fees_eur,quality) VALUES(?,?,?,?,?,?)',(now(),str(cash),str(pv),str(total),str(fees),'INCOMPLETE' if missing else 'VALID'))
 def execute(self,symbol,side,gross,reason,decision):
  x=self.price(symbol)
  if not x:raise ValueError('Kein Livepreis')
  market=D(x['last']);gross=D(gross);cash,pv,total,_=self.equity();pos=next((p for p in self.positions() if p['symbol']==symbol),None);oldqty=D(pos['quantity']) if pos else D(0);oldcost=D(pos['avg_cost_eur']) if pos else D(0)
  if side=='BUY':
   gross=min(gross,cash/(1+self.fee));execp=market*(1+self.slip);qty=(gross/execp).quantize(Decimal('0.00000001'),rounding=ROUND_DOWN);gross=qty*execp;fee=gross*self.fee;net=gross+fee
   if qty<=0 or net>cash:raise ValueError('Nicht genügend Paper-Cash')
   newqty=oldqty+qty;avg=((oldqty*oldcost)+gross)/newqty;newcash=cash-net
  else:
   qty=min(oldqty,(gross/(market*(1-self.slip))).quantize(Decimal('0.00000001'),rounding=ROUND_DOWN));execp=market*(1-self.slip);gross=qty*execp;fee=gross*self.fee;net=gross-fee
   if qty<=0:raise ValueError('Keine Paper-Position');newqty=oldqty-qty;avg=oldcost;newcash=cash+net
  slip=abs(execp-market)*qty
  with self.db.con() as c:
   c.execute('UPDATE paper_accounts SET cash_eur=?,updated_at=? WHERE id=1',(str(newcash),now()))
   if newqty>0:c.execute('INSERT OR REPLACE INTO paper_positions VALUES(?,?,?,?)',(symbol,str(newqty),str(avg),now()))
   else:c.execute('DELETE FROM paper_positions WHERE symbol=?',(symbol,))
   cur=c.execute('INSERT INTO paper_trades(created_at,symbol,side,quantity,market_price,execution_price,gross_eur,fee_eur,slippage_eur,net_eur,reason,decision_json) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',(now(),symbol,side,str(qty),str(market),str(execp),str(gross),str(fee),str(slip),str(net),reason,json.dumps(decision,sort_keys=True)));tid=cur.lastrowid
  self.snapshot();return tid
 def run(self):
  active=self.db.value('automation_enabled','false')=='true';scanner_required=self.db.value('scanner_required','true')=='true';results=[];cash,pv,total,missing=self.equity();allowed=[x['symbol'] for x in self.db.rows("SELECT symbol FROM research_watchlist WHERE status='ANALYZED' ORDER BY CAST(prefilter_score AS REAL) DESC")]
  for symbol in allowed:
   x=self.price(symbol);scan=self.scanner(symbol);action='HOLD';executed=0;tid=None;quality='LIVE' if x else 'MISSING';score=D(scan['score']) if scan else D(0);reason='Kein aktueller Livepreis';pos=next((p for p in self.positions() if p['symbol']==symbol),None);value=D(pos['quantity'])*D(x['last']) if pos and x else D(0);cap=total*self.maxpct
   if x and scanner_required and (not scan or scan['quality']!='VALID'):quality='SCANNER_MISSING';reason='Keine abgeschlossene valide Analyse; fail-closed'
   elif x and scanner_required:action=scan['signal'] if scan['signal'] in ('BUY','HOLD') else ('SELL' if scan['signal']=='AVOID' and value>0 else 'HOLD');reason='Watchlist-Analyse '+scan['signal']+' Score '+scan['score']
   elif x:
    score=D(x.get('change_pct'));action='BUY' if score>=D('1') and value<cap else ('SELL' if score<=D('-1.5') and value>0 else 'HOLD');reason='Deterministisches Fallback-Momentum'
   decision={'symbol':symbol,'score':str(score),'action':action,'quality':quality,'automation_enabled':active,'watchlist_required':True}
   if active and quality=='LIVE' and action in ('BUY','SELL'):
    try:tid=self.execute(symbol,action,min(self.trade_eur,max(D(0),cap-value) if action=='BUY' else value),reason,decision);executed=1
    except ValueError as e:reason+='; nicht ausgeführt: '+str(e)
   with self.db.con() as c:c.execute('INSERT INTO paper_decisions(created_at,symbol,action,score,reason,data_quality,executed,trade_id) VALUES(?,?,?,?,?,?,?,?)',(now(),symbol,action,str(score),reason,quality,executed,tid))
   results.append(decision|{'executed':bool(executed),'reason':reason})
  self.snapshot();self.db.audit('PAPER_STRATEGY_RUN',json.dumps({'watchlist':len(allowed),'executed':sum(1 for x in results if x['executed']),'automation_enabled':active}));return results
def configure_engine(engine):
 def value(key,default):
  rows=engine.db.rows('SELECT value FROM settings WHERE key=?',(key,));return rows[0]['value'] if rows else default
 engine.fee=D(value('paper_fee_bps',40))/10000
 engine.slip=D(value('paper_slippage_bps',10))/10000
 engine.maxpct=D(value('paper_max_position_pct',10))/100
 engine.trade_eur=D(value('paper_trade_eur',25))
 return engine
