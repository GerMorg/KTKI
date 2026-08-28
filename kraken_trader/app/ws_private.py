import json,threading
from datetime import datetime,timezone
try:import websocket
except ImportError:websocket=None
URL='wss://ws-auth.kraken.com/v2'
def iso():return datetime.now(timezone.utc).isoformat()
def parse_private(raw):
 data=json.loads(raw) if isinstance(raw,str) else raw;channel=data.get('channel')
 if channel=='status' and data.get('data'):
  x=data['data'][0];return {'kind':'status','system':x.get('system'),'connection_id':x.get('connection_id'),'received_at':iso()}
 if channel=='heartbeat':return {'kind':'heartbeat','received_at':iso()}
 if channel=='balances':return {'kind':'balances','type':data.get('type'),'sequence':data.get('sequence'),'items':data.get('data') or [],'received_at':iso()}
 if channel=='executions':return {'kind':'executions','type':data.get('type'),'sequence':data.get('sequence'),'items':data.get('data') or [],'received_at':iso()}
 if data.get('method')=='subscribe':return {'kind':'subscription','success':bool(data.get('success')),'channel':(data.get('result') or {}).get('channel'),'error':data.get('error'),'received_at':iso()}
 return {'kind':'ignored'}
class PrivateStream:
 def __init__(self,db,client,enabled=False,stale_seconds=30):
  self.db,self.client,self.enabled,self.stale_seconds=db,client,enabled,max(10,int(stale_seconds));self.thread=None;self.stop=threading.Event();self.ws=None;self.sequences={}
 def start(self):
  if not self.enabled or websocket is None or self.thread:return
  self.stop.clear();self.thread=threading.Thread(target=self._loop,name='kraken-private-ws',daemon=True);self.thread.start()
 def shutdown(self):
  self.stop.set()
  if self.ws:
   try:self.ws.close()
   except Exception:pass
  if self.thread:self.thread.join(timeout=3)
  self.thread=None
 def state(self,state,error=''):self.db.set_private_stream_state(state,error)
 def handle(self,raw):
  msg=parse_private(raw);kind=msg['kind']
  if kind in ('balances','executions'):
   seq=msg.get('sequence');previous=self.sequences.get(kind)
   if seq is not None and previous is not None and seq!=previous+1:
    self.db.record_sequence_gap(kind,previous,seq);self.state('DEGRADED','sequence gap');raise ValueError('private sequence gap')
   if seq is not None:self.sequences[kind]=seq
   if kind=='balances':self.db.apply_private_balances(msg['type'],msg['items'],seq,msg['received_at'])
   else:self.db.apply_private_executions(msg['type'],msg['items'],seq,msg['received_at'])
   self.db.touch_private_stream(msg['received_at'])
  elif kind=='status':self.db.set_private_stream_status(msg.get('system'),msg.get('connection_id'),msg['received_at'])
  elif kind=='heartbeat':self.db.touch_private_stream(msg['received_at'])
  elif kind=='subscription' and not msg['success']:self.state('ERROR',str(msg.get('error') or 'subscription failed')[:300])
  return msg
 def _loop(self):
  delay=1
  while not self.stop.is_set():
   try:
    self.state('AUTHENTICATING');token=self.client.websocket_token().get('token')
    if not token:raise RuntimeError('token missing')
    self.sequences={}
    def opened(ws):
     self.state('CONNECTED')
     ws.send(json.dumps({'method':'subscribe','params':{'channel':'balances','snapshot':True,'token':token},'req_id':101}))
     ws.send(json.dumps({'method':'subscribe','params':{'channel':'executions','snap_orders':True,'snap_trades':True,'order_status':True,'token':token},'req_id':102}))
    def message(ws,raw):
     try:self.handle(raw)
     except ValueError:ws.close()
    def error(ws,err):self.state('ERROR',type(err).__name__)
    self.ws=websocket.WebSocketApp(URL,on_open=opened,on_message=message,on_error=error)
    self.ws.run_forever(ping_interval=20,ping_timeout=10)
   except Exception as exc:self.state('ERROR',type(exc).__name__)
   finally:self.ws=None
   if self.stop.is_set():break
   self.state('RECONNECTING');self.stop.wait(delay);delay=min(delay*2,30)
 def status(self):
  st=self.db.private_stream_status();st['configured_enabled']=self.enabled;st['sequences']=dict(self.sequences);st['effective_state']=st.get('state','STOPPED');return st
