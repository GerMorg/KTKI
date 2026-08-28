import os,sys,tempfile,unittest
sys.path.insert(0,os.path.join(os.path.dirname(__file__),'..','app'))
from db import DB
from fee_profile import FeeProfile
class PairClient:
 def __init__(self):self.calls=[]
 def pairs(self,asset_class='currency'):return {'XXBTZEUR':{'altname':'XBTEUR','wsname':'XBT/EUR'}}
 def trade_volume(self,pairs,fee_info=True):
  self.calls.append(list(pairs))
  if 'BADPAIR' in pairs:raise RuntimeError('EQuery:Unknown asset pair')
  return {'currency':'ZUSD','volume':'10','fees':{'XXBTZEUR':{'fee':'0.40'}},'fees_maker':{'XXBTZEUR':{'fee':'0.25'}}}
class Dev39FeeTests(unittest.TestCase):
 def setUp(self):
  self.db=DB(tempfile.mktemp());self.db.init(1000)
  with self.db.con() as c:c.execute('CREATE TABLE market_universe(symbol TEXT,asset_class TEXT,source_key TEXT)')
 def test_display_symbol_resolves_to_kraken_source_key(self):
  with self.db.con() as c:c.execute("INSERT INTO market_universe VALUES('BTC/EUR','currency','XXBTZEUR')")
  client=PairClient();result=FeeProfile(self.db,client).refresh(['BTC/EUR']);self.assertEqual(result['status'],'VALID');self.assertEqual(client.calls[0],['XXBTZEUR']);self.assertEqual(FeeProfile(self.db,client).rows()[0]['taker_bps'],'40.0000')
 def test_unsupported_asset_class_is_skipped_with_config_fallback(self):
  with self.db.con() as c:c.execute("INSERT INTO market_universe VALUES('AAPL/USD','tokenized_asset','AAPLUSD')")
  result=FeeProfile(self.db,PairClient()).refresh(['AAPL/USD']);self.assertEqual(result['status'],'FALLBACK');self.assertEqual(result['skipped'][0]['reason'],'UNSUPPORTED_ASSET_CLASS')
 def test_bad_pair_does_not_discard_valid_pair(self):
  with self.db.con() as c:c.execute("INSERT INTO market_universe VALUES('BTC/EUR','currency','XXBTZEUR')");c.execute("INSERT INTO market_universe VALUES('BAD/EUR','currency','BADPAIR')")
  result=FeeProfile(self.db,PairClient()).refresh(['BTC/EUR','BAD/EUR']);self.assertEqual(result['status'],'PARTIAL');self.assertEqual(result['saved'],1);self.assertEqual(result['errors'][0]['pair'],'BADPAIR')
class Dev39GuiTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  os.environ['APP_DATA_DIR']=tempfile.mkdtemp();os.environ['APP_DISABLE_PAPER_SCHEDULER']='1';os.environ['APP_DISABLE_RESEARCH_SCHEDULER']='1';import main;cls.client=main.app.test_client()
 def test_guided_dashboard_and_safety_banner(self):
  body=self.client.get('/').data.decode('utf-8');self.assertIn('Empfohlener Ablauf',body);self.assertIn('REALHANDEL DEAKTIVIERT',body)
 def test_learning_page_explains_activation(self):
  body=self.client.get('/controlled-learning').data.decode('utf-8');self.assertIn('ausdrÃ¼cklichen Freigabe',body);self.assertIn('Aktive Version',body);self.assertIn('Freigaberegeln',body)
if __name__=='__main__':unittest.main()
