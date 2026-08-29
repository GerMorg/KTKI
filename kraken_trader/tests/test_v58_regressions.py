import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

from display_format import DisplayFloat, display_tree


class V58DisplayRegressionTests(unittest.TestCase):
    def test_localized_display_value_remains_numeric(self):
        values = display_tree({'active': '0.1375', 'candidate': '0.1875'})
        self.assertIsInstance(values['active'], float)
        self.assertAlmostEqual(values['candidate'] - values['active'], 0.05, places=8)
        self.assertEqual(str(values['active']), '0,1375')

    def test_numeric_template_values_support_jinja_style_float_formatting(self):
        value = DisplayFloat('62.123456789')
        self.assertAlmostEqual(float(value), 62.123456789)
        self.assertEqual(f'{value:.2f}', '62.12')

    def test_json_text_is_not_recursively_localized(self):
        raw = '{"x":1.23456789}'
        self.assertEqual(display_tree({'parameters_json': raw})['parameters_json'], raw)


class V58VersionTests(unittest.TestCase):
    def test_release_metadata_is_58(self):
        addon = os.path.join(os.path.dirname(__file__), '..')
        root = os.path.join(addon, '..')
        self.assertIn("0.1.0-dev.58", open(os.path.join(addon, 'app', 'version.py'), encoding='utf-8').read())
        self.assertIn("version: 0.1.0-dev.58", open(os.path.join(addon, 'config.yaml'), encoding='utf-8').read())
        self.assertIn("version: 0.1.0-dev.58", open(os.path.join(root, 'repository.yaml'), encoding='utf-8').read())


if __name__ == '__main__':
    unittest.main()
