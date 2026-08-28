import os,sys
sys.path.insert(0,os.path.join(os.path.dirname(__file__),'..','app'))
from db import DB
from real_trade import RealTradeEngine
class Client:
 def __init__(self):self.calls=[]
 def add_order(self,**data):self.calls.append(data);return {'descr':{'order':'validated'}}
def engine(tmp_path):
 d=DB(str(tmp_path/'x.db'));d.init();d.set_setting('real_max_order_volume','2');return d,Client()
def test_validate_only_never_requires_live_enable(tmp_path):
 d,c=engine(tmp_path);r=RealTradeEngine(d,c).submit('BTC/EUR','buy','1','limit','100');assert r['status']=='VALIDATED';assert c.calls[0]['validate']=='true'
def test_live_fails_closed(tmp_path):
 d,c=engine(tmp_path)
 try:RealTradeEngine(d,c).submit('BTC/EUR','buy','1','limit','100',validate_only=False)
 except PermissionError:pass
 else:assert False
def test_duplicate_is_not_resubmitted(tmp_path):
 d,c=engine(tmp_path);e=RealTradeEngine(d,c);e.submit('BTC/EUR','buy','1','limit','100','same');r=e.submit('BTC/EUR','buy','1','limit','100','same');assert r['duplicate'] and len(c.calls)==1
def test_paper_tables_untouched(tmp_path):
 d,c=engine(tmp_path);RealTradeEngine(d,c).submit('BTC/EUR','buy','1','limit','100');assert d.rows('SELECT COUNT(*) n FROM paper_trades')[0]['n']==0
