import json
from decimal import Decimal
from db import now
D=lambda x:Decimal(str(x or 0))
class FeeProfile:
 def __init__(self,db,client):self.db,self.client=db,client;self.ensure()
 def ensure(self):
  with self.db.con() as c:c.executescript("""CREATE TABLE IF NOT EXISTS account_fee_snapshots(id INTEGER PRIMARY KEY AUTOINCREMENT,created_at TEXT NOT NULL,status TEXT NOT NULL,volume_currency TEXT,volume_30d TEXT,source TEXT NOT NULL,error_reason TEXT,payload_json TEXT NOT NULL);CREATE TABLE IF NOT EXISTS account_pair_fees(symbol TEXT PRIMARY KEY,maker_bps TEXT NOT NULL,taker_bps TEXT NOT NULL,source TEXT NOT NULL,effective_at TEXT NOT NULL,snapshot_id INTEGER,payload_json TEXT NOT NULL);""")
 def _rate(self,value):
  x=D(value);return str((x*100).quantize(Decimal('0.0001')))
 def refresh(self,symbols):
  symbols=sorted(set(x for x in symbols if x));stamp=now()
  try:payload=self.client.trade_volume(symbols,fee_info=True);fees=payload.get('fees') or {};makers=payload.get('fees_maker') or {};saved=0
  except Exception as exc:
   with self.db.con() as c:c.execute('INSERT INTO account_fee_snapshots(created_at,status,source,error_reason,payload_json) VALUES(?,?,?,?,?)',(stamp,'FALLBACK','CONFIG',type(exc).__name__+': '+str(exc)[:200],'{}'))
   self.db.audit('ACCOUNT_FEE_REFRESH_FAILED',type(exc).__name__+': '+str(exc)[:200],'warning');return {'status':'FALLBACK','saved':0,'error':type(exc).__name__}
  with self.db.con() as c:
   cur=c.execute('INSERT INTO account_fee_snapshots(created_at,status,volume_currency,volume_30d,source,error_reason,payload_json) VALUES(?,?,?,?,?,?,?)',(stamp,'VALID',str(payload.get('currency') or ''),str(payload.get('volume') or ''),'KRAKEN_TRADE_VOLUME',None,json.dumps(payload,sort_keys=True)));sid=cur.lastrowid
   for symbol in symbols:
    item=fees.get(symbol) or fees.get(symbol.replace('/','')) or {};maker=makers.get(symbol) or makers.get(symbol.replace('/','')) or item
    taker_value=item.get('fee') if isinstance(item,dict) else None;maker_value=maker.get('fee') if isinstance(maker,dict) else None
    if taker_value is None:continue
    taker=self._rate(taker_value);maker_bps=self._rate(maker_value if maker_value is not None else taker_value)
    c.execute('INSERT INTO account_pair_fees(symbol,maker_bps,taker_bps,source,effective_at,snapshot_id,payload_json) VALUES(?,?,?,?,?,?,?) ON CONFLICT(symbol) DO UPDATE SET maker_bps=excluded.maker_bps,taker_bps=excluded.taker_bps,source=excluded.source,effective_at=excluded.effective_at,snapshot_id=excluded.snapshot_id,payload_json=excluded.payload_json',(symbol,maker_bps,taker,'KRAKEN_TRADE_VOLUME',stamp,sid,json.dumps({'taker':item,'maker':maker},sort_keys=True)));saved+=1
  self.db.audit('ACCOUNT_FEE_REFRESHED',json.dumps({'pairs':saved,'volume_30d':str(payload.get('volume') or '')}));return {'status':'VALID','saved':saved,'volume_30d':payload.get('volume'),'currency':payload.get('currency')}
 def rate_bps(self,symbol,side='taker',fallback=None):
  r=self.db.rows('SELECT maker_bps,taker_bps,source,effective_at FROM account_pair_fees WHERE symbol=?',(symbol,))
  if r:return D(r[0]['maker_bps' if side=='maker' else 'taker_bps']),r[0]['source'],r[0]['effective_at']
  return D(fallback if fallback is not None else self.db.value('paper_fee_bps','40')),'CONFIG',None
 def rows(self):return self.db.rows('SELECT * FROM account_pair_fees ORDER BY symbol')
 def latest(self):
  r=self.db.rows('SELECT * FROM account_fee_snapshots ORDER BY id DESC LIMIT 1');return r[0] if r else None


