import os,sys,tempfile,unittest
sys.path.insert(0,os.path.join(os.path.dirname(__file__),'..','app'))
from db import DB
from scanner import MarketScanner
class Fake:pass
class ScannerTests(unittest.TestCase):
 def setUp(self):self.db=DB(tempfile.mktemp());self.db.init();self.s=MarketScanner(self.db,Fake())
 def candles(self,rise=True):
  out=[]
  for i in range(50):
   close=100+i*.3 if rise else 100-i*.1;out.append([i,str(close-.1),str(close+.2),str(close-.3),str(close),str(close),str(1000+i),10])
  return out
 def test_valid_rank(self):
  r=self.s.analyze('BTC/EUR',self.candles(),{'b':['114.6'],'a':['114.8']});self.assertEqual(r['quality'],'VALID');self.assertGreater(r['score'],0);self.assertEqual(r['data_points'],49)
 def test_incomplete(self):self.assertEqual(self.s.analyze('X/EUR',self.candles()[:10],{})['quality'],'INSUFFICIENT')
 def test_persistence(self):
  self.s.client.ohlc=lambda sym,interval:{sym:self.candles(),'last':1};self.s.client.ticker=lambda syms:{'BTC/EUR':{'b':['114.6'],'a':['114.8']}}
  self.s.run(['BTC/EUR']);self.assertTrue(self.db.rows('SELECT * FROM scanner_results'));self.assertTrue(self.db.rows('SELECT * FROM scanner_runs'))
