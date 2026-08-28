import os,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,os.path.join(os.path.dirname(__file__),'..','app'))
from db import DB
from text_encoding import repair_database,repair_text,corruption_score
from market_universe import MarketUniverse
from prefilter import MarketPrefilter
class Client:
 def pairs(self,ac):
  if ac=='tokenized_asset':return {'AAPLUSD':{'wsname':'AAPLx/USD','base':'AAPLx','quote':'USD','status':'online','leverage_buy':[2],'leverage_sell':[2]}}
  return {}
 def ticker(self,symbols,ac='currency'):return {'AAPLUSD':{'b':['99'],'a':['101'],'c':['100'],'o':'98','v':['10','20']}}
class News:
 def collect(self):return {'saved':0,'errors':[]}
 def link_markets(self,markets):return 0
class Tests(unittest.TestCase):
 def test_repository_and_visible_routes_have_no_mojibake(self):
  root=Path(__file__).parents[2]
  for path in root.rglob('*'):
   if path.is_file() and path.suffix.lower() in ('','.py','.md','.yaml','.yml','.txt','.sh'):
    self.assertEqual(corruption_score(path.read_text('utf-8')),0,str(path))
 def test_database_v2_repairs_even_if_v1_was_done(self):
  db=DB(tempfile.mktemp());db.init();db.set_setting('utf8_data_migration_v1','done')
  broken='Geb'+chr(0xc3)+chr(0xbc)+'hr und '+chr(0xc3)+chr(0x153)+'bersicht'
  with db.con() as c:c.execute("INSERT INTO audit(created_at,event,level,details) VALUES('x','OLD','info',?)",(broken,))
  result=repair_database(db);self.assertEqual(result['status'],'DONE');self.assertEqual(db.rows("SELECT details FROM audit WHERE event='OLD'")[0]['details'],'GebÃ¼hr und Ãœbersicht');self.assertEqual(repair_database(db)['status'],'ALREADY_DONE')
 def test_multicategory_prefilter_is_unique_across_repeated_runs(self):
  db=DB(tempfile.mktemp());db.init();
  with db.con() as c:c.execute('CREATE TABLE news_market_links(news_id TEXT,symbol TEXT,relevance TEXT,reason TEXT,PRIMARY KEY(news_id,symbol))')
  u=MarketUniverse(db,Client());u.set_categories({'xstocks','leveraged_spot'});u.sync();p=MarketPrefilter(db,Client(),News())
  first=p.run(8);second=p.run(8)
  for rid in (first['run_id'],second['run_id']):self.assertEqual(len(db.rows('SELECT symbol FROM prefilter_results WHERE run_id=?',(rid,))),1)
