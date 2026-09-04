import json,math
from db import now
from execution_costs import choose_execution_pair,ticker_item
from payload_utils import as_mapping

def chunks(xs,n=80):
 for i in range(0,len(xs),n):yield xs[i:i+n]

def merge_mapping(target,payload):
 if isinstance(payload,dict):target.update(payload);return
 if isinstance(payload,list):
  for item in payload:
   if isinstance(item,dict):target.update(item)

class MarketPrefilter:
 def __init__(self,db,client,news):self.db,self.client,self.news=db,client,news;self.ensure()
 def ensure(self):
  with self.db.con() as c:c.executescript("""CREATE TABLE IF NOT EXISTS prefilter_runs(id INTEGER PRIMARY KEY AUTOINCREMENT,created_at TEXT NOT NULL,status TEXT NOT NULL,market_count INTEGER NOT NULL,candidate_count INTEGER NOT NULL,news_items INTEGER NOT NULL,details_json TEXT NOT NULL);CREATE TABLE IF NOT EXISTS prefilter_results(run_id INTEGER NOT NULL,symbol TEXT NOT NULL,category TEXT NOT NULL,score TEXT NOT NULL,liquidity_score TEXT NOT NULL,spread_score TEXT NOT NULL,momentum_score TEXT NOT NULL,news_score TEXT NOT NULL,quality TEXT NOT NULL,reasons_json TEXT NOT NULL,PRIMARY KEY(run_id,symbol));CREATE TABLE IF NOT EXISTS research_watchlist(symbol TEXT PRIMARY KEY,category TEXT NOT NULL,prefilter_score TEXT NOT NULL,status TEXT NOT NULL,selected_at TEXT NOT NULL,run_id INTEGER NOT NULL,reasons_json TEXT NOT NULL);CREATE TABLE IF NOT EXISTS watchlist_versions(id INTEGER PRIMARY KEY AUTOINCREMENT,created_at TEXT NOT NULL,prefilter_run_id INTEGER NOT NULL,status TEXT NOT NULL,item_count INTEGER NOT NULL,items_json TEXT NOT NULL);""")
 def markets(self):
  primary=self.db.rows("SELECT u.symbol,u.asset_class,u.base_asset,u.quote_asset,u.source_key,u.category AS primary_category,m.category,u.canonical_id FROM market_universe u JOIN market_category_members m ON m.symbol=u.symbol AND m.asset_class=u.asset_class JOIN product_categories c ON c.category=m.category AND c.enabled=1 WHERE LOWER(COALESCE(u.status,'online')) IN ('online','post_only','limit_only') AND (u.symbol LIKE '%/EUR' OR u.symbol LIKE '%/USD') ORDER BY u.symbol")
  if not primary:
   primary=self.db.rows("SELECT symbol,asset_class,base_asset,quote_asset,source_key,category AS primary_category,category,canonical_id FROM market_universe WHERE LOWER(COALESCE(status,'online')) IN ('online','post_only','limit_only') AND (symbol LIKE '%/EUR' OR symbol LIKE '%/USD') ORDER BY symbol")
  priority={'xstocks':0,'forex':1,'crypto_spot':2,'leveraged_spot':3};by_symbol={}
  for row in primary:
   cur=by_symbol.get(row['symbol'])
   if cur is None or priority.get(row['category'],99)<priority.get(cur['category'],99):by_symbol[row['symbol']]=row
  return [by_symbol[x] for x in sorted(by_symbol)]
 def _cached_ticker(self,symbol):
  rows=self.db.rows('SELECT last,bid,ask,change_pct,received_at FROM live_prices WHERE symbol=?',(symbol,))
  if not rows:return None
  row=rows[0];last=float(row.get('last') or 0)
  if last<=0:return None
  bid=float(row.get('bid') or last);ask=float(row.get('ask') or last);change=float(row.get('change_pct') or 0);openp=last/(1+change/100) if 1+change/100 else last
  return {'b':[str(bid)],'a':[str(ask)],'c':[str(last)],'o':str(openp),'v':['0','0'],'_cached':True}
 def _canonical_markets(self,markets,tickers):
  groups={}
  for market in markets:groups.setdefault(market.get('canonical_id') or market['asset_class']+':'+str(market.get('base_asset')),[]).append(market)
  out=[];trade_fee=self.db.value('paper_fee_bps','40');fx_fee=self.db.value('paper_fx_fee_bps','10');slippage=self.db.value('paper_slippage_bps','10')
  for cid,alternatives in groups.items():
   choice=choose_execution_pair(alternatives,tickers,trade_fee,fx_fee,slippage)
   if not isinstance(choice,(list,tuple)) or len(choice)!=3:continue
   chosen,costs,ranking=choice
   if not isinstance(chosen,dict):continue
   chosen=dict(chosen);chosen['alternatives']=[x['symbol'] for x in alternatives if isinstance(x,dict) and x.get('symbol')];chosen['execution_costs']=costs if isinstance(costs,dict) else {};chosen['pair_ranking']=ranking if isinstance(ranking,list) else [];out.append(chosen)
   with self.db.con() as c:c.execute('UPDATE canonical_products SET selected_symbol=?,alternatives_json=?,updated_at=? WHERE canonical_id=?',(chosen['symbol'],json.dumps({'pairs':chosen['alternatives'],'ranking':chosen['pair_ranking']},ensure_ascii=False,sort_keys=True),now(),cid))
  return sorted(out,key=lambda x:x.get('symbol',''))
 def run(self,top=8):
  markets=self.markets();nr=as_mapping(self.news.collect(),{'saved':0,'errors':[]});self.news.link_markets(markets);tickers={};errors=[]
  groups={}
  for m in markets:groups.setdefault(m['asset_class'],[]).append(m['symbol'])
  if any(m['symbol'].endswith('/USD') for m in markets):groups.setdefault('forex',[]).append('EUR/USD')
  for ac,syms in groups.items():
   for block in chunks(syms):
    try:merge_mapping(tickers,self.client.ticker(block,ac))
    except Exception as exc:
     errors.append({'source':ac,'scope':'batch','error':type(exc).__name__})
     for pair in block:
      try:merge_mapping(tickers,self.client.ticker([pair],ac))
      except Exception as one:errors.append({'source':ac,'scope':pair,'error':type(one).__name__})
  markets=self._canonical_markets(markets,tickers)
  rows=[];stamp=now();seen=set()
  for m in markets:
   symbol=m['symbol']
   if symbol in seen:continue
   seen.add(symbol);t=ticker_item(tickers,m) or self._cached_ticker(symbol);cached=isinstance(t,dict) and bool(t.get('_cached'))
   liq=spread_s=mom=0.;quality='VALID' if isinstance(t,dict) else 'PENDING_TICKER';reasons=['Kanonisches Produkt; Alternativen: '+', '.join(m.get('alternatives',[]))]
   if isinstance(t,dict):
    bid=float((t.get('b') or [0])[0] or 0);ask=float((t.get('a') or [0])[0] or 0);last=float((t.get('c') or [0])[0] or 0);op=float(t.get('o') or 0);vol=float((t.get('v') or [0,0])[-1] or 0);mid=(bid+ask)/2 if bid>0 and ask>0 else 0;valid_quote=last>0 and mid>0 and ask>=bid>0
    sp=(ask-bid)/mid*100 if valid_quote else 999;chg=(last/op-1)*100 if op>0 and last>0 else 0;turn=max(0,vol*last);spread_s=max(0,min(35,35-max(0,sp)*35));mom=max(0,min(25,12.5+chg*2));liq=max(0,min(30,math.log10(turn+1)*5));costs=m.get('execution_costs') or {}
    if not valid_quote:
     quality='INVALID_QUOTE';spread_s=0;reasons.append('Ungültiger oder gekreuzter Bid/Ask-Quote verworfen')
    else:quality='CACHED' if cached else 'VALID'
    reasons+=(['Verwendeter Preis stammt aus dem lokalen Live-Preis-Cache'] if cached else []);reasons+=['Ausführungskosten gesamt '+str(round(float(costs.get('total_rate',999))*100,4))+' %',f'Spread {sp:.3f} %',f'24h-Veränderung {chg:.2f} %',f'Umsatzindikator {turn:.2f}']
   if not isinstance(t,dict):reasons.append('Kein aktueller Ticker verfügbar; Markt bleibt sichtbar, wird aber nicht als echter Prefilter-Kandidat gewählt')
   nl=self.db.rows('SELECT relevance FROM news_market_links WHERE symbol=?',(symbol,));news=max(0,min(10,sum(float(x['relevance']) for x in nl)));reasons.append(f'Nachrichten {news:.2f}/10 aus {len(nl)} Zuordnungen');score=max(0,min(100,liq+spread_s+mom+news));rows.append({'symbol':symbol,'category':m['category'],'score':round(score,4),'liq':liq,'spread':spread_s,'mom':mom,'news':news,'quality':quality,'reasons':reasons})
  valid=[x for x in rows if x['quality'] in ('VALID','CACHED')];chosen=[]
  for cat in sorted({x['category'] for x in rows}):
   pool=sorted([x for x in rows if x['category']==cat and x['quality'] in ('VALID','CACHED')],key=lambda x:x['score'],reverse=True);chosen+=pool[:top]
  status='VALID' if valid and not errors else ('VALID_WITH_WARNINGS' if rows else 'INCOMPLETE')
  with self.db.con() as c:
   cur=c.execute('INSERT INTO prefilter_runs VALUES(NULL,?,?,?,?,?,?)',(stamp,status,len(markets),len(chosen),int(nr.get('saved',0) or 0),json.dumps({'errors':errors+list(nr.get('errors',[]) or [])},ensure_ascii=False)));rid=cur.lastrowid
   c.executemany('INSERT INTO prefilter_results(run_id,symbol,category,score,liquidity_score,spread_score,momentum_score,news_score,quality,reasons_json) VALUES(?,?,?,?,?,?,?,?,?,?) ON CONFLICT(run_id,symbol) DO UPDATE SET category=excluded.category,score=excluded.score,liquidity_score=excluded.liquidity_score,spread_score=excluded.spread_score,momentum_score=excluded.momentum_score,news_score=excluded.news_score,quality=excluded.quality,reasons_json=excluded.reasons_json',[(rid,x['symbol'],x['category'],str(x['score']),str(x['liq']),str(x['spread']),str(x['mom']),str(x['news']),x['quality'],json.dumps(x['reasons'],ensure_ascii=False)) for x in rows]);c.execute("UPDATE research_watchlist SET status='STALE'");c.executemany('INSERT OR REPLACE INTO research_watchlist VALUES(?,?,?,?,?,?,?)',[(x['symbol'],x['category'],str(x['score']),'PREFILTERED',stamp,rid,json.dumps(x['reasons'],ensure_ascii=False)) for x in chosen]);c.execute('INSERT INTO watchlist_versions VALUES(NULL,?,?,?,?,?)',(stamp,rid,'CREATED',len(chosen),json.dumps(chosen,ensure_ascii=False)))
  return {'run_id':rid,'markets':len(markets),'valid':len(valid),'pending_ticker':sum(x['quality']=='PENDING_TICKER' for x in rows),'invalid_quote':sum(x['quality']=='INVALID_QUOTE' for x in rows),'cached':sum(x['quality']=='CACHED' for x in rows),'candidates':len(chosen),'errors':errors+list(nr.get('errors',[]) or [])}
 def candidates(self):return [x['symbol'] for x in self.db.rows("SELECT symbol FROM research_watchlist WHERE status IN ('PREFILTERED','ANALYZED') ORDER BY CAST(prefilter_score AS REAL) DESC")]
