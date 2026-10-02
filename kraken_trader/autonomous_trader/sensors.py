from __future__ import annotations
import json,os,time,threading,urllib.request
from decimal import Decimal

BINARY=("trading_enabled","system_ready","market_data_healthy","private_data_healthy","portfolio_consistent","model_ready","news_healthy","gemini_healthy","circuit_breaker","margin_safe")
NUMERIC=("portfolio_equity","available_cash","available_margin","used_margin","gross_exposure","net_exposure","realized_pnl","unrealized_pnl","daily_pnl","drawdown","open_positions","open_orders","orders_today","current_leverage","average_slippage","average_latency","expected_edge")
TEXT=("system_state","last_action","last_symbol","last_direction","last_blocker","last_trade","active_strategy","active_model","active_regime","last_news_event","gemini_status","learning_status")

PREFIX="autonomous_kraken_trader"

class SensorPublisher:
    """Publishes a local diagnostic snapshot and native Home Assistant state entities.

    HA publishing is fire-and-forget so a slow/unavailable Supervisor API cannot block the
    trading cycle. Missing SUPERVISOR_TOKEN simply disables the native state bridge.
    """
    def __init__(self,path="/data/autonomous_trader/sensors.json",timeout=2.0):
        self.path=path if os.path.isdir("/data") and os.access("/data",os.W_OK) else "./autonomous_trader_sensors.json"
        self.timeout=float(timeout);self.token=os.getenv("SUPERVISOR_TOKEN","")
        self._lock=threading.Lock();self._publishing=False;self._queued=None

    def _payload(self,state):
        return {
            "updated_at":time.time(),
            "binary":{k:bool(state.get(k,False)) for k in BINARY},
            "numeric":{k:state.get(k) for k in NUMERIC},
            "text":{k:str(state.get(k,""))[:300] for k in TEXT},
        }

    def _write_snapshot(self,payload):
        os.makedirs(os.path.dirname(self.path) or ".",exist_ok=True)
        tmp=self.path+".tmp"
        with open(tmp,"w",encoding="utf-8") as f:json.dump(payload,f,sort_keys=True,ensure_ascii=False)
        os.replace(tmp,self.path)

    @staticmethod
    def _entity_id(domain,key):
        return f"{domain}.{PREFIX}_{key}"

    def _post_state(self,domain,key,state,attributes):
        url=f"http://supervisor/core/api/states/{self._entity_id(domain,key)}"
        body=json.dumps({"state":str(state),"attributes":attributes}).encode()
        req=urllib.request.Request(url,data=body,headers={
            "Authorization":f"Bearer {self.token}",
            "Content-Type":"application/json",
        },method="POST")
        try:
            with urllib.request.urlopen(req,timeout=self.timeout) as response:
                response.read(1)
        except Exception:
            pass

    def _publish_native(self,payload):
        if not self.token:return
        common={"friendly_name":"Autonomous Kraken Trader"}
        for key,value in payload["binary"].items():
            attrs={**common,"device_class":None,"source":"autonomous_kraken_trader"}
            self._post_state("binary_sensor",key,"on" if value else "off",attrs)
        for key,value in payload["numeric"].items():
            if value is None:continue
            attrs={**common,"source":"autonomous_kraken_trader"}
            if key in ("portfolio_equity","available_cash","available_margin","used_margin","gross_exposure","net_exposure","realized_pnl","unrealized_pnl","daily_pnl","drawdown"):
                attrs["unit_of_measurement"]="EUR" if key not in ("drawdown",) else "%"
            self._post_state("sensor",key,value,attrs)
        for key,value in payload["text"].items():
            self._post_state("sensor",key,value,{**common,"source":"autonomous_kraken_trader"})

    def _worker(self):
        while True:
            with self._lock:
                payload=self._queued
                self._queued=None
                if payload is None:
                    self._publishing=False
                    return
            self._publish_native(payload)

    def publish(self,state):
        payload=self._payload(state)
        self._write_snapshot(payload)
        with self._lock:
            self._queued=payload
            if not self._publishing:
                self._publishing=True
                threading.Thread(target=self._worker,name="ha-sensor-publisher",daemon=True).start()
        return payload
