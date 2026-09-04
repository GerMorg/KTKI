import ast
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1];APP=ROOT/'app';REPO=ROOT.parent
class V74RegressionTests(unittest.TestCase):
 def test_active_runtime_and_version_are_v80(self):
  run=(ROOT/'run.sh').read_text(encoding='utf-8');version=(APP/'version.py').read_text(encoding='utf-8');config=(ROOT/'config.yaml').read_text(encoding='utf-8');runtime=(APP/'v80_main.py').read_text(encoding='utf-8');repo=(REPO/'repository.yaml').read_text(encoding='utf-8')
  self.assertIn('v80_main:app',run);self.assertIn("APP_VERSION='0.1.0-dev.80'",version);self.assertIn('version: 0.1.0-dev.80',config);self.assertIn('version: 0.1.0-dev.80',repo);self.assertIn("'research_shape_error_quarantine': True",(APP/'v76_main.py').read_text(encoding='utf-8'));self.assertIn("'version':'0.1.0-dev.80'",runtime)
 def test_deep_scan_is_fail_soft_at_runtime_boundary(self):
  source=(APP/'v74_main.py').read_text(encoding='utf-8');self.assertIn('_original_scanner_run = MarketScanner.run',source);self.assertIn('def _scanner_run_v74',source);self.assertIn("'DEEP_SCAN_DEGRADED'",source);self.assertIn("'status': 'DEGRADED'",source);self.assertIn('_original_shadow_run = ForexShadow.run',source);self.assertIn("'FOREX_SHADOW_DEGRADED'",source)
 def test_research_pipeline_has_final_shape_error_quarantine_and_recovery(self):
  source=(APP/'research_pipeline.py').read_text(encoding='utf-8');self.assertIn('def _is_payload_shape_error',source);self.assertIn('def _shape_guard',source);self.assertIn('def _complete_degraded',source);self.assertIn('RESEARCH_PIPELINE_SHAPE_ERROR_QUARANTINED',source);self.assertIn('def _recover_watchlist',source);self.assertIn('prefilter.recovery',source);self.assertNotIn('ForexShadow(self.db).run(symbols)',source)
 def test_active_runtime_does_not_use_unprotected_ticker_update(self):
  source=(APP/'prefilter.py').read_text(encoding='utf-8');self.assertNotIn('tickers.update(self.client.ticker(block,ac))',source);self.assertNotIn('tickers[ac].update(single if isinstance(single,dict) else {})',source)
 def test_external_payload_iterators_are_not_directly_tuple_unpacked(self):
  external_calls={'ticker','ohlc','pairs','collect','fetch','request','json'}
  for name in ('scanner.py','prefilter.py','execution_costs.py','execution_router.py','market_universe.py','payload_utils.py','forex_shadow.py','research_pipeline.py'):
   tree=ast.parse((APP/name).read_text(encoding='utf-8'),filename=name)
   for node in ast.walk(tree):
    if isinstance(node,ast.For) and isinstance(node.target,ast.Tuple):
     if isinstance(node.iter,ast.Call) and isinstance(node.iter.func,ast.Attribute) and node.iter.func.attr in {'items','keys','values'}:continue
     if isinstance(node.iter,ast.Name) and node.iter.id in {'payload','response','result','raw','items'}:self.fail(f'unsafe external iterable tuple unpacking in {name}')
    if isinstance(node,ast.Assign) and isinstance(node.targets[0],ast.Tuple) and isinstance(node.value,ast.Call):
     func=node.value.func;called=func.attr if isinstance(func,ast.Attribute) else func.id if isinstance(func,ast.Name) else ''
     if called in external_calls:self.fail(f'external call tuple unpacking in {name}: {called}')
 def test_premarket_external_payload_boundaries_are_explicit(self):
  for name in ('prefilter.py','market_universe.py','scanner.py','forex_shadow.py','research_pipeline.py'):
   source=(APP/name).read_text(encoding='utf-8');self.assertIn('isinstance(',source,name)
 def test_all_v80_runtime_modules_compile(self):
  for name in ('v80_main.py','v79_main.py','v78_main.py','v77_main.py','v76_main.py','v75_main.py','v74_main.py','research_pipeline.py','scanner.py','forex_shadow.py','prefilter.py','market_universe.py','payload_utils.py','ws_market.py'):
   ast.parse((APP/name).read_text(encoding='utf-8'),filename=name)
if __name__=='__main__':unittest.main()
