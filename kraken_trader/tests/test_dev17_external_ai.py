import json,os,sys,tempfile,unittest
sys.path.insert(0,os.path.join(os.path.dirname(__file__),'..','app'))
from db import DB,now
from external_ai import ExternalNewsAI
class T(unittest.TestCase):
 def setUp(self):
  self.db=DB(tempfile.mktemp());self.db.init()
  with self.db.con() as c:c.execute('CREATE TABLE news_items(id TEXT PRIMARY KEY,source_name TEXT,title TEXT,url TEXT,published_at TEXT,fetched_at TEXT,summary TEXT)');c.execute("INSERT INTO news_items VALUES('n','s','t','u','',?,'x')",(now(),))
 def response(self):
  x={'relevance':.8,'sentiment':0,'expected_impact':.2,'horizon':'days','confidence':.7,'fact_status':'confirmed','priced_in':'partial','topics':[],'affected_assets':[],'summary':'x','counterarguments':[]};return {'choices':[{'message':{'content':json.dumps(x)}}]}
 def test_valid(self):
  a=ExternalNewsAI(self.db,{'ai_news_enabled':True,'ai_api_key':'secret','ai_model':'test'},lambda p:self.response());self.assertEqual(a.analyze_pending()['succeeded'],1)
 def test_invalid_fails_closed(self):
  a=ExternalNewsAI(self.db,{'ai_news_enabled':True,'ai_api_key':'secret','ai_model':'test'},lambda p:{'choices':[{'message':{'content':'{}'}}]});self.assertEqual(a.analyze_pending()['failed'],1)
 def test_disabled_without_key(self):self.assertEqual(ExternalNewsAI(self.db,{'ai_news_enabled':True}).analyze_pending()['status'],'DISABLED')


