import os,sys,tempfile,unittest
sys.path.insert(0,os.path.join(os.path.dirname(__file__),'..','app'))
from db import DB,now
from kraken import KrakenClient
from product_identity import canonical_product_id
from scanner import MarketScanner
from unittest.mock import patch
class T(unittest.TestCase):
 def test_eur_usd_same_product(self):self.assertEqual(canonical_product_id('tokenized_asset','AAPLx','xstocks'),canonical_product_id('tokenized_asset','AAPLx','xstocks'))
 def test_forex_pairs_uses_asset_class(self):
  k=KrakenClient()
  with patch.object(k,'call',return_value={}) as c:k.pairs('forex');self.assertEqual(c.call_args.args[1]['aclass_base'],'currency');self.assertNotIn('asset_class',c.call_args.args[1])
 def test_forex_profile_is_not_crypto(self):
  db=DB(tempfile.mktemp());db.init();s=MarketScanner(db,object())
  with db.con() as c:c.execute('CREATE TABLE news_market_links(news_id TEXT,symbol TEXT,relevance TEXT,reason TEXT)')
  candles=[[i,'99','101','98',str(100+i*.1),'100','1000',2] for i in range(40)]
  r=s.analyze('EUR/USD',candles,{'b':['1.1'],'a':['1.101']},'forex','USD');self.assertIn('forex-v1',' '.join(r['reasons']))
if __name__=='__main__':unittest.main()







