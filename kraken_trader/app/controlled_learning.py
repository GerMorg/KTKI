import json,math
from db import now
FAMILIES={
 'crypto_spot':{'base_score':50.0,'momentum_weight':5.0,'trend_weight':8.0,'buy_threshold':65.0},
 'xstocks':{'base_score':50.0,'momentum_weight':4.0,'trend_weight':10.0,'buy_threshold':62.0},
 'forex':{'base_score':50.0,'momentum_weight':4.0,'trend_weight':9.0,'buy_threshold':64.0}}
BOUNDS={'base_score':(35,65),'momentum_weight':(1,10),'trend_weight':(2,16),'buy_threshold':(50,80)}
class ControlledLearning:
 def __init__(self,db):self.db=db;self.ensure()
 def ensure(self):
  with self.db.con() as c:
   c.executescript("""CREATE TABLE IF NOT EXISTS parameter_family_versions(id INTEGER PRIMARY KEY AUTOINCREMENT,created_at TEXT NOT NULL,family TEXT NOT NULL,version INTEGER NOT NULL,status TEXT NOT NULL,parameters_json TEXT NOT NULL,parent_version INTEGER,source TEXT NOT NULL,reason TEXT NOT NULL,UNIQUE(family,version));CREATE TABLE IF NOT EXISTS learning_candidates(id INTEGER PRIMARY KEY AUTOINCREMENT,created_at TEXT NOT NULL,family TEXT NOT NULL,status TEXT NOT NULL,base_version INTEGER NOT NULL,sample_count INTEGER NOT NULL,active_accuracy TEXT NOT NULL,candidate_accuracy TEXT NOT NULL,improvement TEXT NOT NULL,ci_low TEXT NOT NULL,ci_high TEXT NOT NULL,parameters_json TEXT NOT NULL,reason TEXT NOT NULL,decided_at TEXT);CREATE TABLE IF NOT EXISTS learning_shadow_results(id INTEGER PRIMARY KEY AUTOINCREMENT,created_at TEXT NOT NULL,candidate_id INTEGER NOT NULL,forecast_id INTEGER NOT NULL,active_correct INTEGER NOT NULL,candidate_correct INTEGER NOT NULL,details_json TEXT NOT NULL,UNIQUE(candidate_id,forecast_id));""")
   for family,params in FAMILIES.items():c.execute('INSERT OR IGNORE INTO parameter_family_versions(created_at,family,version,status,parameters_json,parent_version,source,reason) VALUES(?,?,1,?,?,NULL,?,?)',(now(),family,'ACTIVE',json.dumps(params,sort_keys=True),'DEFAULT','Deterministische Ausgangsversion'))
 def _wilson(self,successes,n,z=1.96):
  if not n:return 0.0,1.0
  p=successes/n;d=1+z*z/n;center=(p+z*z/(2*n))/d;margin=z*math.sqrt((p*(1-p)+z*z/(4*n))/n)/d;return max(0,center-margin),min(1,center+margin)
 def active(self,family):
  r=self.db.rows("SELECT * FROM parameter_family_versions WHERE family=? AND status='ACTIVE' ORDER BY version DESC LIMIT 1",(family,));return r[0] if r else None
 def _evaluations(self,family):return self.db.rows("SELECT f.id,f.direction,f.scanner_score,e.direction_correct,e.actual_return_pct FROM forecast_evaluations e JOIN research_forecasts f ON f.id=e.forecast_id JOIN market_universe u ON u.symbol=f.symbol WHERE u.category=? ORDER BY f.id",(family,))
 def propose(self,family,min_sample=10,min_improvement=.02):
  if family not in FAMILIES:return {'status':'UNKNOWN_FAMILY'}
  rows=self._evaluations(family);n=len(rows)
  if n<min_sample:return {'status':'INSUFFICIENT_DATA','sample_count':n,'required':min_sample}
  active=self.active(family);params=json.loads(active['parameters_json']);correct=sum(int(x['direction_correct']) for x in rows);accuracy=correct/n
  candidate=dict(params);direction=1 if accuracy>=.55 else -1;candidate['buy_threshold']=round(max(BOUNDS['buy_threshold'][0],min(BOUNDS['buy_threshold'][1],candidate['buy_threshold']-direction)),4);candidate['trend_weight']=round(max(BOUNDS['trend_weight'][0],min(BOUNDS['trend_weight'][1],candidate['trend_weight']+.25*direction)),4)
  # Shadow estimate is deliberately conservative: only evaluated outcomes above the candidate threshold count as directional candidates.
  shadow=[]
  for x in rows:
   selected=float(x.get('scanner_score') or 0)>=candidate['buy_threshold'];candidate_correct=int(x['direction_correct']) if selected else 0;shadow.append((x['id'],int(x['direction_correct']),candidate_correct))
  cand_correct=sum(x[2] for x in shadow);cand_accuracy=cand_correct/n;improvement=cand_accuracy-accuracy;low,high=self._wilson(cand_correct,n);status='PENDING' if improvement>=min_improvement else 'REJECTED_GATE'
  with self.db.con() as c:
   cur=c.execute('INSERT INTO learning_candidates(created_at,family,status,base_version,sample_count,active_accuracy,candidate_accuracy,improvement,ci_low,ci_high,parameters_json,reason,decided_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)',(now(),family,status,active['version'],n,str(accuracy),str(cand_accuracy),str(improvement),str(low),str(high),json.dumps(candidate,sort_keys=True),'Schattenvergleich gegen aktive Version; keine automatische Aktivierung',now() if status!='PENDING' else None));cid=cur.lastrowid
   c.executemany('INSERT INTO learning_shadow_results(created_at,candidate_id,forecast_id,active_correct,candidate_correct,details_json) VALUES(?,?,?,?,?,?)',[(now(),cid,fid,a,cc,'{}') for fid,a,cc in shadow])
  self.db.audit('CONTROLLED_LEARNING_CANDIDATE',json.dumps({'candidate_id':cid,'family':family,'status':status,'sample_count':n,'improvement':improvement}));return {'status':status,'candidate_id':cid,'sample_count':n,'improvement':improvement,'ci':[low,high]}
 def decide(self,candidate_id,action):
  rows=self.db.rows('SELECT * FROM learning_candidates WHERE id=?',(candidate_id,));
  if not rows:return {'status':'NOT_FOUND'}
  p=rows[0]
  if p['status']!='PENDING':return {'status':'NOT_PENDING'}
  if action=='reject':
   with self.db.con() as c:c.execute("UPDATE learning_candidates SET status='REJECTED',decided_at=? WHERE id=?",(now(),candidate_id))
   self.db.audit('CONTROLLED_LEARNING_REJECTED',str(candidate_id));return {'status':'REJECTED'}
  if action!='approve':return {'status':'INVALID_ACTION'}
  params=json.loads(p['parameters_json'])
  if set(params)!=set(FAMILIES[p['family']]):return {'status':'INVALID_PARAMETER_SET'}
  for name,value in params.items():
   lo,hi=BOUNDS[name]
   if not lo<=float(value)<=hi:return {'status':'OUT_OF_BOUNDS','parameter':name}
  new_version=int(p['base_version'])+1
  with self.db.con() as c:
   c.execute("UPDATE parameter_family_versions SET status='SUPERSEDED' WHERE family=? AND status='ACTIVE'",(p['family'],));c.execute('INSERT INTO parameter_family_versions(created_at,family,version,status,parameters_json,parent_version,source,reason) VALUES(?,?,?,?,?,?,?,?)',(now(),p['family'],new_version,'ACTIVE',p['parameters_json'],p['base_version'],f'APPROVED_CANDIDATE_{candidate_id}','Explizite Benutzerfreigabe'));c.execute("UPDATE learning_candidates SET status='APPROVED',decided_at=? WHERE id=?",(now(),candidate_id))
  self.db.audit('CONTROLLED_LEARNING_APPROVED',json.dumps({'candidate_id':candidate_id,'family':p['family'],'version':new_version}));return {'status':'APPROVED','version':new_version}
 def rollback(self,family,target_version):
  target=self.db.rows('SELECT * FROM parameter_family_versions WHERE family=? AND version=?',(family,target_version,));
  if not target:return {'status':'NOT_FOUND'}
  current=self.active(family);next_version=int(current['version'])+1
  with self.db.con() as c:c.execute("UPDATE parameter_family_versions SET status='SUPERSEDED' WHERE family=? AND status='ACTIVE'",(family,));c.execute('INSERT INTO parameter_family_versions(created_at,family,version,status,parameters_json,parent_version,source,reason) VALUES(?,?,?,?,?,?,?,?)',(now(),family,next_version,'ACTIVE',target[0]['parameters_json'],current['version'],f'ROLLBACK_TO_{target_version}','Vollständiger kontrollierter Rollback'))
  self.db.audit('CONTROLLED_LEARNING_ROLLBACK',json.dumps({'family':family,'target_version':target_version,'new_version':next_version}));return {'status':'ROLLED_BACK','version':next_version}
 def candidates(self):return self.db.rows('SELECT * FROM learning_candidates ORDER BY id DESC LIMIT 100')
 def versions(self):return self.db.rows('SELECT * FROM parameter_family_versions ORDER BY family,version DESC')
