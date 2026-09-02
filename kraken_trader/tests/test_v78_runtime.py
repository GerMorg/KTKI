import ast
import unittest
from pathlib import Path

ADDON=Path(__file__).resolve().parents[1]
REPO=ADDON.parent
APP=ADDON/'app'

class V78RuntimeTests(unittest.TestCase):
 def test_single_entrypoint(self):
  run=(ADDON/'run.sh').read_text()
  self.assertIn('v78_main:app',run);self.assertIn('--workers 1',run);self.assertIn('--threads 2',run)
 def test_version(self):
  ns={};exec((APP/'version.py').read_text(),ns)
  self.assertEqual(ns['APP_VERSION'],'0.1.0-dev.78');self.assertEqual(ns['USER_AGENT'],'HA-Kraken-Trader/0.1.0-dev.78')
 def test_legacy_runtime_files_removed(self):
  for name in ('v66_integration_marker.txt','version_v66.py','autonomous_orchestrator_v66.py','autonomous_portfolio_v65.py','model_validation_v63.py','portfolio_digital_twin_v64.py','portfolio_optimization_v64.py','v77_main.py'):
   self.assertFalse((APP/name).exists(),name)
 def test_legacy_scheduler_is_not_referenced(self):
  controller=(APP/'automation_controller.py').read_text()
  self.assertNotIn('automation_runs_v67',controller);self.assertIn('self.thread',controller);self.assertIn('is_alive()',controller)
 def test_lazy_start_guards(self):
  runtime=(APP/'v78_main.py').read_text()
  for token in ('APP_DISABLE_WEBSOCKETS','APP_SKIP_TEXT_REPAIR','AutomationController','ControlledLearning','NewsLearning','/lernen','/automatik','/tax-info'):
   self.assertIn(token,runtime)
 def test_python_syntax(self):
  for path in (APP/'v78_main.py',APP/'automation_controller.py',APP/'text_encoding.py',APP/'main.py'):
   ast.parse(path.read_text(),filename=str(path))
 def test_clean_addon_config(self):
  config=(ADDON/'config.yaml').read_text()
  self.assertIn('version: 0.1.0-dev.78',config);self.assertIn('public_websocket_enabled:',config);self.assertIn('private_websocket_readonly_enabled:',config)
 def test_repository_duplicates_removed(self):
  self.assertFalse((REPO/'config.yaml').exists());self.assertFalse((REPO/'PROJECT_HANDOVER.txt').exists());self.assertFalse((REPO/'v66_ci_refresh_20260830.txt').exists())

if __name__=='__main__':unittest.main()
