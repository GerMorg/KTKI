import ast
import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
APP=ROOT/'app'

class V72RegressionTests(unittest.TestCase):
    def test_pipeline_records_stage_operation_and_details(self):
        source=(APP/'research_pipeline.py').read_text(encoding='utf-8')
        self.assertIn('def fail(self,jid,stage,operation,exc,context=None):',source)
        self.assertIn("RESEARCH_STAGE_FAILED",source)
        self.assertIn('traceback.format_exc',source)
        self.assertIn("stage,operation='ForecastTracker.snapshot'",source)
        self.assertIn("stage,operation='ForecastTracker.evaluate_due'",source)

    def test_forecast_snapshot_isolates_symbol_failures(self):
        source=(APP/'forecast_tracker.py').read_text(encoding='utf-8')
        self.assertIn("FORECAST_SNAPSHOT_SYMBOL_FAILED",source)
        self.assertIn("FORECAST_SNAPSHOT_COMPLETED",source)
        self.assertIn('failed+=1',source)

    def test_forecast_evaluation_isolates_record_failures(self):
        source=(APP/'forecast_tracker.py').read_text(encoding='utf-8')
        self.assertIn("FORECAST_EVALUATION_FAILED",source)
        self.assertIn("FORECAST_EVALUATION_COMPLETED_WITH_ERRORS",source)

    def test_analysis_failure_is_recorded_in_automation_history(self):
        source=(APP/'v72_main.py').read_text(encoding='utf-8')
        self.assertIn('def _record_finished_analysis',source)
        self.assertIn("controller._record('analysis','FAILED'",source)
        self.assertIn("'research_monitor-v72'" not in source, source)

    def test_v72_is_active_runtime(self):
        run=(ROOT/'run.sh').read_text(encoding='utf-8')
        runtime=(APP/'v72_main.py').read_text(encoding='utf-8')
        version=(APP/'version.py').read_text(encoding='utf-8')
        config=(ROOT/'config.yaml').read_text(encoding='utf-8')
        self.assertIn('v72_main:app',run)
        self.assertIn("'version':'0.1.0-dev.72'",runtime)
        self.assertIn("APP_VERSION='0.1.0-dev.72'",version)
        self.assertIn('version: 0.1.0-dev.72',config)

    def test_v72_modules_compile(self):
        for name in ('research_pipeline.py','forecast_tracker.py','v71_main.py','v72_main.py'):
            ast.parse((APP/name).read_text(encoding='utf-8'),filename=name)

if __name__=='__main__':
    unittest.main()
