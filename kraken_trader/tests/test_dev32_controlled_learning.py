import os,sys,tempfile,unittest
sys.path.insert(0,os.path.join(os.path.dirname(__file__),'..','app'))
from db import DB
from controlled_learning import ControlledLearning,FAMILIES
class T(unittest.TestCase):
 def setUp(self):
  self.db=DB(tempfile.mktemp());self.db.init();self.db.set('learning_required_horizons','0');self.db.set('learning_min_horizon_samples','1');self.db.set('learning_min_candidate_coverage','0');self.db.set('learning_min_net_return_improvement','0');self.l=ControlledLearning(self.db)
  with self.db.con() as c:
   c.execute('CREATE TABLE research_forecasts(id INTEGER PRIMARY KEY,symbol TEXT,direction TEXT,scanner_score TEXT)');c.execute('CREATE TABLE forecast_evaluations(forecast_id INTEGER PRIMARY KEY,direction_correct INTEGER,actual_return_pct TEXT)');c.execute('CREATE TABLE market_universe(symbol TEXT,category TEXT)');c.execute("INSERT INTO market_universe VALUES('EUR/USD','forex')")
 def seed(self,n=12,correct=12,score=80):
  with self.db.con() as c:
   for i in range(1,n+1):c.execute('INSERT INTO research_forecasts VALUES(?,?,?,?)',(i,'EUR/USD','UP',str(score)));c.execute('INSERT INTO forecast_evaluations VALUES(?,?,?)',(i,1 if i<=correct else 0,'1'))
 def test_separate_families_have_active_defaults(self):
  self.assertEqual({x['family'] for x in self.l.versions() if x['status']=='ACTIVE'},set(FAMILIES))
 def test_minimum_sample_gate(self):
  self.seed(5);r=self.l.propose('forex',10);self.assertEqual(r['status'],'INSUFFICIENT_DATA')
 def test_candidate_has_shadow_rows_and_confidence_interval(self):
  self.seed();r=self.l.propose('forex',10,0);self.assertEqual(r['status'],'PENDING');p=self.l.candidates()[0];self.assertLessEqual(float(p['ci_low']),float(p['candidate_accuracy']));self.assertGreaterEqual(float(p['ci_high']),float(p['candidate_accuracy']));self.assertEqual(len(self.db.rows('SELECT * FROM learning_shadow_results')),12)
 def test_no_automatic_activation_and_explicit_approval(self):
  self.seed();before=self.l.active('forex')['version'];r=self.l.propose('forex',10,0);self.assertEqual(self.l.active('forex')['version'],before);approved=self.l.decide(r['candidate_id'],'approve');self.assertEqual(approved['status'],'APPROVED');self.assertEqual(self.l.active('forex')['version'],before+1)
 def test_reject_and_full_rollback(self):
  self.seed();r=self.l.propose('forex',10,0);self.assertEqual(self.l.decide(r['candidate_id'],'reject')['status'],'REJECTED');self.assertEqual(self.l.rollback('forex',1)['status'],'ROLLED_BACK')
if __name__=='__main__':unittest.main()



