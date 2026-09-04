import ast
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1];APP=ROOT/'app'
class V67RepositoryTests(unittest.TestCase):
 def test_new_modules_compile(self):
  for name in ('automation_v67.py','v67_main.py','v68_main.py','v69_main.py','v70_main.py','v71_main.py','v72_main.py','v73_main.py','v74_main.py','v75_main.py','v76_main.py','v77_main.py','v78_main.py','v79_main.py','v80_main.py','payload_utils.py','at_income_tax_v68.py'):
   ast.parse((APP/name).read_text(encoding='utf-8'),filename=name)
 def test_runtime_uses_latest_entrypoint(self):
  run=(ROOT/'run.sh').read_text(encoding='utf-8');self.assertIn('v80_main:app',run)
 def test_versions_and_new_controls(self):
  version=(APP/'version.py').read_text(encoding='utf-8');config=(ROOT/'config.yaml').read_text(encoding='utf-8')
  self.assertIn("APP_VERSION='0.1.0-dev.80'",version);self.assertIn('version: 0.1.0-dev.80',config)
  for key in ('automation_master_enabled','automation_analysis_enabled','automation_news_enabled','automation_learning_enabled','automation_paper_enabled','automation_real_enabled','automation_real_execute_enabled','learning_max_evaluations','news_learning_max_samples','analysis_max_symbols'):
   self.assertIn(key+':',config)
 def test_process_navigation_and_portfolio_graph(self):
  source=(APP/'v67_main.py').read_text(encoding='utf-8');expected=["('/', 'Übersicht')","('/analyse','1 Analyse')","('/portfolio-modern','2 Portfolio')","('/handel','3 Handel')","('/lernen-modern','4 Lernen')","('/automatik','5 Automatik')"];positions=[source.index(x) for x in expected];self.assertEqual(positions,sorted(positions));self.assertIn('polyline',source);self.assertIn('Portfolioverlauf',source)
 def test_single_scheduler_disables_legacy_schedulers(self):
  source=(APP/'v67_main.py').read_text(encoding='utf-8');self.assertIn('APP_DISABLE_PAPER_SCHEDULER',source);self.assertIn('APP_DISABLE_RESEARCH_SCHEDULER',source);self.assertIn('APP_DISABLE_REAL_BALANCING_SCHEDULER',source)
 def test_v68_tax_runtime_replacement_exists(self):
  source=(APP/'v68_main.py').read_text(encoding='utf-8');self.assertIn('at_tax_v63.tax_info',source);self.assertIn('AustrianTaxV68',source);self.assertIn('tax-info-v68.zip',source)
if __name__=='__main__':unittest.main()
