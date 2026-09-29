import json
import tempfile
import unittest
from pathlib import Path

class FakeKraken:
 def __init__(self):
  self.orders=[]
 def open_positions(self,docalcs=True,consolidation='market',rebase_multiplier='rebased'):
  return {}
 def trade_balance(self,asset='ZEUR'):
  return {'e':'1000','mf':'800','m':'200','n':'0','ml':'500'}
 def add_order(self,**data):
  self.orders.append(data)
  return {'txid':['TEST-MARGIN-ORDER'],'descr':{'order':'margin test'}}

class V91MarginTests(unittest.TestCase):
 def _db(self):
  import sys
  sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'app'))
  from db import DB
  handle=tempfile.NamedTemporaryFile(suffix='.db',delete=False);handle.close()
  db=DB(handle.name);db.init()
  return db,handle.name

 def test_margin_order_uses_leverage_and_reduce_only(self):
  from real_trade import RealTradeEngine
  db,path=self._db()
  try:
   client=FakeKraken();engine=RealTradeEngine(db,client)
   db.set_setting('real_margin_enabled','true');db.set_setting('real_margin_max_leverage','3')
   db.set_setting('real_margin_default_leverage','2');db.set_setting('real_margin_allow_shorts','true')
   db.set_setting('real_max_orders_per_day','10');db.set_setting('real_allowed_symbols','BTC/EUR')
   with db.con() as c:
    c.execute("CREATE TABLE market_universe(symbol TEXT PRIMARY KEY,asset_class TEXT,category TEXT,base_asset TEXT,quote_asset TEXT,status TEXT,ordermin TEXT,costmin TEXT,lot_decimals INTEGER,pair_decimals INTEGER,leverage_buy_json TEXT,leverage_sell_json TEXT,source_key TEXT,updated_at TEXT,canonical_id TEXT,product_kind TEXT,metadata_json TEXT)")
    c.execute("CREATE TABLE live_prices(symbol TEXT PRIMARY KEY,last TEXT,bid TEXT,ask TEXT,received_at TEXT)")
    c.execute("INSERT INTO market_universe(symbol,asset_class,category,base_asset,quote_asset,status,ordermin,costmin,lot_decimals,pair_decimals,leverage_buy_json,leverage_sell_json,source_key,updated_at,canonical_id,product_kind,metadata_json) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
      ('BTC/EUR','currency','crypto_spot','BTC','EUR','online','0','0',8,2,'[2,3]','[2,3]','BTCEUR','2026-01-01','BTC','crypto','{}'))
    c.execute("INSERT INTO live_prices(symbol,last,bid,ask,received_at) VALUES(?,?,?,?,?)",('BTC/EUR','50000','49999','50001','2026-01-01'))
   result=engine.submit('BTC/EUR','sell','0.01','limit','49999','test-margin',None,True,None,3,True,True)
   self.assertEqual(result['status'],'VALIDATED')
   self.assertEqual(client.orders[0]['leverage'],'3')
   self.assertEqual(client.orders[0]['reduce_only'],'true')
  finally:Path(path).unlink(missing_ok=True)

 def test_margin_calibration_requires_directional_evidence(self):
  from model_health import ModelHealth
  db,path=self._db()
  try:
   with db.con() as c:
    c.executescript("CREATE TABLE research_forecasts(id INTEGER PRIMARY KEY,family TEXT,horizon_hours INTEGER,direction TEXT,features_json TEXT);CREATE TABLE forecast_evaluations(forecast_id INTEGER PRIMARY KEY,actual_return_pct TEXT,direction_correct INTEGER);")
    for i,value in enumerate((-3,-2,-4,-1,-2),1):
     c.execute("INSERT INTO research_forecasts VALUES(?,?,?,?,?)",(i,'crypto_spot',24,'DOWN',json.dumps({'estimated_roundtrip_cost_pct':0.2})))
     c.execute("INSERT INTO forecast_evaluations VALUES(?,?,?)",(i,str(value),1))
   cal=ModelHealth(db).margin_calibration('crypto_spot','DOWN',24,5,-25)
   self.assertEqual(cal['status'],'READY')
   self.assertEqual(cal['samples'],5)
   self.assertGreater(cal['net_return_pct'],0)
  finally:Path(path).unlink(missing_ok=True)

 def test_v91_runtime_metadata_is_active_and_margin_gated(self):
  root=Path(__file__).resolve().parents[1]
  self.assertIn('v91_main:app',(root/'run.sh').read_text())
  self.assertIn('0.1.0-dev.91',(root/'app/version.py').read_text())
  self.assertIn('real_margin_enabled',(root/'config.yaml').read_text())
  runtime=(root/'app/v91_main.py').read_text()
  self.assertIn('DIRECTIONAL_H24_CALIBRATION',runtime)
  self.assertIn('futures_not_enabled',runtime)

if __name__=='__main__':unittest.main()
