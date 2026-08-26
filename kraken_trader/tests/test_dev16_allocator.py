import json,os,sys,tempfile,unittest
sys.path.insert(0,os.path.join(os.path.dirname(__file__),'..','app'))
from db import DB,now
from paper_engine import PaperEngine
from portfolio_allocator import PortfolioAllocator
from scanner import MarketScanner
from real_execution_adapter import RealExecutionAdapter,RealExecutionDisabled
class Tests(unittest.TestCase):
 def setUp(self):
  self.db=DB(tempfile.mktemp());self.db.init();PaperEngine(self.db);MarketScanner(self.db,object())
  with self.db.con() as c:
   c.execute("INSERT INTO research_watchlist VALUES('BTC/EUR','crypto_spot','80','ANALYZED',?,1,'[]')",(now(),));c.execute("INSERT INTO scanner_results VALUES('BTC/EUR',?,'80','BUY','2','1','1','.1','100',50,'VALID','[]')",(now(),));c.execute("CREATE TABLE IF NOT EXISTS market_universe(symbol TEXT,asset_class TEXT,category TEXT,base_asset TEXT,quote_asset TEXT,status TEXT,ordermin TEXT,costmin TEXT,lot_decimals INTEGER,pair_decimals INTEGER,leverage_buy_json TEXT,leverage_sell_json TEXT,source_key TEXT,updated_at TEXT,PRIMARY KEY(symbol,asset_class))");c.execute("INSERT INTO market_universe VALUES('BTC/EUR','currency','crypto_spot','BTC','EUR','online',NULL,NULL,8,2,'[2,3,5]','[]','X',?)",(now(),))
 def test_leverage_comes_from_metadata_and_limit(self):
  self.db.set_setting('paper_leverage_enabled','true');self.db.set_setting('paper_max_leverage','3');p=PortfolioAllocator(self.db).plans(1000)[0];self.assertIn(p['leverage'],(1,2,3));self.assertLessEqual(p['leverage'],3)
 def test_real_execution_is_disabled(self):
  with self.assertRaises(RealExecutionDisabled):RealExecutionAdapter().execute({'symbol':'BTC/EUR','action':'BUY','amount':'1'})


