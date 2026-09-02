import json,threading,traceback
from forex_shadow import ForexShadow
from db import now
from payload_utils import as_mapping


def _is_payload_shape_error(exc):
    if not isinstance(exc, ValueError):
        return False
    text=str(exc).lower()
    return 'too many values to unpack' in text or 'not enough values to unpack' in text


class ResearchPipeline:
 def __init__(self,db,universe,prefilter,scanner,forecasts=None,shadow=None):
  if forecasts is None:
   from forecast_tracker import ForecastTracker
   forecasts=ForecastTracker(db)
  self.db,self.universe,self.prefilter,self.scanner,self.forecasts=db,universe,prefilter,scanner,forecasts
  self.shadow=shadow or ForexShadow(db);self.lock=threading.Lock();self.ensure()
 def ensure(self):
  with self.db.con() as c:c.execute("CREATE TABLE IF NOT EXISTS research_jobs(id INTEGER PRIMARY KEY AUTOINCREMENT,created_at TEXT NOT NULL,started_at TEXT,finished_at TEXT,status TEXT NOT NULL,stage TEXT NOT NULL,progress_current INTEGER NOT NULL,progress_total INTEGER NOT NULL,error TEXT,details_json TEXT NOT NULL)")
 def start(self):
  if not self.lock.acquire(False):return {'status':'BUSY'}
  with self.db.con() as c:cur=c.execute("INSERT INTO research_jobs VALUES(NULL,?,?,NULL,'QUEUED','UNIVERSE',0,6,NULL,'{}')",(now(),None));jid=cur.lastrowid
  threading.Thread(target=self._run,args=(jid,),daemon=True,name='research-pipeline').start();return {'status':'QUEUED','job_id':jid}
 def step(self,jid,stage,n,d=None):
  payload=d if isinstance(d,dict) else {'value':d}
  with self.db.con() as c:c.execute('UPDATE research_jobs SET status=?,stage=?,progress_current=?,details_json=? WHERE id=?',('RUNNING',stage,n,json.dumps(payload or {},ensure_ascii=False,default=str),jid))
 def _degrade(self,jid,stage,operation,exc,context=None):
  error=type(exc).__name__+': '+str(exc)[:500];payload={'job_id':jid,'stage':stage,'operation':operation,'error':error,'context':context or {}}
  self.db.audit('RESEARCH_STAGE_DEGRADED',json.dumps(payload,ensure_ascii=False,sort_keys=True,default=str),'warning')
  return {'status':'DEGRADED','error':error}
 def _shape_guard(self,jid,stage,operation,fn,fallback,context=None):
  try:return fn(),False
  except Exception as exc:
   if _is_payload_shape_error(exc):return self._degrade(jid,stage,operation,exc,context),True
   raise
 def fail(self,jid,stage,operation,exc,context=None):
  error=type(exc).__name__+': '+str(exc)[:500]
  details={'stage':stage,'operation':operation,'error':error,'context':context or {}}
  with self.db.con() as c:c.execute('UPDATE research_jobs SET status=?,finished_at=?,error=?,details_json=? WHERE id=?',('FAILED',now(),error,json.dumps(details,ensure_ascii=False,sort_keys=True,default=str),jid))
  self.db.audit('RESEARCH_STAGE_FAILED',json.dumps({'job_id':jid,**details},ensure_ascii=False,sort_keys=True,default=str),'error')
  self.db.audit('RESEARCH_PIPELINE_FAILED',error,'error')
 def _run(self,jid):
  stage='UNIVERSE';operation='start';degraded=[]
  try:
   with self.db.con() as c:c.execute('UPDATE research_jobs SET status=?,started_at=? WHERE id=?',('RUNNING',now(),jid))
   stage,operation='UNIVERSE','universe.sync';self.step(jid,stage,1);u,was=self._shape_guard(jid,stage,operation,self.universe.sync,{'total':0,'enabled':0,'quality':'ERROR','errors':[]});degraded+= [operation] if was else []
   stage,operation='NEWS_AND_PREFILTER','prefilter.run';self.step(jid,stage,2,{'universe':u});p,was=self._shape_guard(jid,stage,operation,lambda:self.prefilter.run(int(float(self.db.value('prefilter_top_per_category','8')))),{'status':'DEGRADED'}, {'universe':u});degraded+= [operation] if was else []
   symbols=list(self.prefilter.candidates() or []) if not was else []
   stage,operation='DEEP_SCAN','scanner.run';self.step(jid,stage,3,{'candidates':len(symbols)});s,was=self._shape_guard(jid,stage,operation,lambda:self.scanner.run(symbols,60,limit=len(symbols),delay_seconds=float(self.db.value('scanner_delay_seconds','1.05'))),{'status':'DEGRADED','processed':0,'results':[]},{'candidates':len(symbols)});degraded+= [operation] if was else []
   stage,operation='DEEP_SCAN','research_watchlist.update'
   with self.db.con() as c:c.execute("UPDATE research_watchlist SET status='ANALYZED' WHERE symbol IN (SELECT symbol FROM scanner_results WHERE quality='VALID')")
   stage,operation='DEEP_SCAN','ForexShadow.run';shadow_obj=self.shadow or ForexShadow(self.db);shadow,was=self._shape_guard(jid,stage,operation,lambda:shadow_obj.run(symbols),{'status':'DEGRADED','snapshots':0,'symbols':0},{'symbols':len(symbols)});degraded+= [operation] if was else []
   stage,operation='FORECAST_SNAPSHOT';self.step(jid,stage,4,{'symbols':len(symbols)})
   stage,operation='ForecastTracker.snapshot';forecast_count,was=self._shape_guard(jid,stage,operation,lambda:self.forecasts.snapshot(symbols),0,{'symbols':len(symbols)});degraded+= [operation] if was else []
   stage,operation='ForecastTracker.evaluate_due';evaluated,was=self._shape_guard(jid,stage,operation,self.forecasts.evaluate_due,0);degraded+= [operation] if was else []
   stage,operation='LEARNING_CANDIDATES';self.step(jid,stage,5,{'forecasts':forecast_count,'evaluated':evaluated})
   from controlled_learning import ControlledLearning
   from news_learning import NewsLearning
   stage,operation='ControlledLearning.propose_all';controlled,was=self._shape_guard(jid,stage,operation,lambda:ControlledLearning(self.db).propose_all(automatic=True),{'status':'DEGRADED','families':{} });degraded+= [operation] if was else []
   stage,operation='NewsLearning.propose';news,was=self._shape_guard(jid,stage,operation,lambda:NewsLearning(self.db).propose(automatic=True),{'status':'DEGRADED'});degraded+= [operation] if was else []
   learning={'controlled':controlled,'news':news};final_status='COMPLETED_DEGRADED' if degraded else 'COMPLETED';details={'universe':u,'prefilter':p,'scanner':s,'forex_shadow':shadow,'forecasts':forecast_count,'evaluated':evaluated,'learning':learning,'degraded_stages':degraded}
   with self.db.con() as c:c.execute('UPDATE research_jobs SET status=?,stage=?,progress_current=?,finished_at=?,error=?,details_json=? WHERE id=?',(final_status,'DONE',6,now(),None,json.dumps(details,ensure_ascii=False,default=str),jid))
   self.db.audit('RESEARCH_PIPELINE_COMPLETED',json.dumps({'job_id':jid,'status':final_status,'degraded_stages':degraded},ensure_ascii=False,sort_keys=True))
  except Exception as exc:self.fail(jid,stage,operation,exc,{'traceback':traceback.format_exc(limit=8)})
  finally:self.lock.release()
 def latest(self):
  r=self.db.rows('SELECT * FROM research_jobs ORDER BY id DESC LIMIT 1');return r[0] if r else None
