import hashlib,json,time,urllib.request
from db import now
PROMPT_VERSION='news-research-v1';SCHEMA_VERSION='news-analysis-v1'
REQUIRED={'relevance','sentiment','expected_impact','horizon','confidence','fact_status','priced_in','topics','affected_assets','summary','counterarguments'}
class ExternalNewsAI:
 def __init__(self,db,options=None,transport=None):self.db,self.options,self.transport=db,options or {},transport;self.ensure()
 def ensure(self):
  with self.db.con() as c:c.executescript("""CREATE TABLE IF NOT EXISTS ai_news_analyses(news_id TEXT NOT NULL,provider TEXT NOT NULL,model TEXT NOT NULL,prompt_version TEXT NOT NULL,schema_version TEXT NOT NULL,created_at TEXT NOT NULL,status TEXT NOT NULL,relevance TEXT,confidence TEXT,payload_json TEXT NOT NULL,request_hash TEXT NOT NULL,latency_ms INTEGER,error TEXT,PRIMARY KEY(news_id,prompt_version,schema_version,model));CREATE TABLE IF NOT EXISTS ai_news_runs(id INTEGER PRIMARY KEY AUTOINCREMENT,created_at TEXT NOT NULL,provider TEXT NOT NULL,model TEXT NOT NULL,requested INTEGER NOT NULL,succeeded INTEGER NOT NULL,failed INTEGER NOT NULL,status TEXT NOT NULL);""")
 def enabled(self):return bool(self.options.get('ai_news_enabled')) and bool(self.options.get('ai_api_key'))
 def _call(self,item):
  prompt={'source':item['source_name'],'title':item['title'],'summary':item['summary'],'published_at':item['published_at'],'url':item['url']};model=self.options.get('ai_model','gpt-4o-mini')
  body={'model':model,'temperature':0,'messages':[{'role':'system','content':'Analysiere nur den gelieferten Nachrichtentext. Keine Orderempfehlung. Antworte als JSON mit relevance, sentiment, expected_impact, horizon, confidence, fact_status, priced_in, topics, affected_assets, summary, counterarguments.'},{'role':'user','content':json.dumps(prompt,ensure_ascii=False)}],'response_format':{'type':'json_object'}}
  if self.transport:return self.transport(body),body
  endpoint=str(self.options.get('ai_endpoint') or 'https://api.openai.com/v1/chat/completions');headers={'Content-Type':'application/json'};key=str(self.options.get('ai_api_key'))
  headers['api-key' if self.options.get('ai_provider')=='azure_openai' else 'Authorization']=key if self.options.get('ai_provider')=='azure_openai' else 'Bearer '+key
  with urllib.request.urlopen(urllib.request.Request(endpoint,data=json.dumps(body).encode(),headers=headers),timeout=int(self.options.get('ai_timeout_seconds',30))) as r:return json.load(r),body
 def analyze_pending(self):
  if not self.enabled():return {'status':'DISABLED','requested':0,'succeeded':0,'failed':0}
  model=str(self.options.get('ai_model','gpt-4o-mini'));limit=max(1,min(int(self.options.get('ai_max_items_per_run',20)),100));rows=self.db.rows("SELECT id,source_name,title,url,published_at,summary FROM news_items WHERE id NOT IN (SELECT news_id FROM ai_news_analyses WHERE status='VALID' AND model=?) ORDER BY fetched_at DESC LIMIT ?",(model,limit));ok=0
  for item in rows:
   start=time.monotonic();status='ERROR';error=None;data={};body={}
   try:
    response,body=self._call(item);content=((response.get('choices') or [{}])[0].get('message') or {}).get('content');data=json.loads(content) if isinstance(content,str) else content
    if not isinstance(data,dict) or not REQUIRED.issubset(data):raise ValueError('Ungültiges KI-Schema')
    data['relevance']=max(0,min(1,float(data['relevance'])));data['confidence']=max(0,min(1,float(data['confidence'])));status='VALID';ok+=1
   except Exception as exc:error=type(exc).__name__+': '+str(exc)[:200]
   digest=hashlib.sha256(json.dumps(body,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
   with self.db.con() as c:c.execute('INSERT OR REPLACE INTO ai_news_analyses VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)',(item['id'],str(self.options.get('ai_provider','openai')),model,PROMPT_VERSION,SCHEMA_VERSION,now(),status,str(data.get('relevance')) if status=='VALID' else None,str(data.get('confidence')) if status=='VALID' else None,json.dumps(data,ensure_ascii=False),digest,int((time.monotonic()-start)*1000),error))
  failed=len(rows)-ok;state='VALID' if rows and not failed else ('EMPTY' if not rows else 'INCOMPLETE')
  with self.db.con() as c:c.execute('INSERT INTO ai_news_runs VALUES(NULL,?,?,?,?,?,?,?)',(now(),str(self.options.get('ai_provider','openai')),model,len(rows),ok,failed,state))
  return {'status':state,'requested':len(rows),'succeeded':ok,'failed':failed}
