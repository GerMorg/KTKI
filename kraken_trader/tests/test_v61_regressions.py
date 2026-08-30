import ast
import pathlib
import unittest

from app.display_format import display_number, display_tree


class V61Regressions(unittest.TestCase):
    def test_compact_display_for_numeric_database_text(self):
        values = display_tree({'score': '72.123456789', 'return': '0.123456789', 'tiny': '0.000123456789', 'id': '123'})
        self.assertEqual(str(values['score']), '72,12')
        self.assertEqual(str(values['return']), '0,123')
        self.assertEqual(str(values['tiny']), '0,000123')
        self.assertEqual(values['id'], '123')
        self.assertEqual(display_number(72.123456789), '72,12')

    def test_no_module_free_chosen_name(self):
        root = pathlib.Path(__file__).resolve().parents[1] / 'app'
        offenders = []
        for path in root.glob('*.py'):
            tree = ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
            assigned = set()
            loaded = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Name):
                    if isinstance(node.ctx, ast.Load) and node.id == 'chosen':
                        loaded.append(node.lineno)
                    elif isinstance(node.ctx, (ast.Store, ast.Del)):
                        assigned.add(node.id)
                elif isinstance(node, ast.Import):
                    assigned.update(a.asname or a.name.split('.')[0] for a in node.names)
                elif isinstance(node, ast.ImportFrom):
                    assigned.update(a.asname or a.name for a in node.names)
            if loaded and 'chosen' not in assigned:
                offenders.append(f'{path}:{loaded}')
        self.assertEqual(offenders, [], 'module-level free chosen reference(s): ' + ', '.join(offenders))


if __name__ == '__main__':
    unittest.main()
