import json
import time
import urllib.error
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
  return ('Bewerte die Nachricht ausschließlich als JSON mit den Feldern relevance, sentiment, expected_impact, horizon, confidence, fact_status, priced_in, topics, affected_assets, summary, counterarguments. '
          'Keine Handelsanweisung. Nachricht: '+str(row.get('title') or '')+'\n'+str(row.get('summary') or ''))
 def _provider(self):return str(self.options.get('ai_provider') or 'openai').strip().lower()
 def _model(self,provider=None):
  provider=provider or self._provider();model=str(self.options.get('ai_model') or '').strip()
  if provider=='gemini' and not model.lower().startswith('gemini-'):return 'gemini-2.5-flash-lite'
  if provider in ('openai','azure_openai') and not model:return 'gpt-4o-mini'
  return model or 'gemini-2.5-flash-lite'
 def _http_transport(self,request):
  provider=self._provider();key=str(self.options.get('ai_api_key') or '').strip();model=self._model(provider)
  timeout=max(5,min(120,int(self.options.get('ai_timeout_seconds',30))));prompt=self._prompt(request['news'])
  if provider=='gemini':
   endpoint=str(self.options.get('ai_endpoint') or 'https://generativelanguage.googleapis.com/v1beta').rstrip('/')
   url=endpoint+'/models/'+urllib.parse.quote(model,safe='-_.')+':generateContent'
   body={'contents':[{'parts':[{'text':prompt}]}],'generationConfig':{'responseMimeType':'application/json'}}
   headers={'Content-Type':'application/json','X-Goog-Api-Key':key}
  elif provider in ('openai','azure_openai'):
   endpoint=str(self.options.get('ai_endpoint') or 'https://api.openai.com/v1/chat/completions');url=endpoint
   body={'model':model,'messages':[{'role':'user','content':prompt}],'response_format':{'type':'json_object'}}
   headers={'Content-Type':'application/json','Authorization':'Bearer '+key}
   if provider=='azure_openai':headers={'Content-Type':'application/json','api-key':key}
  else:raise ValueError('unsupported provider: '+provider)
  encoded=json.dumps(body).encode('utf-8');last=None
  for attempt in range(3):
   req=urllib.request.Request(url,data=encoded,headers=headers,method='POST')
   try:
    with urllib.request.urlopen(req,timeout=timeout) as response:return json.load(response)
   except urllib.error.HTTPError as exc:
    try:detail=exc.read().decode('utf-8','replace')[:1000]
    except Exception:detail=''
    last=RuntimeError('HTTP '+str(exc.code)+' '+detail)
    if exc.code not in (429,500,502,503,504) or attempt==2:raise last
   except urllib.error.URLError as exc:
    last=RuntimeError('Network error: '+str(getattr(exc,'reason',exc))[:500])
    if attempt==2:raise last
   time.sleep(1.0*(2**attempt))
  raise last or RuntimeError('AI request failed')
 def _content(self,payload):
  provider=self._provider()
  if provider=='gemini':
   candidates=payload.get('candidates') if isinstance(payload,dict) else None
   if not candidates:raise ValueError('Gemini response has no candidates: '+json.dumps(payload,ensure_ascii=False)[:500])
   parts=((candidates[0].get('content') or {}).get('parts') or [])
   text=''.join(str(x.get('text') or '') for x in parts if isinstance(x,dict)).strip()
   if not text:raise ValueError('Gemini response has no text content')
   return text
  return payload['choices'][0]['message']['content']
 def analyze_pending(self):
  if not self.options.get('ai_news_enabled') or not self.options.get('ai_api_key'):return {'status':'DISABLED','processed':0,'succeeded':0,'failed':0,'provider':self._provider(),'model':self._model()}
  limit=max(1,min(100,int(self.options.get('ai_max_items_per_run',20))))
  rows=self.db.rows("SELECT n.id,n.title,n.summary FROM news_items n LEFT JOIN external_news_ai_results a ON a.news_id=n.id WHERE a.news_id IS NULL OR a.status!='VALID' ORDER BY CASE WHEN a.status='INVALID' THEN 0 ELSE 1 END,n.id LIMIT "+str(limit));ok=failed=0;errors=[]
  for row in rows:
   try:
    payload=self.transport({'model':self._model(),'news':row});result=json.loads(self._content(payload))
    if not isinstance(result,dict) or not REQUIRED.issubset(result):raise ValueError('incomplete response; missing '+','.join(sorted(REQUIRED-set(result if isinstance(result,dict) else {}))))
    status='VALID';error=None;ok+=1
   except Exception as exc:
    result={};status='INVALID';error=type(exc).__name__+': '+str(exc)[:1000];failed+=1;errors.append({'news_id':row['id'],'error':error})
   with self.db.con() as c:c.execute('INSERT OR REPLACE INTO external_news_ai_results VALUES(?,?,?,?,?)',(row['id'],now(),status,json.dumps(result,sort_keys=True,ensure_ascii=False),error))
  comparison={'status':'NOT_RUN'}
  if ok and getattr(self,'news_learning',None):
   try:comparison=self.news_learning.propose(automatic=True)
   except Exception as exc:comparison={'status':'FAILED','error':type(exc).__name__+': '+str(exc)[:500]}
  result={'status':'COMPLETED' if not failed else ('COMPLETED_WITH_WARNINGS' if ok else 'FAILED'),'provider':self._provider(),'model':self._model(),'processed':len(rows),'succeeded':ok,'failed':failed,'errors':errors[:10],'local_comparison':comparison}
  self.db.audit('EXTERNAL_NEWS_AI_RUN',json.dumps(result,ensure_ascii=False,sort_keys=True,default=str),'warning' if failed else 'info')
  return result
