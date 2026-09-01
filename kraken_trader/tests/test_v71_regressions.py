import ast
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
APP=ROOT/'app'

class V71RegressionTests(unittest.TestCase):
    def test_controller_normalizes_before_status_get(self):
        source=(APP/'automation_v67.py').read_text(encoding='utf-8')
        self.assertIn('def as_mapping',source)
        self.assertIn('result=as_mapping(result)',source)
        self.assertIn("result.get('status')",source)

    def test_v69_uses_actual_legacy_core(self):
        source=(APP/'v69_main.py').read_text(encoding='utf-8')
        self.assertIn('legacy = core.legacy',source)
        self.assertIn('symbols = list(legacy.current_market_batch())',source)
        self.assertNotIn('core.current_market_batch()',source)

    def test_v71_remains_available_as_compatibility_runtime(self):
        source=(APP/'v71_main.py').read_text(encoding='utf-8')
        self.assertIn("'runtime': 'v71_main'",source)
        self.assertIn("'paper_market_batch_source': 'legacy.current_market_batch'",source)

    def test_all_runtime_modules_compile(self):
        for name in ('automation_v67.py','v67_main.py','v68_main.py','v69_main.py','v70_main.py','v71_main.py','v72_main.py'):
            ast.parse((APP/name).read_text(encoding='utf-8'),filename=name)

if __name__=='__main__':
    unittest.main()
