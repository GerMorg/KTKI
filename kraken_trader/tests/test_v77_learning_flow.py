import json
import tempfile
import unittest
from pathlib import Path
import sys

APP = Path(__file__).resolve().parents[1] / 'app'
sys.path.insert(0, str(APP))

from db import DB
from controlled_learning import ControlledLearning


class V77LearningFlowTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = DB(str(Path(self.tmp.name) / 'test.db'))
        self.db.init(1000)
        self.learning = ControlledLearning(self.db)

    def tearDown(self):
        self.tmp.cleanup()

    def test_active_parameters_have_versioned_state(self):
        families = self.learning.active_versions()
        self.assertEqual({x['family'] for x in families}, {'forex', 'xstocks', 'crypto_spot'})
        for row in families:
            self.assertEqual(row['status'], 'ACTIVE')
            params = json.loads(row['parameters_json'])
            self.assertTrue(params)

    def test_gate_policy_is_explicit(self):
        policy = self.learning.gate_policy()
        self.assertEqual(policy['required_horizons'], [24, 168])
        self.assertGreaterEqual(policy['minimum_horizon_samples'], 1)
        self.assertGreaterEqual(policy['minimum_candidate_coverage'], 0)
        self.assertIn('minimum_net_return_improvement', policy)
        self.assertIn('maximum_candidate_drawdown_pct', policy)

    def test_insufficient_data_is_explicit_not_silent(self):
        result = self.learning.propose('forex', min_sample=10)
        self.assertEqual(result['status'], 'INSUFFICIENT_DATA')
        self.assertEqual(result['sample_count'], 0)
        self.assertEqual(result['required'], 10)

    def test_no_implicit_activation_without_candidate(self):
        before = self.learning.active('forex')
        result = self.learning.propose('forex', min_sample=10)
        after = self.learning.active('forex')
        self.assertEqual(result['status'], 'INSUFFICIENT_DATA')
        self.assertEqual(before['version'], after['version'])
        self.assertEqual(before['parameters_json'], after['parameters_json'])


if __name__ == '__main__':
    unittest.main()
