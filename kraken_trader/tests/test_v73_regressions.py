import ast
import tempfile
import threading
import unittest
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];APP=ROOT/'app';sys.path.insert(0,str(APP))
from db import DB
from payload_utils import as_pair_mapping
class V73RegressionTests(unittest.TestCase):
 def test_asset_pairs_list_never_requires_tuple_unpacking(self):
  value=[{'wsname':'BTC/EUR','altname':'BTCEUR','base':'XXBT','quote':'ZEUR','status':'online'}]
  self.assertEqual(list(as_pair_mapping(value)),['BTC/EUR'])
  self.assertEqual(as_pair_mapping(value)['BTC/EUR']['base'],'XXBT')
 def test_db_init_moves_audit_schema_change_out_of_audit_path(self):
  source=(APP/'db.py').read_text(encoding='utf-8')
  self.assertIn("CREATE TABLE IF NOT EXISTS audit",source)
  self.assertIn("trade_context TEXT NOT NULL DEFAULT 'SYSTEM'",source)
  self.assertNotIn("ALTER TABLE audit ADD COLUMN trade_context",source.split(' def audit(',1)[1].split(' def replace_balances',1)[0])
 def test_db_con_serializes_threads_and_retries_locked_writes(self):
  with tempfile.NamedTemporaryFile(suffix='.db') as f:
   db=DB(f.name);db.init();errors=[]
   def worker(n):
    try:
     for i in range(25):db.audit('V73_CONCURRENCY',f'{n}:{i}')
    except Exception as exc:errors.append(exc)
   threads=[threading.Thread(target=worker,args=(i,)) for i in range(8)]
   for t in threads:t.start()
   for t in threads:t.join()
   self.assertFalse(errors)
   self.assertEqual(len(db.rows("SELECT * FROM audit WHERE event='V73_CONCURRENCY'")),200)
 def test_legacy_v73_runtime_remains_available(self):
  for name in ('v73_main.py',):ast.parse((APP/name).read_text(encoding='utf-8'),filename=name)
 def test_all_v73_modules_compile(self):
  for name in ('db.py','market_universe.py','payload_utils.py','v73_main.py'):
   ast.parse((APP/name).read_text(encoding='utf-8'),filename=name)
if __name__=='__main__':unittest.main()
