import os,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,os.path.join(os.path.dirname(__file__),'..','app'))
from db import DB
from controlled_learning import ControlledLearning
class Dev44LearningVersionTests(unittest.TestCase):
 def setUp(self):
  self.db=DB(tempfile.mktemp());self.db.init();self.learning=ControlledLearning(self.db)
 def test_active_versions_include_every_learning_family(self):
  self.assertEqual({x['family'] for x in self.learning.active_versions()},{'forex','xstocks','crypto_spot'})
 def test_source_renders_all_current_versions(self):
  source=(Path(__file__).parents[1]/'app'/'main.py').read_text('utf-8')
  self.assertIn('Aktuelle Versionen',source);self.assertIn("'xstocks':'xStocks'",source);self.assertIn("'crypto_spot':'Krypto Spot'",source)



