import ast
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / 'app'


class V77RuntimeTests(unittest.TestCase):
    def test_single_active_runtime(self):
        run = (ROOT / 'run.sh').read_text(encoding='utf-8')
        version = (APP / 'version.py').read_text(encoding='utf-8')
        config = (ROOT / 'config.yaml').read_text(encoding='utf-8')
        self.assertIn('v77_main:app', run)
        self.assertNotIn('v76_main:app', run)
        self.assertIn("APP_VERSION='0.1.0-dev.77'", version)
        self.assertIn('version: 0.1.0-dev.77', config)

    def test_old_runtime_wrappers_are_removed(self):
        removed = [*(f'v{x}_main.py' for x in range(67, 77)), 'automation_v67.py', 'at_income_tax_v68.py']
        for name in removed:
            self.assertFalse((APP / name).exists(), name)

    def test_v77_exposes_learning_transparency(self):
        source = (APP / 'v77_main.py').read_text(encoding='utf-8')
        for token in ('/lernen', '/lernen/run', '/lernen/decision', 'learning_reason', 'gate_results', 'comparison_json'):
            self.assertIn(token, source)

    def test_v77_exposes_austrian_income_tax(self):
        source = (APP / 'v77_main.py').read_text(encoding='utf-8')
        tax = (APP / 'at_income_tax.py').read_text(encoding='utf-8')
        self.assertIn("'/tax-info'", source)
        self.assertIn('Einkommensteuer AT', source)
        self.assertIn("@bp.get('/tax-info'", tax)
        self.assertIn('27,5 %', tax)

    def test_only_new_automation_controller_is_used(self):
        source = (APP / 'v77_main.py').read_text(encoding='utf-8')
        controller = (APP / 'automation_controller.py').read_text(encoding='utf-8')
        self.assertIn('from automation_controller import AutomationController', source)
        self.assertIn('class AutomationController', controller)
        self.assertNotIn('from automation_v67 import', source)

    def test_learning_decision_persistence_exists(self):
        source = (APP / 'controlled_learning.py').read_text(encoding='utf-8')
        for token in ('REJECTED_GATE', 'PENDING', 'APPROVED', 'gate_results_json', 'validation_fingerprint', 'CONTROLLED_LEARNING_APPROVAL_BLOCKED'):
            self.assertIn(token, source)

    def test_all_v77_sources_compile(self):
        for name in ('v77_main.py', 'automation_controller.py', 'controlled_learning.py', 'news_learning.py', 'at_income_tax.py', 'research_pipeline.py'):
            ast.parse((APP / name).read_text(encoding='utf-8'), filename=name)


if __name__ == '__main__':
    unittest.main()
