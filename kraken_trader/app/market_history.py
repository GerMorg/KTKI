import csv,io,json
from datetime import datetime,timezone
from db import now

class MarketHistory:
 def __init__(self,db):self.db=db;self.ensure()
 def ensure(self):
  with self.db.con() as c:c.executescript("""CREATE TABLE IF NOT EXISTS ohlc_cache(symbol TEXT NOT NULL,interval_min INTEGER NOT NULL,open_time INTEGER NOT NULL,open TEXT NOT NULL,high TEXT NOT NULL,low TEXT NOT NULL,close TEXT NOT NULL,vwap TEXT,volume TEXT,trades INTEGER,received_at TEXT NOT NULL,PRIMARY KEY(symbol,interval_min,open_time));CREATE TABLE IF NOT EXISTS market_data_diagnostics(symbol TEXT PRIMARY KEY,asset_class TEXT NOT NULL,ticker_status TEXT NOT NULL,ticker_at TEXT,bid TEXT,ask TEXT,last TEXT,volume TEXT,ohlc_status TEXT NOT NULL,ohlc_at TEXT,ohlc_points INTEGER NOT NULL DEFAULT 0,last_committed_open_time INTEGER,error_reason TEXT,updated_at TEXT NOT NULL);CREATE TABLE IF NOT EXISTS history_imports(id INTEGER PRIMARY KEY AUTOINCREMENT,created_at TEXT NOT NULL,source TEXT NOT NULL,symbol TEXT NOT NULL,interval_min INTEGER NOT NULL,rows_seen INTEGER NOT NULL,rows_saved INTEGER NOT NULL,status TEXT NOT NULL,details_json TEXT NOT NULL);""")
 def ticker(self,symbol,asset_class,item=None,error=None):
  bid=(item.get('b') or [None])[0] if item else None;ask=(item.get('a') or [None])[0] if item else None;last=(item.get('c') or [None])[0] if item else None;volume=(item.get('v') or [None,None])[-1] if item else None
  with self.db.con() as c:c.execute("""INSERT INTO market_data_diagnostics(symbol,asset_class,ticker_status,ticker_at,bid,ask,last,volume,ohlc_status,ohlc_points,error_reason,updated_at) VALUES(?,?,?,?,?,?,?,?,'PENDING',0,?,?) ON CONFLICT(symbol) DO UPDATE SET asset_class=excluded.asset_class,ticker_status=excluded.ticker_status,ticker_at=excluded.ticker_at,bid=excluded.bid,ask=excluded.ask,last=excluded.last,volume=excluded.volume,error_reason=excluded.error_reason,updated_at=excluded.updated_at""",(symbol,asset_class,'ERROR' if error else ('VALID' if item else 'MISSING'),now(),bid,ask,last,volume,error,now()))
 def ohlc(self,symbol,asset_class,candles=None,error=None):
  committed=(candles or [])[:-1] if len(candles or [])>1 else [];last_open=int(committed[-1][0]) if committed else None
  with self.db.con() as c:c.execute("""INSERT INTO market_data_diagnostics(symbol,asset_class,ticker_status,ohlc_status,ohlc_at,ohlc_points,last_committed_open_time,error_reason,updated_at) VALUES(?,?,'PENDING',?,?,?,?,?,?) ON CONFLICT(symbol) DO UPDATE SET asset_class=excluded.asset_class,ohlc_status=excluded.ohlc_status,ohlc_at=excluded.ohlc_at,ohlc_points=excluded.ohlc_points,last_committed_open_time=excluded.last_committed_open_time,error_reason=excluded.error_reason,updated_at=excluded.updated_at""",(symbol,asset_class,'ERROR' if error else ('VALID' if committed else 'MISSING'),now(),len(committed),last_open,error,now()))
 def import_csv(self,symbol,interval_min,text,source='CSV'):
  seen=saved=0
  with self.db.con() as c:
   for row in csv.reader(io.StringIO(text)):
    seen+=1
    if len(row)<8:continue
    try:ts=int(float(row[0]));vals=(symbol,int(interval_min),ts,*[str(x) for x in row[1:7]],int(float(row[7])),now())
    except (ValueError,TypeError):continue
    c.execute('INSERT OR REPLACE INTO ohlc_cache(symbol,interval_min,open_time,open,high,low,close,vwap,volume,trades,received_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)',vals);saved+=1
   c.execute('INSERT INTO history_imports(created_at,source,symbol,interval_min,rows_seen,rows_saved,status,details_json) VALUES(?,?,?,?,?,?,?,?)',(now(),source,symbol,int(interval_min),seen,saved,'VALID' if saved else 'ERROR',json.dumps({'format':'Kraken OHLCVT CSV'})))
  return {'status':'VALID' if saved else 'ERROR','rows_seen':seen,'rows_saved':saved}
 def diagnostics(self):return self.db.rows('SELECT * FROM market_data_diagnostics ORDER BY asset_class,symbol')
