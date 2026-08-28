import os, sys, tempfile, unittest
from pathlib import Path
ROOT = Path(__file__).parents[1]
os.environ["APP_DISABLE_PAPER_SCHEDULER"] = "1"
os.environ["APP_DISABLE_RESEARCH_SCHEDULER"] = "1"
os.environ["APP_DATA_DIR"] = tempfile.mkdtemp()
sys.path.insert(0, str(ROOT / "app"))
from version import APP_VERSION, USER_AGENT
import main

class Dev36ConsistencyTests(unittest.TestCase):
    def test_runtime_version_is_centralized(self):
        self.assertEqual(APP_VERSION, "0.1.0-dev.40")
        self.assertEqual(main.app.test_client().get("/health").json["version"], APP_VERSION)
        self.assertIn(APP_VERSION, main.app.test_client().get("/").data.decode("utf-8"))
        self.assertTrue(USER_AGENT.endswith(APP_VERSION))

    def test_addon_metadata_matches_runtime(self):
        self.assertIn(f'version: "{APP_VERSION}"', (ROOT / "config.yaml").read_text("utf-8"))

    def test_repository_has_no_common_mojibake_markers(self):
        bad = (chr(0x00C3), chr(0x00C2), chr(0x00E2)+chr(0x20AC), chr(0x00F0)+chr(0x0178), chr(0xFFFD))
        offenders = []
        for path in ROOT.parent.rglob("*"):
            if path.is_file() and path.suffix in {".py", ".md", ".yaml", ".yml", ".txt", ".sh"}:
                text = path.read_text("utf-8")
                if any(marker in text for marker in bad): offenders.append(str(path.relative_to(ROOT.parent)))
        self.assertEqual(offenders, [])

    def test_real_trading_remains_disabled(self):
        self.assertFalse(main.app.test_client().get("/health").json["real_trading"])

if __name__ == "__main__": unittest.main()
