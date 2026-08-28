import json,math,statistics
from db import now
SAFE={'USD':1.0,'CHF':0.9,'JPY':0.8,'EUR':0.4,'GBP':0.2,'CAD':0.1,'AUD':-0.2,'NZD':-0.3}
class ForexShadow:
 def __init__(self,db):self.db=db;self.ensure()
 def ensure(self):
  with self.db.con() as c:c.executescript("""CREATE TABLE IF NOT EXISTS forex_feature_snapshots(id INTEGER PRIMARY KEY AUTOINCREMENT,created_at TEXT NOT NULL,symbol TEXT NOT NULL,model_version TEXT NOT NULL,horizon TEXT NOT NULL,features_json TEXT NOT NULL,score TEXT NOT NULL,signal TEXT NOT NULL,quality TEXT NOT NULL,reasons_json TEXT NOT NULL);CREATE TABLE IF NOT EXISTS forex_shadow_comparisons(id INTEGER PRIMARY KEY AUTOINCREMENT,created_at TEXT NOT NULL,symbol TEXT NOT NULL,active_model TEXT NOT NULL,active_score TEXT NOT NULL,active_signal TEXT NOT NULL,candidate_model TEXT NOT NULL,candidate_score TEXT NOT NULL,candidate_signal TEXT NOT NULL,disagrees INTEGER NOT NULL,snapshot_id INTEGER NOT NULL);""")
 def _currency_strength(self,currency):
  rows=self.db.rows("SELECT symbol,change_pct FROM live_prices WHERE symbol LIKE ? OR symbol LIKE ?",(currency+'/%','%/'+currency));vals=[]
  for x in rows:
   try:v=float(x.get('change_pct') or 0)
   except ValueError:continue
   vals.append(v if x['symbol'].startswith(currency+'/') else -v)
  return sum(vals)/len(vals) if vals else 0.0
 def score(self,symbol,active):
  base,quote=(symbol.split('/')+[''])[:2];reasons=json.loads(active.get('reasons_json') or '[]');momentum=float(active.get('momentum_pct') or 0);trend=float(active.get('trend_pct') or 0);vol=float(active.get('volatility_pct') or 0);spread=float(active.get('spread_pct') or 999)
  bs=self._currency_strength(base);qs=self._currency_strength(quote);relative=bs-qs;risk_regime=max(-1,min(1,(SAFE.get(base,0)-SAFE.get(quote,0))))
  horizons={'short':momentum,'medium':trend};out=[]
  linked=self.db.rows('SELECT COUNT(*) n,COALESCE(SUM(CAST(relevance AS REAL)),0) relevance FROM news_market_links WHERE symbol=?',(symbol,));news_count=int(linked[0]['n']) if linked else 0;news_relevance=float(linked[0]['relevance']) if linked else 0
  for horizon,hvalue in horizons.items():
   score=50+max(-18,min(18,hvalue*(4 if horizon=='short' else 8)))+max(-15,min(15,relative*3))+risk_regime*4-max(0,min(16,vol))-max(0,min(22,spread*28))+min(8,news_relevance)
   score=max(0,min(100,score));signal='BUY' if score>=65 and spread<=.7 else ('AVOID' if score<35 or spread>1.3 else 'HOLD');quality='VALID' if active.get('quality')=='VALID' and spread<999 else 'INCOMPLETE'
   features={'schema_version':1,'base_currency':base,'quote_currency':quote,'relative_strength':relative,'base_strength':bs,'quote_strength':qs,'momentum_pct':momentum,'trend_pct':trend,'volatility_pct':vol,'spread_pct':spread,'risk_safe_haven_regime':risk_regime,'linked_news_count':news_count,'linked_news_relevance':news_relevance,'interest_differential':None,'inflation_growth_differential':None,'central_bank_surprise':None,'missing_features':['interest_differential','inflation_growth_differential','central_bank_surprise']}
   why=['forex-v2 shadow, keine Handelswirkung',f'Relative Währungsstärke {relative:.4f}',f'Risiko-/Safe-Haven-Regime {risk_regime:.2f}',f'Zeithorizont {horizon}',f'Paarbezogene Nachrichten {news_count}']
   with self.db.con() as c:
    cur=c.execute('INSERT INTO forex_feature_snapshots(created_at,symbol,model_version,horizon,features_json,score,signal,quality,reasons_json) VALUES(?,?,?,?,?,?,?,?,?)',(now(),symbol,'forex-v2-shadow',horizon,json.dumps(features,sort_keys=True),str(round(score,4)),signal,quality,json.dumps(why,ensure_ascii=False)));sid=cur.lastrowid
    c.execute('INSERT INTO forex_shadow_comparisons(created_at,symbol,active_model,active_score,active_signal,candidate_model,candidate_score,candidate_signal,disagrees,snapshot_id) VALUES(?,?,?,?,?,?,?,?,?,?)',(now(),symbol,'forex-v1',str(active.get('score') or 0),active.get('signal') or 'AVOID','forex-v2-shadow',str(round(score,4)),signal,1 if signal!=(active.get('signal') or 'AVOID') else 0,sid))
   out.append({'horizon':horizon,'score':score,'signal':signal,'quality':quality})
  return out
 def run(self,symbols=None):
  query="SELECT s.* FROM scanner_results s JOIN market_universe u ON u.symbol=s.symbol WHERE u.category='forex'";rows=self.db.rows(query);wanted=set(symbols or [])
  results=[]
  for row in rows:
   if wanted and row['symbol'] not in wanted:continue
   results.extend([dict(x,symbol=row['symbol']) for x in self.score(row['symbol'],row)])
  self.db.audit('FOREX_V2_SHADOW_RUN',json.dumps({'snapshots':len(results),'symbols':len(set(x['symbol'] for x in results))}));return {'status':'SHADOW_ONLY','snapshots':len(results),'symbols':len(set(x['symbol'] for x in results))}
 def comparisons(self):return self.db.rows('SELECT * FROM forex_shadow_comparisons ORDER BY id DESC LIMIT 200')



