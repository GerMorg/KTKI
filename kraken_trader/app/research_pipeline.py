import json,threading,traceback
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
  with self.db.con() as c:cur=c.execute("INSERT INTO research_jobs VALUES(NULL,?,?,NULL,'QUEUED','UNIVERSE',0,6,NULL,'{}')",(now(),None));jid=cur.lastrowid
  threading.Thread(target=self._run,args=(jid,),daemon=True,name='research-pipeline').start();return {'status':'QUEUED','job_id':jid}
 def step(self,jid,stage,n,d=None):
  payload=d if isinstance(d,dict) else {'value':d}
  with self.db.con() as c:c.execute('UPDATE research_jobs SET status=?,stage=?,progress_current=?,details_json=? WHERE id=?',('RUNNING',stage,n,json.dumps(payload or {},ensure_ascii=False,default=str),jid))
 def fail(self,jid,stage,operation,exc,context=None):
  error=type(exc).__name__+': '+str(exc)[:500]
  details={'stage':stage,'operation':operation,'error':error,'context':context or {}}
  with self.db.con() as c:c.execute('UPDATE research_jobs SET status=?,finished_at=?,error=?,details_json=? WHERE id=?',('FAILED',now(),error,json.dumps(details,ensure_ascii=False,sort_keys=True,default=str),jid))
  self.db.audit('RESEARCH_STAGE_FAILED',json.dumps({'job_id':jid,**details},ensure_ascii=False,sort_keys=True,default=str),'error')
  self.db.audit('RESEARCH_PIPELINE_FAILED',error,'error')
 def _run(self,jid):
  stage='UNIVERSE';operation='start'
  try:
   with self.db.con() as c:c.execute('UPDATE research_jobs SET status=?,started_at=? WHERE id=?',('RUNNING',now(),jid))
   stage,operation='UNIVERSE','universe.sync';self.step(jid,stage,1);u=self.universe.sync()
   stage,operation='NEWS_AND_PREFILTER','prefilter.run';self.step(jid,stage,2,{'universe':u});p=self.prefilter.run(int(float(self.db.value('prefilter_top_per_category','8'))));symbols=self.prefilter.candidates()
   stage,operation='DEEP_SCAN','scanner.run';self.step(jid,stage,3,{'candidates':len(symbols)});s=self.scanner.run(symbols,60,limit=len(symbols),delay_seconds=float(self.db.value('scanner_delay_seconds','1.05')))
   stage,operation='DEEP_SCAN','research_watchlist.update'
   with self.db.con() as c:c.execute("UPDATE research_watchlist SET status='ANALYZED' WHERE symbol IN (SELECT symbol FROM scanner_results WHERE quality='VALID')")
   stage,operation='DEEP_SCAN','ForexShadow.run';shadow=ForexShadow(self.db).run(symbols)
   stage,operation='FORECAST_SNAPSHOT';self.step(jid,stage,4,{'symbols':len(symbols)})
   stage,operation='ForecastTracker.snapshot';forecast_count=self.forecasts.snapshot(symbols)
   stage,operation='ForecastTracker.evaluate_due';evaluated=self.forecasts.evaluate_due()
   stage,operation='LEARNING_CANDIDATES';self.step(jid,stage,5,{'forecasts':forecast_count,'evaluated':evaluated})
   from controlled_learning import ControlledLearning
   from news_learning import NewsLearning
   stage,operation='ControlledLearning.propose_all';controlled=ControlledLearning(self.db).propose_all(automatic=True)
   stage,operation='NewsLearning.propose';news=NewsLearning(self.db).propose(automatic=True)
   learning={'controlled':controlled,'news':news}
   with self.db.con() as c:c.execute('UPDATE research_jobs SET status=?,stage=?,progress_current=?,finished_at=?,details_json=? WHERE id=?',('COMPLETED','DONE',6,now(),json.dumps({'universe':u,'prefilter':p,'scanner':s,'forex_shadow':shadow,'forecasts':forecast_count,'evaluated':evaluated,'learning':learning},ensure_ascii=False,default=str),jid))
  except Exception as exc:
   self.fail(jid,stage,operation,exc,{'traceback':traceback.format_exc(limit=8)})
  finally:self.lock.release()
 def latest(self):
  r=self.db.rows('SELECT * FROM research_jobs ORDER BY id DESC LIMIT 1');return r[0] if r else None
