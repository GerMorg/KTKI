import ast
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
APP=ROOT/'app'

class V83CompatibilityTests(unittest.TestCase):
    def test_v86_compatibility_runtime_wiring_is_safe(self):
        source=(APP/'v86_main.py').read_text(encoding='utf-8')
        self.assertNotIn('import v81_main as base', source)
        self.assertNotIn('import v82_main as base', source)
        self.assertIn('import v84_main as base', source)
        self.assertIn('controller = base.controller', source)
        self.assertIn('legacy.db', source)
        self.assertIn("\"version\": \"0.1.0-dev.86\"", source)
        ast.parse(source, filename='v86_main.py')

    def test_active_runtime_and_version_are_v86(self):
        self.assertIn('v86_main:app',(ROOT/'run.sh').read_text(encoding='utf-8'))
        self.assertIn("APP_VERSION='0.1.0-dev.86'",(APP/'version.py').read_text(encoding='utf-8'))
        self.assertIn('version: 0.1.0-dev.86',(ROOT/'config.yaml').read_text(encoding='utf-8'))
        self.assertIn('version: 0.1.0-dev.86',(ROOT.parent/'repository.yaml').read_text(encoding='utf-8'))

    def test_secret_sync_does_not_expose_hash(self):
        source=(APP/'v86_main.py').read_text(encoding='utf-8')
        self.assertIn('real_balancing_automation_secret_hash', source)
        self.assertIn('automation_secret_configured', source)
        self.assertNotIn('"real_balancing_automation_secret_hash":', source)

if __name__=='__main__':
    unittest.main()
