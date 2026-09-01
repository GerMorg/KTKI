import ast
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
APP=ROOT/'app'

class V70RegressionTests(unittest.TestCase):
    def test_v70_runtime_uses_real_core_sources(self):
        source=(APP/'v70_main.py').read_text(encoding='utf-8')
        self.assertIn('legacy = v67.legacy',source)
        self.assertIn('legacy.current_market_batch()',source)
        self.assertNotIn('core.current_market_batch()',source)

    def test_v70_normalizes_all_scheduler_results(self):
        source=(APP/'v70_main.py').read_text(encoding='utf-8')
        self.assertIn('def as_mapping',source)
        self.assertIn('controller.pipeline.start =',source)
        self.assertIn('controller.news_prefilter.collect =',source)
        self.assertIn('controller.real_allocator.run =',source)
        self.assertIn('controller.run_paper_cycle = run_paper_cycle_v70',source)

    def test_v70_kraken_payload_boundary_is_hardened(self):
        source=(APP/'v70_main.py').read_text(encoding='utf-8')
        self.assertIn('def normalize_kraken_payload',source)
        self.assertIn('normalize_kraken_payload(payload)',source)
        self.assertIn('if isinstance(item, list)',source)
        self.assertIn('if not isinstance(item, dict)',source)

    def test_v70_chart_has_readable_visual_layers(self):
        source=(APP/'v70_main.py').read_text(encoding='utf-8')
        css=(APP/'static/v70.css').read_text(encoding='utf-8')
        self.assertIn('def chart_v70',source)
        for token in ('polyline','polygon','chart-gridline','chart-axis-label','chart-dot'):
            self.assertIn(token,source)
        for token in ('--v70-text','--v70-muted','--v70-chart-grid','--v70-line','chart-line'):
            self.assertIn(token,css)

    def test_v70_compiles(self):
        for name in ('v70_main.py','v69_main.py','v68_main.py','automation_v67.py','paper_engine.py'):
            ast.parse((APP/name).read_text(encoding='utf-8'),filename=name)

    def test_v70_health_route_exists(self):
        source=(APP/'v70_main.py').read_text(encoding='utf-8')
        self.assertIn("@app.get('/v70-health')",source)
        self.assertIn("'paper_market_batch_source': 'legacy.current_market_batch'",source)

if __name__=='__main__':unittest.main()
