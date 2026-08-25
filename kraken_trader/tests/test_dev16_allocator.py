import json,os,sys,tempfile,unittest,urllib.error
from unittest.mock import patch
sys.path.insert(0,os.path.join(os.path.dirname(__file__),'..','app'))
from db import DB,now
from portfolio_allocator import PortfolioAllocator
from paper_engine import PaperEngine
from market_universe import MarketUniverse
from ws_market import MarketStream
from news_prefilter import NewsPrefilter
class Client:
 def pairs(self,ac):
  if ac=='tokenized_asset':return {'AAPLx/USD':{'wsname':'AAPLx/USD','base':'AAPLx','quote':'USD','status':'online','leverage_buy':[2,3],'leverage_sell':[2,3]}}
  if ac=='currency':return {'EUR/USD':{'wsname':'EUR/USD','base':'EUR','quote':'USD','status':'online','leverage_buy':[],'leverage_sell':[]}}
  return {}
class Tests(unittest.TestCase):
 def setUp(self):
  self.db=DB(tempfile.mktemp());self.db.init(1000);self.engine=PaperEngine(self.db,1000);from scanner import MarketScanner;MarketScanner(self.db,Client());self.u=MarketUniverse(self.db,Client());self.u.set_categories({'xstocks','leveraged_spot','forex'});self.u.sync()
  with self.db.con() as c:
   c.execute("INSERT OR REPLACE INTO live_prices VALUES(?,?,?,?,?,?)",('AAPLx/USD','220','219','221','2',now()));c.execute("INSERT OR REPLACE INTO live_prices VALUES(?,?,?,?,?,?)",('EUR/USD','1.1','1.09','1.11','0',now()));c.execute("INSERT OR REPLACE INTO research_watchlist VALUES('AAPLx/USD','xstocks','90','ANALYZED',?,1,'[]')",(now(),));c.execute("INSERT OR REPLACE INTO scanner_results VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",('AAPLx/USD',now(),'92','BUY','2','1','1','0.1','100000',50,'VALID','[]'))
 def test_xstocks_and_usd_stream_are_supported(self):
  self.assertIn('AAPLx/USD',self.u.symbols(None));stream=MarketStream(self.db,False);stream.set_symbols(['AAPLx/USD']);self.assertEqual(stream.symbols,['AAPLx/USD'])
 def test_dynamic_leverage_uses_only_kraken_levels(self):
  self.db.set_setting('paper_leverage_enabled','true');self.db.set_setting('paper_max_leverage','3');a=PortfolioAllocator(self.db);p=a.plans(__import__('decimal').Decimal('1000'))[0];self.assertIn(p['leverage'],[2,3])
 def test_leveraged_paper_buy_tracks_debt(self):
  self.db.set_setting('automation_enabled','true');self.db.set_setting('paper_leverage_enabled','true');self.db.set_setting('paper_max_leverage','3');self.db.set_setting('paper_min_transfer_eur','5');e=self.engine;e.run();risk=self.db.rows('SELECT * FROM paper_position_risk');self.assertTrue(risk);self.assertGreater(float(risk[0]['borrowed_eur']),0)
 def test_tls_timeout_sets_cooldown(self):
  n=NewsPrefilter(self.db)
  with self.db.con() as c:c.execute('UPDATE news_sources SET enabled=0');c.execute("UPDATE news_sources SET enabled=1 WHERE name='GDELT Wirtschaft'")
  with patch.object(n,'_read',side_effect=urllib.error.URLError('_ssl.c:1064: The handshake operation timed out')):n.collect()
  row=self.db.rows("SELECT last_status,cooldown_until FROM news_sources WHERE name='GDELT Wirtschaft'")[0];self.assertEqual(row['last_status'],'DEGRADED TLS COOLDOWN');self.assertTrue(row['cooldown_until'])
