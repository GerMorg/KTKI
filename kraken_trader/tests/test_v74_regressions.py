import ast
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
APP=ROOT/'app'
REPO=ROOT.parent
class V74RegressionTests(unittest.TestCase):
 def test_active_runtime_and_version_are_v75(self):
  run=(ROOT/'run.sh').read_text(encoding='utf-8');version=(APP/'version.py').read_text(encoding='utf-8');config=(ROOT/'config.yaml').read_text(encoding='utf-8');runtime=(APP/'v75_main.py').read_text(encoding='utf-8');repo=(REPO/'repository.yaml').read_text(encoding='utf-8')
  self.assertIn('v75_main:app',run);self.assertIn("APP_VERSION='0.1.0-dev.75'",version);self.assertIn('version: 0.1.0-dev.75',config);self.assertIn('version: 0.1.0-dev.75',repo);self.assertIn("'research_payload_isolation': True",runtime)
 def test_deep_scan_is_fail_soft_at_runtime_boundary(self):
  source=(APP/'v74_main.py').read_text(encoding='utf-8');self.assertIn('_original_scanner_run = MarketScanner.run',source);self.assertIn('def _scanner_run_v74',source);self.assertIn("'DEEP_SCAN_DEGRADED'",source);self.assertIn("'status': 'DEGRADED'",source);self.assertIn('_original_shadow_run = ForexShadow.run',source);self.assertIn("'FOREX_SHADOW_DEGRADED'",source)
 def test_research_pipeline_has_final_shape_error_boundary(self):
  source=(APP/'research_pipeline.py').read_text(encoding='utf-8');self.assertIn('def _is_payload_shape_error',source);self.assertIn('def _shape_guard',source);self.assertIn('RESEARCH_STAGE_DEGRADED',source);self.assertIn("'quality':'DEGRADED' if degraded else 'VALID'",source);self.assertIn('shadow_obj=self.shadow or ForexShadow(self.db)',source);self.assertNotIn('ForexShadow(self.db).run(symbols)',source)
 def test_active_runtime_does_not_use_unprotected_ticker_update(self):
  source=(APP/'prefilter.py').read_text(encoding='utf-8');self.assertNotIn('tickers.update(self.client.ticker(block,ac))',source);self.assertNotIn('tickers[ac].update(single if isinstance(single,dict) else {})',source)
 def test_payload_shape_assignments_are_not_directly_unpacked(self):
  names=('scanner.py','prefilter.py','execution_costs.py','execution_router.py','market_universe.py','payload_utils.py','forex_shadow.py','research_pipeline.py')
  for name in names:
   tree=ast.parse((APP/name).read_text(encoding='utf-8'),filename=name)
   for node in ast.walk(tree):
    if isinstance(node,ast.Assign) and isinstance(node.targets[0],ast.Tuple) and isinstance(node.value,ast.Call): self.fail(f'direct call tuple unpacking in {name}')
    if isinstance(node,ast.For) and isinstance(node.target,ast.Tuple) and isinstance(node.iter,ast.Name) and node.iter.id in {'payload','response','result','raw','items','rows'}: self.fail(f'unsafe iterable tuple unpacking in {name}')
 def test_premarket_external_payload_boundaries_are_explicit(self):
  for name in ('prefilter.py','market_universe.py','scanner.py','forex_shadow.py','research_pipeline.py'):
   source=(APP/name).read_text(encoding='utf-8');self.assertIn('isinstance(',source,name)
 def test_all_v75_modules_compile(self):
  for name in ('v75_main.py','research_pipeline.py','scanner.py','forex_shadow.py','prefilter.py','market_universe.py','payload_utils.py'):
   ast.parse((APP/name).read_text(encoding='utf-8'),filename=name)
if __name__=='__main__':unittest.main()
