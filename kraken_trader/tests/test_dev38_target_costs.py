import json, os, sys, tempfile, unittest
from datetime import datetime, timezone, timedelta
sys.path.insert(0,os.path.join(os.path.dirname(__file__),'..','app'))
from db import DB, now
from forecast_tracker import ForecastTracker

class Dev38Tests(unittest.TestCase):
 def setUp(self):
  self.db=DB(tempfile.mktemp());self.db.init();self.f=ForecastTracker(self.db)
  with self.db.con() as c:c.execute('CREATE TABLE IF NOT EXISTS ohlc_cache(symbol TEXT,interval_min INTEGER,open_time INTEGER,open TEXT,high TEXT,low TEXT,close TEXT,vwap TEXT,volume TEXT,trades INTEGER,received_at TEXT,PRIMARY KEY(symbol,interval_min,open_time))')
 def add_forecast(self,created,horizon=24):
  with self.db.con() as c:
   cur=c.execute("INSERT INTO research_forecasts(created_at,symbol,model_version,horizon_hours,direction,baseline_price,scanner_score,confidence,status,features_json,family,parameter_version,parameters_json,feature_schema_version) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",(created,'BTC/EUR','test',horizon,'UP','100','80','.8','OPEN','{}','crypto_spot',1,'{}',3));return cur.lastrowid
 def candle(self,ts,close):
  with self.db.con() as c:c.execute('INSERT INTO ohlc_cache VALUES(?,?,?,?,?,?,?,?,?,?,?)',('BTC/EUR',60,ts,'100','110','90',str(close),'100','1',1,now()))
 def test_first_closed_candle_at_or_after_target_is_used(self):
  target=datetime.now(timezone.utc)-timedelta(hours=3);created=target-timedelta(hours=24);fid=self.add_forecast(created.isoformat());self.candle(int(target.timestamp())-3600,150);self.candle(int(target.timestamp())+10,110);self.candle(int(target.timestamp())+3610,120)
  self.assertEqual(self.f.evaluate_due(),1);e=self.db.rows('SELECT * FROM forecast_evaluations WHERE forecast_id=?',(fid,))[0];self.assertEqual(float(e['actual_price']),110);self.assertEqual(e['price_source'],'OHLC_CACHE_FIRST_CLOSED_AT_OR_AFTER_TARGET');self.assertEqual(e['timing_error_seconds'],10)
 def test_no_historical_target_candle_keeps_forecast_open(self):
  target=datetime.now(timezone.utc)-timedelta(hours=3);fid=self.add_forecast((target-timedelta(hours=24)).isoformat());
  with self.db.con() as c:c.execute("INSERT OR REPLACE INTO live_prices(symbol,last,received_at) VALUES('BTC/EUR','999',?)",(now(),))
  self.assertEqual(self.f.evaluate_due(),0);self.assertEqual(self.db.rows('SELECT status FROM research_forecasts WHERE id=?',(fid,))[0]['status'],'OPEN')
 def test_cost_snapshot_separates_entry_exit_and_provenance(self):
  with self.db.con() as c:
   c.execute('CREATE TABLE account_pair_fees(symbol TEXT PRIMARY KEY,maker_bps TEXT,taker_bps TEXT,source TEXT,effective_at TEXT,snapshot_id INTEGER,payload_json TEXT)');c.execute("INSERT INTO account_pair_fees VALUES('BTC/EUR','20','30','KRAKEN_TRADE_VOLUME','2026-01-01',1,'{}')")
  x=self.f._cost_snapshot('BTC/EUR',.2);self.assertAlmostEqual(x['roundtrip_cost_pct'],x['entry_cost_pct']+x['exit_cost_pct']);self.assertEqual(x['provenance']['trade_fee_source'],'KRAKEN_TRADE_VOLUME');self.assertIn('entry',x['components_pct']);self.assertIn('exit',x['components_pct'])
 def test_old_evaluation_schema_migrates_idempotently(self):
  cols={x['name'] for x in self.db.rows('PRAGMA table_info(forecast_evaluations)')};self.assertTrue({'target_at','price_source','source_open_time','timing_error_seconds'}.issubset(cols));ForecastTracker(self.db);self.assertEqual(cols,{x['name'] for x in self.db.rows('PRAGMA table_info(forecast_evaluations)')})
if __name__=='__main__':unittest.main()

