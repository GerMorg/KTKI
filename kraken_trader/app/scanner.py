import json,math,statistics,time,threading
from db import now
from market_history import MarketHistory
from strategy_profiles import active_profile,score_features,family_for_category
class MarketScanner:
 def __init__(self,db,client):self.db,self.client=db,client;self.lock=threading.Lock();self.ensure();self.history=MarketHistory(db);self.batch_offset=0
 def ensure(self):
  with self.db.con() as c:c.executescript("""CREATE TABLE IF NOT EXISTS scanner_results(symbol TEXT PRIMARY KEY,scanned_at TEXT NOT NULL,score TEXT NOT NULL,signal TEXT NOT NULL,momentum_pct TEXT,volatility_pct TEXT,trend_pct TEXT,spread_pct TEXT,volume_quote TEXT,data_points INTEGER NOT NULL,quality TEXT NOT NULL,reasons_json TEXT NOT NULL);CREATE TABLE IF NOT EXISTS ohlc_cache(symbol TEXT NOT NULL,interval_min INTEGER NOT NULL,open_time INTEGER NOT NULL,open TEXT NOT NULL,high TEXT NOT NULL,low TEXT NOT NULL,close TEXT NOT NULL,vwap TEXT,volume TEXT,trades INTEGER,received_at TEXT NOT NULL,PRIMARY KEY(symbol,interval_min,open_time));CREATE TABLE IF NOT EXISTS scanner_runs(id INTEGER PRIMARY KEY AUTOINCREMENT,created_at TEXT NOT NULL,symbols_requested INTEGER NOT NULL,symbols_valid INTEGER NOT NULL,buy_count INTEGER NOT NULL,hold_count INTEGER NOT NULL,avoid_count INTEGER NOT NULL,quality TEXT NOT NULL);""")
 def profile(self,symbol):
  try:r=self.db.rows('SELECT asset_class,category,quote_asset,source_key FROM market_universe WHERE symbol=? LIMIT 1',(symbol,))
  except Exception:r=[]
  return r[0] if r else {'asset_class':'currency','category':'crypto_spot','quote_asset':symbol.rsplit('/',1)[-1],'source_key':symbol}
 @staticmethod
 def match(payload,symbol,source_key=None):
  if not isinstance(payload,dict): return None
  wants={str(symbol).replace('/','').upper(),str(source_key or '').replace('/','').upper()};wants|={x.replace('BTC','XBT').replace('X','') for x in list(wants)}
  for entry in payload.items():
   key,value=entry[0],entry[1]
   compact=str(key).replace('/','').upper();variants={compact,compact.replace('X','').replace('Z','')}
   if any(w and (w in variants or w.replace('X','') in variants) for w in wants):return value if isinstance(value,dict) else None
  return next((v for v in payload.values() if isinstance(v,dict)),None) if len(payload)==1 else None
 @staticmethod
 def _ticker_dict(ticker):
  if isinstance(ticker,dict):return ticker
  if isinstance(ticker,list):
   for item in ticker:
    if isinstance(item,dict):return item
  return {}
 @staticmethod
 def _ohlc_rows(payload):
  if not isinstance(payload,dict):return []
  key=next((k for k in payload if k!='last'),None);rows=payload.get(key,[]) if key else []
  return rows if isinstance(rows,list) else []
 def analyze(self,symbol,candles,ticker,category='crypto_spot',quote='EUR'):
  committed=candles[:-1] if isinstance(candles,list) and len(candles)>1 else [];closes=[];volumes=[]
  for x in committed:
   if not isinstance(x,(list,tuple)) or len(x)<=6:continue
   try:
    close=float(x[4]);volume=float(x[6])
    if close>0:closes.append(close);volumes.append(volume)
   except (TypeError,ValueError):continue
  if len(closes)<30:return {'symbol':symbol,'score':0,'signal':'AVOID','momentum_pct':None,'volatility_pct':None,'trend_pct':None,'spread_pct':None,'volume_quote':None,'data_points':len(closes),'quality':'INSUFFICIENT','reasons':['Weniger als 30 abgeschlossene Kerzen']}
  returns=[closes[i]/closes[i-1]-1 for i in range(1,len(closes))];momentum=(closes[-1]/closes[-25]-1)*100;short=sum(closes[-10:])/10;long=sum(closes[-30:])/30;trend=(short/long-1)*100;volatility=statistics.pstdev(returns[-30:])*math.sqrt(24)*100;t=self._ticker_dict(ticker)
  def first(key):
   value=t.get(key,['0']) if isinstance(t,dict) else ['0'];return value[0] if isinstance(value,(list,tuple)) and value else value
  try:bid=float(first('b') or 0);ask=float(first('a') or 0)
  except (TypeError,ValueError):bid=ask=0
  mid=(bid+ask)/2;spread=(ask-bid)/mid*100 if mid else 999;volume_quote=sum(v*p for v,p in zip(volumes[-24:],closes[-24:]));family=family_for_category(category);profile_data=active_profile(self.db,family);version=profile_data[0] if isinstance(profile_data,(list,tuple)) and len(profile_data)>0 else 1;params=profile_data[1] if isinstance(profile_data,(list,tuple)) and len(profile_data)>1 and isinstance(profile_data[1],dict) else {};news_score=0.0
  if family=='forex':news_rows=self.db.rows('SELECT relevance FROM news_market_links WHERE symbol=?',(symbol,));news_score=min(10,sum(float(x['relevance']) for x in news_rows))
  features={'momentum_pct':momentum,'trend_pct':trend,'volatility_pct':volatility,'spread_pct':spread,'news_score':news_score};scored=score_features(features,params);score=scored[0] if isinstance(scored,(list,tuple)) and len(scored)>0 else 0;signal=scored[1] if isinstance(scored,(list,tuple)) and len(scored)>1 else 'HOLD';score=max(0,min(100,score));signal='BUY' if signal=='BUY' else ('AVOID' if signal=='AVOID' else 'HOLD');model=f'{family}-controlled-v{version}';aliases={'xstocks':f'xstocks-v1 / xstocks-approved-v{version}','forex':'forex-v1','crypto_spot':'crypto-v1'};reasons=[f'Modell {aliases.get(family,family)} / {model}',f'24h-Momentum {momentum:.2f} %',f'Trend SMA10/SMA30 {trend:.2f} %',f'Volatilität {volatility:.2f} %',f'Spread {spread:.3f} %',f'24h-Quotevolumen ca. {volume_quote:.2f} {quote}']
  return {'symbol':symbol,'score':round(score,4),'signal':signal,'momentum_pct':round(momentum,6),'volatility_pct':round(volatility,6),'trend_pct':round(trend,6),'spread_pct':round(spread,6),'volume_quote':round(volume_quote,4),'data_points':len(closes),'quality':'VALID','reasons':reasons}
 def run(self,symbols,interval=60,limit=None,delay_seconds=None):
  if not self.lock.acquire(False):return {'status':'BUSY','processed':0}
  all_symbols=list(dict.fromkeys(symbols));batch_size=int(limit or len(all_symbols) or 0);start=self.batch_offset%len(all_symbols) if all_symbols else 0;symbols=(all_symbols[start:start+batch_size] if start+batch_size<=len(all_symbols) else all_symbols[start:]+all_symbols[:(start+batch_size)%len(all_symbols)]);self.batch_offset=(start+len(symbols))%len(all_symbols) if all_symbols else 0;delay=float(delay_seconds if delay_seconds is not None else self.db.value('scanner_delay_seconds','1.05'));stamp=now();counts={'valid':0,'buy':0,'hold':0,'avoid':0}
  try:
   profiles={s:self.profile(s) for s in symbols};groups={}
   for s,p in profiles.items():groups.setdefault(p['asset_class'],[]).append(s)
   tickers={}
   for entry in groups.items():
    ac,batch=entry[0],entry[1]
    try:payload=self.client.ticker(batch,ac);tickers[ac]=payload if isinstance(payload,dict) else {}
    except Exception:
     tickers[ac]={}
     for symbol in batch:
      try:single=self.client.ticker([symbol],ac);tickers[ac].update(single if isinstance(single,dict) else {})
      except Exception as inner:self.history.ticker(symbol,ac,error=type(inner).__name__+': '+str(inner)[:160])
   for symbol in symbols:
    p=profiles[symbol]
    try:
     pair=p.get('source_key') or symbol
     try:payload=self.client.ohlc(pair,interval,p['asset_class'])
     except Exception:payload=self.client.ohlc(symbol,interval,p['asset_class']) if pair!=symbol else {}
     candles=self._ohlc_rows(payload);ticker=self.match(tickers.get(p['asset_class'],{}),symbol,p.get('source_key'));self.history.ticker(symbol,p['asset_class'],ticker or {});r=self.analyze(symbol,candles,ticker,p['category'],p.get('quote_asset') or 'EUR');self.history.ohlc(symbol,p['asset_class'],candles)
     with self.db.con() as c:
      for x in candles:
       if isinstance(x,(list,tuple)) and len(x)>=8:c.execute('INSERT OR REPLACE INTO ohlc_cache VALUES(?,?,?,?,?,?,?,?,?,?,?)',(symbol,interval,int(x[0]),str(x[1]),str(x[2]),str(x[3]),str(x[4]),str(x[5]),str(x[6]),int(x[7]),stamp))
    except Exception as exc:self.history.ohlc(symbol,p['asset_class'],error=type(exc).__name__+': '+str(exc)[:160]);r={'symbol':symbol,'score':0,'signal':'AVOID','momentum_pct':None,'volatility_pct':None,'trend_pct':None,'spread_pct':None,'volume_quote':None,'data_points':0,'quality':'ERROR','reasons':[type(exc).__name__+': '+str(exc)[:180]]}
    counts['valid']+=r['quality']=='VALID';counts[r['signal'].lower()]+=1
    with self.db.con() as c:c.execute('INSERT OR REPLACE INTO scanner_results VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',(symbol,stamp,str(r['score']),r['signal'],*(None if r[k] is None else str(r[k]) for k in ('momentum_pct','volatility_pct','trend_pct','spread_pct','volume_quote')),r['data_points'],r['quality'],json.dumps(r['reasons'],ensure_ascii=False)))
    if delay:time.sleep(delay)
   quality='VALID' if symbols and counts['valid']==len(symbols) else 'INCOMPLETE'
   with self.db.con() as c:c.execute('INSERT INTO scanner_runs(created_at,symbols_requested,symbols_valid,buy_count,hold_count,avoid_count,quality) VALUES(?,?,?,?,?,?,?)',(stamp,len(symbols),counts['valid'],counts['buy'],counts['hold'],counts['avoid'],quality))
   self.db.audit('SCANNER_RUN',json.dumps({'requested':len(symbols),**counts,'quality':quality}));return {'status':'COMPLETED','processed':len(symbols),'batch_start':start,'results':self.db.rows('SELECT * FROM scanner_results ORDER BY CAST(score AS REAL) DESC')}
  finally:self.lock.release()