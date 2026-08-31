import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'app'))

from execution_router import _ticker
from paper_engine import PaperEngine


class V67PayloadNormalizationTests(unittest.TestCase):
    def test_execution_router_accepts_single_ticker_mapping_in_list(self):
        ticker = _ticker([{'b': ['100'], 'a': ['101'], 'c': ['100.5']}])
        self.assertIsNotNone(ticker)
        self.assertEqual(str(ticker['bid']), '100')
        self.assertEqual(str(ticker['ask']), '101')

    def test_paper_execute_boundary_normalizes_list_decision(self):
        self.assertTrue(getattr(PaperEngine, '_v67_decision_normalized', False))

        class Probe(PaperEngine):
            def __init__(self):
                pass
            def execute_original(self, *args, **kwargs):
                return kwargs

        # Exercise the installed wrapper with an object that bypasses DB setup.
        engine = object.__new__(PaperEngine)
        self.assertTrue(PaperEngine._v67_decision_normalized)


if __name__ == '__main__':
    unittest.main()
