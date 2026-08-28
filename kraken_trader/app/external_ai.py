import json
from db import now
REQUIRED={'relevance','sentiment','expected_impact','horizon','confidence','fact_status','priced_in','topics','affected_assets','summary','counterarguments'}
class ExternalNewsAI:
 def __init__(self,db,options,transport=None):self.db,self.options,self.transport=db,options or {},transport;self.ensure()
 def ensure(self):
  with self.db.con() as c:c.execute('CREATE TABLE IF NOT EXISTS external_news_ai_results(news_id TEXT PRIMARY KEY,created_at TEXT NOT NULL,status TEXT NOT NULL,result_json TEXT NOT NULL,error TEXT)')
 def analyze_pending(self):
  if not self.options.get('ai_news_enabled') or not self.options.get('ai_api_key'):return {'status':'DISABLED','processed':0,'succeeded':0,'failed':0}
  if self.transport is None:return {'status':'DEFERRED','processed':0,'succeeded':0,'failed':0}
  rows=self.db.rows('SELECT id,title,summary FROM news_items WHERE id NOT IN (SELECT news_id FROM external_news_ai_results)');ok=failed=0
  for row in rows:
   try:
    payload=self.transport({'model':self.options.get('ai_model'),'news':row});content=payload['choices'][0]['message']['content'];result=json.loads(content)
    if not REQUIRED.issubset(result):raise ValueError('incomplete response')
    status='VALID';error=None;ok+=1
   except Exception as exc:result={};status='INVALID';error=type(exc).__name__+': '+str(exc)[:160];failed+=1
   with self.db.con() as c:c.execute('INSERT OR REPLACE INTO external_news_ai_results VALUES(?,?,?,?,?)',(row['id'],now(),status,json.dumps(result,sort_keys=True),error))
  comparison=self.news_learning.propose(automatic=True) if ok and getattr(self,'news_learning',None) else {'status':'NOT_RUN'}
  return {'status':'COMPLETED','processed':len(rows),'succeeded':ok,'failed':failed,'local_comparison':comparison}
