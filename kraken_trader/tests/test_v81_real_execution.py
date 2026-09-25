import hashlib
import os
import sys
import tempfile
import unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))
from db import DB
from real_autonomous_v81 import RealPortfolioAllocatorV81, install_real_settings


class Engine:
    def __init__(self):
        self.calls = []
        self.client = None
    def enabled(self):
        return True
    def submit(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        return {'status': 'SUBMITTED', 'client_order_id': kwargs.get('client_order_id') or args[5]}


class V81RealExecutionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = DB(os.path.join(self.tmp.name, 'x.db'))
        self.db.init()

    def tearDown(self):
        self.tmp.cleanup()

    def test_real_options_are_persisted_and_secret_is_hashed(self):
        install_real_settings(self.db, {
            'real_trading_enabled': True,
            'real_kill_switch': False,
            'real_balancing_automation_secret': 'test-secret',
        })
        self.assertEqual(self.db.value('real_trading_enabled'), 'True')
        self.assertEqual(self.db.value('real_kill_switch'), 'False')
        self.assertEqual(self.db.value('real_balancing_automation_secret_hash'), hashlib.sha256(b'test-secret').hexdigest())

    def test_held_symbols_are_discoverable_for_rebalancing(self):
        with self.db.con() as c:
            c.execute("INSERT INTO private_balances VALUES('XBT','0.01','[]',1,CURRENT_TIMESTAMP)")
            c.execute("INSERT INTO market_universe(symbol,canonical_id,asset_class,category,base_asset,quote_asset,source_key,ordermin,costmin) VALUES('BTC/EUR','BTC','crypto','crypto_spot','XBT','EUR','BTC/EUR','0.0001','5')")
        allocator = RealPortfolioAllocatorV81(self.db, Engine())
        self.assertEqual(allocator._held_symbols(), ['BTC/EUR'])

    def test_dry_run_never_submits(self):
        self.db.set_setting('real_balancing_enabled', 'true')
        self.db.set_setting('real_trading_enabled', 'true')
        self.db.set_setting('real_kill_switch', 'false')
        self.db.set_setting('real_balancing_execute_enabled', 'true')
        self.db.set_setting('real_balancing_dry_run', 'true')
        allocator = RealPortfolioAllocatorV81(self.db, Engine())
        result = allocator.run(True)
        self.assertIn(result['status'], ('COMPLETED', 'DISABLED', 'BUSY'))
        self.assertEqual(allocator.trade_engine.calls, [])


if __name__ == '__main__':
    unittest.main()
