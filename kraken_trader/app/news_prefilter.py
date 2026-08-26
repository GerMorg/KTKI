import hashlib,json,re,time,urllib.error,urllib.request,xml.etree.ElementTree as ET
from db import now
from datetime import datetime,timezone,timedelta
SOURCES=[
 {'name':'GDELT Wirtschaft','url':'https://api.gdeltproject.org/api/v2/doc/doc?query=economy&mode=ArtList&maxrecords=50&format=json&timespan=24h','kind':'gdelt_json','class':'aggregator','weight':0.70},
 {'name':'GDELT Geopolitik','url':'https://api.gdeltproject.org/api/v2/doc/doc?query=geopolitics&mode=ArtList&maxrecords=50&format=json&timespan=24h','kind':'gdelt_json','class':'aggregator','weight':0.70},
 {'name':'Google News Wirtschaft AT','url':'https://news.google.com/rss/search?q=Wirtschaft%20OR%20Inflation%20OR%20Zinsen%20when%3A1d&hl=de&gl=AT&ceid=AT%3Ade','kind':'rss','class':'aggregator','weight':0.55},
 {'name':'Google News Geopolitik AT','url':'https://news.google.com/rss/search?q=Krieg%20OR%20Sanktionen%20OR%20Zoelle%20OR%20Trump%20when%3A1d&hl=de&gl=AT&ceid=AT%3Ade','kind':'rss','class':'aggregator','weight':0.55},
 {'name':'EZB Presse','url':'https://www.ecb.europa.eu/rss/press.html','kind':'rss','class':'primary','weight':1.00},
 {'name':'Federal Reserve','url':'https://www.federalreserve.gov/feeds/press_all.xml','kind':'rss','class':'primary','weight':1.00},
 {'name':'Kraken Blog','url':'https://blog.kraken.com/feed','kind':'rss','class':'issuer','weight':0.85},
]
ALIASES={'BTC':['bitcoin','btc'],'ETH':['ethereum','ether','eth'],'XRP':['xrp','ripple'],'SOL':['solana','sol'],'EUR':['euro','ecb','ezb'],'USD':['dollar','fed','federal reserve'],'AAPL':['apple'],'TSLA':['tesla'],'NVDA':['nvidia']}
CATEGORY_TERMS={'crypto_spot':['crypto','cryptocurrency','bitcoin','blockchain','token'],'xstocks':['stock','equity','shares','earnings','company'],'forex':['currency','forex','central bank','interest rate','inflation'],'leveraged_spot':['margin','leverage','volatility']}
TAXONOMY={
 'monetary_policy':['central bank','interest rate','rate cut','rate hike','monetary policy','fed','ecb'],
 'inflation':['inflation','consumer prices','cpi','producer prices'],
 'growth':['gdp','economic growth','recession','business activity'],
 'labor':['employment','unemployment','jobs','wages'],
 'regulation':['regulation','regulator','sec','law','ban','approval'],
 'geopolitics':['war','krieg','sanction','sanktion','tariff','zoll','geopolitical','geopolitik','election','wahl','trump'],
 'earnings':['earnings','revenue','profit','guidance','forecast'],
 'product_event':['launch','listing','delisting','acquisition','merger'],
 'security':['hack','exploit','breach','fraud','outage'],
 'flows':['inflow','outflow','fund flow','etf flow','liquidity'],
}
EVENT_TYPES={'policy':['decision','announces','approval','ban','regulation'],'shock':['unexpected','emergency','crisis','collapse','surge'],'scheduled':['meeting','report','results','earnings'],'structural':['adoption','partnership','acquisition','launch']}
def clean(x):return re.sub(r'\s+',' ',re.sub(r'<[^>]+>',' ',x or '')).strip()
def norm(x):return re.sub(r'[^a-z0-9 ]',' ',clean(x).lower())
def classify(text):
 h=norm(text);topics=[k for k,terms in TAXONOMY.items() if any(re.search(r'\b'+re.escape(t)+r'\b',h) for t in terms)];events=[k for k,terms in EVENT_TYPES.items() if any(re.search(r'\b'+re.escape(t)+r'\b',h) for t in terms)]
 return topics or ['general_market'],events or ['unspecified']
