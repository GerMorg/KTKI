import json,os,sys,tempfile,unittest
sys.path.insert(0,os.path.join(os.path.dirname(__file__),'..','app'))
from db import DB,now
from external_ai import ExternalNewsAI,PROMPT_VERSION,SCHEMA_VERSION
class Tests(unittest.TestCase):
 def setUp(self):
  self.db=DB(tempfile.mktemp());self.db.init()
  with self.db.con() as c:c.execute("CREATE TABLE news_items(id TEXT PRIMARY KEY,source_name TEXT,title TEXT,url TEXT,published_at TEXT,fetched_at TEXT,summary TEXT,topics_json TEXT,event_types_json TEXT,raw_json TEXT)");c.execute("INSERT INTO news_items VALUES('N1','Test','Central bank changes rates','u','',?,'Policy decision','[]','[]','{}')",(now(),))
 def response(self,**overrides):
  value={'relevance':.8,'sentiment':-.2,'expected_impact':-.4,'horizon':'days','confidence':.7,'fact_status':'confirmed','priced_in':'partial','topics':['monetary_policy'],'affected_assets':['EUR'],'summary':'Zinsentscheidung','counterarguments':['Markt hatte sie erwartet']};value.update(overrides);return {'choices':[{'message':{'content':json.dumps(value)}}]}
 def test_structured_result_is_persisted(self):
  ai=ExternalNewsAI(self.db,{'ai_news_enabled':True,'ai_api_key':'SECRET','ai_model':'test'},lambda payload:self.response());r=ai.analyze_pending();self.assertEqual(r['succeeded'],1);row=self.db.rows('SELECT * FROM ai_news_analyses')[0];self.assertEqual(row['status'],'VALID');self.assertEqual(row['prompt_version'],PROMPT_VERSION);self.assertEqual(row['schema_version'],SCHEMA_VERSION)
 def test_invalid_result_fails_closed(self):
  ai=ExternalNewsAI(self.db,{'ai_news_enabled':True,'ai_api_key':'SECRET','ai_model':'test'},lambda payload:{'choices':[{'message':{'content':'{}'}}]});r=ai.analyze_pending();self.assertEqual(r['failed'],1);self.assertEqual(self.db.rows('SELECT status FROM ai_news_analyses')[0]['status'],'ERROR')
 def test_secret_is_never_persisted_or_audited(self):
  ai=ExternalNewsAI(self.db,{'ai_news_enabled':True,'ai_api_key':'VERY_SECRET','ai_model':'test'},lambda payload:self.response());ai.analyze_pending();dump=json.dumps(self.db.rows('SELECT * FROM ai_news_analyses'))+json.dumps(self.db.rows('SELECT * FROM audit'));self.assertNotIn('VERY_SECRET',dump)
 def test_disabled_without_key(self):
  ai=ExternalNewsAI(self.db,{'ai_news_enabled':True});self.assertEqual(ai.analyze_pending()['status'],'DISABLED')
