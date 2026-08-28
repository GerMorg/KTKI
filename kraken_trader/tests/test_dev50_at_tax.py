import os,sys
sys.path.insert(0,os.path.join(os.path.dirname(__file__),"..","app"))
from db import DB
from at_income_tax import AustrianTaxInfo
def test_average(tmp_path):
 d=DB(str(tmp_path/"x.db"));d.init()
 with d.con() as c:c.executescript("CREATE TABLE market_universe(symbol TEXT PRIMARY KEY,asset_class TEXT,category TEXT);INSERT INTO market_universe VALUES('BTC/EUR','currency','crypto_spot');CREATE TABLE paper_trades(id INTEGER PRIMARY KEY AUTOINCREMENT,created_at TEXT,symbol TEXT,side TEXT,quantity TEXT,market_price TEXT,execution_price TEXT,gross_eur TEXT,fee_eur TEXT,slippage_eur TEXT,net_eur TEXT,reason TEXT,decision_json TEXT);INSERT INTO paper_trades(created_at,symbol,side,quantity,market_price,execution_price,gross_eur,fee_eur,slippage_eur,net_eur,reason,decision_json) VALUES('2024-01-01','BTC/EUR','BUY','1','1','1','100','1','0','101','t','{}'),('2024-02-01','BTC/EUR','BUY','1','1','1','200','2','0','202','t','{}'),('2025-03-01','BTC/EUR','SELL','1','1','1','250','2','0','248','t','{}');")
 r=AustrianTaxInfo(d).analyze(2025);assert r["rows"][0]["acquisition_cost_eur"]=="151.50";assert r["estimated_tax_eur"]=="26.54"



