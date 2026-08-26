import os,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,os.path.join(os.path.dirname(__file__),'..','app'))
from db import DB
from market_universe import MarketUniverse
from news_prefilter import NewsPrefilter
from prefilter import MarketPrefilter
class Client:
 def pairs(self,ac):
  if ac=='tokenized_asset':return {'AAPLx/USD':{'wsname':'AAPLx/USD','base':'AAPLx','quote':'USD','status':'online','leverage_buy':[2,3],'leverage_sell':[2,3]}}
  return {}
 def ticker(self,symbols,ac='currency'):return {x:{'b':['99'],'a':['101'],'c':['100'],'o':'95','v':['10','20']} for x in symbols}
class News(NewsPrefilter):
 def collect(self):return {'saved':0,'errors':[]}
class Tests(unittest.TestCase):
 def setUp(self):
  self.db=DB(tempfile.mktemp());self.db.init();self.u=MarketUniverse(self.db,Client());self.u.set_categories({'xstocks','leveraged_spot'});self.u.sync();self.n=News(self.db);self.p=MarketPrefilter(self.db,Client(),self.n)
 def test_multicategory_symbol_persists_once(self):
  raw=self.db.rows("SELECT * FROM market_category_members WHERE symbol='AAPLx/USD'");self.assertEqual(len(raw),2)
  self.assertEqual(sum(x['symbol']=='AAPLx/USD' for x in self.p.markets()),1)
  result=self.p.run(8);rows=self.db.rows('SELECT * FROM prefilter_results WHERE run_id=? AND symbol=?',(result['run_id'],'AAPLx/USD'));self.assertEqual(len(rows),1)
 def test_repeated_run_has_no_integrity_error(self):
  self.p.run(8);self.p.run(8);self.assertEqual(len(self.db.rows('SELECT * FROM prefilter_runs')),2)
 def test_repository_and_gui_sources_are_utf8_without_mojibake(self):
  root=Path(__file__).parents[2];bad=(chr(0x00c3),chr(0x00c2),chr(0x00e2)+chr(0x20ac),chr(0x00f0)+chr(0x0178),chr(0xfffd))
  for path in root.rglob('*'):
   if path.is_file() and path.suffix in ('','.py','.md','.yaml','.txt'):
    text=path.read_text('utf-8');self.assertFalse(any(x in text for x in bad),str(path))
  main=(root/'kraken_trader/app/main.py').read_text('utf-8');self.assertIn('Übersicht',main);self.assertIn('Gebühr',main)







