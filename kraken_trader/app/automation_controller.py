import json
import threading
from datetime import datetime, timezone, timedelta
from db import now

DEFAULTS = {'automation_master_enabled':'false','automation_analysis_enabled':'false','automation_news_enabled':'false','automation_learning_enabled':'false','automation_learning_auto_approve_enabled':'false','automation_paper_enabled':'false','automation_real_enabled':'false','automation_real_execute_enabled':'false','automation_tick_minutes':'5','automation_analysis_interval_minutes':'60','automation_news_interval_minutes':'30','automation_learning_interval_minutes':'60','automation_paper_interval_minutes':'15','automation_real_interval_minutes':'60','analysis_top_per_category':'5','analysis_max_symbols':'20','analysis_max_delay_seconds':'0.35','learning_max_evaluations':'600','news_learning_max_samples':'600','news_local_eval_max_items':'1000','forecast_due_batch_limit':'1000'}

def as_mapping(value, default=None):
    if isinstance(value, dict): return value
    if isinstance(value, list):
        mappings=[x for x in value if isinstance(x,dict)]
        return mappings[0] if len(mappings)==1 else {'status':'COMPLETED','items':mappings}
    if value is None: return dict(default or {'status':'COMPLETED'})
    return {'status':'COMPLETED','value':value}

