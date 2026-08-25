import os,sys,tempfile,unittest
os.environ['APP_DATA_DIR']=tempfile.mkdtemp();os.environ['APP_DISABLE_PAPER_SCHEDULER']='1';os.environ['APP_DISABLE_WEBSOCKET']='1';sys.path.insert(0,os.path.join(os.path.dirname(__file__),'..','app'));import main
class ConfigTests(unittest.TestCase):
 def setUp(self):self.c=main.app.test_client()
 def test_settings_visible_and_save(self):
  data=self.c.get('/settings').data
  self.assertIn(b'paper_trade_eur',data);self.assertIn(b'paper_fee_bps',data)
  main.client.pairs=lambda asset_class:{'BTCEUR':{'wsname':'BTC/EUR','base':'BTC','quote':'EUR','status':'online','leverage_buy':[],'leverage_sell':[]}} if asset_class=='currency' else {};res=self.c.post('/settings',data={'automation':'on','categories':['crypto_spot'],'paper_trade_eur':'30','paper_fee_bps':'35','paper_slippage_bps':'8','paper_max_position_pct':'12','paper_interval_minutes':'5'})
  self.assertEqual(res.status_code,302);self.assertEqual(main.db.rows("SELECT value FROM settings WHERE key='automation_enabled'")[0]['value'],'true');self.assertEqual(main.universe.enabled(),{'crypto_spot'})
 def test_rest_price_fallback(self):
  main.client.ticker=lambda symbols,*args:{'XXBTZEUR':{'c':['50000'],'b':['49990'],'a':['50010'],'o':'49000'}}
  with main.db.con() as c:
   c.execute("INSERT OR REPLACE INTO product_categories VALUES('crypto_spot','Kryptowährungen (Spot)',1,?)",(main.__import__('db').now() if False else __import__('db').now(),));c.execute("INSERT OR REPLACE INTO market_universe VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",('BTC/EUR','currency','crypto_spot','BTC','EUR','online','0.0001','5',8,1,'[]','[]','BTCEUR',__import__('db').now()));c.execute("INSERT OR REPLACE INTO market_category_members VALUES('BTC/EUR','currency','crypto_spot')")
  self.assertEqual(main.refresh_allowed_prices(),1);self.assertTrue(main.db.rows("SELECT * FROM live_prices WHERE symbol='BTC/EUR'"))
