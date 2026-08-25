import hashlib,json,time,urllib.error,urllib.request
from db import now
PROMPT_VERSION='news-research-v1'
SCHEMA_VERSION='news-analysis-v1'
SCHEMA={
 'type':'object','additionalProperties':False,
 'properties':{
  'relevance':{'type':'number','minimum':0,'maximum':1},
  'sentiment':{'type':'number','minimum':-1,'maximum':1},
  'expected_impact':{'type':'number','minimum':-1,'maximum':1},
  'horizon':{'type':'string','enum':['intraday','days','weeks','months','structural','unclear']},
  'confidence':{'type':'number','minimum':0,'maximum':1},
  'fact_status':{'type':'string','enum':['confirmed','expectation','interpretation','unconfirmed','unclear']},
  'priced_in':{'type':'string','enum':['unlikely','partial','likely','unclear']},
  'topics':{'type':'array','items':{'type':'string'},'maxItems':8},
  'affected_assets':{'type':'array','items':{'type':'string'},'maxItems':12},
  'summary':{'type':'string','maxLength':600},
  'counterarguments':{'type':'array','items':{'type':'string'},'maxItems':5},
 },
 'required':['relevance','sentiment','expected_impact','horizon','confidence','fact_status','priced_in','topics','affected_assets','summary','counterarguments']
}
def clamp(x,lo,hi):return max(lo,min(hi,float(x)))
class ExternalNewsAI:
 def __init__(self,db,options=None,transport=None):
  self.db,self.options,self.transport=db,options or {},transport;self.ensure()
 def ensure(self):
  with self.db.con() as c:c.executescript("""CREATE TABLE IF NOT EXISTS ai_news_analyses(news_id TEXT NOT NULL,provider TEXT NOT NULL,model TEXT NOT NULL,prompt_version TEXT NOT NULL,schema_version TEXT NOT NULL,created_at TEXT NOT NULL,status TEXT NOT NULL,relevance TEXT,sentiment TEXT,expected_impact TEXT,horizon TEXT,confidence TEXT,fact_status TEXT,priced_in TEXT,topics_json TEXT NOT NULL,affected_assets_json TEXT NOT NULL,summary TEXT NOT NULL,counterarguments_json TEXT NOT NULL,request_hash TEXT NOT NULL,latency_ms INTEGER,error TEXT,PRIMARY KEY(news_id,prompt_version,schema_version,model));CREATE TABLE IF NOT EXISTS ai_news_runs(id INTEGER PRIMARY KEY AUTOINCREMENT,created_at TEXT NOT NULL,provider TEXT NOT NULL,model TEXT NOT NULL,requested INTEGER NOT NULL,succeeded INTEGER NOT NULL,failed INTEGER NOT NULL,status TEXT NOT NULL,details_json TEXT NOT NULL);""")
 def enabled(self):return bool(self.options.get('ai_news_enabled',False)) and bool(self.options.get('ai_api_key'))
 def endpoint(self):
  custom=str(self.options.get('ai_endpoint') or '').rstrip('/')
  if custom:return custom if custom.endswith('/chat/completions') else custom+'/chat/completions'
  return 'https://api.openai.com/v1/chat/completions'
 def _payload(self,item):
  model=str(self.options.get('ai_model') or 'gpt-4o-mini')
  source={'source':item.get('source_name'),'title':item.get('title'),'summary':item.get('summary'),'published_at':item.get('published_at'),'url':item.get('url')}
  system='''Du bist ein neutraler Finanznachrichten-Analyst. Bewerte ausschließlich den gelieferten Text. Erfinde keine Tatsachen. Eine Nachricht ist niemals ein Handelssignal. Trenne bestätigte Fakten, Erwartungen, Interpretationen und unbestätigte Aussagen. Relevanz bedeutet Bedeutung für die marktweite Research-Priorisierung. Gib nur das verlangte Schema zurück.'''
  return {'model':model,'temperature':0,'messages':[{'role':'system','content':system},{'role':'user','content':json.dumps(source,ensure_ascii=False)}],'response_format':{'type':'json_schema','json_schema':{'name':'news_analysis','strict':True,'schema':SCHEMA}}}
 def _request(self,payload):
  if self.transport:return self.transport(payload)
  provider=str(self.options.get('ai_provider') or 'openai').lower();key=str(self.options.get('ai_api_key') or '');headers={'Content-Type':'application/json','User-Agent':'HA-Kraken-Trader/0.1.0-dev.17'}
  if provider=='azure_openai':headers['api-key']=key
  else:headers['Authorization']='Bearer '+key
  req=urllib.request.Request(self.endpoint(),data=json.dumps(payload).encode('utf-8'),headers=headers,method='POST')
  with urllib.request.urlopen(req,timeout=max(5,min(int(self.options.get('ai_timeout_seconds',30)),120))) as response:return json.load(response)
 def _extract(self,response):
  content=((response.get('choices') or [{}])[0].get('message') or {}).get('content')
  if isinstance(content,list):content=''.join(x.get('text','') for x in content if isinstance(x,dict))
  if not content:raise ValueError('Leere KI-Antwort')
  return json.loads(content) if isinstance(content,str) else content
 def _validate(self,x):
  required=set(SCHEMA['required'])
  if not isinstance(x,dict) or not required.issubset(x):raise ValueError('Ungültiges Antwortschema')
  horizon=str(x['horizon']);fact=str(x['fact_status']);priced=str(x['priced_in'])
  if horizon not in SCHEMA['properties']['horizon']['enum'] or fact not in SCHEMA['properties']['fact_status']['enum'] or priced not in SCHEMA['properties']['priced_in']['enum']:raise ValueError('Ungültiger Enum-Wert')
  return {'relevance':clamp(x['relevance'],0,1),'sentiment':clamp(x['sentiment'],-1,1),'expected_impact':clamp(x['expected_impact'],-1,1),'horizon':horizon,'confidence':clamp(x['confidence'],0,1),'fact_status':fact,'priced_in':priced,'topics':[str(v)[:80] for v in x['topics'][:8]],'affected_assets':[str(v)[:80] for v in x['affected_assets'][:12]],'summary':str(x['summary'])[:600],'counterarguments':[str(v)[:240] for v in x['counterarguments'][:5]]}
 def analyze_item(self,item):
  payload=self._payload(item);request_hash=hashlib.sha256(json.dumps(payload,sort_keys=True,ensure_ascii=False).encode()).hexdigest();started=time.monotonic();provider=str(self.options.get('ai_provider') or 'openai');model=str(self.options.get('ai_model') or 'gpt-4o-mini')
  try:
   data=self._validate(self._extract(self._request(payload)));status='VALID';error=None
  except Exception as exc:
   data={'relevance':None,'sentiment':None,'expected_impact':None,'horizon':None,'confidence':None,'fact_status':None,'priced_in':None,'topics':[],'affected_assets':[],'summary':'','counterarguments':[]};status='ERROR';error=type(exc).__name__+': '+str(exc)[:240]
  latency=int((time.monotonic()-started)*1000)
  with self.db.con() as c:c.execute('INSERT OR REPLACE INTO ai_news_analyses(news_id,provider,model,prompt_version,schema_version,created_at,status,relevance,sentiment,expected_impact,horizon,confidence,fact_status,priced_in,topics_json,affected_assets_json,summary,counterarguments_json,request_hash,latency_ms,error) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(item['id'],provider,model,PROMPT_VERSION,SCHEMA_VERSION,now(),status,None if data['relevance'] is None else str(data['relevance']),None if data['sentiment'] is None else str(data['sentiment']),None if data['expected_impact'] is None else str(data['expected_impact']),data['horizon'],None if data['confidence'] is None else str(data['confidence']),data['fact_status'],data['priced_in'],json.dumps(data['topics'],ensure_ascii=False),json.dumps(data['affected_assets'],ensure_ascii=False),data['summary'],json.dumps(data['counterarguments'],ensure_ascii=False),request_hash,latency,error))
  return status=='VALID'
 def analyze_pending(self):
  if not self.enabled():return {'status':'DISABLED','requested':0,'succeeded':0,'failed':0}
  limit=max(1,min(int(self.options.get('ai_max_items_per_run',20)),100));model=str(self.options.get('ai_model') or 'gpt-4o-mini')
  rows=self.db.rows('''SELECT n.id,n.source_name,n.title,n.url,n.published_at,n.summary FROM news_items n WHERE NOT EXISTS(SELECT 1 FROM ai_news_analyses a WHERE a.news_id=n.id AND a.model=? AND a.prompt_version=? AND a.schema_version=? AND a.status='VALID') ORDER BY n.fetched_at DESC LIMIT ?''',(model,PROMPT_VERSION,SCHEMA_VERSION,limit));ok=sum(self.analyze_item(x) for x in rows);failed=len(rows)-ok;status='VALID' if rows and not failed else ('EMPTY' if not rows else 'INCOMPLETE')
  with self.db.con() as c:c.execute('INSERT INTO ai_news_runs VALUES(NULL,?,?,?,?,?,?,?,?)',(now(),str(self.options.get('ai_provider') or 'openai'),model,len(rows),ok,failed,status,json.dumps({'prompt_version':PROMPT_VERSION,'schema_version':SCHEMA_VERSION})))
  self.db.audit('AI_NEWS_ANALYSIS_RUN',json.dumps({'requested':len(rows),'succeeded':ok,'failed':failed,'status':status}),'warning' if failed else 'info');return {'status':status,'requested':len(rows),'succeeded':ok,'failed':failed}
