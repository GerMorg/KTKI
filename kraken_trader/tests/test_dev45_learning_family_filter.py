import os,sys,tempfile,unittest
sys.path.insert(0,os.path.join(os.path.dirname(__file__),'..','app'))
from db import DB,now
from controlled_learning import ControlledLearning
class Dev45LearningFamilyFilterTests(unittest.TestCase):
 def setUp(self):
  self.db=DB(tempfile.mktemp());self.db.init();self.learning=ControlledLearning(self.db)
  with self.db.con() as c:
   for family in ('forex','xstocks'):
    c.execute("INSERT INTO learning_candidates(created_at,family,status,base_version,sample_count,active_accuracy,candidate_accuracy,improvement,ci_low,ci_high,parameters_json,reason,decided_at,gate_results_json,gate_policy_json) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",(now(),family,'REJECTED',1,0,'0','0','0','0','0','{}','test',now(),'[]','{}'))
   ids={r['family']:r['id'] for r in c.execute('SELECT id,family FROM learning_candidates').fetchall()}
   for family,cid in ids.items(): c.execute("INSERT INTO learning_candidate_metrics(candidate_id,horizon_hours,sample_count,active_decisions,candidate_decisions,active_coverage,candidate_coverage,active_net_return,candidate_net_return,net_return_improvement,active_max_drawdown,candidate_max_drawdown,details_json) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",(cid,24,1,1,1,'1','1','0','0','0','0','0','{}'))
 def test_candidates_are_filtered_by_family(self):
  self.assertEqual({x['family'] for x in self.learning.candidates('xstocks')},{'xstocks'})
 def test_versions_are_filtered_by_family(self):
  self.assertTrue(all(x['family']=='crypto_spot' for x in self.learning.versions('crypto_spot')))
 def test_metrics_are_filtered_through_candidate_family(self):
  candidate_ids={x['id'] for x in self.learning.candidates('forex')}
  metric_ids={x['candidate_id'] for x in self.learning.metrics(family='forex')}
  self.assertTrue(metric_ids);self.assertTrue(metric_ids.issubset(candidate_ids))






