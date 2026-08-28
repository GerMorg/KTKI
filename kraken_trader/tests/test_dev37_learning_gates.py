import json, os, sys, tempfile, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))
from db import DB, now
from controlled_learning import ControlledLearning, FAMILIES


class Dev37LearningGateTests(unittest.TestCase):
    def setUp(self):
        self.db = DB(tempfile.mktemp())
        self.db.init()
        self.learning = ControlledLearning(self.db)

    def metric(self, horizon=24, samples=10, coverage=.8, improvement=.4,
               active_dd=-5, candidate_dd=-6):
        return {'horizon_hours': horizon, 'sample_count': samples,
                'active_coverage': .8, 'candidate_coverage': coverage,
                'active_net_return': 1, 'candidate_net_return': 1 + improvement,
                'net_return_improvement': improvement,
                'active_max_drawdown': active_dd,
                'candidate_max_drawdown': candidate_dd,
                'active_decisions': 8, 'candidate_decisions': int(samples * coverage)}

    def passing_metrics(self):
        return [self.metric(24), self.metric(168)]

    def test_default_policy_requires_both_horizons(self):
        gates = self.learning._gate_results([self.metric(24)], .03, .02)
        failed = {(x['gate'], x['horizon_hours']) for x in gates if not x['passed']}
        self.assertIn(('HORIZON_PRESENT', 168), failed)

    def test_coverage_net_return_and_drawdown_are_hard_gates(self):
        cases = [
            (self.metric(24, coverage=.2), 'MINIMUM_CANDIDATE_COVERAGE'),
            (self.metric(24, improvement=-.1), 'POSITIVE_NET_RETURN_IMPROVEMENT'),
            (self.metric(24, candidate_dd=-30), 'MAXIMUM_CANDIDATE_DRAWDOWN'),
            (self.metric(24, active_dd=-2, candidate_dd=-8), 'MAXIMUM_DRAWDOWN_DEGRADATION'),
        ]
        for broken, expected in cases:
            metrics = [broken, self.metric(168)]
            failed = {x['gate'] for x in self.learning._gate_results(metrics, .03, .02) if not x['passed']}
            self.assertIn(expected, failed)

    def test_policy_is_configurable_and_bounded(self):
        self.db.set('learning_min_candidate_coverage', '1.5')
        self.db.set('learning_max_drawdown_degradation_pct', '-4')
        policy = self.learning.gate_policy()
        self.assertEqual(policy['minimum_candidate_coverage'], 1.0)
        self.assertEqual(policy['maximum_drawdown_degradation_pct'], 0.0)

    def create_pending(self):
        active = self.learning.active('forex')
        params = active['parameters_json']
        policy = self.learning.gate_policy()
        gates = self.learning._gate_results(self.passing_metrics(), .03, .02, policy)
        with self.db.con() as c:
            cur = c.execute('INSERT INTO learning_candidates(created_at,family,status,base_version,sample_count,active_accuracy,candidate_accuracy,improvement,ci_low,ci_high,parameters_json,reason,decided_at,gate_policy_json,gate_results_json) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                (now(), 'forex', 'PENDING', active['version'], 20, '.6', '.63', '.03', '.4', '.8', params,
                 'test', None, json.dumps(policy), json.dumps(gates)))
            cid = cur.lastrowid
            for metric in self.passing_metrics():
                c.execute('INSERT INTO learning_candidate_metrics(candidate_id,horizon_hours,sample_count,active_decisions,candidate_decisions,active_coverage,candidate_coverage,active_net_return,candidate_net_return,net_return_improvement,active_max_drawdown,candidate_max_drawdown,details_json) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)',
                    (cid, metric['horizon_hours'], metric['sample_count'], metric['active_decisions'],
                     metric['candidate_decisions'], str(metric['active_coverage']), str(metric['candidate_coverage']),
                     str(metric['active_net_return']), str(metric['candidate_net_return']),
                     str(metric['net_return_improvement']), str(metric['active_max_drawdown']),
                     str(metric['candidate_max_drawdown']), json.dumps(metric)))
        return cid

    def test_approval_rechecks_and_allows_unchanged_passing_metrics(self):
        cid = self.create_pending()
        result = self.learning.decide(cid, 'approve')
        self.assertEqual(result['status'], 'APPROVED')
        self.assertEqual(self.learning.active('forex')['version'], 2)

    def test_approval_recheck_blocks_changed_metrics_atomically(self):
        cid = self.create_pending()
        with self.db.con() as c:
            c.execute("UPDATE learning_candidate_metrics SET candidate_coverage='0' WHERE candidate_id=? AND horizon_hours=24", (cid,))
        result = self.learning.decide(cid, 'approve')
        self.assertEqual(result['status'], 'REJECTED_RECHECK')
        self.assertEqual(self.learning.active('forex')['version'], 1)
        self.assertEqual(self.learning.candidates()[0]['status'], 'REJECTED_RECHECK')

    def test_old_schema_migrates_gate_columns_idempotently(self):
        cols = {x['name'] for x in self.db.rows('PRAGMA table_info(learning_candidates)')}
        self.assertTrue({'gate_policy_json', 'gate_results_json'}.issubset(cols))
        ControlledLearning(self.db)
        cols2 = {x['name'] for x in self.db.rows('PRAGMA table_info(learning_candidates)')}
        self.assertEqual(cols, cols2)


if __name__ == '__main__':
    unittest.main()

