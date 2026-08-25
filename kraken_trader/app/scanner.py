import json, math, statistics, time
from decimal import Decimal
from db import now
D=lambda x:Decimal(str(x or 0))
class MarketScanner:
 def __init__(self,db,client):self.db,self.client=db,client;self.ensure()
 def ensure(self):
  with self.db.con() as c:c.executescript("""CREATE TABLE IF NOT EXISTS scanner_results(symbol TEXT PRIMARY KEY,scanned_at TEXT NOT NULL,score TEXT NOT NULL,signal TEXT NOT NULL,momentum_pct TEXT,volatility_pct TEXT,trend_pct TEXT,spread_pct TEXT,volume_quote TEXT,data_points INTEGER NOT NULL,quality TEXT NOT NULL,reasons_json TEXT NOT NULL);CREATE TABLE IF NOT EXISTS ohlc_cache(symbol TEXT NOT NULL,interval_min INTEGER NOT NULL,open_time INTEGER NOT NULL,open TEXT NOT NULL,high TEXT NOT NULL,low TEXT NOT NULL,close TEXT NOT NULL,vwap TEXT,volume TEXT,trades INTEGER,received_at TEXT NOT NULL,PRIMARY KEY(symbol,interval_min,open_time));CREATE TABLE IF NOT EXISTS scanner_runs(id INTEGER PRIMARY KEY AUTOINCREMENT,created_at TEXT NOT NULL,symbols_requested INTEGER NOT NULL,symbols_valid INTEGER NOT NULL,buy_count INTEGER NOT NULL,hold_count INTEGER NOT NULL,avoid_count INTEGER NOT NULL,quality TEXT NOT NULL);""")
 def analyze(self,symbol,candles,ticker):
  committed=candles[:-1] if len(candles)>1 else []
  closes=[float(x[4]) for x in committed if len(x)>6 and float(x[4])>0];volumes=[float(x[6]) for x in committed if len(x)>6]
  reasons=[]
  if len(closes)<30:return {'symbol':symbol,'score':0,'signal':'AVOID','momentum_pct':None,'volatility_pct':None,'trend_pct':None,'spread_pct':None,'volume_quote':None,'data_points':len(closes),'quality':'INSUFFICIENT','reasons':['Weniger als 30 abgeschlossene Kerzen']}
  returns=[closes[i]/closes[i-1]-1 for i in range(1,len(closes))]
  momentum=(closes[-1]/closes[-25]-1)*100 if len(closes)>=25 else 0
  short=sum(closes[-10:])/10;long=sum(closes[-30:])/30;trend=(short/long-1)*100
  volatility=statistics.pstdev(returns[-30:])*math.sqrt(24)*100 if len(returns)>=2 else 0
  bid=float((ticker or {}).get('b',['0'])[0] or 0);ask=float((ticker or {}).get('a',['0'])[0] or 0);mid=(bid+ask)/2;spread=((ask-bid)/mid*100) if mid else 999
  volume_quote=sum(v*p for v,p in zip(volumes[-24:],closes[-24:]))
  score=50+max(-25,min(25,momentum*5))+max(-15,min(15,trend*8))-max(0,min(20,volatility*1.5))-max(0,min(20,spread*25))
  score=max(0,min(100,score));signal='BUY' if score>=65 and momentum>0 and trend>0 and spread<=0.8 else ('AVOID' if score<35 or spread>1.5 else 'HOLD')
  reasons += [f'24h-Momentum {momentum:.2f} %',f'Trend SMA10/SMA30 {trend:.2f} %',f'Volatilität {volatility:.2f} %',f'Spread {spread:.3f} %',f'24h-Quotevolumen ca. {volume_quote:.2f} EUR']
  return {'symbol':symbol,'score':round(score,4),'signal':signal,'momentum_pct':round(momentum,6),'volatility_pct':round(volatility,6),'trend_pct':round(trend,6),'spread_pct':round(spread,6),'volume_quote':round(volume_quote,4),'data_points':len(closes),'quality':'VALID','reasons':reasons}
 def run(self,symbols,interval=60,limit=None,delay_seconds=None):
  symbols=list(symbols)[:int(limit or len(symbols))];delay=float(delay_seconds if delay_seconds is not None else self.db.value('scanner_delay_seconds','1.05'));stamp=now();valid=buy=hold=avoid=0
  try:tickers=self.client.ticker(symbols)
  except Exception:tickers={}
  for symbol in symbols:
   try:
    ac=self.db.rows('SELECT asset_class FROM market_universe WHERE symbol=? LIMIT 1',(symbol,));payload=self.client.ohlc(symbol,interval,ac[0]['asset_class'] if ac else 'currency');key=next((k for k in payload if k!='last'),None);candles=payload.get(key,[]) if key else []
    with self.db.con() as c:
     for x in candles:c.execute('INSERT OR REPLACE INTO ohlc_cache VALUES(?,?,?,?,?,?,?,?,?,?,?)',(symbol,interval,int(x[0]),str(x[1]),str(x[2]),str(x[3]),str(x[4]),str(x[5]),str(x[6]),int(x[7]),stamp))
    ticker=None
    for k,v in tickers.items():
     if symbol.replace('BTC','XBT').replace('/','') in k.replace('X','').replace('Z','').replace('/','') or len(tickers)==1:ticker=v;break
    r=self.analyze(symbol,candles,ticker);valid+=r['quality']=='VALID';buy+=r['signal']=='BUY';hold+=r['signal']=='HOLD';avoid+=r['signal']=='AVOID'
   except Exception as exc:r={'symbol':symbol,'score':0,'signal':'AVOID','momentum_pct':None,'volatility_pct':None,'trend_pct':None,'spread_pct':None,'volume_quote':None,'data_points':0,'quality':'ERROR','reasons':[type(exc).__name__]};avoid+=1
   with self.db.con() as c:c.execute('INSERT OR REPLACE INTO scanner_results VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',(r['symbol'],stamp,str(r['score']),r['signal'],None if r['momentum_pct'] is None else str(r['momentum_pct']),None if r['volatility_pct'] is None else str(r['volatility_pct']),None if r['trend_pct'] is None else str(r['trend_pct']),None if r['spread_pct'] is None else str(r['spread_pct']),None if r['volume_quote'] is None else str(r['volume_quote']),r['data_points'],r['quality'],json.dumps(r['reasons'],ensure_ascii=False),))
   if delay:time.sleep(delay)
  quality='VALID' if symbols and valid==len(symbols) else 'INCOMPLETE'
  with self.db.con() as c:c.execute('INSERT INTO scanner_runs(created_at,symbols_requested,symbols_valid,buy_count,hold_count,avoid_count,quality) VALUES(?,?,?,?,?,?,?)',(stamp,len(symbols),valid,buy,hold,avoid,quality))
  self.db.audit('SCANNER_RUN',json.dumps({'requested':len(symbols),'valid':valid,'buy':buy,'hold':hold,'avoid':avoid,'quality':quality}));return self.db.rows('SELECT * FROM scanner_results ORDER BY CAST(score AS REAL) DESC')
