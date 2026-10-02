from __future__ import annotations
from contextlib import contextmanager
import json,os,sqlite3,threading,time

SCHEMA='''CREATE TABLE IF NOT EXISTS schema_meta(key TEXT PRIMARY KEY,value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS cycles(id TEXT PRIMARY KEY,started_at REAL NOT NULL,finished_at REAL,state TEXT NOT NULL,details_json TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS market_snapshots(id INTEGER PRIMARY KEY AUTOINCREMENT,cycle_id TEXT NOT NULL,symbol TEXT NOT NULL,ts REAL NOT NULL,bid TEXT,ask TEXT,last TEXT,volume TEXT,depth_bid TEXT,depth_ask TEXT,imbalance TEXT,features_json TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS instrument_metadata(instrument_id TEXT PRIMARY KEY,venue TEXT,product_type TEXT,symbol TEXT,altname TEXT,base TEXT,quote TEXT,status TEXT,metadata_json TEXT NOT NULL,updated_at REAL NOT NULL);
CREATE TABLE IF NOT EXISTS portfolio_snapshots(id INTEGER PRIMARY KEY AUTOINCREMENT,cycle_id TEXT,ts REAL NOT NULL,equity TEXT,cash TEXT,available_margin TEXT,used_margin TEXT,gross_exposure TEXT,net_exposure TEXT,realized_pnl TEXT,unrealized_pnl TEXT,daily_pnl TEXT,drawdown TEXT,quality TEXT,details_json TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS portfolio_positions(id INTEGER PRIMARY KEY AUTOINCREMENT,cycle_id TEXT,symbol TEXT,side TEXT,quantity TEXT,notional TEXT,entry_price TEXT,mark_price TEXT,unrealized_pnl TEXT,leverage TEXT,margin TEXT,details_json TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS decisions(id TEXT PRIMARY KEY,cycle_id TEXT,symbol TEXT,action TEXT,side TEXT,target_notional TEXT,current_notional TEXT,delta_notional TEXT,expected_edge TEXT,confidence TEXT,uncertainty TEXT,leverage TEXT,margin INTEGER,status TEXT,blocker TEXT,strategy_version TEXT,model_version TEXT,config_hash TEXT,digest TEXT,evidence_json TEXT NOT NULL,created_at REAL NOT NULL);
CREATE TABLE IF NOT EXISTS decision_checks(id INTEGER PRIMARY KEY AUTOINCREMENT,decision_id TEXT,check_name TEXT,result INTEGER,actual TEXT,required TEXT,threshold TEXT,details_json TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS orders(id INTEGER PRIMARY KEY AUTOINCREMENT,intent_id TEXT UNIQUE,cycle_id TEXT,decision_id TEXT,client_order_id TEXT UNIQUE,kraken_order_id TEXT,symbol TEXT,side TEXT,order_type TEXT,volume TEXT,price TEXT,leverage TEXT,margin INTEGER,reduce_only INTEGER,state TEXT,error_code TEXT,created_at REAL NOT NULL,updated_at REAL NOT NULL,details_json TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS order_events(id INTEGER PRIMARY KEY AUTOINCREMENT,client_order_id TEXT,state TEXT,ts REAL,event_code TEXT,details_json TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS fills(id INTEGER PRIMARY KEY AUTOINCREMENT,client_order_id TEXT,kraken_trade_id TEXT,ts REAL,price TEXT,volume TEXT,fee TEXT,fee_currency TEXT,side TEXT,details_json TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS positions(id INTEGER PRIMARY KEY AUTOINCREMENT,cycle_id TEXT,symbol TEXT,side TEXT,quantity TEXT,entry_price TEXT,mark_price TEXT,notional TEXT,realized_pnl TEXT,unrealized_pnl TEXT,leverage TEXT,margin TEXT,details_json TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS news_events(id TEXT PRIMARY KEY,source TEXT,title TEXT,url TEXT,published_at REAL,observed_at REAL,entity_json TEXT,direction TEXT,impact TEXT,novelty TEXT,credibility TEXT,horizon TEXT,market_confirmation TEXT,outcome_json TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS news_analysis(id INTEGER PRIMARY KEY AUTOINCREMENT,news_id TEXT,symbol TEXT,direction TEXT,impact TEXT,confidence TEXT,model_version TEXT,evidence_json TEXT NOT NULL,created_at REAL NOT NULL);
CREATE TABLE IF NOT EXISTS gemini_analysis(id INTEGER PRIMARY KEY AUTOINCREMENT,news_id TEXT,symbol TEXT,event TEXT,direction TEXT,impact TEXT,confidence TEXT,time_horizon TEXT,novelty TEXT,market_confirmation TEXT,risk_flags_json TEXT NOT NULL,model_version TEXT,status TEXT,raw_json TEXT NOT NULL,created_at REAL NOT NULL);
CREATE TABLE IF NOT EXISTS predictions(id INTEGER PRIMARY KEY AUTOINCREMENT,cycle_id TEXT,symbol TEXT,horizon_hours INTEGER,direction TEXT,probability TEXT,expected_return TEXT,confidence TEXT,model_version TEXT,created_at REAL NOT NULL,outcome_status TEXT);
CREATE TABLE IF NOT EXISTS prediction_outcomes(id INTEGER PRIMARY KEY AUTOINCREMENT,prediction_id INTEGER UNIQUE,evaluated_at REAL,realized_return TEXT,direction_correct INTEGER,cost_adjusted_return TEXT,details_json TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS learning_events(id INTEGER PRIMARY KEY AUTOINCREMENT,ts REAL,event_type TEXT,cycle_id TEXT,decision_id TEXT,details_json TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS calibration_history(id INTEGER PRIMARY KEY AUTOINCREMENT,ts REAL,metric TEXT,value TEXT,sample_count INTEGER,details_json TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS strategy_versions(version TEXT PRIMARY KEY,parent_version TEXT,hash TEXT,status TEXT,parameters_json TEXT NOT NULL,created_at REAL,reason TEXT);
CREATE TABLE IF NOT EXISTS model_versions(version TEXT PRIMARY KEY,parent_version TEXT,hash TEXT,status TEXT,parameters_json TEXT NOT NULL,created_at REAL,reason TEXT);
CREATE TABLE IF NOT EXISTS model_evaluations(id INTEGER PRIMARY KEY AUTOINCREMENT,version TEXT,window_start REAL,window_end REAL,sample_count INTEGER,net_return TEXT,max_drawdown TEXT,sharpe TEXT,sortino TEXT,expected_shortfall TEXT,turnover TEXT,regime_metrics_json TEXT NOT NULL,cost_adjusted INTEGER,passed INTEGER,details_json TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS risk_events(id INTEGER PRIMARY KEY AUTOINCREMENT,ts REAL,code TEXT,symbol TEXT,actual TEXT,required TEXT,threshold TEXT,details_json TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS health_snapshots(id INTEGER PRIMARY KEY AUTOINCREMENT,ts REAL,state TEXT,public_ok INTEGER,private_ok INTEGER,portfolio_ok INTEGER,model_ok INTEGER,news_ok INTEGER,gemini_ok INTEGER,circuit_breaker INTEGER,margin_safe INTEGER,details_json TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS app_events(id INTEGER PRIMARY KEY AUTOINCREMENT,ts REAL,level TEXT,event_code TEXT,stage TEXT,cycle_id TEXT,decision_id TEXT,intent_id TEXT,client_order_id TEXT,kraken_order_id TEXT,symbol TEXT,actual TEXT,required TEXT,threshold TEXT,message TEXT,details_json TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS error_events(id INTEGER PRIMARY KEY AUTOINCREMENT,ts REAL,error_code TEXT,stage TEXT,cycle_id TEXT,symbol TEXT,message TEXT,details_json TEXT NOT NULL);'''

