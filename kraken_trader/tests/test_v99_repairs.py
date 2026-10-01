import json
import tempfile
import unittest
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"app"))

from db import DB
from external_ai import ExternalNewsAI
from news_learning import NewsLearning
from news_prefilter import NewsPrefilter


class V99RepairTests(unittest.TestCase):
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
            self.assertEqual(ai._model(),"gemini-2.5-flash-lite")
            content=ai._content({"candidates":[{"content":{"parts":[{"text":"{\"relevance\": 1}"}]}}]})
            self.assertEqual(json.loads(content)["relevance"],1)
        finally:
            Path(f.name).unlink(missing_ok=True)

    def test_runtime_and_config_are_v99_and_consolidated(self):
        run=(ROOT/"run.sh").read_text(encoding="utf-8")
        self.assertIn("v99_main:app",run)
        config=(ROOT/"config.yaml").read_text(encoding="utf-8")
        self.assertIn("version: 0.1.0-dev.99",config)
        for forbidden in ("ai_provider:", "ai_endpoint:", "azure_openai", "gpt-4o-mini"):
            self.assertNotIn(forbidden,config)
        self.assertIn("ai_api_key:",config)
        self.assertIn("automation_enabled:",config)

    def test_v99_runtime_exposes_real_positions_source(self):
        source=(ROOT/"app"/"v99_main.py").read_text(encoding="utf-8")
        self.assertIn("FROM portfolio_assets",source)
        self.assertIn("Paper-Depot · Positionen",source)
        self.assertIn("Reales Depot · Positionen",source)
        self.assertIn("FROM real_margin_positions",source)


if __name__=="__main__":
    unittest.main()
