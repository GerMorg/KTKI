import ast
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
APP=ROOT/'app'

class V84RuntimeTests(unittest.TestCase):
    def test_v84_is_active_and_syncs_explicit_automation_options(self):
        runtime=(APP/'v84_main.py').read_text(encoding='utf-8')
        self.assertIn('import v80_main as base',runtime)
        self.assertIn('def _sync_options',runtime)
        self.assertIn('automation_real_execute_enabled',runtime)
        self.assertIn('db.set(key, normalized)',runtime)
        self.assertIn('"version": "0.1.0-dev.84"',runtime)
        self.assertNotIn('"real_balancing_automation_secret_hash":',runtime)
        self.assertIn('v84_main:app',(ROOT/'run.sh').read_text(encoding='utf-8'))
        self.assertIn("APP_VERSION='0.1.0-dev.84'",(APP/'version.py').read_text(encoding='utf-8'))
        self.assertIn('version: 0.1.0-dev.84',(ROOT/'config.yaml').read_text(encoding='utf-8'))
        self.assertIn('version: 0.1.0-dev.84',(ROOT.parent/'repository.yaml').read_text(encoding='utf-8'))
        ast.parse(runtime,filename='v84_main.py')

    def test_rebalancing_does_not_slice_candidates_before_gate_evaluation(self):
        source=(APP/'real_portfolio_allocator.py').read_text(encoding='utf-8')
        self.assertIn('for target in targets:',source)
        self.assertIn('submitted_count>=room',source)
        self.assertIn("if status=='SUBMITTED':submitted_count+=1",source)
        self.assertNotIn("for target in targets[:min(cfg['max_actions_per_run'],room)]:",source)
        self.assertIn("'evaluated_candidates':evaluated_count",source)
        self.assertIn("'skipped_for_capacity':skipped_for_capacity",source)

if __name__=='__main__':
    unittest.main()
