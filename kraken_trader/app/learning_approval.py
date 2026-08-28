import json
from db import now
PARAMETERS={
'xstocks_base_score':(50.,40.,60.),'xstocks_momentum_weight':(4.,2.,6.),'xstocks_trend_weight':(10.,6.,14.),'xstocks_volatility_penalty':(1.2,.6,2.),'xstocks_spread_penalty':(18.,10.,28.),'xstocks_buy_threshold':(62.,55.,75.),'xstocks_buy_max_spread_pct':(1.2,.4,2.),'xstocks_avoid_threshold':(32.,20.,45.),'xstocks_avoid_spread_pct':(2.5,1.,4.)}
LABELS={'xstocks_base_score':'Basiswert','xstocks_momentum_weight':'Momentum-Gewicht','xstocks_trend_weight':'Trend-Gewicht','xstocks_volatility_penalty':'VolatilitÃ¤tsabzug','xstocks_spread_penalty':'Spread-Abzug','xstocks_buy_threshold':'BUY-Schwelle','xstocks_buy_max_spread_pct':'Maximaler BUY-Spread %','xstocks_avoid_threshold':'AVOID-Schwelle','xstocks_avoid_spread_pct':'AVOID-Spread %'}
class LearningApproval:
 def __init__(self,db):self.db=db;self.ensure()
 def ensure(self):
  with self.db.con() as c:
   c.executescript("CREATE TABLE IF NOT EXISTS strategy_parameters(name TEXT PRIMARY KEY,value TEXT NOT NULL,version INTEGER NOT NULL,updated_at TEXT NOT NULL,source TEXT NOT NULL);CREATE TABLE IF NOT EXISTS learning_proposals(id INTEGER PRIMARY KEY AUTOINCREMENT,created_at TEXT NOT NULL,status TEXT NOT NULL,base_version INTEGER NOT NULL,sample_count INTEGER NOT NULL,accuracy TEXT,parameters_json TEXT NOT NULL,reason TEXT NOT NULL,approved_at TEXT);")
   for name,(default,_,_) in PARAMETERS.items():c.execute('INSERT OR IGNORE INTO strategy_parameters VALUES(?,?,1,?,?)',(name,str(default),now(),'DEFAULT'))
 def values(self):return {x['name']:float(x['value']) for x in self.db.rows('SELECT * FROM strategy_parameters')}
 def rows(self):
  current=self.values();latest=self.latest();proposed=json.loads(latest['parameters_json']) if latest and latest['status']=='PENDING' else {}
  return [{'name':n,'label':LABELS[n],'current':current[n],'proposed':proposed.get(n),'minimum':lo,'maximum':hi} for n,(_,lo,hi) in PARAMETERS.items()]
 def latest(self):
  r=self.db.rows('SELECT * FROM learning_proposals ORDER BY id DESC LIMIT 1');return r[0] if r else None
 def create_proposal(self):
  rows=self.db.rows("SELECT e.direction_correct,e.actual_return_pct FROM forecast_evaluations e JOIN research_forecasts f ON f.id=e.forecast_id JOIN market_universe u ON u.symbol=f.symbol WHERE u.category='xstocks'")
  if len(rows)<5:return {'status':'INSUFFICIENT_DATA','sample_count':len(rows),'required':5}
  accuracy=sum(int(x['direction_correct']) for x in rows)/len(rows);avg_return=sum(float(x['actual_return_pct']) for x in rows)/len(rows);direction=1 if accuracy>=.6 and avg_return>=0 else -1;current=self.values()
  steps={'xstocks_base_score':.5,'xstocks_momentum_weight':.2,'xstocks_trend_weight':.5,'xstocks_volatility_penalty':-.05,'xstocks_spread_penalty':-.5,'xstocks_buy_threshold':-.5,'xstocks_buy_max_spread_pct':.05,'xstocks_avoid_threshold':-.5,'xstocks_avoid_spread_pct':.1};proposed={}
  for name,(_,lo,hi) in PARAMETERS.items():proposed[name]=round(max(lo,min(hi,current[name]+steps[name]*direction)),4)
  version=max((x['version'] for x in self.db.rows('SELECT version FROM strategy_parameters')),default=1)
  with self.db.con() as c:c.execute("UPDATE learning_proposals SET status='SUPERSEDED' WHERE status='PENDING'");c.execute('INSERT INTO learning_proposals(created_at,status,base_version,sample_count,accuracy,parameters_json,reason,approved_at) VALUES(?,?,?,?,?,?,?,NULL)',(now(),'PENDING',version,len(rows),str(accuracy),json.dumps(proposed,sort_keys=True),'Begrenzter Kandidat aus ausgewerteten xStock-Prognosen'))
  self.db.audit('LEARNING_PROPOSAL_CREATED',json.dumps({'sample_count':len(rows),'accuracy':accuracy}));return {'status':'PENDING','sample_count':len(rows),'accuracy':accuracy}
 def approve_latest(self):
  p=self.latest()
  if not p or p['status']!='PENDING':return {'status':'NOTHING_TO_APPROVE'}
  params=json.loads(p['parameters_json']);new_version=int(p['base_version'])+1
  if set(params)!=set(PARAMETERS):return {'status':'INVALID_PARAMETER_SET'}
  for name,value in params.items():
   _,lo,hi=PARAMETERS[name]
   if not lo<=float(value)<=hi:return {'status':'OUT_OF_BOUNDS','parameter':name}
  with self.db.con() as c:
   for name,value in params.items():c.execute('UPDATE strategy_parameters SET value=?,version=?,updated_at=?,source=? WHERE name=?',(str(value),new_version,now(),f'APPROVED_PROPOSAL_{p["id"]}',name))
   c.execute("UPDATE learning_proposals SET status='APPROVED',approved_at=? WHERE id=?",(now(),p['id']))
  self.db.audit('LEARNING_PROPOSAL_APPROVED',json.dumps({'proposal_id':p['id'],'version':new_version,'parameter_count':9}));return {'status':'APPROVED','version':new_version,'parameter_count':9}


