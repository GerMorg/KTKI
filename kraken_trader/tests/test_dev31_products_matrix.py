import json,os,sys,tempfile,unittest
sys.path.insert(0,os.path.join(os.path.dirname(__file__),'..','app'))
from db import DB,now
from product_view import ProductView
from decision_matrix import DecisionMatrix
class T(unittest.TestCase):
 def setUp(self):
  self.db=DB(tempfile.mktemp());self.db.init();
  with self.db.con() as c:
   c.execute("CREATE TABLE canonical_products(canonical_id TEXT PRIMARY KEY,asset_class TEXT,base_asset TEXT,category TEXT,selected_symbol TEXT,alternatives_json TEXT,updated_at TEXT)");c.execute("CREATE TABLE paper_positions(symbol TEXT PRIMARY KEY,quantity TEXT,avg_cost_eur TEXT,updated_at TEXT)")
   data={'pairs':['AAPLx/EUR','AAPLx/USD'],'ranking':[{'symbol':'AAPLx/EUR','total_cost_rate':'0.020'},{'symbol':'AAPLx/USD','total_cost_rate':'0.010'}]};c.execute("INSERT INTO canonical_products VALUES('xstock:AAPLX','tokenized_asset','AAPLx','xstocks','AAPLx/USD',?,?)",(json.dumps(data),now()));c.execute("INSERT INTO paper_positions VALUES('AAPLx/USD','2','100',?)",(now(),))
 def test_product_view_exposes_identity_alternatives_costs_and_position(self):
  r=ProductView(self.db).rows()[0];self.assertEqual(r['canonical_id'],'xstock:AAPLX');self.assertEqual(r['selected_symbol'],'AAPLx/USD');self.assertEqual(r['eur_cost'],'0.020');self.assertEqual(r['usd_cost'],'0.010');self.assertEqual(r['position_quantity'],'2')
 def test_matrix_persists_all_seven_rules_and_first_blocker(self):
  m=DecisionMatrix(self.db);r=m.evaluate('EUR/USD','BUY',{'canonical_id':'forex:EUR','confirmation_count':2,'confirmation_required':2,'minimum_hold_ok':True,'cooldown_ok':True,'daily_limit_ok':False,'improvement_after_costs':'5','tax_loss_ok':True,'data_fresh':True});self.assertFalse(r['allowed']);self.assertIn('Umschichtungslimit',r['blocker']);self.assertEqual(len(m.recent()),7)
 def test_data_freshness_is_hard_gate(self):
  r=DecisionMatrix(self.db).evaluate('EUR/USD','BUY',{'confirmation_count':1,'confirmation_required':1,'improvement_after_costs':'1','data_fresh':False});self.assertFalse(r['allowed']);self.assertEqual(r['checks'][-1]['rule_key'],'DATA_FRESHNESS')
if __name__=='__main__':unittest.main()





