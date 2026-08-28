import json,os,sys,tempfile,unittest
sys.path.insert(0,os.path.join(os.path.dirname(__file__),'..','app'))
from db import DB,now
from controlled_learning import ControlledLearning
from forecast_tracker import ForecastTracker
class T(unittest.TestCase):
 def setUp(self):
  self.db=DB(tempfile.mktemp());self.db.init();ForecastTracker(self.db);self.db.set('learning_min_net_return_improvement','0');self.learning=ControlledLearning(self.db)
  with self.db.con() as c:
   c.execute('CREATE TABLE market_universe(symbol TEXT,category TEXT)');c.execute("INSERT INTO market_universe VALUES('EUR/USD','forex')")
 def seed(self):
  features={'momentum_pct':2,'trend_pct':2,'volatility_pct':.1,'spread_pct':.05,'estimated_roundtrip_cost_pct':.2}
  with self.db.con() as c:
   for i in range(12):
    h=24 if i<6 else 168;c.execute('INSERT INTO research_forecasts(created_at,symbol,model_version,horizon_hours,direction,baseline_price,scanner_score,confidence,status,features_json,family,parameter_version,parameters_json,feature_schema_version) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(now(),'EUR/USD','forex-controlled-v1',h,'UP','100','80','.8','EVALUATED',json.dumps(features),'forex',1,'{}',2));fid=c.execute('SELECT last_insert_rowid()').fetchone()[0];c.execute('INSERT INTO forecast_evaluations(forecast_id,evaluated_at,actual_price,actual_return_pct,direction_correct,details_json) VALUES(?,?,?,?,?,?)',(fid,now(),'101','1',1,'{}'))
 def test_metrics_are_separate_by_horizon_and_cost_aware(self):
  self.seed();r=self.learning.propose('forex',10,0);self.assertEqual(r['status'],'PENDING');metrics=self.learning.metrics(r['candidate_id']);self.assertEqual({x['horizon_hours'] for x in metrics},{24,168});self.assertTrue(all(float(x['active_net_return'])<x['sample_count'] for x in metrics));self.assertTrue(all(0<=float(x['candidate_coverage'])<=1 for x in metrics))
 def test_forecast_snapshot_contains_cost_components(self):
  with self.db.con() as c:
   c.execute('CREATE TABLE watchlist_versions(id INTEGER PRIMARY KEY)');c.execute('INSERT INTO watchlist_versions VALUES(1)');c.execute("INSERT INTO live_prices(symbol,last,received_at) VALUES('EUR/USD','1.1',?)",(now(),));c.execute('CREATE TABLE scanner_results(symbol TEXT PRIMARY KEY,score TEXT,signal TEXT,quality TEXT,momentum_pct TEXT,trend_pct TEXT,volatility_pct TEXT,spread_pct TEXT)');c.execute("INSERT INTO scanner_results VALUES('EUR/USD','80','BUY','VALID','1','1','.1','.05')")
  self.assertEqual(ForecastTracker(self.db).snapshot(['EUR/USD']),2);f=json.loads(self.db.rows('SELECT features_json FROM research_forecasts WHERE status=\'OPEN\' LIMIT 1')[0]['features_json']);self.assertEqual(f['schema_version'],3);self.assertIn('estimated_roundtrip_cost_pct',f);self.assertIn('cost_components_pct',f)
if __name__=='__main__':unittest.main()

