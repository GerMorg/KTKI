import json,os,sys,tempfile,unittest
sys.path.insert(0,os.path.join(os.path.dirname(__file__),'..','app'))
from db import DB
from ws_market import MarketStream,parse_message
class WebSocketTests(unittest.TestCase):
 def setUp(self):self.db=DB(os.path.join(tempfile.mkdtemp(),'x.db'));self.db.init(100);self.stream=MarketStream(self.db,False,30)
 def test_status_heartbeat_and_ticker(self):
  self.stream.handle(json.dumps({'channel':'status','type':'update','data':[{'system':'online','connection_id':42}]}))
  self.stream.handle(json.dumps({'channel':'ticker','type':'snapshot','data':[{'symbol':'BTC/EUR','last':50000,'bid':49999,'ask':50001}]}))
  self.assertEqual(self.db.stream_status()['system_status'],'online');self.assertEqual(self.db.rows('SELECT last FROM live_prices')[0]['last'],'50000')
 def test_subscription_error_is_fail_visible(self):
  self.stream.handle(json.dumps({'method':'subscribe','success':False,'error':'bad symbol'}));self.assertEqual(self.db.stream_status()['state'],'ERROR')
 def test_symbol_filter_and_health(self):
  self.stream.set_symbols(['BTC/EUR','BTC/EUR','ETH/USD']);self.assertEqual(self.stream.symbols,['BTC/EUR']);self.assertTrue(self.stream.status()['stale'])
if __name__=='__main__':unittest.main()




