from __future__ import annotations
import json,threading,time

try:
    import websocket
except Exception:
    websocket=None

class WebSocketSupervisor:
    """Read-only market/private transport boundary. It can never submit an order."""
    def __init__(self,db,url,subscribe_message=None,name="kraken-ws"):
        self.db,self.url,self.subscribe_message,self.name=db,url,subscribe_message or {},name
        self._stop=threading.Event();self._thread=None;self._ws=None;self._last_seq={};self.connected=False
    def _on_open(self,ws):
        self.connected=True;self.db.event("info","WS_CONNECTED","PUBLIC_DATA_CONNECT",message=self.name)
        if self.subscribe_message:ws.send(json.dumps(self.subscribe_message))
    def _on_message(self,ws,message):
        try:
            item=json.loads(message)
        except Exception:
            self.db.error("DATA_ERROR","PUBLIC_DATA_CONNECT",message="invalid websocket json");return
        seq=item.get("seq")
        stream=str(item.get("channel") or item.get("feed") or "")
        if seq is not None and stream:
            try:
                seq=int(seq);previous=self._last_seq.get(stream)
                if previous is not None and seq>previous+1:
                    self.db.event("warning","PRIVATE_SEQUENCE_GAP" if "private" in self.name else "PUBLIC_SEQUENCE_GAP","PRIVATE_DATA_CONNECT" if "private" in self.name else "PUBLIC_DATA_CONNECT",
                                  message=f"{stream}:{previous}->{seq}")
                    self.db.event("warning","RECOVERY_STARTED","RECONCILIATION",message="sequence gap requires REST reconcile")
                self._last_seq[stream]=seq
            except (TypeError,ValueError):pass
    def _on_close(self,ws,code,msg):
        self.connected=False;self.db.event("warning","WS_DISCONNECTED","PRIVATE_DATA_CONNECT" if "private" in self.name else "PUBLIC_DATA_CONNECT",message=str(code or "closed"))
    def _on_error(self,ws,error):
        self.connected=False;self.db.event("warning","WS_ERROR","PRIVATE_DATA_CONNECT" if "private" in self.name else "PUBLIC_DATA_CONNECT",message=type(error).__name__)
    def start(self):
        if websocket is None:return False
        if self._thread and self._thread.is_alive():return True
        self._stop.clear()
        self._thread=threading.Thread(target=self._run,name=self.name,daemon=True);self._thread.start();return True
    def _run(self):
        while not self._stop.is_set():
            try:
                self._ws=websocket.WebSocketApp(self.url,on_open=self._on_open,on_message=self._on_message,on_close=self._on_close,on_error=self._on_error)
                self._ws.run_forever(ping_interval=20,ping_timeout=10)
            except Exception as exc:
                self.db.event("warning","WS_RECONNECT_REQUIRED","RECOVERY",message=type(exc).__name__)
            if not self._stop.is_set():
                self.db.event("info","RECOVERY_STARTED","RECOVERY",message="websocket reconnect/resubscribe")
                self._stop.wait(2)
    def stop(self):
        self._stop.set()
        if self._ws:
            try:self._ws.close()
            except Exception:pass
        self.connected=False
