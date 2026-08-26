import json,os,sys,tempfile,unittest
from unittest.mock import patch
sys.path.insert(0,os.path.join(os.path.dirname(__file__),'..','app'))
from db import DB,now
from fee_profile import FeeProfile
from kraken import KrakenClient
from paper_engine import PaperEngine
class Client:
 def trade_volume(self,pairs,fee_info=True):return {'currency':'USD','volume':'1234','fees':{'BTC/EUR':{'fee':'0.4'}},'fees_maker':{'BTC/EUR':{'fee':'0.25'}}}
class T(unittest.TestCase):
 def setUp(self):self.db=DB(tempfile.mktemp());self.db.init(1000)
 def test_api_contract_is_private_and_requests_fee_info(self):
  k=KrakenClient('k','c2VjcmV0')
  with patch.object(k,'call',return_value={}) as call:k.trade_volume(['BTC/EUR']);self.assertEqual(call.call_args.args[0],'/0/private/TradeVolume');self.assertTrue(call.call_args.kwargs['private']);self.assertEqual(call.call_args.args[1]['fee-info'],'true')
 def test_maker_taker_and_provenance_persist(self):
  f=FeeProfile(self.db,Client());r=f.refresh(['BTC/EUR']);self.assertEqual(r['status'],'VALID');row=f.rows()[0];self.assertEqual(row['maker_bps'],'25.0000');self.assertEqual(row['taker_bps'],'40.0000');self.assertEqual(row['source'],'KRAKEN_TRADE_VOLUME')
 def test_permission_failure_keeps_config_fallback(self):
  class Fail:
   def trade_volume(self,*a,**k):raise RuntimeError('permission')
  self.db.set_setting('paper_fee_bps','55');f=FeeProfile(self.db,Fail());self.assertEqual(f.refresh(['BTC/EUR'])['status'],'FALLBACK');self.assertEqual(f.rate_bps('BTC/EUR')[0],55)
 def test_paper_trade_records_fee_source(self):
  FeeProfile(self.db,Client()).refresh(['BTC/EUR']);PaperEngine(self.db,1000)
  with self.db.con() as c:c.execute("CREATE TABLE market_universe(symbol TEXT,asset_class TEXT,category TEXT,ordermin TEXT,costmin TEXT,lot_decimals INTEGER,pair_decimals INTEGER)");c.execute("INSERT INTO market_universe VALUES('BTC/EUR','currency','crypto_spot','0.0001','1',8,2)");c.execute("INSERT INTO live_prices VALUES('BTC/EUR','100','99.9','100.1','1',?)",(now(),))
  tid=PaperEngine(self.db,1000).execute('BTC/EUR','BUY',100,'test',{'leverage':1});d=json.loads(self.db.rows('SELECT decision_json FROM paper_trades WHERE id=?',(tid,))[0]['decision_json']);self.assertEqual(d['trade_fee_source'],'KRAKEN_TRADE_VOLUME');self.assertEqual(d['trade_fee_bps'],'40.0000')
if __name__=='__main__':unittest.main()
