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
 if data.get('method')=='subscribe':return {'kind':'subscription','success':bool(data.get('success')),'error':data.get('error'),'received_at':iso()}
 return {'kind':'ignored'}
class MarketStream:
 def __init__(self,db,enabled=True,stale_seconds=30):
  self.db,self.enabled,self.stale_seconds=db,enabled,max(10,int(stale_seconds));self.symbols=[];self.thread=None;self.stop=threading.Event();self.ws=None
 def set_symbols(self,symbols):
  clean=sorted({str(x) for x in symbols if x and '/' in str(x) and str(x).rsplit('/',1)[-1] in {'EUR','USD'}});changed=clean!=self.symbols;self.symbols=clean
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
  elif msg['kind']=='subscription' and not msg['success']:self._record_state('ERROR',str(msg.get('error') or 'subscription failed')[:300])
  return msg
 def _loop(self):
  delay=1
  while not self.stop.is_set():
   if not self.symbols:self.stop.wait(2);continue
   try:
    self._record_state('CONNECTING')
    def opened(ws):
     self._record_state('CONNECTED');ws.send(json.dumps({'method':'subscribe','params':{'channel':'ticker','symbol':self.symbols,'snapshot':True},'req_id':1}))
    def message(ws,raw):self.handle(raw)
    def error(ws,err):self._record_state('ERROR',type(err).__name__)
    self.ws=websocket.WebSocketApp(URL,on_open=opened,on_message=message,on_error=error)
    self.ws.run_forever(ping_interval=20,ping_timeout=10)
   except Exception as exc:self._record_state('ERROR',type(exc).__name__)
   finally:self.ws=None
   if self.stop.is_set():break
   self._record_state('RECONNECTING');self.stop.wait(delay);delay=min(delay*2,30)
 def status(self):
  st=self.db.stream_status();last=st.get('last_message_at');st['configured_enabled']=self.enabled;st['symbols']=self.symbols;st['symbol_count']=len(self.symbols);st['stale']=True
  if last:
   try:st['stale']=(datetime.now(timezone.utc)-datetime.fromisoformat(last)).total_seconds()>self.stale_seconds
   except ValueError:pass
  if st['stale'] and st.get('state')=='CONNECTED':st['effective_state']='STALE'
  else:st['effective_state']=st.get('state','STOPPED')
  return st