class NewsPrefilter:
 def __init__(self,db,timeout=15):self.db,self.timeout=db,timeout;self.ensure()
 def ensure(self):
  with self.db.con() as c:
   c.executescript("""CREATE TABLE IF NOT EXISTS news_sources(name TEXT PRIMARY KEY,url TEXT NOT NULL,kind TEXT NOT NULL,source_class TEXT NOT NULL DEFAULT 'unknown',weight TEXT NOT NULL DEFAULT '0.5',enabled INTEGER NOT NULL DEFAULT 1,last_status TEXT,last_checked_at TEXT);CREATE TABLE IF NOT EXISTS news_items(id TEXT PRIMARY KEY,source_name TEXT NOT NULL,title TEXT NOT NULL,url TEXT,published_at TEXT,fetched_at TEXT NOT NULL,summary TEXT NOT NULL,topics_json TEXT NOT NULL DEFAULT '[\"general_market\"]',event_types_json TEXT NOT NULL DEFAULT '[\"unspecified\"]',raw_json TEXT NOT NULL DEFAULT '{}');CREATE TABLE IF NOT EXISTS news_market_links(news_id TEXT NOT NULL,symbol TEXT NOT NULL,relevance TEXT NOT NULL,reason TEXT NOT NULL,PRIMARY KEY(news_id,symbol));""")
   source_cols={x['name'] for x in self.db.rows('PRAGMA table_info(news_sources)')}
   for name,definition in [('source_class',"TEXT NOT NULL DEFAULT 'unknown'"),('weight',"TEXT NOT NULL DEFAULT '0.5'")]:
    if name not in source_cols:c.execute(f'ALTER TABLE news_sources ADD COLUMN {name} {definition}')
   item_cols={x['name'] for x in self.db.rows('PRAGMA table_info(news_items)')}
   for name,definition in [('topics_json',"TEXT NOT NULL DEFAULT '[\"general_market\"]'"),('event_types_json',"TEXT NOT NULL DEFAULT '[\"unspecified\"]'")]:
    if name not in item_cols:c.execute(f'ALTER TABLE news_items ADD COLUMN {name} {definition}')
   for name,definition in [('last_error','TEXT'),('consecutive_failures','INTEGER NOT NULL DEFAULT 0'),('last_success_at','TEXT'),('cooldown_until','TEXT')]:
    if name not in source_cols:c.execute(f'ALTER TABLE news_sources ADD COLUMN {name} {definition}')
   c.execute("UPDATE news_sources SET enabled=0,last_status='REPLACED' WHERE name='GDELT Global'")
   for item in SOURCES:
    c.execute("INSERT INTO news_sources(name,url,kind,source_class,weight,enabled,last_status,last_checked_at) VALUES(?,?,?,?,?,1,NULL,NULL) ON CONFLICT(name) DO UPDATE SET url=excluded.url,kind=excluded.kind,source_class=excluded.source_class,weight=excluded.weight,enabled=1",(item['name'],item['url'],item['kind'],item['class'],str(item['weight'])))
 def sources(self):return self.db.rows('SELECT * FROM news_sources WHERE enabled=1 ORDER BY source_class DESC,name')
 def _read(self,url,attempts=3):
  headers={'User-Agent':'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 HA-Kraken-Trader/0.1.0-dev.15','Accept':'application/rss+xml,application/xml,application/json,text/xml;q=0.9,*/*;q=0.5'};last=None
  for attempt in range(attempts):
   try:
    req=urllib.request.Request(url,headers=headers)
    with urllib.request.urlopen(req,timeout=self.timeout) as response:return response.read(),int(getattr(response,'status',200) or 200)
   except urllib.error.HTTPError as exc:
    last=exc
    if exc.code not in (429,500,502,503,504) or attempt==attempts-1:raise
    retry=exc.headers.get('Retry-After') if exc.headers else None
    try:delay=max(1,min(float(retry),30)) if retry else 2**attempt
    except ValueError:delay=2**attempt
    time.sleep(delay)
   except urllib.error.URLError as exc:
    last=exc
    if attempt==attempts-1:raise
    time.sleep(2**attempt)
  raise last
 def _rss(self,data):
  root=ET.fromstring(data);nodes=root.findall('.//item') or root.findall('.//{http://www.w3.org/2005/Atom}entry');out=[]
  for n in nodes[:150]:
   def pick(*names):
    for name in names:
     x=n.find(name)
     if x is not None:
      if x.get('href'):return x.get('href')
      if x.text:return clean(x.text)
    return ''
   out.append({'title':pick('title','{http://www.w3.org/2005/Atom}title'),'url':pick('link','{http://www.w3.org/2005/Atom}link'),'published_at':pick('pubDate','published','updated','{http://www.w3.org/2005/Atom}updated'),'summary':pick('description','summary','{http://www.w3.org/2005/Atom}summary')})
  return [x for x in out if x['title']]
 def _json(self,data):
  j=json.loads(data.decode('utf-8'));return [{'title':clean(x.get('title')),'url':x.get('url') or '','published_at':x.get('seendate') or '','summary':''} for x in j.get('articles',[]) if x.get('title')]
 def collect(self):
  saved=0;errors=[]
  for src in self.sources():
   cooldown=src.get('cooldown_until')
   if cooldown:
    try:
     if datetime.now(timezone.utc)<datetime.fromisoformat(cooldown):
      errors.append({'source':src['name'],'error':'COOLDOWN','detail':cooldown});continue
    except ValueError:pass
   try:
    response=self._read(src['url']);data,http_status=response if isinstance(response,tuple) else (response,200);items=self._json(data) if src['kind']=='gdelt_json' else self._rss(data)
    with self.db.con() as c:
     for x in items:
      key=hashlib.sha256((norm(x['title'])+'|'+(x['url'] or '')).encode()).hexdigest();topics,events=classify(x['title']+' '+x['summary']);before=c.total_changes
      c.execute('INSERT OR IGNORE INTO news_items(id,source_name,title,url,published_at,fetched_at,summary,topics_json,event_types_json,raw_json) VALUES(?,?,?,?,?,?,?,?,?,?)',(key,src['name'],x['title'],x['url'],x['published_at'],now(),x['summary'],json.dumps(topics),json.dumps(events),json.dumps(x,ensure_ascii=False)));saved+=c.total_changes-before
     c.execute('UPDATE news_sources SET last_status=?,last_checked_at=?,last_error=NULL,consecutive_failures=0,last_success_at=? WHERE name=?',(f'OK HTTP {http_status}',now(),now(),src['name']))
   except Exception as exc:
    code=getattr(exc,'code',None);reason=str(getattr(exc,'reason',exc))[:240];label=f'HTTP {code}' if code else type(exc).__name__;errors.append({'source':src['name'],'error':label,'detail':reason})
    is_tls='handshake operation timed out' in reason.lower();cooldown=(datetime.now(timezone.utc)+timedelta(hours=6)).isoformat() if is_tls else None
    with self.db.con() as c:c.execute('UPDATE news_sources SET last_status=?,last_checked_at=?,last_error=?,consecutive_failures=COALESCE(consecutive_failures,0)+1,cooldown_until=? WHERE name=?',(('DEGRADED TLS COOLDOWN' if is_tls else f'ERROR {label}'),now(),reason,cooldown,src['name']))
  ai=self.external_ai.analyze_pending() if getattr(self,'external_ai',None) else {'status':'DISABLED'};self.db.audit('NEWS_COLLECT',json.dumps({'saved':saved,'errors':errors,'ai':ai},ensure_ascii=False),'warning' if errors else 'info');return {'saved':saved,'errors':errors,'ai':ai}
 def link_markets(self,markets,limit=500):
  items=self.db.rows('SELECT n.id,n.title,n.summary,s.weight FROM news_items n JOIN news_sources s ON s.name=n.source_name ORDER BY n.fetched_at DESC LIMIT ?',(limit,));links=[]
  for m in markets:
   symbol=m['symbol'];base=(m.get('base_asset') or symbol.split('/')[0]).replace('XBT','BTC');terms=ALIASES.get(base.upper(),[base.lower()])+CATEGORY_TERMS.get(m.get('category') or '',[]);specific=set(ALIASES.get(base.upper(),[base.lower()]))
   for item in items:
    h=norm(item['title']+' '+item['summary']);hits=[t for t in terms if t and re.search(r'\b'+re.escape(t)+r'\b',h)]
    if hits:
     direct=any(x in specific for x in hits);rel=float(item['weight'])*(1.0 if direct else .25);links.append((item['id'],symbol,str(rel),('Direkter Marktbezug: ' if direct else 'Kategorietrend: ')+', '.join(hits[:4])))
  with self.db.con() as c:c.execute('DELETE FROM news_market_links');c.executemany('INSERT OR REPLACE INTO news_market_links VALUES(?,?,?,?)',links)
  return len(links)




