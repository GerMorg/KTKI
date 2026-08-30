import os, tempfile, unittest
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))
from db import DB
from model_validation import ModelValidationEngine

class V62ModelValidationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.db=DB(os.path.join(self.tmp.name,'x.db')); self.db.init()
        with self.db.con() as c: c.execute('CREATE TABLE ohlc_cache(open_time INTEGER, close TEXT, symbol TEXT, interval_min INTEGER)')
        self.engine=ModelValidationEngine(self.db)
    def tearDown(self): self.tmp.cleanup()
    def _prices(self,n=220):
        p=100.0; out=[]
        for i in range(n): p*=1.001 if (i//12)%2==0 else .999; out.append(p)
        return out
    def test_insufficient_data_is_explicit(self):
        with self.db.con() as c:
            for i,p in enumerate(self._prices(80)): c.execute('INSERT INTO ohlc_cache VALUES(?,?,?,?)',(i,p,'BTC/EUR',60))
        self.assertEqual(self.engine.run('BTC/EUR')['status'],'INSUFFICIENT')
    def test_walk_forward_reports_costs_and_benchmarks(self):
        with self.db.con() as c:
            for i,p in enumerate(self._prices()): c.execute('INSERT INTO ohlc_cache VALUES(?,?,?,?)',(i,p,'BTC/EUR',60))
        result=self.engine.run('BTC/EUR',60,.006,folds=4,embargo_points=2)
        self.assertIn(result['status'],('VALID','NOT_ROBUST')); self.assertEqual(result['method'],'chronological_walk_forward_with_embargo_v62')
        self.assertEqual(len(result['folds']),4); self.assertEqual([g['name'] for g in result['gates']],['POSITIVE_AFTER_COSTS','OUTPERFORMS_BUY_HOLD','CONSISTENT_FOLDS'])
        self.assertTrue(all(f['embargo_points']==2 for f in result['folds']))
    def test_validation_never_executes_orders(self):
        self.assertFalse(hasattr(self.engine,'client')); self.assertFalse(any('AddOrder' in x for x in self.engine.__class__.__dict__))

if __name__=='__main__': unittest.main()
