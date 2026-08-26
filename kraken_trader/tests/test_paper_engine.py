import os,sys,tempfile,unittest
sys.path.insert(0,os.path.join(os.path.dirname(__file__),'..','app'))
from db import DB,now
from paper_engine import PaperEngine
from market_universe import MarketUniverse
class PaperTests(unittest.TestCase):
 def setUp(self):
  self.db=DB(tempfile.mktemp());self.db.init(1000);MarketUniverse(self.db,object());self.db.set_setting('scanner_required','false');self.e=PaperEngine(self.db,1000,40,10,10,25)
  with self.db.con() as c:
   c.execute("INSERT OR REPLACE INTO live_prices VALUES(?,?,?,?,?,?)",('BTC/EUR','50000','49990','50010','2.0',now()))
   c.execute("INSERT OR REPLACE INTO allowlist VALUES('BTC/EUR',1)");c.execute("INSERT OR REPLACE INTO research_watchlist VALUES('BTC/EUR','crypto_spot','80','ANALYZED',?,1,'[]')",(now(),));c.execute("CREATE TABLE scanner_results(symbol TEXT PRIMARY KEY,scanned_at TEXT,score TEXT,signal TEXT,momentum_pct TEXT,volatility_pct TEXT,trend_pct TEXT,spread_pct TEXT,volume_quote TEXT,data_points INTEGER,quality TEXT,reasons_json TEXT)");c.execute("INSERT INTO scanner_results VALUES('BTC/EUR',?,'80','BUY','2','1','1','.1','100',50,'VALID','[]')",(now(),))
 def test_disabled_logs_no_trade(self):
  self.e.run();self.assertEqual(len(self.db.rows('SELECT * FROM paper_trades')),0);self.assertEqual(self.db.rows('SELECT action FROM paper_decisions')[0]['action'],'BUY')
 def test_buy_includes_costs(self):
  self.db.set_setting('automation_enabled','true');self.e.run();t=self.db.rows('SELECT * FROM paper_trades')[0];self.assertGreater(float(t['fee_eur']),0);self.assertGreater(float(t['slippage_eur']),0);self.assertTrue(self.e.positions())
 def test_position_cap(self):
  self.db.set_setting('automation_enabled','true')
  for _ in range(10):self.e.run()
  cash,pv,total,_=self.e.equity();self.assertLessEqual(pv,total*__import__('decimal').Decimal('0.11'))







