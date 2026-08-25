import hashlib,json,re,urllib.request,xml.etree.ElementTree as ET
from datetime import datetime,timezone
from db import now
DEFAULT_SOURCES=[
 {'name':'EZB Presse','url':'https://www.ecb.europa.eu/rss/press.html','kind':'rss_primary'},
 {'name':'GDELT Finanztrends','url':'https://api.gdeltproject.org/api/v2/doc/doc?query=(crypto%20OR%20stocks%20OR%20forex%20OR%20inflation%20OR%20commodities)&mode=ArtList&maxrecords=75&format=json&timespan=24h','kind':'gdelt_json'},
]
ALIASES={'BTC':['bitcoin','btc'],'ETH':['ethereum','ether','eth'],'XRP':['xrp','ripple'],'SOL':['solana','sol'],'EUR':['euro','ezb','ecb'],'USD':['dollar','fed','federal reserve']}
CATEGORY_TERMS={
 'crypto_spot':['crypto','cryptocurrency','bitcoin','blockchain','token'],
 'xstocks':['stock','equity','shares','earnings','company'],
 'forex':['currency','forex','central bank','interest rate','inflation'],
 'leveraged_spot':['margin','leverage','volatility'],
}
def clean(text):return re.sub(r'\s+',' ',re.sub(r'<[^>]+>',' ',text or '')).strip()
def norm(text):return re.sub(r'[^a-z0-9 ]',' ',clean(text).lower())
class NewsPrefilter:
 def __init__(self,db,timeout=12):self.db,self.timeout=db,timeout;self.ensure()
 def ensure(self):
  with self.db.con() as c:c.executescript("""CREATE TABLE IF NOT EXISTS news_sources(name TEXT PRIMARY KEY,url TEXT NOT NULL,kind TEXT NOT NULL,enabled INTEGER NOT NULL,last_status TEXT,last_checked_at TEXT);CREATE TABLE IF NOT EXISTS news_items(id TEXT PRIMARY KEY,source_name TEXT NOT NULL,title TEXT NOT NULL,url TEXT,published_at TEXT,fetched_at TEXT NOT NULL,summary TEXT NOT NULL,raw_json TEXT NOT NULL);CREATE TABLE IF NOT EXISTS news_market_links(news_id TEXT NOT NULL,symbol TEXT NOT NULL,relevance TEXT NOT NULL,reason TEXT NOT NULL,PRIMARY KEY(news_id,symbol));""")
  with self.db.con() as c:
   for s in DEFAULT_SOURCES:c.execute('INSERT OR IGNORE INTO news_sources VALUES(?,?,?,1,NULL,NULL)',(s['name'],s['url'],s['kind']))
 def sources(self):return self.db.rows('SELECT * FROM news_sources WHERE enabled=1 ORDER BY name')
 def _read(self,url):
  req=urllib.request.Request(url,headers={'User-Agent':'HA-Kraken-Trader-News/0.1'});return urllib.request.urlopen(req,timeout=self.timeout).read()
 def _parse_json(self,data):
  payload=json.loads(data.decode('utf-8'));return [{'title':clean(x.get('title')),'url':x.get('url') or '','published_at':x.get('seendate') or '','summary':''} for x in payload.get('articles',[]) if x.get('title')]
 def _parse(self,data):
  root=ET.fromstring(data);out=[]
  nodes=root.findall('.//item') or root.findall('.//{http://www.w3.org/2005/Atom}entry')
  for n in nodes[:100]:
   def text(*names):
    for name in names:
     x=n.find(name)
     if x is not None:
      if name.endswith('link') and x.get('href'):return x.get('href')
      if x.text:return clean(x.text)
    return ''
   out.append({'title':text('title','{http://www.w3.org/2005/Atom}title'),'url':text('link','{http://www.w3.org/2005/Atom}link'),'published_at':text('pubDate','published','updated','{http://www.w3.org/2005/Atom}published','{http://www.w3.org/2005/Atom}updated'),'summary':text('description','summary','{http://www.w3.org/2005/Atom}summary')})
  return [x for x in out if x['title']]
 def collect(self):
  saved=0;errors=[]
  for src in self.sources():
   try:
    data=self._read(src['url']);items=self._parse_json(data) if src['kind']=='gdelt_json' else self._parse(data)
    with self.db.con() as c:
     for x in items:
      key=hashlib.sha256((norm(x['title'])+'|'+(x['url'] or '')).encode()).hexdigest()
      before=c.total_changes;c.execute('INSERT OR IGNORE INTO news_items VALUES(?,?,?,?,?,?,?,?)',(key,src['name'],x['title'],x['url'],x['published_at'],now(),x['summary'],json.dumps(x,ensure_ascii=False)));saved+=c.total_changes-before
     c.execute('UPDATE news_sources SET last_status=?,last_checked_at=? WHERE name=?',('OK',now(),src['name']))
   except Exception as exc:
    errors.append({'source':src['name'],'error':type(exc).__name__})
    with self.db.con() as c:c.execute('UPDATE news_sources SET last_status=?,last_checked_at=? WHERE name=?',('ERROR:'+type(exc).__name__,now(),src['name']))
  self.db.audit('NEWS_COLLECT',json.dumps({'saved':saved,'errors':errors},ensure_ascii=False),'warning' if errors else 'info');return {'saved':saved,'errors':errors}
 def link_markets(self,markets,limit_items=300):
  items=self.db.rows('SELECT id,title,summary FROM news_items ORDER BY fetched_at DESC LIMIT ?',(limit_items,));links=[]
  for m in markets:
   symbol=m['symbol'];base=(m.get('base_asset') or symbol.split('/')[0]).replace('XBT','BTC');cat=m.get('category') or ''
   terms=ALIASES.get(base.upper(),[base.lower()])+CATEGORY_TERMS.get(cat,[])
   specific=set(ALIASES.get(base.upper(),[base.lower()]))
   for item in items:
    hay=norm(item['title']+' '+item['summary']);hits=[t for t in terms if t and re.search(r'\b'+re.escape(t.lower())+r'\b',hay)]
    if not hits:continue
    direct=any(x in specific for x in hits);rel='1.0' if direct else '0.25';reason=('Direkter Marktbezug: ' if direct else 'Kategorietrend: ')+', '.join(hits[:4]);links.append((item['id'],symbol,rel,reason))
  with self.db.con() as c:
   c.execute('DELETE FROM news_market_links');c.executemany('INSERT OR REPLACE INTO news_market_links VALUES(?,?,?,?)',links)
  return len(links)
