import os,sys,tempfile,unittest
sys.path.insert(0,os.path.join(os.path.dirname(__file__),'..','app'))
from db import DB
from market_universe import MarketUniverse,classify
class Fake:
 def pairs(self,aclass):
  if aclass=='tokenized_asset':return {'AAPLUSD':{'wsname':'AAPLx/USD','base':'AAPLx','quote':'USD','status':'online','ordermin':'0.01','costmin':'1','leverage_buy':[],'leverage_sell':[]}}
  if aclass=='forex':return {'EURUSD':{'wsname':'EUR/USD','base':'EUR','quote':'USD','status':'online','leverage_buy':[],'leverage_sell':[]}}
  return {'BTCEUR':{'wsname':'BTC/EUR','base':'BTC','quote':'EUR','status':'online','leverage_buy':[],'leverage_sell':[]},'ETHEUR':{'wsname':'ETH/EUR','base':'ETH','quote':'EUR','status':'online','leverage_buy':[2],'leverage_sell':[2]}}
class Tests(unittest.TestCase):
 def setUp(self):self.db=DB(tempfile.mktemp());self.db.init();self.u=MarketUniverse(self.db,Fake())
 def test_category_classification(self):
  self.assertEqual(classify({},'tokenized_asset'),'xstocks');self.assertEqual(classify({'leverage_buy':[2]},'currency'),'leveraged_spot')
 def test_full_enabled_category_market(self):
  self.u.set_categories({'crypto_spot','xstocks'});r=self.u.sync();self.assertEqual(r['total'],4);self.assertEqual(self.u.symbols('EUR'),['BTC/EUR','ETH/EUR'])
 def test_no_individual_allowlist_required(self):
  self.u.set_categories({'leveraged_spot'});self.u.sync();self.assertEqual(self.u.symbols('EUR'),['ETH/EUR'])
 def test_settings_utf8(self):
  labels=' '.join(x['label'] for x in self.u.categories());self.assertIn('Kryptowährungen',labels);self.assertIn('Hebelfähige',labels)
