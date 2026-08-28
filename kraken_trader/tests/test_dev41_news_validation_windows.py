import json,os,sys,tempfile,unittest
from datetime import datetime,timezone,timedelta
sys.path.insert(0,os.path.join(os.path.dirname(__file__),'..','app'))
from db import DB
from news_learning import NewsLearning

class Dev41NewsWindows(unittest.TestCase):
 def setUp(self):
  self.db=DB(tempfile.mktemp());self.db.init();self.nl=NewsLearning(self.db)
  with self.db.con() as c:
   c.execute('CREATE TABLE news_sources(name TEXT PRIMARY KEY,source_class TEXT)')
   c.execute('CREATE TABLE news_items(id TEXT PRIMARY KEY,title TEXT,summary TEXT,source_name TEXT,published_at TEXT,fetched_at TEXT)')
   c.execute('CREATE TABLE external_news_ai_results(news_id TEXT PRIMARY KEY,created_at TEXT,status TEXT,result_json TEXT,error TEXT)')
   c.execute("INSERT INTO news_sources VALUES('primary','primary')")
   base=datetime(2026,1,1,tzinfo=timezone.utc)
   for i in range(20):
    positive=i%2==0;stamp=(base+timedelta(hours=i)).isoformat();title=('gain ' if positive else 'loss ')+str(i)
    ai={'relevance':1,'sentiment':'positive' if positive else 'negative','expected_impact':'medium','confidence':1,'priced_in':False}
    c.execute("INSERT INTO news_items VALUES(?,?,?,'primary',?,?)",(str(i),title,'',stamp,stamp))
    c.execute("INSERT INTO external_news_ai_results VALUES(?,?, 'VALID',?,NULL)",(str(i),stamp,json.dumps(ai)))
 def test_time_split_is_ordered_and_disjoint(self):
  training,validation,policy=self.nl._split(self.nl._samples(),.30,3)
  self.assertEqual((len(training),len(validation)),(14,6));self.assertTrue(policy['no_overlap'])
  self.assertLessEqual(training[-1]['observed_at'],validation[0]['observed_at'])
 def test_candidate_persists_window_provenance(self):
  result=self.nl.propose(min_sample=10,min_improvement=0)
  row=self.db.rows('SELECT * FROM news_model_candidates WHERE id=?',(result['candidate_id'],))[0]
  self.assertEqual(row['training_count'],14);self.assertEqual(row['validation_count'],6)
  self.assertEqual(json.loads(row['window_policy_json'])['kind'],'EXPANDING_TIME_SPLIT')
 def test_approval_rejects_changed_sample(self):
  result=self.nl.propose(min_sample=10,min_improvement=0)
  if result['status']!='PENDING':self.skipTest('Deterministischer Kandidat erfüllt Vergleichsgate nicht')
  with self.db.con() as c:
   c.execute("INSERT INTO news_items VALUES('new','gain','','primary','2026-02-01T00:00:00+00:00','2026-02-01T00:00:00+00:00')")
   c.execute("INSERT INTO external_news_ai_results VALUES('new','2026-02-01T00:00:00+00:00','VALID',?,NULL)",(json.dumps({'relevance':1,'sentiment':'positive','expected_impact':'medium','confidence':1,'priced_in':False}),))
  self.assertEqual(self.nl.decide(result['candidate_id'],'approve')['status'],'REJECTED_RECHECK')
 def test_schema_migration_is_idempotent(self):
  self.nl.ensure();self.nl.ensure();cols={x['name'] for x in self.db.rows('PRAGMA table_info(news_model_candidates)')}
  self.assertIn('validation_start_at',cols);self.assertIn('window_policy_json',cols)

if __name__=='__main__':unittest.main()
