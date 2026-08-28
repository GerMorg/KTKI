import json,threading
from forex_shadow import ForexShadow
from db import now
class ResearchPipeline:
 def __init__(self,db,universe,prefilter,scanner,forecasts=None):
  if forecasts is None:
   from forecast_tracker import ForecastTracker
   forecasts=ForecastTracker(db)
  self.db,self.universe,self.prefilter,self.scanner,self.forecasts=db,universe,prefilter,scanner,forecasts;self.lock=threading.Lock();self.ensure()
 def ensure(self):
  with self.db.con() as c:c.execute("CREATE TABLE IF NOT EXISTS research_jobs(id INTEGER PRIMARY KEY AUTOINCREMENT,created_at TEXT NOT NULL,started_at TEXT,finished_at TEXT,status TEXT NOT NULL,stage TEXT NOT NULL,progress_current INTEGER NOT NULL,progress_total INTEGER NOT NULL,error TEXT,details_json TEXT NOT NULL)")
 def start(self):
  if not self.lock.acquire(False):return {'status':'BUSY'}
  with self.db.con() as c:cur=c.execute("INSERT INTO research_jobs VALUES(NULL,?,?,NULL,'QUEUED','UNIVERSE',0,5,NULL,'{}')",(now(),None));jid=cur.lastrowid
  threading.Thread(target=self._run,args=(jid,),daemon=True,name='research-pipeline').start();return {'status':'QUEUED','job_id':jid}
 def step(self,jid,stage,n,d=None):
  with self.db.con() as c:c.execute('UPDATE research_jobs SET status=?,stage=?,progress_current=?,details_json=? WHERE id=?',('RUNNING',stage,n,json.dumps(d or {},ensure_ascii=False),jid))
 def _run(self,jid):
  try:
   with self.db.con() as c:c.execute('UPDATE research_jobs SET status=?,started_at=? WHERE id=?',('RUNNING',now(),jid))
   self.step(jid,'UNIVERSE',1);u=self.universe.sync();self.step(jid,'NEWS_AND_PREFILTER',2,u);p=self.prefilter.run(int(float(self.db.value('prefilter_top_per_category','8'))));symbols=self.prefilter.candidates();self.step(jid,'DEEP_SCAN',3,{'candidates':len(symbols)});s=self.scanner.run(symbols,60,limit=len(symbols),delay_seconds=float(self.db.value('scanner_delay_seconds','1.05')))
   with self.db.con() as c:c.execute("UPDATE research_watchlist SET status='ANALYZED' WHERE symbol IN (SELECT symbol FROM scanner_results WHERE quality='VALID')")
   shadow=ForexShadow(self.db).run(symbols)
   self.step(jid,'FORECAST_SNAPSHOT',4);forecast_count=self.forecasts.snapshot(symbols);evaluated=self.forecasts.evaluate_due()
   with self.db.con() as c:c.execute('UPDATE research_jobs SET status=?,stage=?,progress_current=?,finished_at=?,details_json=? WHERE id=?',('COMPLETED','DONE',5,now(),json.dumps({'universe':u,'prefilter':p,'scanner':s,'forex_shadow':shadow,'forecasts':forecast_count,'evaluated':evaluated},ensure_ascii=False),jid))
  except Exception as exc:
   with self.db.con() as c:c.execute('UPDATE research_jobs SET status=?,finished_at=?,error=? WHERE id=?',('FAILED',now(),type(exc).__name__+': '+str(exc)[:300],jid))
   self.db.audit('RESEARCH_PIPELINE_FAILED',type(exc).__name__+': '+str(exc)[:300],'error')
  finally:self.lock.release()
 def latest(self):
  r=self.db.rows('SELECT * FROM research_jobs ORDER BY id DESC LIMIT 1');return r[0] if r else None






