import os,sys,tempfile,unittest
sys.path.insert(0,os.path.join(os.path.dirname(__file__),'..','app'))
from db import DB,now
from paper_engine import PaperEngine
class Dev9Tests(unittest.TestCase):
 def setUp(self):
  self.db=DB(tempfile.mktemp());self.db.init(1000);self.e=PaperEngine(self.db,1000,40,10,20,100);self.db.set_setting('automation_enabled','true');self.db.set_setting('scanner_required','true')
  with self.db.con() as c:
   c.execute("INSERT OR REPLACE INTO product_categories VALUES('crypto_spot','Kryptowährungen (Spot)',1,?)",(now(),));c.execute("INSERT OR REPLACE INTO market_universe VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",('BTC/EUR','currency','crypto_spot','BTC','EUR','online','0.0001','5',8,1,'[]','[]','BTCEUR',now()));c.execute("INSERT OR REPLACE INTO market_category_members VALUES('BTC/EUR','currency','crypto_spot')");c.execute('INSERT OR REPLACE INTO live_prices VALUES(?,?,?,?,?,?)',('BTC/EUR','50000','49990','50010','2',now()))
   c.execute('INSERT OR REPLACE INTO pair_rules VALUES(?,?,?,?,?,?,?,?)',('BTC/EUR','0.0001','5',8,1,'0.40','online',now()))
 def scanner(self,signal='BUY',quality='VALID',score='80'):
  with self.db.con() as c:c.execute('INSERT OR REPLACE INTO scanner_results VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',('BTC/EUR',now(),score,signal,'2','1','1','0.04','100000',50,quality,'[]'))
 def test_missing_scanner_fails_closed(self):
  self.e.run();self.assertFalse(self.db.rows('SELECT * FROM paper_trades'));self.assertEqual(self.db.rows('SELECT data_quality FROM paper_decisions')[0]['data_quality'],'SCANNER_MISSING')
 def test_valid_scanner_buy_uses_pair_fee(self):
  self.scanner();self.e.run();t=self.db.rows('SELECT * FROM paper_trades')[0];self.assertGreater(float(t['fee_eur']),0);self.assertIn('fee_rate_pct',t['decision_json'])
 def test_minimum_order_blocks(self):
  self.e.trade_eur=__import__('decimal').Decimal('1');self.scanner();self.e.run();self.assertFalse(self.db.rows('SELECT * FROM paper_trades'));self.assertIn('Mindest',self.db.rows('SELECT reason FROM paper_decisions')[0]['reason'])
 def test_avoid_sells_existing_position(self):
  with self.db.con() as c:c.execute('INSERT INTO paper_positions VALUES(?,?,?,?)',('BTC/EUR','0.001','49000',now()))
  self.scanner('AVOID','VALID','20');self.e.run();self.assertEqual(self.db.rows('SELECT side FROM paper_trades')[0]['side'],'SELL')