class Database:
    def __init__(self,path="/data/autonomous_trader/trader.sqlite3"):
        self.path=path;os.makedirs(os.path.dirname(path),exist_ok=True);self.lock=threading.RLock();self._init()
    @contextmanager
    def tx(self):
        with self.lock:
            con=sqlite3.connect(self.path);con.row_factory=sqlite3.Row
            try: con.execute("PRAGMA journal_mode=WAL");yield con;con.commit()
            except Exception: con.rollback();raise
            finally: con.close()
    def _init(self):
        with self.tx() as c:c.executescript(SCHEMA);c.execute("INSERT OR IGNORE INTO schema_meta VALUES('schema_version','1')")
    def rows(self,sql,args=()):
        with self.tx() as c:return [dict(r) for r in c.execute(sql,args).fetchall()]
    def one(self,sql,args=()):
        rows=self.rows(sql,args);return rows[0] if rows else None
    def event(self,level,event_code,stage="",cycle_id="",decision_id="",intent_id="",client_order_id="",kraken_order_id="",symbol="",actual="",required="",threshold="",message="",details=None):
        with self.tx() as c:c.execute("INSERT INTO app_events VALUES(NULL,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",(time.time(),level,event_code,stage,cycle_id,decision_id,intent_id,client_order_id,kraken_order_id,symbol,actual,required,threshold,message,json.dumps(details or {},sort_keys=True,default=str)))
    def error(self,code,stage="",cycle_id="",symbol="",message="",details=None):
        self.event("error",code,stage=stage,cycle_id=cycle_id,symbol=symbol,message=message,details=details)
        with self.tx() as c:c.execute("INSERT INTO error_events VALUES(NULL,?,?,?,?,?,?,?)",(time.time(),code,stage,cycle_id,symbol,message,json.dumps(details or {},sort_keys=True,default=str)))
    def save_decision(self,d,created_at=None):
        with self.tx() as c:c.execute("INSERT OR REPLACE INTO decisions VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
          (d.decision_id,d.cycle_id,d.symbol,d.action.value,d.side,str(d.target_notional),str(d.current_notional),str(d.delta_notional),str(d.expected_edge),str(d.confidence),str(d.uncertainty),str(d.leverage),1 if d.margin else 0,d.status,d.blocker,d.strategy_version,d.model_version,d.config_hash,d.digest(),json.dumps(d.evidence,sort_keys=True,default=str),created_at or time.time()))
    def save_check(self,decision_id,name,result,actual="",required="",threshold="",details=None):
        with self.tx() as c:c.execute("INSERT INTO decision_checks(decision_id,check_name,result,actual,required,threshold,details_json) VALUES(?,?,?,?,?,?,?)",(decision_id,name,1 if result else 0,str(actual),str(required),str(threshold),json.dumps(details or {},sort_keys=True,default=str)))
    def save_order(self,intent,state,kraken_order_id="",error_code="",details=None):
        with self.tx() as c:
            now=time.time()
            c.execute("INSERT OR REPLACE INTO orders VALUES(NULL,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
              (intent.intent_id,intent.cycle_id,intent.decision_id,intent.client_order_id,kraken_order_id,intent.symbol,intent.side,intent.order_type,str(intent.volume),str(intent.price) if intent.price else None,str(intent.leverage),1 if intent.margin else 0,1 if intent.reduce_only else 0,state,error_code,now,now,json.dumps(details or {},sort_keys=True,default=str)))
            c.execute("INSERT INTO order_events VALUES(NULL,?,?,?, ?,?)",(intent.client_order_id,state,now,"ORDER_STATE_CHANGED",json.dumps(details or {},sort_keys=True,default=str)))
    def update_order(self,client_order_id,state,kraken_order_id=None,error_code="",details=None):
        with self.tx() as c:
            c.execute("UPDATE orders SET state=?,kraken_order_id=COALESCE(?,kraken_order_id),error_code=?,updated_at=?,details_json=? WHERE client_order_id=?",(state,kraken_order_id,error_code,time.time(),json.dumps(details or {},sort_keys=True,default=str),client_order_id))
            c.execute("INSERT INTO order_events VALUES(NULL,?,?,?, ?,?)",(client_order_id,state,time.time(),"ORDER_STATUS_CHANGED",json.dumps(details or {},sort_keys=True,default=str)))
    def start_cycle(self,cycle_id):
        with self.tx() as c:c.execute("INSERT INTO cycles VALUES(?,?,NULL,'RUNNING','{}')",(cycle_id,time.time()))
    def finish_cycle(self,cycle_id,state,details):
        with self.tx() as c:c.execute("UPDATE cycles SET finished_at=?,state=?,details_json=? WHERE id=?",(time.time(),state,json.dumps(details or {},sort_keys=True,default=str),cycle_id))
