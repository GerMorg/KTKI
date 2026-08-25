import json,math
from decimal import Decimal,InvalidOperation
from db import now
D=lambda x:Decimal(str(x or 0))
def chunks(xs,n=80):
 for i in range(0,len(xs),n):yield xs[i:i+n]
class MarketPrefilter:
 def __init__(self,db,client,news):self.db,self.client,self.news=db,client,news;self.ensure()
 def ensure(self):
  with self.db.con() as c:c.executescript("""CREATE TABLE IF NOT EXISTS prefilter_runs(id INTEGER PRIMARY KEY AUTOINCREMENT,created_at TEXT NOT NULL,status TEXT NOT NULL,market_count INTEGER NOT NULL,candidate_count INTEGER NOT NULL,news_items INTEGER NOT NULL,details_json TEXT NOT NULL);CREATE TABLE IF NOT EXISTS prefilter_results(run_id INTEGER NOT NULL,symbol TEXT NOT NULL,category TEXT NOT NULL,score TEXT NOT NULL,liquidity_score TEXT NOT NULL,spread_score TEXT NOT NULL,momentum_score TEXT NOT NULL,news_score TEXT NOT NULL,quality TEXT NOT NULL,reasons_json TEXT NOT NULL,PRIMARY KEY(run_id,symbol));CREATE TABLE IF NOT EXISTS research_watchlist(symbol TEXT PRIMARY KEY,category TEXT NOT NULL,prefilter_score TEXT NOT NULL,status TEXT NOT NULL,selected_at TEXT NOT NULL,run_id INTEGER NOT NULL,reasons_json TEXT NOT NULL);""")
 def markets(self):return self.db.rows("SELECT DISTINCT u.symbol,u.asset_class,u.base_asset,u.quote_asset,u.source_key,m.category FROM market_universe u JOIN market_category_members m ON m.symbol=u.symbol AND m.asset_class=u.asset_class JOIN product_categories c ON c.category=m.category AND c.enabled=1 WHERE u.status='online' AND u.symbol LIKE '%/EUR' ORDER BY u.symbol")
 def run(self,top_per_category=8):
  markets=self.markets();news_result=self.news.collect();self.news.link_markets(markets);tickers={};errors=[]
  byclass={}
  for m in markets:byclass.setdefault(m['asset_class'],[]).append(m['symbol'])
  for ac,syms in byclass.items():
   for block in chunks(syms):
    try:tickers.update(self.client.ticker(block,ac))
    except Exception as exc:errors.append({'asset_class':ac,'error':type(exc).__name__})
  stamp=now();rows=[]
  for m in markets:
   symbol=m['symbol'];t=tickers.get(m.get('source_key')) or tickers.get(symbol)
   if t is None:
    wanted=symbol.replace('BTC','XBT').replace('/','')
    for k,v in tickers.items():
     compact=k.replace('/','');reduced=compact.replace('X','').replace('Z','');wanted_reduced=wanted.replace('X','').replace('Z','')
     if wanted==compact or wanted in compact or wanted_reduced==reduced or wanted_reduced in reduced:t=v;break
   reasons=[];quality='VALID' if t else 'NO_TICKER';spread_score=momentum_score=liquidity_score=0.0
   if t:
    bid=float((t.get('b') or [0])[0] or 0);ask=float((t.get('a') or [0])[0] or 0);last=float((t.get('c') or [0])[0] or 0);openp=float(t.get('o') or 0);vol=float((t.get('v') or [0,0])[-1] or 0);mid=(bid+ask)/2;spread=(ask-bid)/mid*100 if mid else 999;change=(last/openp-1)*100 if openp else 0;turnover=max(0,vol*last)
    spread_score=max(0,35-min(35,spread*35));momentum_score=max(0,min(25,12.5+change*2));liquidity_score=max(0,min(30,math.log10(turnover+1)*5));reasons += [f'Spread {spread:.3f} %',f'24h-Veränderung {change:.2f} %',f'24h-Umsatzindikator {turnover:.2f}']
   newsrows=self.db.rows('SELECT relevance,reason FROM news_market_links WHERE symbol=?',(symbol,));news_score=min(10,sum(float(x['relevance']) for x in newsrows));reasons.append(f'Nachrichtenfilter {news_score:.2f}/10 aus {len(newsrows)} Zuordnungen')
   score=spread_score+momentum_score+liquidity_score+news_score;rows.append(dict(symbol=symbol,category=m['category'],score=round(score,4),liquidity=round(liquidity_score,4),spread=round(spread_score,4),momentum=round(momentum_score,4),news=round(news_score,4),quality=quality,reasons=reasons))
  valid=[x for x in rows if x['quality']=='VALID'];chosen=[]
  for cat in sorted({x['category'] for x in valid}):chosen += sorted([x for x in valid if x['category']==cat],key=lambda x:x['score'],reverse=True)[:top_per_category]
  with self.db.con() as c:
   cur=c.execute('INSERT INTO prefilter_runs(created_at,status,market_count,candidate_count,news_items,details_json) VALUES(?,?,?,?,?,?)',(stamp,'VALID' if valid else 'INCOMPLETE',len(markets),len(chosen),news_result['saved'],json.dumps({'ticker_errors':errors,'news_errors':news_result['errors']},ensure_ascii=False)));rid=cur.lastrowid
   c.executemany('INSERT INTO prefilter_results VALUES(?,?,?,?,?,?,?,?,?,?)',[(rid,x['symbol'],x['category'],str(x['score']),str(x['liquidity']),str(x['spread']),str(x['momentum']),str(x['news']),x['quality'],json.dumps(x['reasons'],ensure_ascii=False)) for x in rows])
   c.execute("UPDATE research_watchlist SET status='STALE'")
   c.executemany('INSERT OR REPLACE INTO research_watchlist VALUES(?,?,?,?,?,?,?)',[(x['symbol'],x['category'],str(x['score']),'PREFILTERED',stamp,rid,json.dumps(x['reasons'],ensure_ascii=False)) for x in chosen])
  self.db.audit('PREFILTER_RUN',json.dumps({'markets':len(markets),'valid':len(valid),'candidates':len(chosen),'run_id':rid},ensure_ascii=False));return {'run_id':rid,'markets':len(markets),'valid':len(valid),'candidates':len(chosen),'news_saved':news_result['saved'],'errors':errors+news_result['errors']}
 def candidates(self):return [x['symbol'] for x in self.db.rows("SELECT symbol FROM research_watchlist WHERE status IN ('PREFILTERED','ANALYZED') ORDER BY CAST(prefilter_score AS REAL) DESC")]
