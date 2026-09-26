import ast
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
APP=ROOT/'app'

class V84RuntimeTests(unittest.TestCase):
    def test_v84_compatibility_runtime_syncs_explicit_automation_options(self):
        runtime=(APP/'v86_main.py').read_text(encoding='utf-8')
        self.assertIn('import v84_main as base',runtime)
        self.assertNotIn('def _sync_options',runtime)
        self.assertIn("'automation_real_execute_enabled'",(APP/'automation_v67.py').read_text(encoding='utf-8'))
        self.assertIn('controller = base.controller',runtime)
        self.assertIn('"version": "0.1.0-dev.86"',runtime)
        self.assertNotIn('"real_balancing_automation_secret_hash":',runtime)
        self.assertIn('v87_main:app',(ROOT/'run.sh').read_text(encoding='utf-8'))
        self.assertIn("APP_VERSION='0.1.0-dev.87'",(APP/'version.py').read_text(encoding='utf-8'))
        self.assertIn('version: 0.1.0-dev.87',(ROOT/'config.yaml').read_text(encoding='utf-8'))
        self.assertIn('version: 0.1.0-dev.87',(ROOT.parent/'repository.yaml').read_text(encoding='utf-8'))
        ast.parse(runtime,filename='v86_main.py')

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
