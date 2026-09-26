import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]


class V86RuntimeTests(unittest.TestCase):
    def test_active_runtime_is_v86(self):
        run_sh = (ROOT / "run.sh").read_text(encoding="utf-8")
        self.assertIn("v86_main:app", run_sh)
        self.assertNotIn("v85_main:app", run_sh)

    def test_v86_entrypoint_delegates_to_v84(self):
        source = (ROOT / "app" / "v86_main.py").read_text(encoding="utf-8")
        self.assertIn("import v84_main as base", source)
        self.assertIn('"/v86-health"', source)

    def test_v86_does_not_import_v85_runtime(self):
        source = (ROOT / "app" / "v86_main.py").read_text(encoding="utf-8")
        self.assertNotIn("import v85_main", source)
        self.assertNotIn("from v85_main", source)


if __name__ == "__main__":
    unittest.main()
