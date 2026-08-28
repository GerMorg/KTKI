import os,sys,tempfile,unittest
sys.path.insert(0,os.path.join(os.path.dirname(__file__),'..','app'))
from db import DB,now
from paper_engine import PaperEngine
from market_universe import MarketUniverse
from scanner import MarketScanner
class Dev9Tests(unittest.TestCase):
 def setUp(self):
  self.db=DB(tempfile.mktemp());self.db.init(1000);MarketUniverse(self.db,object());MarketScanner(self.db,object());self.e=PaperEngine(self.db,1000,40,10,20,100);self.db.set_setting('automation_enabled','true');self.db.set_setting('scanner_required','true')
  with self.db.con() as c:
   c.execute("INSERT OR REPLACE INTO product_categories VALUES('crypto_spot','Kryptowährungen (Spot)',1,?)",(now(),));c.execute("INSERT OR REPLACE INTO market_universe(symbol,asset_class,category,base_asset,quote_asset,status,ordermin,costmin,lot_decimals,pair_decimals,leverage_buy_json,leverage_sell_json,source_key,updated_at,canonical_id,product_kind,metadata_json) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",('BTC/EUR','currency','crypto_spot','BTC','EUR','online','0.0001','5',8,1,'[]','[]','BTCEUR',now(),'crypto_spot:BTC','crypto_spot','{}'));c.execute("INSERT OR REPLACE INTO market_category_members VALUES('BTC/EUR','currency','crypto_spot')");c.execute("INSERT OR REPLACE INTO research_watchlist VALUES('BTC/EUR','crypto_spot','80','ANALYZED',?,1,'[]')",(now(),));c.execute('INSERT OR REPLACE INTO live_prices VALUES(?,?,?,?,?,?)',('BTC/EUR','50000','49990','50010','2',now()))
 def scanner(self,signal='BUY',quality='VALID',score='80'):
  with self.db.con() as c:c.execute('INSERT OR REPLACE INTO scanner_results VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',('BTC/EUR',now(),score,signal,'2','1','1','0.04','100000',50,quality,'[]'))
 def test_missing_scanner_fails_closed(self):
  self.e.run();self.assertFalse(self.db.rows('SELECT * FROM paper_trades'));self.assertFalse(self.db.rows('SELECT * FROM paper_decisions'))
 def test_valid_scanner_buy_uses_pair_fee(self):
  self.scanner();self.e.run();t=self.db.rows('SELECT * FROM paper_trades')[0];self.assertGreater(float(t['fee_eur']),0);self.assertIn('trade_fee_bps',t['decision_json'])
 def test_minimum_order_blocks(self):
  self.db.rows("UPDATE market_universe SET ordermin='100' WHERE symbol='BTC/EUR'");self.scanner();self.e.run();self.assertFalse(self.db.rows('SELECT * FROM paper_trades'));self.assertIn('Mindest',self.db.rows('SELECT reason FROM paper_decisions')[0]['reason'])
 def test_avoid_sells_existing_position(self):
  with self.db.con() as c:c.execute('INSERT INTO paper_positions VALUES(?,?,?,?)',('BTC/EUR','0.001','49000',now()))
  self.scanner('AVOID','VALID','20');self.e.run();self.assertFalse(self.db.rows('SELECT side FROM paper_trades'))

