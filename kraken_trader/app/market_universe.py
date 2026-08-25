import json
from db import now
CATEGORIES={'crypto_spot':('Kryptowährungen (Spot)','currency'),'xstocks':('xStocks / tokenisierte Aktien und ETFs','tokenized_asset'),'forex':('Devisen (Forex)','forex'),'leveraged_spot':('Hebelfähige Spot-Produkte','derived')}
def classify(pair,ac):
 if ac=='tokenized_asset':return 'xstocks'
 if ac=='forex':return 'forex'
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
  with self.db.con() as c:
   for key,(label,_) in CATEGORIES.items():c.execute('INSERT OR REPLACE INTO product_categories VALUES(?,?,?,?)',(key,label,1 if key in enabled else 0,now()))
 def enabled(self):return {x['category'] for x in self.categories() if x['enabled']}
 def sync(self):
  rows=[];members=[];errors=[];stamp=now()
  for ac in ('currency','tokenized_asset','forex'):
   try:pairs=self.client.pairs(ac)
   except Exception as exc:errors.append({'asset_class':ac,'error':type(exc).__name__});continue
   for source,p in pairs.items():
    symbol=p.get('wsname') or p.get('altname')
    if not symbol:continue
    cat=classify(p,ac);cats=[cat]
    if ac=='currency' and cat=='leveraged_spot':cats.append('crypto_spot')
    if ac=='tokenized_asset' and (p.get('leverage_buy') or p.get('leverage_sell')):cats.append('leveraged_spot')
    members.extend((symbol,ac,x) for x in cats);rows.append((symbol,ac,cat,p.get('base'),p.get('quote'),p.get('status'),str(p.get('ordermin')) if p.get('ordermin') is not None else None,str(p.get('costmin')) if p.get('costmin') is not None else None,p.get('lot_decimals'),p.get('pair_decimals'),json.dumps(p.get('leverage_buy') or []),json.dumps(p.get('leverage_sell') or []),source,stamp))
  if rows:
   with self.db.con() as c:c.executemany('INSERT OR REPLACE INTO market_universe VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)',rows);c.execute('DELETE FROM market_category_members');c.executemany('INSERT OR REPLACE INTO market_category_members VALUES(?,?,?)',members)
  enabled=self.enabled();count=len({(s,a) for s,a,c in members if c in enabled});quality='VALID' if rows and not errors else ('INCOMPLETE' if rows else 'ERROR')
  with self.db.con() as c:c.execute('INSERT INTO universe_sync_runs VALUES(NULL,?,?,?,?,?)',(stamp,len(rows),count,quality,json.dumps({'errors':errors})))
  return {'total':len(rows),'enabled':count,'quality':quality,'errors':errors}
 def symbols(self,quote='EUR'):
  enabled=self.enabled()
  if not enabled:return []
  marks=','.join('?'*len(enabled));rows=self.db.rows(f"SELECT DISTINCT u.symbol FROM market_universe u JOIN market_category_members m ON m.symbol=u.symbol AND m.asset_class=u.asset_class WHERE m.category IN ({marks}) AND u.status='online'",list(enabled));symbols=[x['symbol'] for x in rows]
  return sorted(x for x in set(symbols) if not quote or x.rsplit('/',1)[-1]==quote)
