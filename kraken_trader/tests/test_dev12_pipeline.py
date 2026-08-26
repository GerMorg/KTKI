import os,sys,tempfile,time,unittest
sys.path.insert(0,os.path.join(os.path.dirname(__file__),'..','app'))
from db import DB,now
from market_universe import MarketUniverse
from news_prefilter import NewsPrefilter
from prefilter import MarketPrefilter
from scanner import MarketScanner
from research_pipeline import ResearchPipeline
class FakeClient:
 def pairs(self,ac):
  return {'BTCEUR':{'wsname':'BTC/EUR','base':'BTC','quote':'EUR','status':'online','leverage_buy':[],'leverage_sell':[],'ordermin':'0.0001','costmin':'5'}} if ac=='currency' else {}
 def ticker(self,symbols,*args):return {'XXBTZEUR':{'b':['49990'],'a':['50010'],'c':['50000'],'o':'49000','v':['10','20']}}
 def ohlc(self,symbol,interval,*args):return {symbol:[[i,'100','101','99',str(100+i),'100','1000',2] for i in range(40)],'last':0}
class FakeNews(NewsPrefilter):
 def _read(self,url):return b'<rss><channel><item><title>Bitcoin market trend strengthens</title><link>https://example.test/a</link><description>Bitcoin liquidity improves</description></item></channel></rss>'
class Tests(unittest.TestCase):
 def setUp(self):
  self.db=DB(tempfile.mktemp());self.db.init();self.client=FakeClient();self.u=MarketUniverse(self.db,self.client);self.u.set_categories({'crypto_spot'});self.news=FakeNews(self.db);self.pre=MarketPrefilter(self.db,self.client,self.news);self.scan=MarketScanner(self.db,self.client)
 def test_news_is_used_only_for_prefilter(self):
  self.u.sync();r=self.pre.run(5);row=self.db.rows('SELECT * FROM prefilter_results')[0];self.assertGreater(float(row['news_score']),0);self.assertEqual(r['candidates'],1);from paper_engine import PaperEngine;PaperEngine(self.db);self.assertFalse(self.db.rows('SELECT * FROM paper_trades'))
 def test_pipeline_persists_progress_and_watchlist(self):
  p=ResearchPipeline(self.db,self.u,self.pre,self.scan);r=p.start();self.assertEqual(r['status'],'QUEUED')
  for _ in range(100):
   job=p.latest()
   if job and job['status'] in ('COMPLETED','FAILED'):break
   time.sleep(.02)
  self.assertEqual(job['status'],'COMPLETED');self.assertEqual(self.db.rows('SELECT status FROM research_watchlist')[0]['status'],'ANALYZED')
 def test_empty_watchlist_paper_engine_does_not_crash(self):
  from paper_engine import PaperEngine
  e=PaperEngine(self.db);self.assertEqual(e.run(),[])




