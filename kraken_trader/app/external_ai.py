import json,re,urllib.request
from db import now
REQUIRED={'relevance','sentiment','expected_impact','horizon','confidence','fact_status','priced_in','topics','affected_assets','summary','counterarguments'}
PROMPT='''Bewerte die folgende Finanznachricht. Antworte ausschliesslich als JSON-Objekt mit den Feldern relevance, sentiment, expected_impact, horizon, confidence, fact_status, priced_in, topics, affected_assets, summary, counterarguments. Numerische Werte relevance, sentiment, expected_impact und confidence muessen zwischen -1 und 1 liegen, wobei relevance und confidence nicht negativ sein duerfen. Keine Handelsanweisung. Nachricht:\n'''
class ExternalNewsAI:
 def __init__(self,db,options,transport=None):self.db,self.options,self.transport=db,options or {},transport;self.ensure()
 def ensure(self):
  with self.db.con() as c:c.executescript("""CREATE TABLE IF NOT EXISTS external_news_ai_results(news_id TEXT PRIMARY KEY,created_at TEXT NOT NULL,status TEXT NOT NULL,result_json TEXT NOT NULL,error TEXT);CREATE TABLE IF NOT EXISTS news_ai_calibration(news_id TEXT PRIMARY KEY,created_at TEXT NOT NULL,provider TEXT NOT NULL,model TEXT NOT NULL,local_topics_json TEXT NOT NULL,external_topics_json TEXT NOT NULL,topic_overlap TEXT NOT NULL,missing_local_topics_json TEXT NOT NULL,affected_assets_json TEXT NOT NULL,details_json TEXT NOT NULL);""")
 def _post(self,url,body,headers):
  req=urllib.request.Request(url,data=json.dumps(body).encode('utf-8'),headers={'Content-Type':'application/json',**headers},method='POST')
  with urllib.request.urlopen(req,timeout=float(self.options.get('ai_timeout_seconds',30))) as response:return json.load(response)
 def _provider_transport(self,payload):
  provider=str(self.options.get('ai_provider') or 'google_ai_studio').lower();model=self.options.get('ai_model') or ('gemini-2.5-flash' if provider=='google_ai_studio' else 'gpt-4o-mini');key=self.options.get('ai_api_key');news=payload['news'];prompt=PROMPT+news.get('title','')+'\n'+news.get('summary','')
  if provider=='google_ai_studio':
   endpoint=self.options.get('ai_endpoint') or f'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent'
   raw=self._post(endpoint,{'contents':[{'parts':[{'text':prompt}]}],'generationConfig':{'temperature':0.1,'responseMimeType':'application/json'}},{'x-goog-api-key':key})
   return {'content':raw['candidates'][0]['content']['parts'][0]['text'],'raw':raw}
  endpoint=self.options.get('ai_endpoint') or 'https://api.openai.com/v1/chat/completions'
  raw=self._post(endpoint,{'model':model,'messages':[{'role':'user','content':prompt}],'temperature':0.1,'response_format':{'type':'json_object'}},{'Authorization':'Bearer '+key})
  return {'content':raw['choices'][0]['message']['content'],'raw':raw}
 def _content(self,payload):
  if 'content' in payload:return payload['content']
  return payload['choices'][0]['message']['content']
 def _json(self,text):
  text=str(text).strip();text=re.sub(r'^```(?:json)?\s*|\s*```$','',text,flags=re.I|re.S);return json.loads(text)
 def _calibrate(self,row,result):
  try:local=set(json.loads(row.get('topics_json') or '[]'))
  except Exception:local=set()
  external=set(str(x) for x in (result.get('topics') or []));overlap=len(local&external)/len(local|external) if local|external else 1.0;missing=sorted(external-local)
  details={'local_only':sorted(local-external),'external_only':missing,'automatic_parameter_change':False}
  with self.db.con() as c:c.execute('INSERT OR REPLACE INTO news_ai_calibration VALUES(?,?,?,?,?,?,?,?,?,?)',(row['id'],now(),str(self.options.get('ai_provider') or 'injected'),str(self.options.get('ai_model') or ''),json.dumps(sorted(local)),json.dumps(sorted(external)),str(overlap),json.dumps(missing),json.dumps(result.get('affected_assets') or []),json.dumps(details,sort_keys=True)))
 def analyze_pending(self):
  if not self.options.get('ai_news_enabled') or not self.options.get('ai_api_key'):return {'status':'DISABLED','processed':0,'succeeded':0,'failed':0}
  transport=self.transport or self._provider_transport;limit=max(1,min(100,int(self.options.get('ai_max_items_per_run',20))))
  cols={x['name'] for x in self.db.rows('PRAGMA table_info(news_items)')};topics='topics_json' if 'topics_json' in cols else "'[]' AS topics_json"
  rows=self.db.rows(f'SELECT id,title,summary,{topics} FROM news_items WHERE id NOT IN (SELECT news_id FROM external_news_ai_results) ORDER BY fetched_at DESC LIMIT ?',(limit,));ok=failed=0
  for row in rows:
   try:
    payload=transport({'model':self.options.get('ai_model'),'news':row});result=self._json(self._content(payload))
    if not REQUIRED.issubset(result):raise ValueError('incomplete response')
    status='VALID';error=None;ok+=1;self._calibrate(row,result)
   except Exception as exc:result={};status='INVALID';error=type(exc).__name__+': '+str(exc)[:240];failed+=1
   with self.db.con() as c:c.execute('INSERT OR REPLACE INTO external_news_ai_results VALUES(?,?,?,?,?)',(row['id'],now(),status,json.dumps(result,sort_keys=True),error))
  self.db.audit('EXTERNAL_NEWS_AI_RUN',json.dumps({'provider':self.options.get('ai_provider'),'model':self.options.get('ai_model'),'processed':len(rows),'succeeded':ok,'failed':failed}))
  return {'status':'COMPLETED','processed':len(rows),'succeeded':ok,'failed':failed}
 def results(self):return self.db.rows('SELECT r.*,n.title FROM external_news_ai_results r LEFT JOIN news_items n ON n.id=r.news_id ORDER BY r.created_at DESC LIMIT 100')
 def calibration(self):return self.db.rows('SELECT c.*,n.title FROM news_ai_calibration c LEFT JOIN news_items n ON n.id=c.news_id ORDER BY c.created_at DESC LIMIT 100')
