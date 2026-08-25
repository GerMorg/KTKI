import json,math,statistics,time
from db import now
class MarketScanner:
 def __init__(self,db,client):self.db,self.client=db,client;self.ensure()
 def ensure(self):
  with self.db.con() as c:c.executescript("""CREATE TABLE IF NOT EXISTS scanner_results(symbol TEXT PRIMARY KEY,scanned_at TEXT NOT NULL,score TEXT NOT NULL,signal TEXT NOT NULL,momentum_pct TEXT,volatility_pct TEXT,trend_pct TEXT,spread_pct TEXT,volume_quote TEXT,data_points INTEGER NOT NULL,quality TEXT NOT NULL,reasons_json TEXT NOT NULL);CREATE TABLE IF NOT EXISTS ohlc_cache(symbol TEXT NOT NULL,interval_min INTEGER NOT NULL,open_time INTEGER NOT NULL,open TEXT NOT NULL,high TEXT NOT NULL,low TEXT NOT NULL,close TEXT NOT NULL,vwap TEXT,volume TEXT,trades INTEGER,received_at TEXT NOT NULL,PRIMARY KEY(symbol,interval_min,open_time));CREATE TABLE IF NOT EXISTS scanner_runs(id INTEGER PRIMARY KEY AUTOINCREMENT,created_at TEXT NOT NULL,symbols_requested INTEGER NOT NULL,symbols_valid INTEGER NOT NULL,buy_count INTEGER NOT NULL,hold_count INTEGER NOT NULL,avoid_count INTEGER NOT NULL,quality TEXT NOT NULL);""")
 def profile(self,symbol):
  r=self.db.rows('SELECT asset_class,category,quote_asset,source_key FROM market_universe WHERE symbol=? LIMIT 1',(symbol,))
  return r[0] if r else {'asset_class':'currency','category':'crypto_spot','quote_asset':symbol.rsplit('/',1)[-1],'source_key':symbol}
 @staticmethod
 def match(payload,symbol,source_key=None):
  wants={str(symbol).replace('/','').upper(),str(source_key or '').replace('/','').upper()}
  wants|={x.replace('BTC','XBT').replace('X','') for x in list(wants)}
  for key,value in (payload or {}).items():
   compact=str(key).replace('/','').upper();variants={compact,compact.replace('X','').replace('Z','')}
   if any(w and (w in variants or w.replace('X','') in variants) for w in wants):return value
  return next(iter(payload.values())) if len(payload or {})==1 else None
 def analyze(self,symbol,candles,ticker,category='crypto_spot',quote='EUR'):
  committed=candles[:-1] if len(candles)>1 else [];closes=[float(x[4]) for x in committed if len(x)>6 and float(x[4])>0];volumes=[float(x[6]) for x in committed if len(x)>6]
  if len(closes)<30:return {'symbol':symbol,'score':0,'signal':'AVOID','momentum_pct':None,'volatility_pct':None,'trend_pct':None,'spread_pct':None,'volume_quote':None,'data_points':len(closes),'quality':'INSUFFICIENT','reasons':['Weniger als 30 abgeschlossene Kerzen']}
  returns=[closes[i]/closes[i-1]-1 for i in range(1,len(closes))];momentum=(closes[-1]/closes[-25]-1)*100;short=sum(closes[-10:])/10;long=sum(closes[-30:])/30;trend=(short/long-1)*100;volatility=statistics.pstdev(returns[-30:])*math.sqrt(24)*100
  bid=float((ticker or {}).get('b',['0'])[0] or 0);ask=float((ticker or {}).get('a',['0'])[0] or 0);mid=(bid+ask)/2;spread=(ask-bid)/mid*100 if mid else 999;volume_quote=sum(v*p for v,p in zip(volumes[-24:],closes[-24:]))
  if category=='xstocks':
   score=50+max(-22,min(22,momentum*4))+max(-18,min(18,trend*10))-max(0,min(18,volatility*1.2))-max(0,min(22,spread*18));buy=score>=62 and momentum>0 and trend>0 and spread<=1.2;avoid=score<32 or spread>2.5;model='xstocks-v1'
  else:
   score=50+max(-25,min(25,momentum*5))+max(-15,min(15,trend*8))-max(0,min(20,volatility*1.5))-max(0,min(20,spread*25));buy=score>=65 and momentum>0 and trend>0 and spread<=.8;avoid=score<35 or spread>1.5;model='crypto-v1'
  score=max(0,min(100,score));signal='BUY' if buy else ('AVOID' if avoid else 'HOLD');reasons=[f'Modell {model}',f'24h-Momentum {momentum:.2f} %',f'Trend SMA10/SMA30 {trend:.2f} %',f'Volatilität {volatility:.2f} %',f'Spread {spread:.3f} %',f'24h-Quotevolumen ca. {volume_quote:.2f} {quote}']
  return {'symbol':symbol,'score':round(score,4),'signal':signal,'momentum_pct':round(momentum,6),'volatility_pct':round(volatility,6),'trend_pct':round(trend,6),'spread_pct':round(spread,6),'volume_quote':round(volume_quote,4),'data_points':len(closes),'quality':'VALID','reasons':reasons}
 def run(self,symbols,interval=60,limit=None,delay_seconds=None):
  symbols=list(dict.fromkeys(symbols))[:int(limit or len(symbols))];delay=float(delay_seconds if delay_seconds is not None else self.db.value('scanner_delay_seconds','1.05'));stamp=now();counts={'valid':0,'buy':0,'hold':0,'avoid':0};tickers={}
  profiles={s:self.profile(s) for s in symbols};groups={}
  for s,p in profiles.items():groups.setdefault(p['asset_class'],[]).append(s)
  for ac,batch in groups.items():
   try:tickers[ac]=self.client.ticker(batch,ac)
   except Exception:
    tickers[ac]={}
    for symbol in batch:
     try:tickers[ac].update(self.client.ticker([symbol],ac))
     except Exception:pass
  for symbol in symbols:
   p=profiles[symbol]
   try:
    pair=p.get('source_key') or symbol
    try:payload=self.client.ohlc(pair,interval,p['asset_class'])
    except Exception:payload=self.client.ohlc(symbol,interval,p['asset_class']) if pair!=symbol else {}
    key=next((k for k in payload if k!='last'),None);candles=payload.get(key,[]) if key else [];ticker=self.match(tickers.get(p['asset_class'],{}),symbol,p.get('source_key'));r=self.analyze(symbol,candles,ticker,p['category'],p.get('quote_asset') or 'EUR')
    with self.db.con() as c:
     for x in candles:c.execute('INSERT OR REPLACE INTO ohlc_cache VALUES(?,?,?,?,?,?,?,?,?,?,?)',(symbol,interval,int(x[0]),str(x[1]),str(x[2]),str(x[3]),str(x[4]),str(x[5]),str(x[6]),int(x[7]),stamp))
   except Exception as exc:r={'symbol':symbol,'score':0,'signal':'AVOID','momentum_pct':None,'volatility_pct':None,'trend_pct':None,'spread_pct':None,'volume_quote':None,'data_points':0,'quality':'ERROR','reasons':[type(exc).__name__+': '+str(exc)[:180]]}
   counts['valid']+=r['quality']=='VALID';counts[r['signal'].lower()]+=1
   with self.db.con() as c:c.execute('INSERT OR REPLACE INTO scanner_results VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',(symbol,stamp,str(r['score']),r['signal'],*(None if r[k] is None else str(r[k]) for k in ('momentum_pct','volatility_pct','trend_pct','spread_pct','volume_quote')),r['data_points'],r['quality'],json.dumps(r['reasons'],ensure_ascii=False)))
   if delay:time.sleep(delay)
  quality='VALID' if symbols and counts['valid']==len(symbols) else 'INCOMPLETE'
  with self.db.con() as c:c.execute('INSERT INTO scanner_runs(created_at,symbols_requested,symbols_valid,buy_count,hold_count,avoid_count,quality) VALUES(?,?,?,?,?,?,?)',(stamp,len(symbols),counts['valid'],counts['buy'],counts['hold'],counts['avoid'],quality))
  self.db.audit('SCANNER_RUN',json.dumps({'requested':len(symbols),**counts,'quality':quality}));return self.db.rows('SELECT * FROM scanner_results ORDER BY CAST(score AS REAL) DESC')
