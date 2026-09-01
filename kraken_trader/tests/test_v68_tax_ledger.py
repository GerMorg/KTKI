import os
import tempfile
import unittest
from datetime import datetime, timezone
from decimal import Decimal

from db import DB
from at_income_tax_v68 import AustrianTaxV68


class V68TaxLedgerTests(unittest.TestCase):
    def setUp(self):
        fd, self.path = tempfile.mkstemp(prefix='ktki-tax-v68-', suffix='.db')
        os.close(fd)
        self.db = DB(self.path)
        self.db.init(1000)
        self.service = AustrianTaxV68(self.db)

    def tearDown(self):
        try:
            os.remove(self.path)
        except FileNotFoundError:
            pass

    @staticmethod
    def ts(value):
        return datetime.fromisoformat(value).replace(tzinfo=timezone.utc).timestamp()

    def add_trade(self, txid, stamp, side, price, volume, cost, fee='0.00', pair='BTC/EUR'):
        with self.db.con() as c:
            c.execute('''INSERT INTO at68_real_trades
                         (txid,trade_time,pair,side,price,volume,cost,fee,ordertxid,raw_json,imported_at)
                         VALUES(?,?,?,?,?,?,?,?,?,?,?)''',
                      (txid, self.ts(stamp), pair, side, str(price), str(volume), str(cost), str(fee), '', '{}', stamp))

    def test_average_cost_realized_gain_and_inventory(self):
        self.add_trade('b1', '2025-01-10T10:00:00', 'buy', 100, 1, 100, '1')
        self.add_trade('b2', '2025-02-10T10:00:00', 'buy', 200, 1, 200, '2')
        self.add_trade('s1', '2025-03-10T10:00:00', 'sell', 250, 1, 250, '2.5')
        report = self.service.analyze(2025, refresh=False)
        sells = [x for x in report['realized'] if x['side'] == 'SELL']
        self.assertEqual(sells[0]['acquisition_basis_eur'], '151.50')
        self.assertEqual(sells[0]['proceeds_eur'], '247.50')
        self.assertEqual(sells[0]['gain_loss_eur'], '96.00')
        self.assertEqual(report['inventory'][0]['quantity'], '1.00')

    def test_usd_trade_uses_cached_historical_fx_rate(self):
        self.add_trade('u1', '2025-05-01T10:00:00', 'buy', 100, 1, 100, '1', 'BTC/USD')
        self.add_trade('u2', '2025-05-05T10:00:00', 'sell', 130, 1, 130, '1.3', 'BTC/USD')
        realized, _, warnings = self.service.build_realized(2025, {'2025-05-01': Decimal('1.10'), '2025-05-05': Decimal('1.05')})
        sells = [x for x in realized if x['side'] == 'SELL']
        self.assertEqual(sells[0]['gross_value_eur'], '123.81')
        self.assertEqual(sells[0]['review_required'], 'no')
        self.assertFalse(warnings)

    def test_missing_fx_requires_review(self):
        self.add_trade('u1', '2025-05-01T10:00:00', 'buy', 100, 1, 100, '1', 'BTC/USD')
        realized, _, _ = self.service.build_realized(2025, {})
        self.assertEqual(realized[0]['review_required'], 'yes')
        self.assertIn('HISTORISCHE_EUR_USD_RATE_FEHLT', realized[0]['review_reasons'])

    def test_missing_opening_basis_requires_review(self):
        self.add_trade('s1', '2025-06-01T10:00:00', 'sell', 250, 1, 250, '2.5')
        realized, _, warnings = self.service.build_realized(2025, {})
        self.assertEqual(realized[0]['review_required'], 'yes')
        self.assertIn('ANSCHAFFUNGSBESTAND_FEHLT_ODER_WIRD_EXTERN_GEHALTEN', realized[0]['review_reasons'])
        self.assertTrue(warnings)

    def test_persist_creates_hashed_machine_readable_exports(self):
        self.add_trade('b1', '2025-01-10T10:00:00', 'buy', 100, 1, 100, '1')
        self.add_trade('s1', '2025-02-10T10:00:00', 'sell', 125, 1, 125, '1.25')
        report = self.service.generate(2025, refresh=False)
        self.assertTrue(report['report_id'])
        self.assertEqual(len(report['summary']['content_sha256']), 64)
        self.assertEqual(set(report['csv']), {'realized', 'inventory', 'cashflow', 'audit', 'e1kv'})
        self.assertTrue(self.service.export_zip(2025).startswith(b'PK'))


if __name__ == '__main__':
    unittest.main()
