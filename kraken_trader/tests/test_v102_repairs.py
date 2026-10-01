import json
import tempfile
import unittest
from pathlib import Path
import sys
import os
import subprocess

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"app"))

from db import DB
from external_ai import ExternalNewsAI
from news_learning import NewsLearning
from news_prefilter import NewsPrefilter


class V102RepairTests(unittest.TestCase):
    def db(self):
        f=tempfile.NamedTemporaryFile(suffix=".db",delete=False)
        f.close()
        db=DB(f.name)
        db.init()
        return f,db

    def test_news_scoring_works_without_ai_and_creates_market_links(self):
        f,db=self.db()
        try:
            learning=NewsLearning(db)
            prefilter=NewsPrefilter(db)
            with db.con() as c:
                c.execute(
                    "INSERT INTO news_sources(name,url,kind,source_class,weight,enabled) VALUES(?,?,?,?,?,1)",
                    ("TEST","https://example.invalid","rss","primary","1")
                )
                c.execute(
                    "INSERT INTO news_items(id,source_name,title,url,published_at,fetched_at,summary,topics_json,event_types_json,raw_json) "
                    "VALUES(?,?,?,?,?,?,?,?,?,?)",
                    ("n1","TEST","Bitcoin rally growth approval","https://example.invalid/n1",
                     "2026-10-01T12:00:00+00:00","2026-10-01T12:00:00+00:00",
                     "bitcoin crypto adoption","[]","[]","{}")
                )
            learning.refresh_local()
            score=float(db.rows("SELECT score FROM news_local_evaluations WHERE news_id='n1'")[0]["score"])
            self.assertGreater(score,0)
            links=prefilter.link_markets([{
                "symbol":"BTC/EUR","base_asset":"BTC","category":"crypto_spot"
            }])
            self.assertGreater(links,0)
            self.assertGreater(float(db.rows("SELECT relevance FROM news_market_links WHERE news_id='n1'")[0]["relevance"]),0)
        finally:
            Path(f.name).unlink(missing_ok=True)

    def test_gemini_result_is_used_as_semantic_news_feature(self):
        f,db=self.db()
        try:
            learning=NewsLearning(db)
            prefilter=NewsPrefilter(db)
            ai=ExternalNewsAI(db,{"ai_news_enabled":True,"ai_api_key":"test"})
            with db.con() as c:
                c.execute(
                    "INSERT INTO news_sources(name,url,kind,source_class,weight,enabled) VALUES(?,?,?,?,?,1)",
                    ("TEST","https://example.invalid","rss","primary","1")
                )
                c.execute(
                    "INSERT INTO news_items(id,source_name,title,url,published_at,fetched_at,summary,topics_json,event_types_json,raw_json) "
                    "VALUES(?,?,?,?,?,?,?,?,?,?)",
                    ("n2","TEST","Bitcoin market","https://example.invalid/n2",
                     "2026-10-01T12:00:00+00:00","2026-10-01T12:00:00+00:00",
                     "market update","[]","[]","{}")
                )
                teacher={
                    "relevance":0.9,"sentiment":"negative","expected_impact":"high",
                    "horizon":"24h","confidence":0.9,"fact_status":"reported",
                    "priced_in":False,"topics":["regulation"],"affected_assets":["BTC"],
                    "summary":"negative","counterarguments":"none"
                }
                c.execute(
                    "INSERT INTO external_news_ai_results(news_id,created_at,status,result_json,error) VALUES(?,?,?,?,?)",
                    ("n2","2026-10-01T12:01:00+00:00","VALID",json.dumps(teacher),"")
                )
            learning.refresh_local()
            row=db.rows("SELECT score,details_json FROM news_local_evaluations WHERE news_id='n2'")[0]
            details=json.loads(row["details_json"])
            self.assertTrue(details["ai_used"])
            self.assertLess(float(row["score"]),0)
        finally:
            Path(f.name).unlink(missing_ok=True)

    def test_news_ai_is_gemini_only(self):
        f,db=self.db()
        try:
            ai=ExternalNewsAI(db,{})
            self.assertEqual(ai._model(),"gemini-3.5-flash-lite")
            content=ai._content({"candidates":[{"content":{"parts":[{"text":"{\"relevance\": 1}"}]}}]})
            self.assertEqual(json.loads(content)["relevance"],1)
        finally:
            Path(f.name).unlink(missing_ok=True)

    def test_runtime_and_config_are_v101_and_consolidated(self):
        run=(ROOT/"run.sh").read_text(encoding="utf-8")
        self.assertIn("v102_main:app",run)
        config=(ROOT/"config.yaml").read_text(encoding="utf-8")
        self.assertIn("version: 0.1.0-dev.102",config)
        for forbidden in ("ai_provider:", "ai_endpoint:", "azure_openai", "gpt-4o-mini"):
            self.assertNotIn(forbidden,config)
        self.assertIn("ai_api_key:",config)
        self.assertIn("automation_enabled:",config)


    def test_v102_application_import_smoke(self):
        with tempfile.TemporaryDirectory() as td:
            options_path=Path(td)/"options.json"
            options_path.write_text(json.dumps({
                "automation_enabled": False,
                "real_trading_enabled": False,
                "real_execute_enabled": False,
                "real_kill_switch": True,
                "paper_start_eur": 1000,
            }),encoding="utf-8")
            env=os.environ.copy()
            env["APP_DATA_DIR"]=td
            env["APP_OPTIONS"]=str(options_path)
            env["APP_DISABLE_WEBSOCKETS"]="1"
            result=subprocess.run(
                [sys.executable,"-c","import v102_main; assert v102_main.app is not None; print('v101 import ok')"],
                cwd=str(ROOT/"app"),env=env,capture_output=True,text=True,timeout=20
            )
            self.assertEqual(result.returncode,0,msg=result.stdout+"\\n"+result.stderr)

    def test_v102_boot_contract(self):
        core=(ROOT/"app"/"core_runtime.py").read_text(encoding="utf-8")
        runtime=(ROOT/"app"/"v102_main.py").read_text(encoding="utf-8")
        run=(ROOT/"run.sh").read_text(encoding="utf-8")
        compile(core,"core_runtime.py","exec")
        compile(runtime,"v102_main.py","exec")
        self.assertIn("legacy = sys.modules[__name__]",core)
        self.assertIn("options=opts",core)
        self.assertIn("controller=None",core)
        self.assertIn("import core_runtime as base",runtime)
        self.assertIn("legacy=base.legacy",runtime)
        self.assertIn("from flask import Response, jsonify, redirect, request, url_for",runtime)
        self.assertIn("v102_main:app",run)

    def test_v102_runtime_exposes_real_positions_source(self):
        source=(ROOT/"app"/"v102_main.py").read_text(encoding="utf-8")
        self.assertIn("FROM portfolio_assets",source)
        self.assertIn("Paper-Depot · Positionen",source)
        self.assertIn("Reales Depot · Positionen",source)
        self.assertIn("FROM real_margin_positions",source)

    def test_v102_unified_real_state_and_clean_gui(self):
        source=(ROOT/"app"/"v102_main.py").read_text(encoding="utf-8")
        helper=(ROOT/"app"/"real_state_v102.py").read_text(encoding="utf-8")
        core=(ROOT/"app"/"core_runtime.py").read_text(encoding="utf-8")
        self.assertIn("build_real_state",source)
        self.assertIn("automatic_execution_ready",helper)
        self.assertNotIn("REAL_EXECUTION_DISABLED",source)
        self.assertNotIn("REAL_DRY_RUN",source)
        self.assertNotIn("/analyse-v98",source)
        self.assertNotIn("/portfolio-v98",source)
        self.assertNotIn("Realhandel bleibt technisch deaktiviert",core)
        self.assertNotIn("@app.route('/settings'",core)

    def test_v102_real_state_behavior(self):
        from db import DB
        from real_state_v102 import build_real_state
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".db") as f:
            db=DB(f.name); db.init()
            s=build_real_state(db,None)
            self.assertFalse(s["manual_order_available"])
            self.assertFalse(s["automatic_execution_ready"])
            db.set_setting("real_trading_enabled","true")
            db.set_setting("real_kill_switch","false")
            s=build_real_state(db,None)
            self.assertTrue(s["manual_order_available"])
            self.assertFalse(s["automatic_execution_ready"])
            db.set_setting("automation_master_enabled","true")
            db.set_setting("automation_real_enabled","true")
            db.set_setting("automation_real_execute_enabled","true")
            s=build_real_state(db,None)
            self.assertTrue(s["manual_order_available"])
            self.assertTrue(s["automatic_execution_ready"])
            self.assertEqual(s["status_label"],"REALHANDEL FREIGEGEBEN")

    def test_v102_tax_exports_are_current_and_routable(self):
        source=(ROOT/"app"/"v102_main.py").read_text(encoding="utf-8")
        self.assertIn('@app.get("/tax-info.zip")',source)
        self.assertIn('@app.get("/tax-info.csv")',source)
        self.assertIn('url_for("tax_csv"',source)
        self.assertNotIn("/tax-info-v68.zip",source)
        self.assertNotIn("/tax-info-v68.csv",source)
        self.assertNotIn("tax_v100_csv",source)

if __name__=="__main__":
    unittest.main()
