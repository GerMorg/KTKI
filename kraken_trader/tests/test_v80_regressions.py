import ast
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1];APP=ROOT/'app';REPO=ROOT.parent

class V80RegressionTests(unittest.TestCase):
 def test_active_runtime_and_versions(self):
  self.assertIn('v80_main:app',(ROOT/'run.sh').read_text(encoding='utf-8'))
  self.assertIn("APP_VERSION='0.1.0-dev.80'",(APP/'version.py').read_text(encoding='utf-8'))
  self.assertIn('version: 0.1.0-dev.80',(ROOT/'config.yaml').read_text(encoding='utf-8'))
  self.assertIn('version: 0.1.0-dev.80',(REPO/'repository.yaml').read_text(encoding='utf-8'))
 def test_gemini_provider_has_provider_specific_model_and_retryable_invalid_rows(self):
  source=(APP/'external_ai.py').read_text(encoding='utf-8')
  self.assertIn("gemini-2.5-flash-lite",source)
  self.assertIn("a.status!='VALID'",source)
  self.assertIn('urllib.error.HTTPError',source)
  self.assertIn("EXTERNAL_NEWS_AI_RUN",source)
 def test_automatic_news_cycle_runs_external_ai(self):
  source=(APP/'automation_v67.py').read_text(encoding='utf-8')
  self.assertIn('def _run_news(self):',source)
  self.assertIn('external.analyze_pending()',source)
  self.assertIn("automation_learning_auto_approve_enabled",source)
 def test_prefilter_scores_are_bounded_and_crossed_quotes_rejected(self):
  source=(APP/'prefilter.py').read_text(encoding='utf-8')
  self.assertIn("quality='INVALID_QUOTE'",source)
  self.assertIn('ask>=bid>0',source)
  self.assertIn('score=max(0,min(100',source)
  self.assertIn('spread_s=max(0,min(35',source)
 def test_v80_navigation_exposes_automation_and_ai(self):
  source=(APP/'v80_main.py').read_text(encoding='utf-8')
  self.assertIn("('/automatik','Automatik')",source)
  self.assertIn("('/news-learning','Nachrichten & AI')",source)
  self.assertIn("@app.get('/v80-health')",source)
 def test_v80_sources_parse(self):
  for name in ('v80_main.py','external_ai.py','prefilter.py','automation_v67.py'):
   ast.parse((APP/name).read_text(encoding='utf-8'),filename=name)

if __name__=='__main__':unittest.main()
