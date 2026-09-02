import ast
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1];APP=ROOT/'app'
class V69RegressionTests(unittest.TestCase):
 def test_runtime_keeps_legacy_baselines_and_uses_latest_runtime(self):
  run=(ROOT/'run.sh').read_text(encoding='utf-8');self.assertIn('v70/v71/v72/v73/v74/v75/v76/v77 remain preserved compatibility baselines',run);self.assertIn('v78_main:app',run);self.assertNotIn('v69_main:app',run);self.assertNotIn('v73_main:app',run);self.assertNotIn('v74_main:app',run);self.assertNotIn('v75_main:app',run);self.assertNotIn('v76_main:app',run);self.assertNotIn('v77_main:app',run)
 def test_paper_payload_normalizer_accepts_list_and_dict(self):
  source=(APP/'v69_main.py').read_text(encoding='utf-8');self.assertIn('_normalize_ticker_payload',source);self.assertIn('if isinstance(payload, list)',source);self.assertIn('if isinstance(item, list)',source)
 def test_tax_gui_is_in_main_process_navigation(self):
  source=(APP/'v69_main.py').read_text(encoding='utf-8');self.assertIn("('/tax-info','6 Steuer')",source);self.assertIn('def tax_ui_v69',source)
 def test_chart_has_line_area_and_grid(self):
  source=(APP/'v69_main.py').read_text(encoding='utf-8');self.assertIn('def chart_v69',source);self.assertIn('polyline',source);self.assertIn('polygon',source);self.assertIn('chart-gridline',source)
 def test_core_modules_parse(self):
  for name in ('v69_main.py','at_income_tax_v68.py'):ast.parse((APP/name).read_text(encoding='utf-8'),filename=name)
if __name__=='__main__':unittest.main()
