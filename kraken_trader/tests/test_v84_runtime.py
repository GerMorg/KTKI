import ast
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
APP=ROOT/'app'

class V84RuntimeTests(unittest.TestCase):
    def test_rebalancing_does_not_slice_candidates_before_gate_evaluation(self):
        source=(APP/'real_portfolio_allocator.py').read_text(encoding='utf-8')
        self.assertIn('for target in targets:',source)
        self.assertIn('submitted_count>=execution_capacity',source)
        self.assertIn("if status=='SUBMITTED':submitted_count+=1",source)
        self.assertNotIn("for target in targets[:min(cfg['max_actions_per_run'],room)]:",source)
        self.assertIn("'evaluated_candidates':evaluated_count",source)
        self.assertIn("'skipped_for_capacity':skipped_for_capacity",source)

if __name__=='__main__':
    unittest.main()
