import json
from db import now
from product_identity import canonical_product_id,is_traditional_stock
FIAT={'EUR','USD','GBP','CHF','JPY','CAD','AUD','NZD'}
CATEGORIES={'crypto_spot':('Kryptowährungen (Spot)','currency'),'xstocks':('xStocks / tokenisierte Aktien und ETFs','tokenized_asset'),'forex':('Devisen (Forex)','forex'),'leveraged_spot':('Hebelfähige Spot-Produkte','derived')}
def classify(pair,ac):
 if ac=='tokenized_asset':return 'xstocks'
 if ac=='forex' or (str(pair.get('base')) in FIAT and str(pair.get('quote')) in FIAT):return 'forex'
 if pair.get('leverage_buy') or pair.get('leverage_sell'):return 'leveraged_spot'
 return 'crypto_spot'
class MarketUniverse:
 def __init__(self,db,client):self.db,self.client=db,client;self.ensure()
 def ensure(self):
  with self.db.con() as c:
   c.executescript("""CREATE TABLE IF NOT EXISTS product_categories(category TEXT PRIMARY KEY,label TEXT NOT NULL,enabled INTEGER NOT NULL,updated_at TEXT NOT NULL);CREATE TABLE IF NOT EXISTS market_universe(symbol TEXT NOT NULL,asset_class TEXT NOT NULL,category TEXT NOT NULL,base_asset TEXT,quote_asset TEXT,status TEXT,ordermin TEXT,costmin TEXT,lot_decimals INTEGER,pair_decimals INTEGER,leverage_buy_json TEXT NOT NULL,leverage_sell_json TEXT NOT NULL,source_key TEXT NOT NULL,updated_at TEXT NOT NULL,canonical_id TEXT,product_kind TEXT,metadata_json TEXT NOT NULL DEFAULT '{}',PRIMARY KEY(symbol,asset_class));CREATE TABLE IF NOT EXISTS market_category_members(symbol TEXT NOT NULL,asset_class TEXT NOT NULL,category TEXT NOT NULL,PRIMARY KEY(symbol,asset_class,category));CREATE TABLE IF NOT EXISTS universe_sync_runs(id INTEGER PRIMARY KEY AUTOINCREMENT,created_at TEXT NOT NULL,total_markets INTEGER NOT NULL,enabled_markets INTEGER NOT NULL,quality TEXT NOT NULL,details_json TEXT NOT NULL);""")
   cols={x['name'] for x in self.db.rows('PRAGMA table_info(market_universe)')}
   for name,definition in [('canonical_id','TEXT'),('product_kind','TEXT'),('metadata_json',"TEXT NOT NULL DEFAULT '{}'")]:
    if name not in cols:c.execute(f'ALTER TABLE market_universe ADD COLUMN {name} {definition}')
   c.executescript("""CREATE TABLE IF NOT EXISTS canonical_products(canonical_id TEXT PRIMARY KEY,asset_class TEXT NOT NULL,base_asset TEXT,category TEXT NOT NULL,selected_symbol TEXT,alternatives_json TEXT NOT NULL,updated_at TEXT NOT NULL);CREATE TABLE IF NOT EXISTS universe_api_metadata(id INTEGER PRIMARY KEY AUTOINCREMENT,created_at TEXT NOT NULL,asset_class TEXT NOT NULL,source_key TEXT NOT NULL,payload_json TEXT NOT NULL);""")
   for key,(label,_) in CATEGORIES.items():c.execute('INSERT OR IGNORE INTO product_categories VALUES(?,?,0,?)',(key,label,now()))
 def categories(self):return self.db.rows('SELECT * FROM product_categories ORDER BY category')
 def set_categories(self,enabled):
  with self.db.con() as c:
   cols={x['name'] for x in self.db.rows('PRAGMA table_info(market_universe)')}
   for name,definition in [('canonical_id','TEXT'),('product_kind','TEXT'),('metadata_json',"TEXT NOT NULL DEFAULT '{}'")]:
    if name not in cols:c.execute(f'ALTER TABLE market_universe ADD COLUMN {name} {definition}')
   c.executescript("""CREATE TABLE IF NOT EXISTS canonical_products(canonical_id TEXT PRIMARY KEY,asset_class TEXT NOT NULL,base_asset TEXT,category TEXT NOT NULL,selected_symbol TEXT,alternatives_json TEXT NOT NULL,updated_at TEXT NOT NULL);CREATE TABLE IF NOT EXISTS universe_api_metadata(id INTEGER PRIMARY KEY AUTOINCREMENT,created_at TEXT NOT NULL,asset_class TEXT NOT NULL,source_key TEXT NOT NULL,payload_json TEXT NOT NULL);""")
   for key,(label,_) in CATEGORIES.items():c.execute('INSERT OR REPLACE INTO product_categories VALUES(?,?,?,?)',(key,label,1 if key in enabled else 0,now()))
 def enabled(self):return {x['category'] for x in self.categories() if x['enabled']}
 def sync(self):
  rows=[];members=[];errors=[];stamp=now()
  for ac in ('currency','tokenized_asset','forex'):
   try:pairs=self.client.pairs(ac)
   except Exception as exc:errors.append({'asset_class':ac,'error':type(exc).__name__});continue
   for source,pair in pairs.items():
    if ac=='currency' and classify(pair,ac)=='forex':continue
    symbol=pair.get('wsname') or pair.get('altname')
    if not symbol:continue
    if is_traditional_stock(ac):
     with self.db.con() as c:c.execute('INSERT INTO universe_api_metadata(created_at,asset_class,source_key,payload_json) VALUES(?,?,?,?)',(stamp,ac,source,json.dumps(pair,ensure_ascii=False,sort_keys=True)))
     continue
    cat=classify(pair,ac);cats=[cat]
    if ac=='currency' and cat=='leveraged_spot':cats.append('crypto_spot')
    if ac=='tokenized_asset' and (pair.get('leverage_buy') or pair.get('leverage_sell')):cats.append('leveraged_spot')
    cid=canonical_product_id(ac,pair.get('base') or symbol.split('/')[0],cat);kind='xstock' if ac=='tokenized_asset' else ('forex' if ac=='forex' else cat)
    members.extend((symbol,ac,x) for x in cats)
    rows.append((symbol,ac,cat,pair.get('base'),pair.get('quote'),pair.get('status'),str(pair.get('ordermin')) if pair.get('ordermin') is not None else None,str(pair.get('costmin')) if pair.get('costmin') is not None else None,pair.get('lot_decimals'),pair.get('pair_decimals'),json.dumps(pair.get('leverage_buy') or []),json.dumps(pair.get('leverage_sell') or []),source,stamp,cid,kind,json.dumps(pair,ensure_ascii=False,sort_keys=True)))
  if rows:
   with self.db.con() as c:
    c.execute("DELETE FROM market_universe WHERE asset_class IN ('currency','tokenized_asset','forex')")
    c.execute('DELETE FROM universe_api_metadata')
    c.executemany('INSERT INTO universe_api_metadata(created_at,asset_class,source_key,payload_json) VALUES(?,?,?,?)',[(stamp,r[1],r[12],r[16]) for r in rows])
    c.executemany('INSERT OR REPLACE INTO market_universe(symbol,asset_class,category,base_asset,quote_asset,status,ordermin,costmin,lot_decimals,pair_decimals,leverage_buy_json,leverage_sell_json,source_key,updated_at,canonical_id,product_kind,metadata_json) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',rows)
    c.execute('DELETE FROM market_category_members');c.executemany('INSERT OR REPLACE INTO market_category_members VALUES(?,?,?)',members);c.execute('DELETE FROM canonical_products')
    grouped={}
    for r in rows:grouped.setdefault(r[14],[]).append({'symbol':r[0],'quote_asset':r[4],'source_key':r[12],'asset_class':r[1],'category':r[2]})
    for cid,alts in grouped.items():
     base=next((r[3] for r in rows if r[14]==cid),None);c.execute('INSERT INTO canonical_products VALUES(?,?,?,?,?,?,?)',(cid,alts[0]['asset_class'],base,alts[0]['category'],None,json.dumps(alts,ensure_ascii=False,sort_keys=True),stamp))
  enabled=self.enabled();count=len({(s,a) for s,a,c in members if c in enabled});quality='VALID' if rows and not errors else ('INCOMPLETE' if rows else 'ERROR')
  with self.db.con() as c:c.execute('INSERT INTO universe_sync_runs VALUES(NULL,?,?,?,?,?)',(stamp,len(rows),count,quality,json.dumps({'errors':errors})))
  return {'total':len(rows),'enabled':count,'quality':quality,'errors':errors}
 def symbols(self,quote='EUR'):
  enabled=self.enabled()
  if not enabled:return []
  marks=','.join('?'*len(enabled));rows=self.db.rows(f"SELECT DISTINCT u.symbol FROM market_universe u JOIN market_category_members m ON m.symbol=u.symbol AND m.asset_class=u.asset_class WHERE m.category IN ({marks}) AND LOWER(COALESCE(u.status,'online')) IN ('online','post_only','limit_only')",list(enabled));symbols=[x['symbol'] for x in rows]
  return sorted(x for x in set(symbols) if not quote or x.rsplit('/',1)[-1]==quote)


