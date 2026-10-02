from __future__ import annotations
import json,os,time
BINARY=("trading_enabled","system_ready","market_data_healthy","private_data_healthy","portfolio_consistent","model_ready","news_healthy","gemini_healthy","circuit_breaker","margin_safe")
NUMERIC=("portfolio_equity","available_cash","available_margin","used_margin","gross_exposure","net_exposure","realized_pnl","unrealized_pnl","daily_pnl","drawdown","open_positions","open_orders","orders_today","current_leverage","average_slippage","average_latency","expected_edge")
TEXT=("system_state","last_action","last_symbol","last_direction","last_blocker","last_trade","active_strategy","active_model","active_regime","last_news_event","gemini_status","learning_status")
class SensorPublisher:
    def __init__(self,path="/data/autonomous_trader/sensors.json"):self.path=path
    def publish(self,state):
        p={"updated_at":time.time(),"binary":{k:bool(state.get(k,False)) for k in BINARY},"numeric":{k:state.get(k) for k in NUMERIC},"text":{k:str(state.get(k,""))[:300] for k in TEXT}}
        os.makedirs(os.path.dirname(self.path),exist_ok=True);tmp=self.path+".tmp"
        with open(tmp,"w",encoding="utf-8") as f:json.dump(p,f,sort_keys=True,ensure_ascii=False)
        os.replace(tmp,self.path);return p
