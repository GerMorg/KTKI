import os,sys,tempfile,unittest,urllib.error
from unittest.mock import patch
sys.path.insert(0,os.path.join(os.path.dirname(__file__),'..','app'))
from db import DB
from news_prefilter import NewsPrefilter
class Response:
 status=200
 def __enter__(self):return self
 def __exit__(self,*args):pass
 def read(self):return b'<rss><channel><item><title>Economy improves</title><link>https://example.test/1</link></item></channel></rss>'
class Tests(unittest.TestCase):
 def old_db(self):
  db=DB(tempfile.mktemp());db.init()
  with db.con() as c:
   c.executescript("""CREATE TABLE news_sources(name TEXT PRIMARY KEY,url TEXT NOT NULL,kind TEXT NOT NULL,source_class TEXT NOT NULL,weight TEXT NOT NULL,enabled INTEGER NOT NULL,last_status TEXT,last_checked_at TEXT);CREATE TABLE news_items(id TEXT PRIMARY KEY,source_name TEXT NOT NULL,title TEXT NOT NULL,url TEXT,published_at TEXT,fetched_at TEXT NOT NULL,summary TEXT NOT NULL,topics_json TEXT NOT NULL,event_types_json TEXT NOT NULL,raw_json TEXT NOT NULL);CREATE TABLE news_market_links(news_id TEXT NOT NULL,symbol TEXT NOT NULL,relevance TEXT NOT NULL,reason TEXT NOT NULL,PRIMARY KEY(news_id,symbol));""")
   c.execute("INSERT INTO news_sources VALUES('GDELT Global','old','gdelt_json','aggregator','0.7',1,'ERROR:URLError',NULL)")
  return db
 def test_obsolete_gdelt_is_replaced_and_health_schema_migrates(self):
  db=self.old_db();n=NewsPrefilter(db);old=db.rows("SELECT enabled,last_status FROM news_sources WHERE name='GDELT Global'")[0];cols={x['name'] for x in db.rows('PRAGMA table_info(news_sources)')}
  self.assertEqual(old['enabled'],0);self.assertEqual(old['last_status'],'REPLACED');self.assertTrue({'last_error','consecutive_failures','last_success_at'}.issubset(cols));self.assertTrue(db.rows("SELECT * FROM news_sources WHERE name='GDELT Wirtschaft' AND enabled=1"));self.assertTrue(db.rows("SELECT * FROM news_sources WHERE name='Google News Wirtschaft AT' AND enabled=1"))
 def test_bounded_retry_recovers(self):
  db=self.old_db();n=NewsPrefilter(db);err=urllib.error.URLError('temporary')
  with patch('urllib.request.urlopen',side_effect=[err,Response()]) as call,patch('time.sleep'):
   data,status=n._read('https://example.test')
  self.assertEqual(status,200);self.assertEqual(call.call_count,2);self.assertIn(b'Economy',data)
 def test_collect_persists_precise_http_error(self):
  db=self.old_db();n=NewsPrefilter(db)
  with db.con() as c:c.execute("UPDATE news_sources SET enabled=0");c.execute("UPDATE news_sources SET enabled=1 WHERE name='GDELT Wirtschaft'")
  error=urllib.error.HTTPError('https://x',429,'Too Many Requests',{},None)
  with patch.object(n,'_read',side_effect=error):r=n.collect()
  row=db.rows("SELECT last_status,last_error,consecutive_failures FROM news_sources WHERE name='GDELT Wirtschaft'")[0]
  self.assertEqual(row['last_status'],'ERROR HTTP 429');self.assertGreater(row['consecutive_failures'],0);self.assertTrue(r['errors'])
