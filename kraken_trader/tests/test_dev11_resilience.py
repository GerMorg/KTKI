import os,sys,tempfile,unittest
sys.path.insert(0,os.path.join(os.path.dirname(__file__),'..','app'))
from db import DB
from scanner import MarketScanner
class Fake:
 def ticker(self,s,*args):return {x:{'b':['100'],'a':['100.1']} for x in s}
 def ohlc(self,s,i,*args):return {s:[[x,'100','101','99',str(100+x/10),'100','1000',2] for x in range(32)],'last':0}
class Tests(unittest.TestCase):
 def setUp(self):self.db=DB(tempfile.mktemp());self.db.init();self.s=MarketScanner(self.db,Fake())
 def test_bounded_rotating_batches(self):
  symbols=[f'S{x}/EUR' for x in range(25)];a=self.s.run(symbols,60,limit=10,delay_seconds=0);b=self.s.run(symbols,60,limit=10,delay_seconds=0)
  self.assertEqual(a['processed'],10);self.assertEqual(b['batch_start'],10);self.assertEqual(len(self.db.rows('SELECT * FROM scanner_results')),20)
 def test_busy_lock_is_fail_visible(self):
  self.s.lock.acquire();r=self.s.run(['BTC/EUR'],60,1,0);self.s.lock.release();self.assertEqual(r['status'],'BUSY')
 def test_utf8_source_has_no_mojibake(self):
  from pathlib import Path
  text=(Path(__file__).parents[1]/'app'/'main.py').read_text('utf-8');self.assertIn('Übersicht',text);self.assertNotIn('à',text)
 def test_html_declares_utf8(self):
  os.environ['APP_DISABLE_PAPER_SCHEDULER']='1';import main
  response=main.app.test_client().get('/');self.assertIn('charset=utf-8',response.headers['Content-Type'].lower());self.assertIn('Übersicht',response.data.decode('utf-8'))
