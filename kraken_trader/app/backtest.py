import json,math
from db import now
class BacktestEngine:
 def __init__(self,db):self.db=db;self.ensure()
 def ensure(self):
  with self.db.con() as c:c.executescript("""CREATE TABLE IF NOT EXISTS backtest_runs(id INTEGER PRIMARY KEY AUTOINCREMENT,created_at TEXT NOT NULL,symbol TEXT NOT NULL,asset_class TEXT NOT NULL,interval_min INTEGER NOT NULL,model_version TEXT NOT NULL,train_points INTEGER NOT NULL,test_points INTEGER NOT NULL,cost_rate TEXT NOT NULL,status TEXT NOT NULL,results_json TEXT NOT NULL);""")
 def run(self,symbol,interval_min=60,cost_rate=.006):
  rows=self.db.rows('SELECT open_time,close FROM ohlc_cache WHERE symbol=? AND interval_min=? ORDER BY open_time',(symbol,int(interval_min)));prices=[float(x['close']) for x in rows if float(x['close'])>0]
  if len(prices)<60:return {'status':'INSUFFICIENT','points':len(prices),'required':60}
  split=max(30,int(len(prices)*.6));test=prices[split:];start=prices[split-1]
  hold=test[-1]/start-1;cash=1.;units=0.;trades=0;curve=[]
  allp=prices[:split]
  for price in test:
   allp.append(price);short=sum(allp[-10:])/10;long=sum(allp[-30:])/30;want=short>long
   if want and not units:units=cash*(1-cost_rate)/price;cash=0;trades+=1
   elif not want and units:cash=units*price*(1-cost_rate);units=0;trades+=1
   curve.append(cash+units*price)
  final=(cash+units*test[-1])*(1-cost_rate if units else 1);trend=final-1;peak=1.;dd=0
  for x in curve:peak=max(peak,x);dd=min(dd,x/peak-1)
  results={'no_position_return':0,'buy_hold_return':hold,'trend_return':trend,'trend_max_drawdown':dd,'turnovers':trades,'estimated_cost_rate':cost_rate}
  ac=(self.db.rows('SELECT asset_class FROM market_universe WHERE symbol=? LIMIT 1',(symbol,)) or [{'asset_class':'unknown'}])[0]['asset_class']
  with self.db.con() as c:cur=c.execute('INSERT INTO backtest_runs(created_at,symbol,asset_class,interval_min,model_version,train_points,test_points,cost_rate,status,results_json) VALUES(?,?,?,?,?,?,?,?,?,?)',(now(),symbol,ac,int(interval_min),'trend-sma10-30-v1',split,len(test),str(cost_rate),'VALID',json.dumps(results,sort_keys=True)));rid=cur.lastrowid
  return {'status':'VALID','run_id':rid,**results}

