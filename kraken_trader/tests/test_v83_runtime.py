import ast
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
APP=ROOT/'app'

class V83CompatibilityTests(unittest.TestCase):
    def test_secret_sync_does_not_expose_hash(self):
        source=(APP/'v86_main.py').read_text(encoding='utf-8')
        self.assertIn('real_balancing_automation_secret_hash', source)
        self.assertIn('automation_secret_configured', source)
        self.assertNotIn('"real_balancing_automation_secret_hash":', source)

if __name__=='__main__':
    unittest.main()
