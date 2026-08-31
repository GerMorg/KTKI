import ast
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / 'app'


class V67RepositoryTests(unittest.TestCase):
    def test_new_entrypoint_compiles(self):
        source = (APP / 'v67_main.py').read_text(encoding='utf-8')
        ast.parse(source, filename='v67_main.py')

    def test_automation_controller_compiles(self):
        source = (APP / 'automation_v67.py').read_text(encoding='utf-8')
        ast.parse(source, filename='automation_v67.py')

    def test_v67_is_runtime_entrypoint(self):
        run = (ROOT / 'run.sh').read_text(encoding='utf-8')
        self.assertIn('v67_main:app', run)
        self.assertIn('APP_DISABLE_PAPER_SCHEDULER', (APP / 'v67_main.py').read_text(encoding='utf-8'))
        self.assertIn('APP_DISABLE_RESEARCH_SCHEDULER', (APP / 'v67_main.py').read_text(encoding='utf-8'))
        self.assertIn('APP_DISABLE_REAL_BALANCING_SCHEDULER', (APP / 'v67_main.py').read_text(encoding='utf-8'))

    def test_version_and_automation_options_are_synchronized(self):
        version = (APP / 'version.py').read_text(encoding='utf-8')
        config = (ROOT / 'config.yaml').read_text(encoding='utf-8')
        repository = (ROOT / 'repository.yaml').read_text(encoding='utf-8')
        self.assertIn("APP_VERSION='0.1.0-dev.67'", version)
        self.assertIn('version: 0.1.0-dev.67', config)
        self.assertIn('version: 0.1.0-dev.67', repository)
        for key in (
            'automation_master_enabled', 'automation_analysis_enabled', 'automation_news_enabled',
            'automation_learning_enabled', 'automation_learning_auto_approve_enabled',
            'automation_paper_enabled', 'automation_real_enabled', 'automation_real_execute_enabled',
            'learning_max_evaluations', 'news_learning_max_samples', 'analysis_max_symbols'):
            self.assertIn(key + ':', config)

    def test_modern_navigation_is_process_ordered(self):
        source = (APP / 'v67_main.py').read_text(encoding='utf-8')
        expected = ["'/', 'Übersicht'", "'/analyse', '1 Analyse'", "'/portfolio-modern', '2 Portfolio'", "'/handel', '3 Handel'", "'/lernen-modern', '4 Lernen'", "'/automatik', '5 Automatik'"]
        positions = [source.index(item) for item in expected]
        self.assertEqual(positions, sorted(positions))

    def test_portfolio_gui_contains_graphs(self):
        source = (APP / 'v67_main.py').read_text(encoding='utf-8')
        self.assertIn('_svg_line', source)
        self.assertIn('Realportfolio', source)
        self.assertIn('Paper-Portfolio', source)


if __name__ == '__main__':
    unittest.main()
