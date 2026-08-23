import os, sys, tempfile, unittest
os.environ['APP_DATA_DIR']=tempfile.mkdtemp(); sys.path.insert(0,os.path.join(os.path.dirname(__file__),'..','app'))
import main
class Tests(unittest.TestCase):
 def setUp(self): self.c=main.app.test_client()
 def test_pages(self):
  self.assertEqual(self.c.get('/').status_code,200); self.assertEqual(self.c.get('/settings').status_code,200)
 def test_hard_disabled(self): self.assertFalse(self.c.get('/health').json['real_trading'])
 def test_secret_not_exposed(self): self.assertNotIn(b'kraken_api_secret',self.c.get('/').data)
 def test_paper_seed(self): self.assertTrue(main.db.rows("SELECT * FROM paper_balances WHERE asset='EUR'"))
if __name__=='__main__': unittest.main()
