import os,sys,tempfile,unittest,json
sys.path.insert(0,os.path.join(os.path.dirname(__file__),'..','app'))
from db import DB,now
from learning_approval import LearningApproval,PARAMETERS
from scanner import MarketScanner
class Client:pass
class Tests(unittest.TestCase):
 def setUp(self):
  self.db=DB(tempfile.mktemp());self.db.init();self.l=LearningApproval(self.db)
  with self.db.con() as c:
   c.executescript("CREATE TABLE research_forecasts(id INTEGER PRIMARY KEY,symbol TEXT,scanner_score TEXT);CREATE TABLE forecast_evaluations(forecast_id INTEGER PRIMARY KEY,direction_correct INTEGER,actual_return_pct TEXT);CREATE TABLE market_universe(symbol TEXT,category TEXT);")
   c.execute("INSERT INTO market_universe VALUES('AAPLx/USD','xstocks')")
   for i in range(1,6):c.execute('INSERT INTO research_forecasts VALUES(?,?,?)',(i,'AAPLx/USD','70'));c.execute('INSERT INTO forecast_evaluations VALUES(?,?,?)',(i,1,'2'))
 def test_proposal_contains_exactly_nine_bounded_parameters(self):
  self.assertEqual(self.l.create_proposal()['status'],'PENDING');p=json.loads(self.l.latest()['parameters_json']);self.assertEqual(set(p),set(PARAMETERS));self.assertEqual(len(p),9)
  for n,v in p.items():self.assertTrue(PARAMETERS[n][1]<=v<=PARAMETERS[n][2])
 def test_one_click_approval_updates_all_nine_as_one_version(self):
  self.l.create_proposal();r=self.l.approve_latest();self.assertEqual(r['parameter_count'],9);rows=self.db.rows('SELECT * FROM strategy_parameters');self.assertEqual(len(rows),9);self.assertEqual(len({x['version'] for x in rows}),1);self.assertTrue(all(x['source'].startswith('APPROVED_PROPOSAL_') for x in rows))
 def test_no_automatic_change_and_insufficient_data_stays_closed(self):
  db=DB(tempfile.mktemp());db.init();l=LearningApproval(db);before=l.values()
  with db.con() as c:c.executescript("CREATE TABLE research_forecasts(id INTEGER PRIMARY KEY,symbol TEXT,scanner_score TEXT);CREATE TABLE forecast_evaluations(forecast_id INTEGER PRIMARY KEY,direction_correct INTEGER,actual_return_pct TEXT);CREATE TABLE market_universe(symbol TEXT,category TEXT);")
  self.assertEqual(l.create_proposal()['status'],'INSUFFICIENT_DATA');self.assertEqual(before,l.values())
