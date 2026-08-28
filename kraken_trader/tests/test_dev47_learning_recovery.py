import os,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,os.path.join(os.path.dirname(__file__),'..','app'))
from db import DB,now
from news_learning import NewsLearning
from news_prefilter import NewsPrefilter
from external_ai import ExternalNewsAI
class Dev47LearningRecoveryTests(unittest.TestCase):
 def setUp(self):
  self.db=DB(tempfile.mktemp());self.db.init();NewsPrefilter(self.db);ExternalNewsAI(self.db,{});self.news=NewsLearning(self.db)
 def test_empty_news_database_has_actionable_diagnostic(self):
  status=self.news.data_status();self.assertEqual(status['status'],'NO_NEWS_ITEMS');self.assertEqual(status['missing'],10);self.assertFalse(status['ready'])
 def test_insufficient_result_contains_diagnostic(self):
  result=self.news.propose();self.assertEqual(result['status'],'INSUFFICIENT_DATA');self.assertEqual(result['reason'],'NO_NEWS_ITEMS');self.assertIn('data_status',result)
 def test_valid_ai_samples_make_status_ready(self):
  import json
  with self.db.con() as c:
   c.execute("INSERT INTO news_sources(name,url,kind,source_class,enabled) VALUES('s','u','rss','primary',1)")
   for i in range(10):
    nid='n'+str(i);c.execute("INSERT INTO news_items(id,source_name,title,summary,url,published_at,fetched_at) VALUES(?,?,?,?,?,?,?)",(nid,'s','growth','summary','u'+str(i),now(),now()));c.execute("INSERT INTO external_news_ai_results(news_id,created_at,status,result_json,error) VALUES(?,?,?,?,NULL)",(nid,now(),'VALID',json.dumps({'relevance':1,'sentiment':'positive','expected_impact':'high','confidence':1})))
  status=self.news.data_status();self.assertTrue(status['ready']);self.assertEqual(status['sample_count'],10)
 def test_main_imports_families_and_news_page_has_diagnostics(self):
  source=(Path(__file__).parents[1]/'app'/'main.py').read_text('utf-8');self.assertIn('from strategy_profiles import FAMILIES',source);self.assertIn('data_status=news_learning.data_status()',source);self.assertIn('AI auswerten',source)
