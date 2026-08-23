import json
from db import now
CATEGORIES={
 'crypto_spot':('Kryptowährungen (Spot)','currency'),
 'xstocks':('xStocks / tokenisierte Aktien und ETFs','tokenized_asset'),
 'forex':('Devisen (Forex)','forex'),
 'leveraged_spot':('Hebelfähige Spot-Produkte','derived'),
}
def classify(pair,asset_class):
 if asset_class=='tokenized_asset':return 'xstocks'
 if asset_class=='forex':return 'forex'
 if pair.get('leverage_buy') or pair.get('leverage_sell'):return 'leveraged_spot'
 return 'crypto_spot'
class MarketUniverse:
 def __init__(self,db,client):self.db,self.client=db,client;self.ensure()
 def ensure(self):
  with self.db.con() as c:
   c.executescript("""CREATE TABLE IF NOT EXISTS product_categories(category TEXT PRIMARY KEY,label TEXT NOT NULL,enabled INTEGER NOT NULL,updated_at TEXT NOT NULL);CREATE TABLE IF NOT EXISTS market_universe(symbol TEXT NOT NULL,asset_class TEXT NOT NULL,category TEXT NOT NULL,base_asset TEXT,quote_asset TEXT,status TEXT,ordermin TEXT,costmin TEXT,lot_decimals INTEGER,pair_decimals INTEGER,leverage_buy_json TEXT NOT NULL,leverage_sell_json TEXT NOT NULL,source_key TEXT NOT NULL,updated_at TEXT NOT NULL,PRIMARY KEY(symbol,asset_class));CREATE TABLE IF NOT EXISTS market_category_members(symbol TEXT NOT NULL,asset_class TEXT NOT NULL,category TEXT NOT NULL,PRIMARY KEY(symbol,asset_class,category));CREATE TABLE IF NOT EXISTS universe_sync_runs(id INTEGER PRIMARY KEY AUTOINCREMENT,created_at TEXT NOT NULL,total_markets INTEGER NOT NULL,enabled_markets INTEGER NOT NULL,quality TEXT NOT NULL,details_json TEXT NOT NULL);""")
   for key,(label,_) in CATEGORIES.items():c.execute('INSERT OR IGNORE INTO product_categories VALUES(?,?,0,?)',(key,label,now()))
 def categories(self):return self.db.rows('SELECT * FROM product_categories ORDER BY category')
 def set_categories(self,enabled):
  stamp=now()
  with self.db.con() as c:
   for key,(label,_) in CATEGORIES.items():c.execute('INSERT OR REPLACE INTO product_categories VALUES(?,?,?,?)',(key,label,1 if key in enabled else 0,stamp))
  self.db.audit('PRODUCT_CATEGORIES_CHANGED',json.dumps({'enabled':sorted(enabled)},ensure_ascii=False))
 def enabled(self):return {x['category'] for x in self.categories() if x['enabled']}
 def sync(self):
  stamp=now();all_rows=[];members=[];errors=[]
  for asset_class in ('currency','tokenized_asset','forex'):
   try:pairs=self.client.pairs(asset_class)
   except Exception as exc:errors.append({'asset_class':asset_class,'error':type(exc).__name__});continue
   for source_key,p in pairs.items():
    symbol=p.get('wsname') or p.get('altname')
    if not symbol:continue
    category=classify(p,asset_class)
    memberships=[category]
    if asset_class=='currency' and category=='leveraged_spot':memberships.append('crypto_spot')
    if asset_class=='tokenized_asset' and (p.get('leverage_buy') or p.get('leverage_sell')):memberships.append('leveraged_spot')
    members.extend((symbol,asset_class,x) for x in memberships)
    all_rows.append((symbol,asset_class,category,p.get('base'),p.get('quote'),p.get('status'),str(p.get('ordermin')) if p.get('ordermin') is not None else None,str(p.get('costmin')) if p.get('costmin') is not None else None,p.get('lot_decimals'),p.get('pair_decimals'),json.dumps(p.get('leverage_buy') or []),json.dumps(p.get('leverage_sell') or []),source_key,stamp))
  if all_rows:
   with self.db.con() as c:
    c.executemany('INSERT OR REPLACE INTO market_universe VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)',all_rows);c.execute('DELETE FROM market_category_members');c.executemany('INSERT OR REPLACE INTO market_category_members VALUES(?,?,?)',members)
  enabled=self.enabled();enabled_count=len({(s,a) for s,a,c in members if c in enabled});quality='VALID' if all_rows and not errors else ('INCOMPLETE' if all_rows else 'ERROR')
  with self.db.con() as c:c.execute('INSERT INTO universe_sync_runs(created_at,total_markets,enabled_markets,quality,details_json) VALUES(?,?,?,?,?)',(stamp,len(all_rows),enabled_count,quality,json.dumps({'errors':errors},ensure_ascii=False)))
  self.db.audit('MARKET_UNIVERSE_SYNC',json.dumps({'total':len(all_rows),'enabled':enabled_count,'quality':quality},ensure_ascii=False));return {'total':len(all_rows),'enabled':enabled_count,'quality':quality,'errors':errors}
 def symbols(self,quote='EUR'):
  enabled=self.enabled()
  if not enabled:return []
  marks=','.join('?'*len(enabled));params=list(sorted(enabled))
  q=f"SELECT DISTINCT u.symbol FROM market_universe u JOIN market_category_members m ON m.symbol=u.symbol AND m.asset_class=u.asset_class WHERE m.category IN ({marks}) AND u.status='online'"
  rows=self.db.rows(q,params)
  symbols=[x['symbol'] for x in rows]
  if quote:symbols=[x for x in symbols if x.rsplit('/',1)[-1]==quote]
  return sorted(set(symbols))
