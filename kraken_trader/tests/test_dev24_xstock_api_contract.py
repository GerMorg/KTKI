import os,sys,tempfile,unittest
from unittest.mock import patch
sys.path.insert(0,os.path.join(os.path.dirname(__file__),'..','app'))
from kraken import KrakenClient
from db import DB,now
from market_universe import MarketUniverse
from scanner import MarketScanner
class Client:
 def pairs(self,ac):return {'AAPLUSD':{'wsname':'AAPLx/USD','base':'AAPLx','quote':'USD','status':'online','ordermin':'0.01','costmin':'1','leverage_buy':[],'leverage_sell':[]}} if ac=='tokenized_asset' else {}
 def ticker(self,pairs,asset_class='currency'):return {'AAPLx/USD':{'b':['119.8'],'a':['120.0'],'c':['119.9'],'o':'108','v':['1','2']}}
 def ohlc(self,pair,interval=60,asset_class='currency'):
  assert pair=='AAPLUSD';assert asset_class=='tokenized_asset'
  return {'AAPLx/USD':[[i,'100','121','99',str(100+i*.5),'100',str(1000+i),5] for i in range(40)],'last':40}
class Tests(unittest.TestCase):
 def test_public_calls_use_documented_asset_class(self):
  k=KrakenClient()
  with patch.object(k,'call',return_value={}) as call:
   k.ticker(['AAPLUSD'],'tokenized_asset');self.assertEqual(call.call_args.args[1]['asset_class'],'tokenized_asset');self.assertNotIn('aclass_base',call.call_args.args[1])
   k.ohlc('AAPLUSD',60,'tokenized_asset');self.assertEqual(call.call_args.args[1]['asset_class'],'tokenized_asset');self.assertEqual(call.call_args.args[1]['assetVersion'],1)
 def test_scanner_uses_kraken_source_key_and_produces_nonzero_score(self):
  db=DB(tempfile.mktemp());db.init();u=MarketUniverse(db,Client());u.set_categories({'xstocks'});u.sync();s=MarketScanner(db,Client());s.run(['AAPLx/USD'],60,1,0);r=db.rows("SELECT * FROM scanner_results WHERE symbol='AAPLx/USD'")[0]
  self.assertEqual(r['quality'],'VALID');self.assertGreater(float(r['score']),0);self.assertIn('xstocks-approved-v1',r['reasons_json'])
