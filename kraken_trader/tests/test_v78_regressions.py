import ast
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1];APP=ROOT/'app'
class V78RegressionTests(unittest.TestCase):
 def test_analysis_has_candidate_recovery(self):
  source=(APP/'research_pipeline.py').read_text(encoding='utf-8');self.assertIn('def _recover_watchlist',source);self.assertIn('symbols=list(self.prefilter.candidates() or [])',source);self.assertIn('symbols=self._recover_watchlist',source);self.assertIn("'candidate_count':len(symbols)",source);self.assertIn("quality='VALID_WITH_WARNINGS'",source)
 def test_universe_defaults_have_categories(self):
  source=(APP/'market_universe.py').read_text(encoding='utf-8');self.assertIn('VALUES(?,?,1,?)',source);self.assertIn('return enabled or set(CATEGORIES)',source)
if __name__=='__main__':unittest.main()