class AutomationController:
    def __init__(self, db, pipeline, news_prefilter, controlled_learning, news_learning, run_paper_cycle, real_allocator):
        self.db=db;self.pipeline=pipeline;self.news_prefilter=news_prefilter;self.controlled_learning=controlled_learning;self.news_learning=news_learning;self.run_paper_cycle=run_paper_cycle;self.real_allocator=real_allocator;self.lock=threading.Lock();self.stop_event=threading.Event();self.ensure()
    def ensure(self):
        with self.db.con() as c:
            c.executescript('''CREATE TABLE IF NOT EXISTS automation_runs(id INTEGER PRIMARY KEY AUTOINCREMENT,created_at TEXT NOT NULL,subsystem TEXT NOT NULL,status TEXT NOT NULL,automatic INTEGER NOT NULL,details_json TEXT NOT NULL,error TEXT);CREATE INDEX IF NOT EXISTS idx_automation_runs_subsystem ON automation_runs(subsystem,id DESC);''')
            for k,v in DEFAULTS.items():
                if not self.db.rows('SELECT value FROM settings WHERE key=?',(k,)): self.db.set_setting(k,v)
            try:
                c.execute('''INSERT INTO automation_runs(created_at,subsystem,status,automatic,details_json,error) SELECT created_at,subsystem,status,automatic,details_json,error FROM automation_runs_v67 WHERE NOT EXISTS (SELECT 1 FROM automation_runs)''')
            except Exception: pass
    def settings(self): return {k:self.db.value(k,v) for k,v in DEFAULTS.items()}
    @staticmethod
    def boolean(v): return str(v).lower()=='true'
    @staticmethod
    def minutes(v,minimum=1):
        try:return max(minimum,int(float(v)))
        except (TypeError,ValueError):return minimum
    def enabled(self,subsystem):
        s=self.settings();return self.boolean(s['automation_master_enabled']) and self.boolean(s[f'automation_{subsystem}_enabled'])
    def due(self,subsystem,interval):
        rows=self.db.rows("SELECT created_at FROM automation_runs WHERE subsystem=? AND status IN ('COMPLETED','QUEUED') ORDER BY id DESC LIMIT 1",(subsystem,))
        if not rows:return True
        try:last=datetime.fromisoformat(rows[0]['created_at'].replace('Z','+00:00'))
        except (TypeError,ValueError):return True
        return datetime.now(timezone.utc)-last>=timedelta(minutes=interval)
    def _record(self,subsystem,status,result=None,error=None):
        with self.db.con() as c:c.execute('INSERT INTO automation_runs(created_at,subsystem,status,automatic,details_json,error) VALUES(?,?,?,?,?,?)',(now(),subsystem,status,1,json.dumps(result or {},sort_keys=True,ensure_ascii=False,default=str),error))
    def _sync(self,s):
        self.db.set('automation_enabled','true' if self.boolean(s['automation_paper_enabled']) else 'false')
        self.db.set('real_balancing_enabled','true' if self.boolean(s['automation_real_enabled']) else 'false')
        self.db.set('real_balancing_execute_enabled','true' if self.boolean(s['automation_real_execute_enabled']) else 'false')
        self.db.set('real_balancing_dry_run','false' if self.boolean(s['automation_real_execute_enabled']) else 'true')
    def _approve(self):
        out=[]
        for active in self.controlled_learning.active_versions():
            for c in self.controlled_learning.candidates(active['family']):
                if isinstance(c,dict) and c.get('status')=='PENDING':out.append({'kind':'strategy','family':active['family'],'candidate_id':int(c['id']),'result':self.controlled_learning.decide(int(c['id']),'approve')})
        for c in self.news_learning.candidates():
            if isinstance(c,dict) and c.get('status')=='PENDING':out.append({'kind':'news','candidate_id':int(c['id']),'result':self.news_learning.decide(int(c['id']),'approve')})
        return out
    def run_learning(self,automatic=True,auto_approve=False):
        strategy=self.controlled_learning.propose_all(automatic=automatic);news=self.news_learning.propose(automatic=automatic);result={'status':'COMPLETED','strategy':strategy,'news':news}
        if auto_approve:result['auto_approved']=self._approve()
        self._record('learning','COMPLETED',result);return result
    def run_once(self,force=False):
        with self.lock:
            s=self.settings()
            if not self.boolean(s['automation_master_enabled']):return {'status':'DISABLED'}
            self._sync(s);results={}
            for subsystem,default_interval in [('news',30),('analysis',60),('learning',60),('paper',15),('real',60)]:
                if not self.enabled(subsystem):continue
                interval=self.minutes(s.get(f'automation_{subsystem}_interval_minutes',default_interval),1 if subsystem=='paper' else 5)
                if not force and not self.due(subsystem,interval):continue
                try:
                    if subsystem=='news':result=self.news_prefilter.collect()
                    elif subsystem=='analysis':result=self.pipeline.start()
                    elif subsystem=='learning':result=self.run_learning(True,self.boolean(s['automation_learning_auto_approve_enabled']))
                    elif subsystem=='paper':result={'cycle':self.run_paper_cycle()}
                    else:result=self.real_allocator.run(automatic=True)
                    result=as_mapping(result);results[subsystem]=result
                    if subsystem!='learning':self._record(subsystem,'QUEUED' if subsystem=='analysis' and result.get('status')=='QUEUED' else 'COMPLETED',result)
                except Exception as exc:
                    error=type(exc).__name__+': '+str(exc)[:500];results[subsystem]={'status':'FAILED','error':error};self._record(subsystem,'FAILED',results[subsystem],error);self.db.audit('AUTOMATION_FAILED',json.dumps({'subsystem':subsystem,'error':error},sort_keys=True),'error')
            return {'status':'COMPLETED','results':results}
    def start_background(self):
        if self.db.value('automation_scheduler_disabled','false').lower()=='true':return None
        t=threading.Thread(target=self._loop,daemon=True,name='automation-controller');t.start();return t
    def _loop(self):
        while not self.stop_event.wait(self.minutes(self.db.value('automation_tick_minutes','5'))*60):
            try:self.run_once()
            except Exception as exc:self.db.audit('AUTOMATION_TICK_FAILED',type(exc).__name__+': '+str(exc)[:500],'error')
    def stop(self):self.stop_event.set()
    def latest(self,limit=100):return self.db.rows('SELECT * FROM automation_runs ORDER BY id DESC LIMIT ?',(max(1,min(500,int(limit))),))
