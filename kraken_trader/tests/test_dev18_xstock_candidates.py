import os,sys,tempfile,unittest
sys.path.insert(0,os.path.join(os.path.dirname(__file__),'..','app'))
from db import DB
from market_universe import MarketUniverse
from prefilter import MarketPrefilter
from scanner import MarketScanner
class News:
 def __init__(self,db):
  with db.con() as c:c.execute('CREATE TABLE IF NOT EXISTS news_market_links(news_id TEXT,symbol TEXT,relevance TEXT,reason TEXT)')
 def collect(self):return {'saved':0,'errors':[]}
 def link_markets(self,markets):return 0
class Client:
 def __init__(self):self.ticker_calls=[]
 def pairs(self,ac):
  if ac=='tokenized_asset':return {'AAPLx/USD':{'wsname':'AAPLx/USD','base':'AAPLx','quote':'USD','status':'online','leverage_buy':[],'leverage_sell':[]},'TSLAx/USD':{'wsname':'TSLAx/USD','base':'TSLAx','quote':'USD','status':'online','leverage_buy':[],'leverage_sell':[]}}
  return {}
 def ticker(self,symbols,ac='currency'):
  self.ticker_calls.append((tuple(symbols),ac))
  if len(symbols)>1:raise RuntimeError('batch rejected')
  if symbols[0]=='AAPLx/USD':return {'AAPLx/USD':{'b':['100'],'a':['101'],'c':['100.5'],'o':'99','v':['10','20']}}
  raise RuntimeError('temporarily unavailable')
 def ohlc(self,symbol,interval,ac='currency'):return {symbol:[[i,'90','101','89',str(90+i/10),'95','50',2] for i in range(40)],'last':0}
class Tests(unittest.TestCase):
 def setUp(self):
  self.db=DB(tempfile.mktemp());self.db.init();self.client=Client();self.u=MarketUniverse(self.db,self.client);self.u.set_categories({'xstocks'});self.u.sync()
 def test_batch_failure_retries_individually_and_keeps_candidates(self):
  result=MarketPrefilter(self.db,self.client,News(self.db)).run(8);self.assertEqual(result['candidates'],2);self.assertEqual(result['valid'],1);self.assertEqual(result['pending_ticker'],1);self.assertEqual(len(self.db.rows('SELECT * FROM research_watchlist')),2)
 def test_scanner_uses_tokenized_asset_ticker_route(self):
  scanner=MarketScanner(self.db,self.client);scanner.run(['AAPLx/USD'],60,1,0);self.assertIn((('AAPLx/USD',),'tokenized_asset'),self.client.ticker_calls)
 def test_empty_enabled_market_set_is_distinguishable(self):
  with self.db.con() as c:c.execute('DELETE FROM market_universe');c.execute('DELETE FROM market_category_members')
  result=MarketPrefilter(self.db,self.client,News(self.db)).run(8);self.assertEqual(result['markets'],0);self.assertEqual(result['candidates'],0)







