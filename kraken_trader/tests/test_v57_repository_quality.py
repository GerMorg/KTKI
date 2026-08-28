from pathlib import Path
import re
import unittest

ADDON = Path(__file__).resolve().parents[1]
ROOT = ADDON.parent
MOJIBAKE = re.compile("|".join(["\u00c3", "\u00c2", "\u00e2\u20ac", "\u00f0\u0178", "\ufffd"]))

class RepositoryQualityTests(unittest.TestCase):
    def test_all_text_files_are_utf8_without_known_mojibake(self):
        failures = []
        for path in ROOT.rglob("*"):
            if not path.is_file() or any(part in {"__pycache__", ".pytest_cache"} for part in path.parts):
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            if MOJIBAKE.search(text):
                failures.append(str(path.relative_to(ROOT)))
        self.assertEqual(failures, [])

    def test_active_versions_are_synchronized(self):
        version = "0.1.0-dev.57"
        self.assertIn(version, (ADDON / "app/version.py").read_text(encoding="utf-8"))
        self.assertIn(f"version: {version}", (ADDON / "config.yaml").read_text(encoding="utf-8"))
        self.assertIn(f"version: {version}", (ROOT / "repository.yaml").read_text(encoding="utf-8"))

    def test_gui_shell_is_centralized_and_accessible(self):
        main = (ADDON / "app/main.py").read_text(encoding="utf-8")
        template = (ADDON / "templates/base.html").read_text(encoding="utf-8")
        css = (ADDON / "static/style.css").read_text(encoding="utf-8")
        self.assertNotIn("BASE=" + "'''", main)
        self.assertIn("render_template('base.html'", main)
        self.assertIn("DEAKTIVIERT", template)
        self.assertIn('aria-current="page"', template)
        self.assertIn(":focus-visible", css)

if __name__ == "__main__":
    unittest.main()
