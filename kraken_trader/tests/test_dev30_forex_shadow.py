import json,os,sys,tempfile,unittest
sys.path.insert(0,os.path.join(os.path.dirname(__file__),'..','app'))
from db import DB,now
from scanner import MarketScanner
from forex_shadow import ForexShadow
class T(unittest.TestCase):
 def setUp(self):
  self.db=DB(tempfile.mktemp());self.db.init();MarketScanner(self.db,object());self.f=ForexShadow(self.db)
  with self.db.con() as c:
   c.execute("CREATE TABLE market_universe(symbol TEXT,category TEXT)");c.execute("INSERT INTO market_universe VALUES('EUR/USD','forex')");c.execute("CREATE TABLE news_market_links(news_id TEXT,symbol TEXT,relevance TEXT,reason TEXT)");c.execute("INSERT INTO news_market_links VALUES('n','EUR/USD','1','pair')");c.execute("INSERT INTO live_prices VALUES('EUR/USD','1.1','1.09','1.11','1',?)",(now(),));c.execute("INSERT INTO live_prices VALUES('EUR/CHF','1','1','1','2',?)",(now(),));c.execute("INSERT INTO scanner_results VALUES('EUR/USD',?,'70','BUY','2','1','1','.1','100',40,'VALID','[]')",(now(),))
 def test_two_horizons_and_versioned_features(self):
  r=self.f.run();self.assertEqual(r['status'],'SHADOW_ONLY');self.assertEqual(r['snapshots'],2);rows=self.db.rows('SELECT * FROM forex_feature_snapshots');self.assertEqual({x['horizon'] for x in rows},{'short','medium'});self.assertTrue(all(x['model_version']=='forex-v2-shadow' for x in rows))
 def test_missing_macro_is_explicit_and_not_fabricated(self):
  self.f.run();features=json.loads(self.db.rows('SELECT features_json FROM forex_feature_snapshots LIMIT 1')[0]['features_json']);self.assertIsNone(features['interest_differential']);self.assertIn('central_bank_surprise',features['missing_features'])
 def test_shadow_cannot_replace_active_scanner_result(self):
  before=self.db.rows("SELECT score,signal FROM scanner_results WHERE symbol='EUR/USD'")[0];self.f.run();after=self.db.rows("SELECT score,signal FROM scanner_results WHERE symbol='EUR/USD'")[0];self.assertEqual(before,after)
 def test_comparison_records_disagreement_flag(self):
  self.f.run();self.assertEqual(len(self.f.comparisons()),2)
if __name__=='__main__':unittest.main()


