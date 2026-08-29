import os,sys,tempfile,unittest
from decimal import Decimal
sys.path.insert(0,os.path.join(os.path.dirname(__file__),'..','app'))
from db import DB
import types
flask=types.ModuleType('flask');flask.Blueprint=object;flask.request=types.SimpleNamespace();sys.modules.setdefault('flask',flask)
from controlled_learning import ControlledLearning
from real_trade import RealTradeEngine
class FakeClient:
 def __init__(self):self.calls=[]
 def add_order(self,**data):self.calls.append(data);return {'ok':True}
class Tests(unittest.TestCase):
 def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.db=DB(os.path.join(self.tmp.name,'x.db'));self.db.init()
 def tearDown(self):self.tmp.cleanup()
 def test_wilson_not_100(self):
  low,high=ControlledLearning(self.db)._wilson(10,10);self.assertLess(low,1);self.assertEqual(high,1)
 def test_hold_abstains(self):
  l=ControlledLearning(self.db);p={'base_score':50,'momentum_weight':4,'trend_weight':9,'volatility_penalty':1.1,'spread_penalty':30,'buy_threshold':80,'buy_max_spread_pct':.05,'avoid_threshold':15,'avoid_spread_pct':4};r={'direction':'UP','actual_return_pct':.2,'features_json':'{"momentum_pct":0,"trend_pct":0,"volatility_pct":0,"spread_pct":0.1}'};x=l._score_parameter_set(p,[r]);self.assertEqual(x['decisions'],0);self.assertIsNone(x['hit_rate_raw'])
 def test_validation_works_default_off(self):
  c=FakeClient();e=RealTradeEngine(self.db,c);self.db.set_setting('real_max_order_volume','1');self.db.set_setting('real_max_order_notional_eur','100');self.assertEqual(e.submit('BTC/EUR','buy','.001','limit','50000',validate_only=True)['status'],'VALIDATED');self.assertEqual(c.calls[0]['validate'],'true')
 def test_market_orders_are_separately_disabled(self):
  c=FakeClient();e=RealTradeEngine(self.db,c);self.db.set_setting('real_max_order_volume','1');self.db.set_setting('real_max_order_notional_eur','100')
  with self.assertRaises(PermissionError):e.submit('BTC/EUR','buy','.001','market',validate_only=True)
 def test_live_guards_and_one_use_token(self):
  c=FakeClient();e=RealTradeEngine(self.db,c);self.db.set_setting('real_max_order_volume','1');self.db.set_setting('real_max_order_notional_eur','100')
  with self.assertRaises(PermissionError):e.submit('BTC/EUR','buy','.001','limit','50000',validate_only=False)
  e._live_price=lambda symbol,side:(Decimal('50000'),{'last':'50000','bid':'49999','ask':'50001'})
  self.db.set_setting('real_trading_enabled','true');self.db.set_setting('real_kill_switch','false');token=e.arm('REALHANDEL AKTIVIEREN');self.assertEqual(e.submit('BTC/EUR','buy','.001','limit','50000',approval_token=token,validate_only=False)['status'],'SUBMITTED')
  with self.assertRaises(PermissionError):e.submit('BTC/EUR','buy','.001','limit','50000',approval_token=token,validate_only=False)
if __name__=='__main__':unittest.main()

class V54DisplayTests(unittest.TestCase):
 def test_display_number_removes_endless_decimals(self):
  from display_format import display_number
  self.assertEqual(display_number('62.123456789'), '62,12');self.assertEqual(display_number('0.123456789'), '0,1235');self.assertEqual(display_number('0.0000123456789'), '0,00001235')
 def test_display_tree_does_not_modify_json_text(self):
  from display_format import display_tree
  self.assertEqual(display_tree({'parameters_json':'{"x":1.23456789}'})['parameters_json'],'{"x":1.23456789}')
