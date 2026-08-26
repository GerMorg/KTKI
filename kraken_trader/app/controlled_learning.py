import json,math
from db import now
from strategy_profiles import FAMILIES,BOUNDS,score_features

class ControlledLearning:
 def __init__(self,db):self.db=db;self.ensure()
 def ensure(self):
  with self.db.con() as c:
   c.executescript("""CREATE TABLE IF NOT EXISTS parameter_family_versions(id INTEGER PRIMARY KEY AUTOINCREMENT,created_at TEXT NOT NULL,family TEXT NOT NULL,version INTEGER NOT NULL,status TEXT NOT NULL,parameters_json TEXT NOT NULL,parent_version INTEGER,source TEXT NOT NULL,reason TEXT NOT NULL,UNIQUE(family,version));CREATE TABLE IF NOT EXISTS learning_candidates(id INTEGER PRIMARY KEY AUTOINCREMENT,created_at TEXT NOT NULL,family TEXT NOT NULL,status TEXT NOT NULL,base_version INTEGER NOT NULL,sample_count INTEGER NOT NULL,active_accuracy TEXT NOT NULL,candidate_accuracy TEXT NOT NULL,improvement TEXT NOT NULL,ci_low TEXT NOT NULL,ci_high TEXT NOT NULL,parameters_json TEXT NOT NULL,reason TEXT NOT NULL,decided_at TEXT);CREATE TABLE IF NOT EXISTS learning_shadow_results(id INTEGER PRIMARY KEY AUTOINCREMENT,created_at TEXT NOT NULL,candidate_id INTEGER NOT NULL,forecast_id INTEGER NOT NULL,active_correct INTEGER NOT NULL,candidate_correct INTEGER NOT NULL,details_json TEXT NOT NULL,UNIQUE(candidate_id,forecast_id));CREATE TABLE IF NOT EXISTS learning_candidate_metrics(candidate_id INTEGER NOT NULL,horizon_hours INTEGER NOT NULL,sample_count INTEGER NOT NULL,active_decisions INTEGER NOT NULL,candidate_decisions INTEGER NOT NULL,active_coverage TEXT NOT NULL,candidate_coverage TEXT NOT NULL,active_net_return TEXT NOT NULL,candidate_net_return TEXT NOT NULL,net_return_improvement TEXT NOT NULL,active_max_drawdown TEXT NOT NULL,candidate_max_drawdown TEXT NOT NULL,details_json TEXT NOT NULL,PRIMARY KEY(candidate_id,horizon_hours));""")
   for family,params in FAMILIES.items():c.execute('INSERT OR IGNORE INTO parameter_family_versions(created_at,family,version,status,parameters_json,parent_version,source,reason) VALUES(?,?,1,?,?,NULL,?,?)',(now(),family,'ACTIVE',json.dumps(params,sort_keys=True),'DEFAULT','Deterministische Ausgangsversion'))
  self._migrate_legacy_xstocks()
 def _migrate_legacy_xstocks(self):
  try:rows=self.db.rows("SELECT name,value,version FROM strategy_parameters WHERE name LIKE 'xstocks_%'")
  except Exception:return
  if not rows:return
  current=self.active('xstocks');params=json.loads(current['parameters_json']);mapping={x['name'].removeprefix('xstocks_'):float(x['value']) for x in rows};params.update({k:v for k,v in mapping.items() if k in params})
  if params==json.loads(current['parameters_json']):return
  with self.db.con() as c:c.execute('UPDATE parameter_family_versions SET parameters_json=?,source=?,reason=? WHERE id=?',(json.dumps(params,sort_keys=True),'LEGACY_MIGRATION','Übernahme der vorhandenen xStock-Parameter',current['id']))
 def _wilson(self,successes,n,z=1.96):
  if not n:return 0.0,1.0
  p=successes/n;d=1+z*z/n;center=(p+z*z/(2*n))/d;margin=z*math.sqrt((p*(1-p)+z*z/(4*n))/n)/d;return max(0,center-margin),min(1,center+margin)
 def active(self,family):
  r=self.db.rows("SELECT * FROM parameter_family_versions WHERE family=? AND status='ACTIVE' ORDER BY version DESC LIMIT 1",(family,));return r[0] if r else None
 def _evaluations(self,family):
  cols={x['name'] for x in self.db.rows('PRAGMA table_info(research_forecasts)')};features='f.features_json' if 'features_json' in cols else "'{}' AS features_json";horizon='f.horizon_hours' if 'horizon_hours' in cols else '0 AS horizon_hours'
  return self.db.rows(f"SELECT f.id,f.direction,f.scanner_score,{features},{horizon},e.direction_correct,e.actual_return_pct FROM forecast_evaluations e JOIN research_forecasts f ON f.id=e.forecast_id JOIN market_universe u ON u.symbol=f.symbol WHERE u.category=? ORDER BY f.id",(family,))
 def _strategy_return(self,signal,actual,cost_rate):
  if signal=='BUY':return actual-cost_rate
  if signal=='AVOID':return -actual-cost_rate
  return 0.0
 def _metrics(self,shadow):
  grouped={}
  for item in shadow:grouped.setdefault(int(item[3].get('horizon_hours') or 0),[]).append(item)
  out=[]
  for horizon,items in sorted(grouped.items()):
   n=len(items);ar=[x[3]['active_return_after_costs_pct'] for x in items];cr=[x[3]['candidate_return_after_costs_pct'] for x in items]
   def drawdown(values):
    equity=peak=1.0;worst=0.0
    for value in values:equity*=max(.000001,1+value/100);peak=max(peak,equity);worst=min(worst,equity/peak-1)
    return worst*100
   ad=sum(x[3]['active_signal']!='HOLD' for x in items);cd=sum(x[3]['candidate_signal']!='HOLD' for x in items);an=sum(ar);cn=sum(cr)
   out.append({'horizon_hours':horizon,'sample_count':n,'active_decisions':ad,'candidate_decisions':cd,'active_coverage':ad/n,'candidate_coverage':cd/n,'active_net_return':an,'candidate_net_return':cn,'net_return_improvement':cn-an,'active_max_drawdown':drawdown(ar),'candidate_max_drawdown':drawdown(cr)})
  return out
 def _candidate(self,family,params,rows):
  avg=sum(float(x.get('actual_return_pct') or 0) for x in rows)/len(rows);accuracy=sum(int(x['direction_correct']) for x in rows)/len(rows);direction=1 if accuracy>=.55 and avg>=0 else -1;out=dict(params)
  steps={'base_score':.25,'momentum_weight':.1,'trend_weight':.25,'volatility_penalty':-.05,'spread_penalty':-.5,'buy_threshold':-.5,'buy_max_spread_pct':.025,'avoid_threshold':-.25,'avoid_spread_pct':.05}
  for name,step in steps.items():
   lo,hi=BOUNDS[family][name];out[name]=round(max(lo,min(hi,out[name]+step*direction)),4)
  return out
 def propose(self,family,min_sample=10,min_improvement=.02):
  if family not in FAMILIES:return {'status':'UNKNOWN_FAMILY'}
  rows=self._evaluations(family);n=len(rows)
  if n<min_sample:return {'status':'INSUFFICIENT_DATA','sample_count':n,'required':min_sample}
  active=self.active(family);params=json.loads(active['parameters_json']);candidate=self._candidate(family,params,rows);shadow=[]
  for x in rows:
   try:features=json.loads(x.get('features_json') or '{}')
   except Exception:features={}
   if not isinstance(features,dict):features={}
   if not {'momentum_pct','trend_pct','volatility_pct','spread_pct'}.issubset(features):
    features={'momentum_pct':1 if x['direction']=='UP' else -1,'trend_pct':1 if x['direction']=='UP' else -1,'volatility_pct':0,'spread_pct':0}
   _,active_signal=score_features(features,params);_,candidate_signal=score_features(features,candidate);actual=float(x.get('actual_return_pct') or 0);cost_rate=float(features.get('estimated_roundtrip_cost_pct') or features.get('estimated_cost_pct') or 0)
   def correct(signal):return int((signal=='BUY' and actual>0) or (signal=='AVOID' and actual<0) or (signal=='HOLD' and abs(actual)<1))
   a,cc=correct(active_signal),correct(candidate_signal);shadow.append((x['id'],a,cc,{'active_signal':active_signal,'candidate_signal':candidate_signal,'actual_return_pct':actual,'horizon_hours':int(x.get('horizon_hours') or 0),'estimated_cost_pct':cost_rate,'active_return_after_costs_pct':self._strategy_return(active_signal,actual,cost_rate),'candidate_return_after_costs_pct':self._strategy_return(candidate_signal,actual,cost_rate)}))
  metrics=self._metrics(shadow);ac=sum(x[1] for x in shadow);cc=sum(x[2] for x in shadow);active_accuracy=ac/n;candidate_accuracy=cc/n;improvement=candidate_accuracy-active_accuracy;low,high=self._wilson(cc,n);status='PENDING' if improvement>=min_improvement else 'REJECTED_GATE'
  with self.db.con() as c:
   cur=c.execute('INSERT INTO learning_candidates(created_at,family,status,base_version,sample_count,active_accuracy,candidate_accuracy,improvement,ci_low,ci_high,parameters_json,reason,decided_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)',(now(),family,status,active['version'],n,str(active_accuracy),str(candidate_accuracy),str(improvement),str(low),str(high),json.dumps(candidate,sort_keys=True),'Paarweiser Schattenvergleich auf identischen Prognosen; keine automatische Aktivierung',now() if status!='PENDING' else None));cid=cur.lastrowid
   c.executemany('INSERT INTO learning_shadow_results(created_at,candidate_id,forecast_id,active_correct,candidate_correct,details_json) VALUES(?,?,?,?,?,?)',[(now(),cid,fid,a,cc,json.dumps(details,sort_keys=True)) for fid,a,cc,details in shadow])
   c.executemany('INSERT INTO learning_candidate_metrics(candidate_id,horizon_hours,sample_count,active_decisions,candidate_decisions,active_coverage,candidate_coverage,active_net_return,candidate_net_return,net_return_improvement,active_max_drawdown,candidate_max_drawdown,details_json) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)',[(cid,m['horizon_hours'],m['sample_count'],m['active_decisions'],m['candidate_decisions'],str(m['active_coverage']),str(m['candidate_coverage']),str(m['active_net_return']),str(m['candidate_net_return']),str(m['net_return_improvement']),str(m['active_max_drawdown']),str(m['candidate_max_drawdown']),json.dumps(m,sort_keys=True)) for m in metrics])
  self.db.audit('CONTROLLED_LEARNING_CANDIDATE',json.dumps({'candidate_id':cid,'family':family,'status':status,'sample_count':n,'improvement':improvement}));return {'status':status,'candidate_id':cid,'sample_count':n,'improvement':improvement,'ci':[low,high],'metrics':metrics}
 def decide(self,candidate_id,action):
  rows=self.db.rows('SELECT * FROM learning_candidates WHERE id=?',(candidate_id,))
  if not rows:return {'status':'NOT_FOUND'}
  p=rows[0]
  if p['status']!='PENDING':return {'status':'NOT_PENDING'}
  current=self.active(p['family'])
  if int(current['version'])!=int(p['base_version']):
   with self.db.con() as c:c.execute("UPDATE learning_candidates SET status='STALE',decided_at=? WHERE id=?",(now(),candidate_id))
   return {'status':'STALE'}
  if action=='reject':
   with self.db.con() as c:c.execute("UPDATE learning_candidates SET status='REJECTED',decided_at=? WHERE id=?",(now(),candidate_id))
   self.db.audit('CONTROLLED_LEARNING_REJECTED',str(candidate_id));return {'status':'REJECTED'}
  if action!='approve':return {'status':'INVALID_ACTION'}
  params=json.loads(p['parameters_json'])
  if set(params)!=set(FAMILIES[p['family']]):return {'status':'INVALID_PARAMETER_SET'}
  for name,value in params.items():
   lo,hi=BOUNDS[p['family']][name]
   if not lo<=float(value)<=hi:return {'status':'OUT_OF_BOUNDS','parameter':name}
  new_version=int(current['version'])+1
  with self.db.con() as c:
   c.execute("UPDATE parameter_family_versions SET status='SUPERSEDED' WHERE family=? AND status='ACTIVE'",(p['family'],));c.execute('INSERT INTO parameter_family_versions(created_at,family,version,status,parameters_json,parent_version,source,reason) VALUES(?,?,?,?,?,?,?,?)',(now(),p['family'],new_version,'ACTIVE',p['parameters_json'],current['version'],f'APPROVED_CANDIDATE_{candidate_id}','Explizite Benutzerfreigabe'));c.execute("UPDATE learning_candidates SET status='APPROVED',decided_at=? WHERE id=?",(now(),candidate_id))
  self.db.audit('CONTROLLED_LEARNING_APPROVED',json.dumps({'candidate_id':candidate_id,'family':p['family'],'version':new_version}));return {'status':'APPROVED','version':new_version}
 def rollback(self,family,target_version):
  target=self.db.rows('SELECT * FROM parameter_family_versions WHERE family=? AND version=?',(family,target_version,));current=self.active(family)
  if not target or not current:return {'status':'NOT_FOUND'}
  next_version=int(current['version'])+1
  with self.db.con() as c:c.execute("UPDATE parameter_family_versions SET status='SUPERSEDED' WHERE family=? AND status='ACTIVE'",(family,));c.execute('INSERT INTO parameter_family_versions(created_at,family,version,status,parameters_json,parent_version,source,reason) VALUES(?,?,?,?,?,?,?,?)',(now(),family,next_version,'ACTIVE',target[0]['parameters_json'],current['version'],f'ROLLBACK_TO_{target_version}','Vollständiger kontrollierter Rollback'))
  self.db.audit('CONTROLLED_LEARNING_ROLLBACK',json.dumps({'family':family,'target_version':target_version,'new_version':next_version}));return {'status':'ROLLED_BACK','version':next_version}
 def candidates(self):return self.db.rows('SELECT * FROM learning_candidates ORDER BY id DESC LIMIT 100')
 def metrics(self,candidate_id=None):
  return self.db.rows('SELECT * FROM learning_candidate_metrics'+(' WHERE candidate_id=?' if candidate_id is not None else '')+' ORDER BY candidate_id DESC,horizon_hours',(candidate_id,) if candidate_id is not None else ())
 def versions(self):return self.db.rows('SELECT * FROM parameter_family_versions ORDER BY family,version DESC')
