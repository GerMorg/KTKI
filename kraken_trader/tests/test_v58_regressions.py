import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

from jinja2 import Template

# test_v52 installs a minimal Flask stub; provide the one additional symbol
# needed to import the tax blueprint module without weakening runtime behavior.
import flask
if not hasattr(flask, 'Response'):
    class Response:  # pragma: no cover - import-only compatibility in tests
        pass
    flask.Response = Response

from at_income_tax import AustrianTaxInfo
from controlled_learning import ControlledLearning
from display_format import DisplayFloat, display_number, display_tree
from learning_approval import LearningApproval
from news_learning import NewsLearning
from strategy_profiles import FAMILIES


class V38DisplayRegressionTests(unittest.TestCase):
    def test_float_display_remains_arithmetic_safe(self):
        values = display_tree({'active': 0.1375, 'candidate': 0.1875})
        self.assertIsInstance(values['active'], DisplayFloat)
        self.assertAlmostEqual(values['candidate'] - values['active'], 0.05, places=8)
        self.assertEqual(str(values['active']), '0,1375')

    def test_jinja_float_filter_can_calculate_with_localized_values(self):
        values = display_tree({'active': 0.1375, 'candidate': 0.1875})
        rendered = Template('{{ "%.2f"|format((candidate-active)*100) }}').render(**values)
        self.assertEqual(rendered, '5.00')

    def test_number_display_avoids_unnecessary_precision_without_losing_small_price_precision(self):
        self.assertEqual(display_number(62.120000), '62,12')
        self.assertEqual(display_number(0.050001), '0,050001')
        self.assertEqual(display_number(0.0000123456), '0,00001235')

    def test_integer_display_remains_numeric(self):
        values = display_tree({'n': 5})
        self.assertEqual(values['n'], 5)
        self.assertIsInstance(values['n'], int)

    def test_float_formatting_and_raw_json_are_preserved(self):
        value = DisplayFloat('62.123456789')
        self.assertAlmostEqual(float(value), 62.123456789)
        self.assertEqual(f'{value:.2f}', '62.12')
        raw = '{"x":1.23456789}'
        self.assertEqual(display_tree({'parameters_json': raw})['parameters_json'], raw)


class V38ControlledLearningTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        from db import DB
        self.db = DB(os.path.join(self.tmp.name, 'x.db'))
        self.db.init()
        self.learning = ControlledLearning(self.db)

    def tearDown(self):
        self.tmp.cleanup()

    def _rows(self, count=20):
        return [{'id': i + 1, 'direction': 'UP' if i % 2 == 0 else 'DOWN', 'scanner_score': 50,
                 'features_json': json.dumps({'momentum_pct': 1 if i % 2 == 0 else -1,
                                               'trend_pct': 1 if i % 2 == 0 else -1,
                                               'volatility_pct': .2, 'spread_pct': .02}),
                 'horizon_hours': 24 if i < count // 2 else 168, 'direction_correct': 1,
                 'actual_return_pct': .5 if i % 2 == 0 else -.5} for i in range(count)]

    def test_candidate_search_uses_exact_training_rows_once(self):
        rows = self._rows(20)
        self.learning._candidate('forex', dict(FAMILIES['forex']), rows)
        self.assertEqual(self.learning._last_search_details['training_count'], len(rows))

    def test_horizon_policy_requires_enough_validation_observations(self):
        self.db.set_setting('learning_min_validation_samples', 3)
        self.db.set_setting('learning_min_horizon_samples', 5)
        policy = self.learning.gate_policy()
        self.assertEqual(policy['required_horizons'], [24, 168])
        self.learning._evaluations = lambda family: []
        result = self.learning.propose('forex', min_sample=10)
        self.assertEqual(result['status'], 'INSUFFICIENT_DATA')

    def test_approval_blocks_changed_validation_sample(self):
        rows = self._rows(1)
        self.learning._evaluations = lambda family: rows
        active = self.learning.active('forex')
        params = json.loads(active['parameters_json'])
        params['base_score'] = min(65.0, params['base_score'] + .5)
        with self.db.con() as c:
            cur = c.execute(
                'INSERT INTO learning_candidates(created_at,family,status,base_version,sample_count,active_accuracy,candidate_accuracy,improvement,ci_low,ci_high,parameters_json,reason,decided_at,gate_policy_json,gate_results_json,validation_fingerprint) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                ('2026-01-01T00:00:00+00:00', 'forex', 'PENDING', active['version'], 1, '0.5', '0.6', '0.1',
                 '0.5', '0.8', json.dumps(params, sort_keys=True), 'test', None, json.dumps(self.learning.gate_policy()), '[]', 'changed'))
            candidate_id = cur.lastrowid
            c.execute('INSERT INTO learning_shadow_results(created_at,candidate_id,forecast_id,active_correct,candidate_correct,details_json) VALUES(?,?,?,?,?,?)',
                      ('2026-01-01T00:00:00+00:00', candidate_id, 1, 1, 1, '{}'))
        result = self.learning.decide(candidate_id, 'approve')
        self.assertEqual(result['status'], 'REJECTED_RECHECK')
        self.assertEqual(result['reason'], 'VALIDATION_SAMPLE_CHANGED')

    def test_legacy_learning_facade_uses_same_active_xstock_version(self):
        facade = LearningApproval(self.db)
        active = self.learning.active('xstocks')
        self.assertEqual(facade.values(), json.loads(active['parameters_json']))
        self.assertIsNone(facade.latest())

    def test_approved_candidates_are_not_shown_as_actionable_again(self):
        active = self.learning.active('forex')
        with self.db.con() as c:
            c.execute(
                'INSERT INTO learning_candidates(created_at,family,status,base_version,sample_count,active_accuracy,candidate_accuracy,improvement,ci_low,ci_high,parameters_json,reason,decided_at,gate_policy_json,gate_results_json,validation_fingerprint) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                ('2026-01-01T00:00:00+00:00', 'forex', 'APPROVED', active['version'], 1, '0.5', '0.6', '0.1',
                 '0.5', '0.8', active['parameters_json'], 'test', '2026-01-01T00:01:00+00:00', '{}', '[]', 'x'))
        self.assertEqual(self.learning.candidates('forex'), [])


