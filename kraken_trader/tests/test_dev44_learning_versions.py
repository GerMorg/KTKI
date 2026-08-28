import os,sys,tempfile,unittest
from pathlib import Path
os.environ['APP_DISABLE_PAPER_SCHEDULER']='1'
os.environ['APP_DISABLE_WEBSOCKET']='1'
sys.path.insert(0,os.path.join(os.path.dirname(__file__),'..','app'))
from db import DB
from controlled_learning import ControlledLearning

class Dev44LearningVersionTests(unittest.TestCase):
 def setUp(self):
  self.db=DB(tempfile.mktemp());self.db.init();self.learning=ControlledLearning(self.db)
 def test_active_versions_include_every_learning_family(self):
  rows=self.learning.active_versions()
  self.assertEqual({x['family'] for x in rows},{'forex','xstocks','crypto_spot'})
  self.assertTrue(all(x['status']=='ACTIVE' for x in rows))
 def test_learning_page_renders_all_current_versions(self):
  source=(Path(__file__).parents[1]/'app'/'main.py').read_text('utf-8')
  self.assertIn('Aktuelle Versionen',source)
  self.assertIn("'forex':'Forex'",source)
  self.assertIn("'xstocks':'xStocks'",source)
  self.assertIn("'crypto_spot':'Krypto Spot'",source)

if __name__=='__main__':unittest.main()
