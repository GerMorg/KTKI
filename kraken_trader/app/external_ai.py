import json,urllib.request
from db import now
class ExternalNewsAI:
 def __init__(self,db,options=None):
  self.db,self.options=db,dict(options or {});self.ensure()
 def ensure(self):
  with self.db.con() as c:c.executescript("""CREATE TABLE IF NOT EXISTS news_ai_analysis(news_id TEXT PRIMARY KEY,analyzed_at TEXT NOT NULL,provider TEXT NOT NULL,model TEXT NOT NULL,status TEXT NOT NULL,result_json TEXT NOT NULL,error TEXT);""")
 def analyze_pending(self):
  if not self.options.get('ai_news_enabled'):return {'status':'DISABLED','processed':0}
  endpoint=str(self.options.get('ai_endpoint') or '').strip();key=str(self.options.get('ai_api_key') or '')
  if not endpoint or not key:return {'status':'NOT_CONFIGURED','processed':0}
  limit=max(1,min(100,int(self.options.get('ai_max_items_per_run',20))));items=self.db.rows("SELECT id,title,summary FROM news_items WHERE id NOT IN (SELECT news_id FROM news_ai_analysis) ORDER BY fetched_at DESC LIMIT ?",(limit,));processed=0
  for item in items:
   try:
    payload=json.dumps({'model':self.options.get('ai_model','gpt-4o-mini'),'messages':[{'role':'system','content':'Return compact JSON market-event classification. Do not recommend or execute trades.'},{'role':'user','content':item['title']+'\n'+item['summary']}]}).encode();req=urllib.request.Request(endpoint,data=payload,headers={'Authorization':'Bearer '+key,'Content-Type':'application/json'});response=urllib.request.urlopen(req,timeout=int(self.options.get('ai_timeout_seconds',30))).read().decode('utf-8')
    with self.db.con() as c:c.execute('INSERT OR REPLACE INTO news_ai_analysis VALUES(?,?,?,?,?,?,NULL)',(item['id'],now(),self.options.get('ai_provider','openai'),self.options.get('ai_model',''), 'OK',response));processed+=1
   except Exception as exc:
    with self.db.con() as c:c.execute('INSERT OR REPLACE INTO news_ai_analysis VALUES(?,?,?,?,?,?,?)',(item['id'],now(),self.options.get('ai_provider','openai'),self.options.get('ai_model',''),'ERROR','{}',type(exc).__name__))
  return {'status':'OK','processed':processed}
