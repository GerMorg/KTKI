import json,threading,time
from datetime import datetime,timezone
try:import websocket
except ImportError:websocket=None
URL='wss://ws.kraken.com/v2'
def iso():return datetime.now(timezone.utc).isoformat()
def parse_message(raw):
 data=json.loads(raw) if isinstance(raw,str) else raw
 if data.get('channel')=='status' and data.get('data'):
  x=data['data'][0];return {'kind':'status','system':x.get('system'),'connection_id':x.get('connection_id'),'received_at':iso()}
 if data.get('channel')=='heartbeat':return {'kind':'heartbeat','received_at':iso()}
 if data.get('channel')=='ticker' and data.get('data'):
  out=[]
  for x in data['data']:
   symbol=x.get('symbol');last=x.get('last')
   if symbol and last is not None:out.append({'symbol':symbol,'last':str(last),'bid':str(x.get('bid')) if x.get('bid') is not None else None,'ask':str(x.get('ask')) if x.get('ask') is not None else None,'change_pct':str(x.get('change_pct')) if x.get('change_pct') is not None else None,'received_at':iso()})
  return {'kind':'ticker','items':out}
 if data.get('method')=='subscribe':return {'kind':'subscription','success':bool(data.get('success')),'error':data.get('error'),'req_id':data.get('req_id'),'received_at':iso()}
 return {'kind':'ignored'}
class MarketStream:
 def __init__(self,db,enabled=True,stale_seconds=30):
  self.db,self.enabled,self.stale_seconds=db,enabled,max(10,int(stale_seconds));self.symbols=[];self.thread=None;self.stop=threading.Event();self.ws=None;self.blocked={};self._req_symbols={};self._lock=threading.RLock()
 def set_symbols(self,symbols):
  with self._lock:
   now_ts=time.time();clean=[]
   for x in symbols or []:
    symbol=str(x)
    if not symbol or '/' not in symbol or symbol.rsplit('/',1)[-1] not in {'EUR','USD'}:continue
    expiry=self.blocked.get(symbol,0)
    if expiry>now_ts:continue
    if symbol not in clean:clean.append(symbol)
   clean=sorted(clean)
   changed=clean!=self.symbols;self.symbols=clean
   if changed and self.ws:
    try:self.ws.close()
    except Exception:pass
 def start(self):
  if not self.enabled or websocket is None or self.thread:return
  self.stop.clear();self.thread=threading.Thread(target=self._loop,name='kraken-public-ws',daemon=True);self.thread.start()
 def shutdown(self):
  self.stop.set()
  if self.ws:
   try:self.ws.close()
   except Exception:pass
  if self.thread:self.thread.join(timeout=3)
  self.thread=None
 def _record_state(self,state,error=''):
  self.db.set_stream_state(state,error)
 def handle(self,raw):
  msg=parse_message(raw)
  if msg['kind']=='status':self.db.set_stream_status(msg.get('system'),msg.get('connection_id'),msg['received_at'])
  elif msg['kind']=='heartbeat':self.db.touch_stream(msg['received_at'])
  elif msg['kind']=='ticker':
   for item in msg['items']:self.db.upsert_live_price(item)
   if msg['items']:self.db.touch_stream(msg['items'][0]['received_at'])
  elif msg['kind']=='subscription' and not msg['success']:
   req_id=msg.get('req_id');symbol=self._req_symbols.get(req_id) if req_id is not None else None
   if symbol:
    with self._lock:self.blocked[symbol]=time.time()+21600;self.symbols=[x for x in self.symbols if x!=symbol]
    self.db.audit('PUBLIC_WS_SYMBOL_REJECTED',json.dumps({'symbol':symbol,'error':msg.get('error') or 'subscription failed'},ensure_ascii=False),'warning')
   else:self.db.audit('PUBLIC_WS_SUBSCRIPTION_REJECTED',json.dumps({'error':msg.get('error') or 'subscription failed'},ensure_ascii=False),'warning')
  return msg
 def _subscribe(self,ws):
  with self._lock:self._req_symbols={};symbols=list(self.symbols)
  req_id=10
  for symbol in symbols:
   if self.stop.is_set():break
   req_id+=1;self._req_symbols[req_id]=symbol
   ws.send(json.dumps({'method':'subscribe','params':{'channel':'ticker','symbol':[symbol],'snapshot':True},'req_id':req_id}))
 def _loop(self):
  delay=1
  while not self.stop.is_set():
   with self._lock:has_symbols=bool(self.symbols)
   if not has_symbols:self.stop.wait(2);continue
   try:
    self._record_state('CONNECTING')
    def opened(ws):
     self._record_state('CONNECTED');self._subscribe(ws)
    def message(ws,raw):self.handle(raw)
    def error(ws,err):self._record_state('ERROR',str(err)[:300])
    self.ws=websocket.WebSocketApp(URL,on_open=opened,on_message=message,on_error=error)
    self.ws.run_forever(ping_interval=20,ping_timeout=10)
   except Exception as exc:self._record_state('ERROR',type(exc).__name__+': '+str(exc)[:250])
   finally:self.ws=None;self._req_symbols={}
   if self.stop.is_set():break
   self._record_state('RECONNECTING');self.stop.wait(delay);delay=min(delay*2,30)
 def status(self):
  st=self.db.stream_status();last=st.get('last_message_at');st['configured_enabled']=self.enabled;st['symbols']=self.symbols;st['symbol_count']=len(self.symbols);st['blocked_symbol_count']=sum(1 for expiry in self.blocked.values() if expiry>time.time());st['stale']=True
  if last:
   try:st['stale']=(datetime.now(timezone.utc)-datetime.fromisoformat(last)).total_seconds()>self.stale_seconds
   except ValueError:pass
  if st['stale'] and st.get('state')=='CONNECTED':st['effective_state']='STALE'
  else:st['effective_state']=st.get('state','STOPPED')
  return st
