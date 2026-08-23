import json,sqlite3
from datetime import datetime,timezone
def now():return datetime.now(timezone.utc).isoformat()
class DB:
 def __init__(self,path):self.path=path
 def con(self):
  c=sqlite3.connect(self.path);c.row_factory=sqlite3.Row;return c
 def init(self,start=1000):
  with self.con() as c:
   c.executescript("""CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY,value TEXT NOT NULL);CREATE TABLE IF NOT EXISTS balances(asset TEXT PRIMARY KEY,amount TEXT NOT NULL,updated_at TEXT NOT NULL);CREATE TABLE IF NOT EXISTS paper_balances(asset TEXT PRIMARY KEY,amount TEXT NOT NULL,updated_at TEXT NOT NULL);CREATE TABLE IF NOT EXISTS ledger(id TEXT PRIMARY KEY,payload TEXT NOT NULL,occurred_at REAL,imported_at TEXT NOT NULL);CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY AUTOINCREMENT,created_at TEXT NOT NULL,event TEXT NOT NULL,level TEXT NOT NULL,details TEXT NOT NULL);CREATE TABLE IF NOT EXISTS allowlist(symbol TEXT PRIMARY KEY,enabled INTEGER NOT NULL);CREATE TABLE IF NOT EXISTS portfolio_assets(asset TEXT PRIMARY KEY,display_name TEXT,amount TEXT NOT NULL,eur_price TEXT,eur_value TEXT,classification TEXT NOT NULL,ever_held INTEGER NOT NULL,updated_at TEXT NOT NULL);CREATE TABLE IF NOT EXISTS portfolio_snapshots(id INTEGER PRIMARY KEY AUTOINCREMENT,created_at TEXT NOT NULL,total_eur TEXT,priced_asset_count INTEGER NOT NULL,unpriced_asset_count INTEGER NOT NULL,quality TEXT NOT NULL);CREATE TABLE IF NOT EXISTS portfolio_snapshot_items(snapshot_id INTEGER NOT NULL,asset TEXT NOT NULL,amount TEXT NOT NULL,eur_price TEXT,eur_value TEXT,classification TEXT NOT NULL,PRIMARY KEY(snapshot_id,asset));""")
   c.execute("INSERT OR IGNORE INTO settings VALUES('automation_enabled','false')");c.execute("INSERT OR IGNORE INTO settings VALUES('kraken_status','not_checked')");c.execute("INSERT OR IGNORE INTO settings VALUES('websocket_status','not_checked')");c.execute("INSERT OR IGNORE INTO paper_balances VALUES('EUR',?,?)",(str(start),now()))
 def rows(self,q,p=()):
  with self.con() as c:return [dict(x) for x in c.execute(q,p).fetchall()]
 def value(self,k,d=''):
  r=self.rows('SELECT value FROM settings WHERE key=?',(k,));return r[0]['value'] if r else d
 def set(self,k,v):
  with self.con() as c:c.execute('INSERT OR REPLACE INTO settings VALUES(?,?)',(k,str(v)))
 def audit(self,e,d='',level='info'):
  with self.con() as c:c.execute('INSERT INTO audit(created_at,event,level,details) VALUES(?,?,?,?)',(now(),e,level,d))
 def replace_balances(self,items):
  with self.con() as c:
   c.execute('DELETE FROM balances');c.executemany('INSERT INTO balances VALUES(?,?,?)',[(k,str(v),now()) for k,v in items.items()])
 def import_ledger(self,data):
  with self.con() as c:
   for i,p in data.items():c.execute('INSERT OR REPLACE INTO ledger VALUES(?,?,?,?)',(i,json.dumps(p,sort_keys=True),p.get('time'),now()))
 def allow(self,syms):
  with self.con() as c:c.execute('UPDATE allowlist SET enabled=0');c.executemany('INSERT INTO allowlist VALUES(?,1) ON CONFLICT(symbol) DO UPDATE SET enabled=1',[(s,) for s in syms])
 def store_portfolio(self,rows,total,quality):
  stamp=now()
  with self.con() as c:
   for x in rows:c.execute('INSERT OR REPLACE INTO portfolio_assets VALUES(?,?,?,?,?,?,?,?)',(x['asset'],x['display_name'],x['amount'],x['eur_price'],x['eur_value'],x['classification'],x['ever_held'],stamp))
   priced=sum(x['eur_value'] is not None for x in rows);unpriced=sum(x['eur_value'] is None and x['amount']!='0' for x in rows);cur=c.execute('INSERT INTO portfolio_snapshots(created_at,total_eur,priced_asset_count,unpriced_asset_count,quality) VALUES(?,?,?,?,?)',(stamp,total,priced,unpriced,quality));sid=cur.lastrowid
   c.executemany('INSERT INTO portfolio_snapshot_items VALUES(?,?,?,?,?,?)',[(sid,x['asset'],x['amount'],x['eur_price'],x['eur_value'],x['classification']) for x in rows])
  return sid
