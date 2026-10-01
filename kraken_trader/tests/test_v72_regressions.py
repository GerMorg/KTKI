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
if __name__=='__main__':unittest.main()