class V38NewsLearningTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        from db import DB
        self.db = DB(os.path.join(self.tmp.name, 'x.db'))
        self.db.init()
        self.learning = NewsLearning(self.db)

    def tearDown(self):
        self.tmp.cleanup()

    def test_candidate_identity_changes_with_teacher_content(self):
        rows = [{'id': '1', 'observed_at': '2026-01-01T00:00:00+00:00', 'title': 'a', 'summary': 'b',
                 'source_class': 'primary', 'teacher': {'sentiment': 'positive', 'relevance': .8, 'confidence': .8,
                                                        'expected_impact': 'medium'}}]
        first = self.learning._fingerprint(rows)
        rows[0]['teacher']['confidence'] = .9
        self.assertNotEqual(first, self.learning._fingerprint(rows))

    def test_active_version_is_part_of_automatic_candidate_dedupe_contract(self):
        cols = {x['name'] for x in self.db.rows('PRAGMA table_info(news_model_candidates)')}
        self.assertIn('base_version', cols)
        self.assertIn('sample_fingerprint', cols)
        self.assertIn('validation_ids_json', cols)
        self.assertIn('validation_fingerprint', cols)


class V38TaxTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        from db import DB
        self.db = DB(os.path.join(self.tmp.name, 'x.db'))
        self.db.init()
        self.tax = AustrianTaxInfo(self.db)

    def tearDown(self):
        self.tmp.cleanup()

    def test_real_trade_report_uses_real_trade_source_and_average_cost(self):
        with self.db.con() as c:
            c.execute('INSERT INTO real_tax_trades(txid,trade_time,pair,side,price,volume,cost,fee,payload_json,imported_at) VALUES(?,?,?,?,?,?,?,?,?,?)',
                      ('b1', 1735689600, 'BTC/EUR', 'buy', '50000', '1', '50000', '50', '{}', '2026-01-01T00:00:00+00:00'))
            c.execute('INSERT INTO real_tax_trades(txid,trade_time,pair,side,price,volume,cost,fee,payload_json,imported_at) VALUES(?,?,?,?,?,?,?,?,?,?)',
                      ('s1', 1735776000, 'BTC/EUR', 'sell', '51000', '1', '51000', '51', '{}', '2026-01-01T00:00:00+00:00'))
        rows, warnings = self.tax._real_rows(2025)
        self.assertEqual(warnings, [])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['source'], 'real')
        self.assertEqual(rows[0]['gain_loss_eur'], '949.00')
        self.assertEqual(rows[0]['estimated_tax_eur'], '260.98')


if __name__ == '__main__':
    unittest.main()
