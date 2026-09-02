import os,tempfile,unittest,sys
from pathlib import Path
APP=Path(__file__).resolve().parents[1]/'app';sys.path.insert(0,str(APP))
from db import DB
from controlled_learning import ControlledLearning

class V78LearningTests(unittest.TestCase):
 def make_db(self):
  tmp=tempfile.NamedTemporaryFile(suffix='.db',delete=False);tmp.close();db=DB(tmp.name);db.init(1000)
  with db.con() as c:
   c.execute('CREATE TABLE IF NOT EXISTS market_universe(symbol TEXT PRIMARY KEY,category TEXT)')
   c.execute('CREATE TABLE IF NOT EXISTS research_forecasts(id INTEGER PRIMARY KEY AUTOINCREMENT,symbol TEXT,direction TEXT,scanner_score REAL,created_at TEXT,horizon_hours INTEGER,status TEXT,model_version TEXT)')
   c.execute('CREATE TABLE IF NOT EXISTS forecast_evaluations(id INTEGER PRIMARY KEY AUTOINCREMENT,forecast_id INTEGER,direction_correct INTEGER,actual_return_pct REAL,evaluated_at TEXT)')
  return db,tmp.name
 def test_families_are_explicit_and_separate(self):
  db,path=self.make_db()
  try:self.assertEqual({x['family'] for x in ControlledLearning(db).family_overview()},{'forex','xstocks','crypto_spot'})
  finally:
   try:os.unlink(path)
   except OSError:pass
 def test_insufficient_data_does_not_change_active_version(self):
  db,path=self.make_db()
  try:
   learning=ControlledLearning(db);active={x['family']:x['active_version'] for x in learning.family_overview()};result=learning.propose('forex')
   self.assertIn(str(result.get('status','')).upper(),{'INSUFFICIENT_DATA','NO_CANDIDATE','COMPLETED'});self.assertEqual(active,{x['family']:x['active_version'] for x in learning.family_overview()})
  finally:
   try:os.unlink(path)
   except OSError:pass
if __name__=='__main__':unittest.main()
