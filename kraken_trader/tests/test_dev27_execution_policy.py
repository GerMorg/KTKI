import json,os,sys,tempfile,unittest
from unittest.mock import patch
sys.path.insert(0,os.path.join(os.path.dirname(__file__),'..','app'))
from db import DB,now
from execution_costs import choose_execution_pair
from kraken import KrakenClient
from market_universe import MarketUniverse
from paper_engine import PaperEngine
from product_identity import canonical_product_id
from text_encoding import repair_text
class Client:
 def pairs(self,asset_class):
  if asset_class=='currency':return {'BTCEUR':{'wsname':'BTC/EUR','base':'BTC','quote':'EUR','status':'online','leverage_buy':[],'leverage_sell':[]},'EURUSD':{'wsname':'EUR/USD','base':'EUR','quote':'USD','status':'online','leverage_buy':[],'leverage_sell':[]}}
  if asset_class=='forex':return {'EURUSD':{'wsname':'EUR/USD','base':'EUR','quote':'USD','status':'online','leverage_buy':[],'leverage_sell':[]}}
  if asset_class=='tokenized_asset':return {'AAPLEUR':{'wsname':'AAPLx/EUR','base':'AAPLx','quote':'EUR','status':'online','leverage_buy':[],'leverage_sell':[]},'AAPLUSD':{'wsname':'AAPLx/USD','base':'AAPLx','quote':'USD','status':'online','leverage_buy':[],'leverage_sell':[]}}
  return {}
class Tests(unittest.TestCase):
 def test_same_canonical_identity_across_quote(self):
  self.assertEqual(canonical_product_id('tokenized_asset','AAPLx','xstocks'),canonical_product_id('tokenized_asset','AAPLx','xstocks'))
 def test_pair_selector_uses_all_in_cost_not_currency_preference(self):
  markets=[{'symbol':'AAPLx/EUR','source_key':'AAPLEUR','quote_asset':'EUR'},{'symbol':'AAPLx/USD','source_key':'AAPLUSD','quote_asset':'USD'}]
  tickers={'AAPLEUR':{'b':['99'],'a':['101'],'c':['100'],'v':['1','10']},'AAPLUSD':{'b':['99.95'],'a':['100.05'],'c':['100'],'v':['1','1000']},'EUR/USD':{'b':['1.0999'],'a':['1.1001'],'c':['1.1'],'v':['1','1000']}}
  selected,costs,ranking=choose_execution_pair(markets,tickers,40,10,10);self.assertEqual(selected['symbol'],'AAPLx/USD');self.assertTrue(costs['fx_required']);self.assertEqual(len(ranking),2)
 def test_forex_universe_is_derived_from_currency_pairs(self):
  k=KrakenClient()
  payload={'BTC/EUR':{'base':'BTC','quote':'EUR'},'EUR/USD':{'base':'EUR','quote':'USD'}}
  with patch.object(k,'call',return_value=payload) as call:
   result=k.pairs('forex');params=call.call_args.args[1]
  self.assertEqual(set(result),{'EUR/USD'});self.assertEqual(params['aclass_base'],'currency');self.assertNotIn('asset_class',params)
 def test_universe_has_one_forex_copy_and_xstock_alternatives(self):
  db=DB(tempfile.mktemp());db.init();u=MarketUniverse(db,Client());u.set_categories({'crypto_spot','forex','xstocks'});u.sync()
  self.assertEqual(len(db.rows("SELECT * FROM market_universe WHERE symbol='EUR/USD'")),1)
  ids={x['canonical_id'] for x in db.rows("SELECT * FROM market_universe WHERE symbol LIKE 'AAPLx/%'")};self.assertEqual(len(ids),1)
  self.assertEqual(len(json.loads(db.rows("SELECT alternatives_json FROM canonical_products WHERE canonical_id LIKE 'xstock:%'")[0]['alternatives_json'])),2)
 def test_usd_execution_records_full_cost_chain(self):
  db=DB(tempfile.mktemp());db.init(1000);PaperEngine(db,1000)
  with db.con() as c:
   c.execute("CREATE TABLE market_universe(symbol TEXT,asset_class TEXT,category TEXT,ordermin TEXT,costmin TEXT,canonical_id TEXT,lot_decimals INTEGER,pair_decimals INTEGER)");c.execute("INSERT INTO market_universe VALUES('AAPLx/USD','tokenized_asset','xstocks','0.001','1','xstock:AAPLX',8,2)")
   c.execute("INSERT INTO live_prices VALUES('AAPLx/USD','100','99.8','100.2','2',?)",(now(),));c.execute("INSERT INTO live_prices VALUES('EUR/USD','1.1','1.099','1.101','0',?)",(now(),))
  e=PaperEngine(db,1000);tid=e.execute('AAPLx/USD','BUY',100,'test',{'leverage':1});d=json.loads(db.rows('SELECT decision_json FROM paper_trades WHERE id=?',(tid,))[0]['decision_json'])
  for key in ('fx_fee_eur','fx_spread_eur','product_spread_eur','slippage_eur','trade_fee_eur'):self.assertIn(key,d)
 def test_utf8_repairs_real_mojibake(self):
  broken='Geb'+chr(0xc3)+chr(0xbc)+'hr und '+chr(0xc3)+chr(0x153)+'bersicht';self.assertEqual(repair_text(broken),'Gebühr und Übersicht')
if __name__=='__main__':unittest.main()
