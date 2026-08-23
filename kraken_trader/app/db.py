import sqlite3, json
from datetime import datetime, timezone

def now(): return datetime.now(timezone.utc).isoformat()
class DB:
 def __init__(self,path): self.path=path
 def con(self):
  c=sqlite3.connect(self.path); c.row_factory=sqlite3.Row; c.execute("PRAGMA journal_mode=WAL"); return c
 def init(self,start):
  with self.con() as c:
   c.executescript("""CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY,value TEXT NOT NULL); CREATE TABLE IF NOT EXISTS balances(asset TEXT PRIMARY KEY,amount TEXT NOT NULL,updated_at TEXT NOT NULL); CREATE TABLE IF NOT EXISTS paper_balances(asset TEXT PRIMARY KEY,amount TEXT NOT NULL,updated_at TEXT NOT NULL); CREATE TABLE IF NOT EXISTS ledger(id TEXT PRIMARY KEY,payload TEXT NOT NULL,occurred_at REAL,imported_at TEXT NOT NULL); CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY AUTOINCREMENT,created_at TEXT NOT NULL,event TEXT NOT NULL,level TEXT NOT NULL,details TEXT NOT NULL); CREATE TABLE IF NOT EXISTS allowlist(symbol TEXT PRIMARY KEY,enabled INTEGER NOT NULL);""")
   c.execute("INSERT OR IGNORE INTO settings VALUES('automation_enabled','false')")
   c.execute("INSERT OR IGNORE INTO paper_balances VALUES('EUR',?,?)",(str(start),now()))
 def audit(self,event,details='',level='info'):
  with self.con() as c:c.execute("INSERT INTO audit(created_at,event,level,details) VALUES(?,?,?,?)",(now(),event,level,details))
 def rows(self,q,p=()):
  with self.con() as c:return [dict(x) for x in c.execute(q,p).fetchall()]
 def replace_balances(self,items):
  with self.con() as c:
   c.execute("DELETE FROM balances")
   c.executemany("INSERT INTO balances VALUES(?,?,?)",[(k,str(v),now()) for k,v in items.items()])
 def import_ledger(self,data):
  with self.con() as c:
   for i,p in data.items(): c.execute("INSERT OR REPLACE INTO ledger VALUES(?,?,?,?)",(i,json.dumps(p,sort_keys=True),p.get('time'),now()))
 def set_setting(self,k,v):
  with self.con() as c:c.execute("INSERT OR REPLACE INTO settings VALUES(?,?)",(k,v))
 def set_allowlist(self,symbols):
  with self.con() as c:
   c.execute("UPDATE allowlist SET enabled=0")
   c.executemany("INSERT INTO allowlist(symbol,enabled) VALUES(?,1) ON CONFLICT(symbol) DO UPDATE SET enabled=1",[(s,) for s in symbols])
