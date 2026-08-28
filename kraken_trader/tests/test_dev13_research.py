import os,sys,tempfile,time,unittest
sys.path.insert(0,os.path.join(os.path.dirname(__file__),'..','app'))
from db import DB
from market_universe import MarketUniverse
from news_prefilter import NewsPrefilter,classify
from prefilter import MarketPrefilter
from scanner import MarketScanner
from forecast_tracker import ForecastTracker
from research_pipeline import ResearchPipeline
class Client:
 def pairs(self,ac):return {'BTCEUR':{'wsname':'BTC/EUR','base':'BTC','quote':'EUR','status':'online','leverage_buy':[],'leverage_sell':[]}} if ac=='currency' else {}
 def ticker(self,s,*args):return {'BTCEUR':{'b':['99'],'a':['101'],'c':['100'],'o':'95','v':['10','20']}}
 def ohlc(self,s,i,*args):return {s:[[x,'90','110','80',str(90+x),'95','1000',5] for x in range(40)],'last':0}
class News(NewsPrefilter):
 def _read(self,url):return b'<rss><channel><item><title>Federal Reserve interest rate decision and Bitcoin liquidity</title><link>https://example.test/a</link></item></channel></rss>'
class Tests(unittest.TestCase):
 def setUp(self):
  self.db=DB(tempfile.mktemp());self.db.init();self.client=Client();self.u=MarketUniverse(self.db,self.client);self.u.set_categories({'crypto_spot'});self.news=News(self.db);self.pre=MarketPrefilter(self.db,self.client,self.news);self.scan=MarketScanner(self.db,self.client);self.fc=ForecastTracker(self.db)
 def test_taxonomy(self):
  topics,events=classify('Federal Reserve interest rate decision');self.assertIn('monetary_policy',topics);self.assertIn('policy',events)
 def test_watchlist_is_versioned(self):
  self.u.sync();r=self.pre.run(3);self.assertEqual(r['candidates'],1);self.assertEqual(len(self.db.rows('SELECT * FROM watchlist_versions')),1);self.assertGreater(float(self.db.rows('SELECT news_score FROM prefilter_results')[0]['news_score']),0)
 def test_pipeline_creates_forecasts(self):
  p=ResearchPipeline(self.db,self.u,self.pre,self.scan,self.fc);p.start()
  for _ in range(200):
   j=p.latest()
   if j and j['status'] in ('COMPLETED','FAILED'):break
   time.sleep(.01)
  self.assertEqual(j['status'],'COMPLETED')
 def test_weights_are_controlled(self):self.assertEqual(self.db.rows("SELECT status FROM model_weights WHERE version='rules-v1'")[0]['status'],'ACTIVE')


