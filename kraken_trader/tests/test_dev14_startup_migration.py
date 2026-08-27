import os,sqlite3,sys,tempfile,unittest
sys.path.insert(0,os.path.join(os.path.dirname(__file__),'..','app'))
from db import DB
from news_prefilter import NewsPrefilter
from forecast_tracker import ForecastTracker
from market_universe import MarketUniverse
from scanner import MarketScanner
from prefilter import MarketPrefilter
from research_pipeline import ResearchPipeline
class FakeClient:pass
class StartupMigrationTests(unittest.TestCase):
 def make_old_db(self):
  path=tempfile.mktemp();db=DB(path);db.init()
  with db.con() as c:
   c.executescript("""CREATE TABLE news_sources(name TEXT PRIMARY KEY,url TEXT NOT NULL,kind TEXT NOT NULL,enabled INTEGER NOT NULL,last_status TEXT,last_checked_at TEXT);CREATE TABLE news_items(id TEXT PRIMARY KEY,source_name TEXT NOT NULL,title TEXT NOT NULL,url TEXT,published_at TEXT,fetched_at TEXT NOT NULL,summary TEXT NOT NULL,raw_json TEXT NOT NULL);CREATE TABLE news_market_links(news_id TEXT NOT NULL,symbol TEXT NOT NULL,relevance TEXT NOT NULL,reason TEXT NOT NULL,PRIMARY KEY(news_id,symbol));""")
   c.execute("INSERT INTO news_sources VALUES('Alt','https://example.invalid','rss',1,NULL,NULL)")
   c.execute("INSERT INTO news_items VALUES('N1','Alt','Titel','https://example.invalid/a','',datetime('now'),'Text','{}')")
  return db
 def test_dev12_news_schema_migrates_without_data_loss(self):
  db=self.make_old_db();news=NewsPrefilter(db)
  source_cols={x['name'] for x in db.rows('PRAGMA table_info(news_sources)')};item_cols={x['name'] for x in db.rows('PRAGMA table_info(news_items)')}
  self.assertTrue({'source_class','weight'}.issubset(source_cols));self.assertTrue({'topics_json','event_types_json'}.issubset(item_cols));self.assertEqual(db.rows("SELECT title FROM news_items WHERE id='N1'")[0]['title'],'Titel');self.assertTrue(news.sources())
 def test_all_startup_services_construct_on_migrated_db(self):
  db=self.make_old_db();client=FakeClient();scanner=MarketScanner(db,client);universe=MarketUniverse(db,client);news=NewsPrefilter(db);prefilter=MarketPrefilter(db,client,news);forecasts=ForecastTracker(db);pipeline=ResearchPipeline(db,universe,prefilter,scanner,forecasts)
  self.assertIsNotNone(pipeline.latest()) if db.rows('SELECT * FROM research_jobs') else self.assertIsNone(pipeline.latest())
