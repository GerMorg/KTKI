import ast
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1];APP=ROOT/'app'
class V78RegressionTests(unittest.TestCase):
 def test_runtime_shell_is_v78(self):
  run=(ROOT/'run.sh').read_text(encoding='utf-8');runtime=(APP/'v78_main.py').read_text(encoding='utf-8');self.assertIn('v78_main:app',run);self.assertIn("app.view_functions['index'] = _dashboard",runtime);self.assertIn("@app.get('/v78-health')",runtime)
 def test_gui_root_is_defensive_and_uses_template_string(self):
  source=(APP/'v78_main.py').read_text(encoding='utf-8');self.assertIn('def _safe(fn, default=None):',source);self.assertIn('portfolio, public, private, research = _status_snapshot()',source);self.assertIn('render_template_string(html',source);self.assertNotIn('render_template(html',source.split("def _dashboard():",1)[1].split("app.view_functions",1)[0])
 def test_analysis_has_candidate_recovery(self):
  source=(APP/'research_pipeline.py').read_text(encoding='utf-8');self.assertIn('def _recover_watchlist',source);self.assertIn('symbols=list(self.prefilter.candidates() or [])',source);self.assertIn('symbols=self._recover_watchlist',source);self.assertIn("'candidate_count':len(symbols)",source);self.assertIn("quality='VALID_WITH_WARNINGS'",source)
 def test_universe_defaults_have_categories(self):
  source=(APP/'market_universe.py').read_text(encoding='utf-8');self.assertIn('VALUES(?,?,1,?)',source);self.assertIn('return enabled or set(CATEGORIES)',source)
 def test_all_v78_runtime_sources_parse(self):
  for name in ('v78_main.py','v77_main.py','v76_main.py','research_pipeline.py','market_universe.py','scanner.py','prefilter.py','ws_private.py','portfolio_sync.py'):ast.parse((APP/name).read_text(encoding='utf-8'),filename=name)
if __name__=='__main__':unittest.main()
