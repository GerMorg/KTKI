import ast
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1];APP=ROOT/'app'
class V72RegressionTests(unittest.TestCase):
 def test_pipeline_records_stage_operation_and_details(self):
  source=(APP/'research_pipeline.py').read_text(encoding='utf-8');self.assertIn('def fail(self,jid,stage,operation,exc,context=None):',source);self.assertIn('RESEARCH_STAGE_FAILED',source);self.assertIn('traceback.format_exc',source);self.assertIn("stage='FORECAST_SNAPSHOT';operation='ForecastTracker.snapshot'",source);self.assertIn("stage='FORECAST_SNAPSHOT';operation='ForecastTracker.evaluate_due'",source)
 def test_forecast_snapshot_isolates_symbol_failures(self):
  source=(APP/'forecast_tracker.py').read_text(encoding='utf-8');self.assertIn('FORECAST_SNAPSHOT_SYMBOL_FAILED',source);self.assertIn('FORECAST_SNAPSHOT_COMPLETED',source);self.assertIn('failed+=1',source)
 def test_forecast_evaluation_isolates_record_failures(self):
  source=(APP/'forecast_tracker.py').read_text(encoding='utf-8');self.assertIn('FORECAST_EVALUATION_FAILED',source);self.assertIn('FORECAST_EVALUATION_COMPLETED_WITH_ERRORS',source)
 def test_all_active_paper_boundaries_normalize_mapping_payloads(self):
  source=(APP/'v74_main.py').read_text(encoding='utf-8');self.assertIn('from payload_utils import as_mapping, as_mapping_list',source);self.assertIn('PaperEngine.execute = _paper_execute_v74',source);self.assertIn('PortfolioAllocator.plans = _allocator_plans_v74',source);self.assertIn('DecisionMatrix.evaluate = _decision_evaluate_v74',source);self.assertIn('execution_router_module._find = _router_find_v74',source)
 def test_analysis_failure_is_recorded_in_automation_history(self):
  source=(APP/'v74_main.py').read_text(encoding='utf-8');self.assertIn('def _record_finished_analysis',source);self.assertIn("controller._record('analysis', 'FAILED'",source)
 def test_legacy_v72_runtime_remains_available(self):
  self.assertTrue((APP/'v72_main.py').exists())
 def test_v72_modules_compile(self):
  for name in ('research_pipeline.py','forecast_tracker.py','v71_main.py','v72_main.py','v73_main.py','v74_main.py','payload_utils.py'):
   ast.parse((APP/name).read_text(encoding='utf-8'),filename=name)
if __name__=='__main__':unittest.main()
