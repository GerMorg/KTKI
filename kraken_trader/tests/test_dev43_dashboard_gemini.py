import json,os,sys,tempfile,unittest
from unittest.mock import patch
os.environ['APP_DISABLE_PAPER_SCHEDULER']='1';os.environ['APP_DISABLE_RESEARCH_SCHEDULER']='1';os.environ['APP_DATA_DIR']=tempfile.mkdtemp()
sys.path.insert(0,os.path.join(os.path.dirname(__file__),'..','app'))
from db import DB,now
from external_ai import ExternalNewsAI
class Response:
 def __enter__(self):return self
 def __exit__(self,*args):pass
 def read(self):return json.dumps({'candidates':[{'content':{'parts':[{'text':json.dumps({'relevance':1,'sentiment':'positive','expected_impact':'medium','horizon':'short','confidence':1,'fact_status':'confirmed','priced_in':False,'topics':[],'affected_assets':[],'summary':'x','counterarguments':[]})}]}}]}).encode()
class Dev43Tests(unittest.TestCase):
 def test_gemini_request_and_response(self):
  db=DB(tempfile.mktemp());db.init()
  with db.con() as c:c.execute('CREATE TABLE news_items(id TEXT PRIMARY KEY,title TEXT,summary TEXT,fetched_at TEXT)');c.execute("INSERT INTO news_items VALUES('n','t','s',?)",(now(),))
  ai=ExternalNewsAI(db,{'ai_news_enabled':True,'ai_provider':'gemini','ai_api_key':'secret','ai_model':'gemini-test'})
  with patch('urllib.request.urlopen',return_value=Response()) as call:r=ai.analyze_pending()
  self.assertEqual(r['succeeded'],1);self.assertIn('generativelanguage.googleapis.com',call.call_args.args[0].full_url);self.assertEqual(call.call_args.args[0].headers['X-goog-api-key'],'secret')
 def test_dashboard_uses_available_data_despite_stream_error(self):
  import main
  with main.db.con() as c:c.execute("UPDATE stream_state SET state='ERROR' WHERE id=1");c.execute("UPDATE private_stream_state SET state='ERROR' WHERE id=1");c.execute("INSERT OR REPLACE INTO live_prices VALUES('BTC/EUR','1',NULL,NULL,NULL,?)",(now(),));c.execute("INSERT INTO portfolio_snapshots(created_at,total_eur,priced_asset_count,unpriced_asset_count,quality) VALUES(?,100,1,0,'COMPLETE')",(now(),))
  body=main.app.test_client().get('/').data.decode('utf-8');self.assertIn('DATEN VERFÃœGBAR',body);self.assertIn('KONTODATEN VERFÃœGBAR',body)
if __name__=='__main__':unittest.main()


