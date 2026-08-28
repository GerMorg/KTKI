import os,sys,tempfile,unittest
sys.path.insert(0,os.path.join(os.path.dirname(__file__),'..','app'))
from db import DB
from market_universe import MarketUniverse
from prefilter import MarketPrefilter
class Client:
 def pairs(self,ac):
  if ac=='tokenized_asset':return {'AAPLx/USD':{'wsname':'AAPLx/USD','base':'AAPLx','quote':'USD','status':'online','leverage_buy':[2,3],'leverage_sell':[2,3]}}
  if ac=='currency':return {'EUR/USD':{'wsname':'EUR/USD','base':'EUR','quote':'USD','status':'online','leverage_buy':[],'leverage_sell':[]}}
  return {}
 def ticker(self,symbols,ac='currency'):
  return {x:{'b':['99'],'a':['101'],'c':['100'],'o':'95','v':['10','20']} for x in symbols}
class News:
 def collect(self):return {'saved':0,'errors':[]}
 def link_markets(self,markets):return 0
class Tests(unittest.TestCase):
 def setUp(self):
  self.db=DB(tempfile.mktemp());self.db.init();
  with self.db.con() as c:c.execute('CREATE TABLE news_market_links(news_id TEXT,symbol TEXT,relevance TEXT,reason TEXT,PRIMARY KEY(news_id,symbol))')
  self.u=MarketUniverse(self.db,Client());self.u.set_categories({'xstocks','leveraged_spot','forex'});self.u.sync();self.p=MarketPrefilter(self.db,Client(),News())
 def test_dual_category_xstock_is_one_prefilter_row(self):
  markets=self.p.markets();self.assertEqual(sum(x['symbol']=='AAPLx/USD' for x in markets),1);r=self.p.run(8);rows=self.db.rows('SELECT * FROM prefilter_results WHERE run_id=?',(r['run_id'],));self.assertEqual(sum(x['symbol']=='AAPLx/USD' for x in rows),1)
 def test_usd_xstock_is_candidate(self):
  r=self.p.run(8);self.assertIn('AAPLx/USD',self.p.candidates())



