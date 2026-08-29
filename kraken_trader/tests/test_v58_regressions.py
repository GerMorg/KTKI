import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

from controlled_learning import ControlledLearning
from display_format import DisplayFloat, display_tree
from learning_approval import LearningApproval
from news_learning import NewsLearning
from strategy_profiles import FAMILIES


class V38DisplayRegressionTests(unittest.TestCase):
    def test_float_display_remains_arithmetic_safe(self):
        values = display_tree({'active': 0.1375, 'candidate': 0.1875})
        self.assertIsInstance(values['active'], DisplayFloat)
        self.assertAlmostEqual(values['candidate'] - values['active'], 0.05, places=8)
        self.assertEqual(str(values['active']), '0,1375')

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

    def test_legacy_learning_facade_uses_same_active_xstock_version(self):
        facade = LearningApproval(self.db)
        active = self.learning.active('xstocks')
        self.assertEqual(facade.values(), json.loads(active['parameters_json']))
        self.assertIsNone(facade.latest())


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


if __name__ == '__main__':
    unittest.main()
