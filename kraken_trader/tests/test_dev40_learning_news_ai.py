import json,os,sys,tempfile,unittest
from unittest.mock import patch
from pathlib import Path
sys.path.insert(0,os.path.join(os.path.dirname(__file__),'..','app'))
from db import DB,now
from external_ai import ExternalNewsAI
class Tests(unittest.TestCase):
 def setUp(self):
  self.db=DB(tempfile.mktemp());self.db.init()
  with self.db.con() as c:c.execute("CREATE TABLE news_items(id TEXT PRIMARY KEY,title TEXT,summary TEXT,fetched_at TEXT,topics_json TEXT)");c.execute("INSERT INTO news_items VALUES('n','Titel','Text',?,?)",(now(),json.dumps(['inflation'])))
 def result(self):return {'relevance':.8,'sentiment':-.2,'expected_impact':.4,'horizon':'days','confidence':.7,'fact_status':'reported','priced_in':'unknown','topics':['inflation','rates'],'affected_assets':['EUR'],'summary':'x','counterarguments':[]}
 def test_google_transport_and_calibration(self):
  a=ExternalNewsAI(self.db,{'ai_news_enabled':True,'ai_api_key':'k','ai_provider':'google_ai_studio','ai_model':'gemini-test'})
  response={'candidates':[{'content':{'parts':[{'text':json.dumps(self.result())}]}}]}
  with patch.object(a,'_post',return_value=response) as post:r=a.analyze_pending()
  self.assertEqual(r['succeeded'],1);self.assertIn('googleapis.com',post.call_args.args[0]);self.assertEqual(json.loads(a.calibration()[0]['missing_local_topics_json']),['rates'])
 def test_legacy_learning_removed(self):self.assertFalse((Path(__file__).parents[1]/'app'/'learning_approval.py').exists())
if __name__=='__main__':unittest.main()
