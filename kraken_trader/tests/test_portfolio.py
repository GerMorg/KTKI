import os,sys,tempfile,unittest
os.environ['APP_DATA_DIR']=tempfile.mkdtemp();sys.path.insert(0,os.path.join(os.path.dirname(__file__),'..','app'))
from portfolio_sync import build_rows
from db import DB
class PortfolioTests(unittest.TestCase):
 def test_held_and_historical_zero(self):
  assets={'XXBT':{'altname':'XBT'},'ZEUR':{'altname':'EUR'}}
  pairs={'XXBTZEUR':{'base':'XXBT','quote':'ZEUR','altname':'XBTEUR'}}
  tickers={'XXBTZEUR':{'c':['50000','1']},'XBTEUR':{'c':['50000','1']}}
  rows,total,quality=build_rows({'XXBT':'0.001','ZEUR':'10'},{'XXBT','XETH'},assets,pairs,tickers)
  by={x['asset']:x for x in rows};self.assertEqual(by['XETH']['classification'],'HISTORICAL_ZERO');self.assertEqual(total,'60.000');self.assertEqual(quality,'VALID')
 def test_snapshot_persistence(self):
  db=DB(os.path.join(tempfile.mkdtemp(),'x.db'));db.init(100)
  sid=db.store_portfolio([{'asset':'ZEUR','display_name':'EUR','amount':'5','eur_price':'1','eur_value':'5','classification':'HELD','ever_held':1}],'5','VALID')
  self.assertEqual(sid,1);self.assertEqual(db.rows('SELECT quality FROM portfolio_snapshots')[0]['quality'],'VALID')
if __name__=='__main__':unittest.main()

