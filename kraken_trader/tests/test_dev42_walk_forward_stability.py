import json,os,sys,tempfile,unittest
from datetime import datetime,timezone,timedelta
sys.path.insert(0,os.path.join(os.path.dirname(__file__),'..','app'))
from db import DB
from news_learning import NewsLearning

class Dev42WalkForward(unittest.TestCase):
 def setUp(self):
  self.db=DB(tempfile.mktemp());self.db.init();self.nl=NewsLearning(self.db)
  with self.db.con() as c:
   c.execute('CREATE TABLE news_sources(name TEXT PRIMARY KEY,source_class TEXT)')
   c.execute('CREATE TABLE news_items(id TEXT PRIMARY KEY,title TEXT,summary TEXT,source_name TEXT,published_at TEXT,fetched_at TEXT)')
   c.execute('CREATE TABLE external_news_ai_results(news_id TEXT PRIMARY KEY,created_at TEXT,status TEXT,result_json TEXT,error TEXT)')
   c.execute("INSERT INTO news_sources VALUES('primary','primary')")
   base=datetime(2026,1,1,tzinfo=timezone.utc)
   for i in range(24):
    pos=i%2==0;stamp=(base+timedelta(hours=i)).isoformat();title=('gain ' if pos else 'loss ')+str(i)
    ai={'relevance':1,'sentiment':'positive' if pos else 'negative','expected_impact':'medium','confidence':1,'priced_in':False}
    c.execute("INSERT INTO news_items VALUES(?,?,?,'primary',?,?)",(str(i),title,'',stamp,stamp))
    c.execute("INSERT INTO external_news_ai_results VALUES(?,?,'VALID',?,NULL)",(str(i),stamp,json.dumps(ai)))
 def test_walk_forward_windows_are_strictly_ordered(self):
  rows=self.nl._samples();active=json.loads(self.nl.active()['parameters_json']);walk=self.nl._walk_forward(rows,active,active,3,3,0)
  self.assertEqual(walk['status'],'VALID');self.assertEqual(len(walk['windows']),3)
  for x in walk['windows']:self.assertLess(x['training_end_at'],x['validation_start_at'])
 def test_candidate_persists_stability_evidence(self):
  result=self.nl.propose(min_sample=10,min_improvement=0,walk_forward_windows=3,required_stable_windows=2)
  row=self.db.rows('SELECT * FROM news_model_candidates WHERE id=?',(result['candidate_id'],))[0]
  self.assertEqual(row['required_stable_windows'],2);self.assertEqual(len(json.loads(row['walk_forward_json'])['windows']),3)
 def test_insufficient_walk_forward_fails_closed(self):
  rows=self.nl._samples()[:8];active=json.loads(self.nl.active()['parameters_json'])
  self.assertEqual(self.nl._walk_forward(rows,active,active,3,3,0)['status'],'INSUFFICIENT')
 def test_migration_idempotent(self):
  self.nl.ensure();self.nl.ensure();cols={x['name'] for x in self.db.rows('PRAGMA table_info(news_model_candidates)')}
  self.assertTrue({'walk_forward_json','stable_window_count','required_stable_windows'}<=cols)
if __name__=='__main__':unittest.main()






