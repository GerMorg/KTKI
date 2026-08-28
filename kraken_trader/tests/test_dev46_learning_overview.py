import os,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,os.path.join(os.path.dirname(__file__),'..','app'))
from db import DB,now
from controlled_learning import ControlledLearning
class Dev46LearningOverviewTests(unittest.TestCase):
 def setUp(self):
  self.db=DB(tempfile.mktemp());self.db.init();self.learning=ControlledLearning(self.db)
 def add_candidate(self,family,status):
  with self.db.con() as c:c.execute("INSERT INTO learning_candidates(created_at,family,status,base_version,sample_count,active_accuracy,candidate_accuracy,improvement,ci_low,ci_high,parameters_json,reason,decided_at,gate_results_json,gate_policy_json) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",(now(),family,status,1,0,'0','0','0','0','0','{}','test',now() if status!='PENDING' else None,'[]','{}'))
 def test_overview_contains_every_family_and_active_version(self):
  rows=self.learning.family_overview();self.assertEqual({x['family'] for x in rows},{'forex','xstocks','crypto_spot'});self.assertTrue(all(x['active_version']==1 for x in rows))
 def test_overview_counts_pending_and_reports_latest(self):
  self.add_candidate('xstocks','REJECTED');self.add_candidate('xstocks','PENDING');row=next(x for x in self.learning.family_overview() if x['family']=='xstocks');self.assertEqual(row['pending_count'],1);self.assertEqual(row['rejected_count'],1);self.assertEqual(row['latest_status'],'PENDING')
 def test_route_fails_closed_to_forex_for_unknown_family(self):
  source=(Path(__file__).parents[1]/'app'/'main.py').read_text('utf-8');self.assertIn("family=family if family in FAMILIES else 'forex'",source)
 def test_gui_shows_pending_and_latest_candidate_columns(self):
  source=(Path(__file__).parents[1]/'app'/'main.py').read_text('utf-8');self.assertIn('<th>Offen</th>',source);self.assertIn('<th>Letzter Kandidat</th>',source)

