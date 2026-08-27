import os,sys,tempfile,unittest,json
sys.path.insert(0,os.path.join(os.path.dirname(__file__),'..','app'))
from db import DB,now
from market_universe import MarketUniverse
from scanner import MarketScanner
from paper_engine import PaperEngine
from portfolio_allocator import PortfolioAllocator
class Client:
 calls=[]
 def pairs(self,ac):
  if ac=='tokenized_asset':return {'AAPLUSD':{'wsname':'AAPLx/USD','base':'AAPLx','quote':'USD','status':'online','ordermin':'0.01','costmin':'1','lot_decimals':4,'pair_decimals':2,'leverage_buy':[],'leverage_sell':[]}}
  if ac=='forex':return {'EURUSD':{'wsname':'EUR/USD','base':'EUR','quote':'USD','status':'online','ordermin':'1','costmin':'1','leverage_buy':[],'leverage_sell':[]}}
  return {}
 def ticker(self,symbols,ac='currency'):
  self.calls.append(('ticker',ac,tuple(symbols)))
  if ac=='tokenized_asset':return {'AAPLUSD':{'b':['119.8'],'a':['120.0'],'c':['119.9'],'o':'108','v':['1000','2000']}}
  return {'EURUSD':{'b':['1.099'],'a':['1.101'],'c':['1.1'],'o':'1.1','v':['1','1']}}
 def ohlc(self,symbol,interval,ac='currency'):
  self.calls.append(('ohlc',ac,symbol));candles=[]
  for i in range(40):
   close=100+i*.5;candles.append([i,str(close-.2),str(close+.3),str(close-.4),str(close),str(close),str(1000+i),10])
  return {'AAPLUSD':candles,'last':40}
class Tests(unittest.TestCase):
 def setUp(self):
  self.db=DB(tempfile.mktemp());self.db.init(1000);self.client=Client();self.u=MarketUniverse(self.db,self.client);self.u.set_categories({'xstocks'});self.u.sync();self.scan=MarketScanner(self.db,self.client);PaperEngine(self.db,1000)
  with self.db.con() as c:
   c.execute("INSERT INTO research_watchlist VALUES('AAPLx/USD','xstocks','80','PREFILTERED',?,1,'[]')",(now(),));c.execute("INSERT OR REPLACE INTO live_prices VALUES('AAPLx/USD','119.9','119.8','120.0','2',?)",(now(),));c.execute("INSERT OR REPLACE INTO live_prices VALUES('EUR/USD','1.1','1.099','1.101','0',?)",(now(),))
 def test_xstock_scan_uses_tokenized_asset_and_creates_score(self):
  self.scan.run(['AAPLx/USD'],60,1,0);r=self.db.rows("SELECT * FROM scanner_results WHERE symbol='AAPLx/USD'")[0]
  self.assertEqual(r['quality'],'VALID');self.assertGreater(float(r['score']),0);self.assertIn(r['signal'],('BUY','HOLD'));self.assertIn(('ohlc','tokenized_asset','AAPLx/USD'),self.client.calls);self.assertIn('xstocks-v1',r['reasons_json'])
 def test_valid_xstock_score_flows_into_eur_paper_trade(self):
  self.scan.run(['AAPLx/USD'],60,1,0)
  with self.db.con() as c:c.execute("UPDATE research_watchlist SET status='ANALYZED'")
  self.db.set_setting('automation_enabled','true');self.db.set_setting('paper_min_transfer_eur','20');e=PaperEngine(self.db,1000,40,10,10,25);plans=PortfolioAllocator(self.db).plans(1000);self.assertTrue(plans);e.run();trade=self.db.rows("SELECT * FROM paper_trades WHERE symbol='AAPLx/USD'")[0]
  decision=json.loads(trade['decision_json']);self.assertEqual(decision['asset_class'],'tokenized_asset');self.assertEqual(decision['category'],'xstocks');self.assertEqual(decision['quote_currency'],'USD');self.assertGreater(float(trade['fee_eur']),0)
 def test_xstock_order_minimum_is_fail_closed(self):
  self.scan.run(['AAPLx/USD'],60,1,0)
  with self.db.con() as c:c.execute("UPDATE research_watchlist SET status='ANALYZED'");c.execute("UPDATE market_universe SET ordermin='100' WHERE symbol='AAPLx/USD'")
  self.db.set_setting('automation_enabled','true');e=PaperEngine(self.db,1000,40,10,10,25);e.run();self.assertFalse(self.db.rows('SELECT * FROM paper_trades'));self.assertIn('Mindestmenge',self.db.rows('SELECT reason FROM paper_decisions ORDER BY id DESC LIMIT 1')[0]['reason'])
