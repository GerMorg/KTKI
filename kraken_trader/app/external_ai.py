import json
import urllib.parse
import urllib.request
from db import now

REQUIRED={'relevance','sentiment','expected_impact','horizon','confidence','fact_status','priced_in','topics','affected_assets','summary','counterarguments'}

class ExternalNewsAI:
 def __init__(self,db,options,transport=None):
  self.db,self.options=db,options or {}
  self.transport=transport or self._http_transport
  self.ensure()
 def ensure(self):
  with self.db.con() as c:c.execute('CREATE TABLE IF NOT EXISTS external_news_ai_results(news_id TEXT PRIMARY KEY,created_at TEXT NOT NULL,status TEXT NOT NULL,result_json TEXT NOT NULL,error TEXT)')
 def _prompt(self,row):
  return ('Bewerte die Nachricht ausschlieÃƒÅ¸lich als JSON mit den Feldern relevance, sentiment, expected_impact, horizon, confidence, fact_status, priced_in, topics, affected_assets, summary, counterarguments. '
          'Keine Handelsanweisung. Nachricht: '+str(row.get('title') or '')+'\n'+str(row.get('summary') or ''))
 def _http_transport(self,request):
  provider=str(self.options.get('ai_provider') or 'openai').lower()
  key=str(self.options.get('ai_api_key') or '')
  model=str(request.get('model') or self.options.get('ai_model') or '')
  timeout=max(5,min(120,int(self.options.get('ai_timeout_seconds',30))))
  prompt=self._prompt(request['news'])
  if provider=='gemini':
   endpoint=str(self.options.get('ai_endpoint') or 'https://generativelanguage.googleapis.com/v1beta').rstrip('/')
   url=endpoint+'/models/'+urllib.parse.quote(model,safe='-_.')+':generateContent'
   body={'contents':[{'parts':[{'text':prompt}]}],'generationConfig':{'responseMimeType':'application/json'}}
   headers={'Content-Type':'application/json','X-Goog-Api-Key':key}
  elif provider in ('openai','azure_openai'):
   endpoint=str(self.options.get('ai_endpoint') or 'https://api.openai.com/v1/chat/completions')
   url=endpoint
   body={'model':model,'messages':[{'role':'user','content':prompt}],'response_format':{'type':'json_object'}}
   headers={'Content-Type':'application/json','Authorization':'Bearer '+key}
   if provider=='azure_openai':headers={'Content-Type':'application/json','api-key':key}
  else:raise ValueError('unsupported provider: '+provider)
  req=urllib.request.Request(url,data=json.dumps(body).encode('utf-8'),headers=headers,method='POST')
  with urllib.request.urlopen(req,timeout=timeout) as response:return json.load(response)
 def _content(self,payload):
  provider=str(self.options.get('ai_provider') or 'openai').lower()
  if provider=='gemini':return payload['candidates'][0]['content']['parts'][0]['text']
  return payload['choices'][0]['message']['content']
 def analyze_pending(self):
  if not self.options.get('ai_news_enabled') or not self.options.get('ai_api_key'):return {'status':'DISABLED','processed':0,'succeeded':0,'failed':0}
  limit=max(1,min(100,int(self.options.get('ai_max_items_per_run',20))))
  rows=self.db.rows('SELECT id,title,summary FROM news_items WHERE id NOT IN (SELECT news_id FROM external_news_ai_results) ORDER BY id LIMIT '+str(limit));ok=failed=0
  for row in rows:
   try:
    payload=self.transport({'model':self.options.get('ai_model'),'news':row});result=json.loads(self._content(payload))
    if not REQUIRED.issubset(result):raise ValueError('incomplete response')
    status='VALID';error=None;ok+=1
   except Exception as exc:result={};status='INVALID';error=type(exc).__name__+': '+str(exc)[:160];failed+=1
   with self.db.con() as c:c.execute('INSERT OR REPLACE INTO external_news_ai_results VALUES(?,?,?,?,?)',(row['id'],now(),status,json.dumps(result,sort_keys=True),error))
  comparison=self.news_learning.propose(automatic=True) if ok and getattr(self,'news_learning',None) else {'status':'NOT_RUN'}
  return {'status':'COMPLETED','provider':str(self.options.get('ai_provider') or 'openai'),'processed':len(rows),'succeeded':ok,'failed':failed,'local_comparison':comparison}
