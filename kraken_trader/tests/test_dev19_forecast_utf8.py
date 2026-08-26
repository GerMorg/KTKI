import json,os,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,os.path.join(os.path.dirname(__file__),'..','app'))
from db import DB,now
from forecast_tracker import ForecastTracker
class Tests(unittest.TestCase):
 def make_ready(self,db):
  with db.con() as c:
   c.execute('CREATE TABLE IF NOT EXISTS watchlist_versions(id INTEGER PRIMARY KEY)');c.execute('INSERT INTO watchlist_versions VALUES(1)')
   c.execute('CREATE TABLE IF NOT EXISTS live_prices(symbol TEXT PRIMARY KEY,last TEXT,bid TEXT,ask TEXT,change_pct TEXT,received_at TEXT)')
   c.execute("INSERT INTO live_prices VALUES('BTC/EUR','100',NULL,NULL,NULL,?)",(now(),))
   c.execute('CREATE TABLE IF NOT EXISTS scanner_results(symbol TEXT PRIMARY KEY,score TEXT,signal TEXT,quality TEXT,reasons_json TEXT)')
   c.execute("INSERT INTO scanner_results VALUES('BTC/EUR','80','BUY','VALID','[]')")
 def test_explicit_forecast_insert_matches_twelve_column_schema(self):
  db=DB(tempfile.mktemp());db.init();f=ForecastTracker(db);self.make_ready(db);self.assertEqual(f.snapshot(['BTC/EUR']),2);self.assertEqual(len(db.rows('SELECT * FROM research_forecasts')),2)
 def test_extra_future_column_does_not_break_named_insert(self):
  db=DB(tempfile.mktemp());db.init();f=ForecastTracker(db);self.make_ready(db)
  with db.con() as c:c.execute("ALTER TABLE research_forecasts ADD COLUMN future_note TEXT DEFAULT ''")
  self.assertEqual(f.snapshot(['BTC/EUR']),2)
 def test_sources_are_utf8_without_known_mojibake_markers(self):
  bad=tuple(chr(x) for x in (0x00c3,0x00c2,0xfffd))+(chr(0x00e2)+chr(0x201a)+chr(0x00ac),chr(0x00e2)+chr(0x20ac))
  for p in Path(__file__).parents[1].rglob('*'):
   if p.is_file() and p.suffix in ('.py','.md','.yaml','.yml','.txt','.sh'):
    text=p.read_text('utf-8');self.assertFalse(any(x in text for x in bad),str(p))
 def test_visible_german_text_is_correct(self):
  text=(Path(__file__).parents[1]/'app'/'main.py').read_text('utf-8');self.assertIn('Übersicht',text);self.assertIn('Gebühr',text);self.assertIn('Qualität',text)







