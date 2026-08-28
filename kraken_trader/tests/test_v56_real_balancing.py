import os,sys,tempfile,unittest
sys.path.insert(0,os.path.join(os.path.dirname(__file__),'..','app'))
from db import DB
from real_portfolio_allocator import RealPortfolioAllocator
class Engine:
 def enabled(self):return True
 def submit(self,*a,**k):return {'status':'SUBMITTED','client_order_id':'x'}
class T(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.db=DB(os.path.join(self.tmp.name,'x.db'));self.db.init()
  with self.db.con() as c:
   c.execute('CREATE TABLE scanner_results(symbol TEXT,score TEXT,quality TEXT,signal TEXT)');c.execute("INSERT INTO scanner_results VALUES('BTC/EUR','90','VALID','BUY')")
   c.execute("INSERT INTO live_prices VALUES('BTC/EUR','50000','49900','50100','0',CURRENT_TIMESTAMP)")
   c.execute("INSERT INTO private_balances VALUES('EUR','1000','[]',1,CURRENT_TIMESTAMP)")
  self.a=RealPortfolioAllocator(self.db,Engine())
 def tearDown(self):self.tmp.cleanup()
 def set(self,k,v):self.db.set_setting(k,v)
 def test_automatic_is_disabled_by_default(self):self.assertEqual(self.a.run(True)['status'],'DISABLED')
 def test_dry_run_is_automatic_but_never_submits(self):
  self.set('real_balancing_enabled','true');self.set('real_trading_enabled','true');self.set('real_kill_switch','false');r=self.a.run(True);self.assertEqual(r['actions'][0]['status'],'DRY_RUN')
 def test_execution_requires_separate_secret(self):
  self.set('real_balancing_enabled','true');self.set('real_trading_enabled','true');self.set('real_kill_switch','false');self.set('real_balancing_execute_enabled','true');self.set('real_balancing_dry_run','false');r=self.a.run(True);self.assertEqual(r['actions'][0]['status'],'BLOCKED_AUTOMATION_SECRET')
 def test_all_settings_are_bounded(self):
  self.set('real_balancing_interval_minutes','1');self.set('real_balancing_max_position_pct','999');s=self.a.settings();self.assertEqual(s['interval_minutes'],5);self.assertEqual(s['max_position_pct'],100)
if __name__=='__main__':unittest.main()
