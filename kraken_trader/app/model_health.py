"""Model-health and expected-edge checks used before autonomous execution."""
import json
from db import now

class ModelHealth:
 REQUIRED_HORIZONS=(24,168)
 def __init__(self,db):self.db=db;self.ensure()
 def ensure(self):
  with self.db.con() as c:c.execute("CREATE TABLE IF NOT EXISTS model_health_snapshots(id INTEGER PRIMARY KEY AUTOINCREMENT,created_at TEXT NOT NULL,family TEXT NOT NULL,status TEXT NOT NULL,score TEXT NOT NULL,details_json TEXT NOT NULL)")
 @staticmethod
 def _drawdown(values):
  equity=peak=1.0;worst=0.0
  for value in values:
   equity*=max(1e-9,1+float(value)/100);peak=max(peak,equity);worst=min(worst,equity/peak-1)
  return worst*100
 def evaluate(self,family,min_samples=20,min_net_return_pct=0.0,max_drawdown_pct=-25.0):
  rows=self.db.rows("SELECT f.horizon_hours,f.direction,f.features_json,e.actual_return_pct,e.direction_correct FROM research_forecasts f JOIN forecast_evaluations e ON e.forecast_id=f.id WHERE f.family=? ORDER BY f.id",(family,))
  details={'family':family,'samples':len(rows),'horizons':{},'gates':[]}
  for horizon in self.REQUIRED_HORIZONS:
   subset=[r for r in rows if int(r['horizon_hours'])==horizon];cost_adjusted=[];up_edges=[]
   for r in subset:
    try:features=json.loads(r.get('features_json') or '{}')
    except Exception:features={}
    cost=float(features.get('estimated_roundtrip_cost_pct') or 0);direction=str(r.get('direction') or 'FLAT');actual=float(r.get('actual_return_pct') or 0);strategy=actual-cost if direction=='UP' else 0.0;cost_adjusted.append(strategy)
    if direction=='UP':up_edges.append(strategy)
   hit=sum(int(r['direction_correct']) for r in subset);n=len(subset);model_net=sum(cost_adjusted);buy_hold=sum(float(r['actual_return_pct'] or 0) for r in subset);dd=self._drawdown(cost_adjusted) if cost_adjusted else None;expected=sum(up_edges)/len(up_edges) if up_edges else None
   details['horizons'][str(horizon)]={'samples':n,'hit_rate':hit/n if n else None,'model_net_return_pct':model_net,'no_position_return_pct':0.0,'buy_hold_return_sum_pct':buy_hold,'excess_vs_no_position_pct':model_net,'expected_up_edge_after_costs_pct':expected,'max_drawdown_pct':dd}
   details['gates'] += [{'name':f'H{horizon}_SAMPLES','passed':n>=min_samples,'actual':n,'required':min_samples},{'name':f'H{horizon}_NET_RETURN','passed':model_net>=min_net_return_pct,'actual':model_net,'required':min_net_return_pct},{'name':f'H{horizon}_DRAWDOWN','passed':dd is None or dd>=max_drawdown_pct,'actual':dd,'required':max_drawdown_pct}]
  hard=all(g['passed'] for g in details['gates']);horizons=[x for x in details['horizons'].values() if x['samples']];benchmark_ok=bool(horizons) and any(x['excess_vs_no_position_pct']>0 for x in horizons)
  details['gates'].append({'name':'POSITIVE_VS_NO_POSITION','passed':benchmark_ok,'actual':max((x['excess_vs_no_position_pct'] for x in horizons),default=None),'required':'> 0'})
  status='READY' if hard and benchmark_ok else 'NOT_READY';score=100.0 if status=='READY' else max(0.0,min(100.0,sum(1 for g in details['gates'] if g['passed'])/max(1,len(details['gates']))*100))
  with self.db.con() as c:c.execute('INSERT INTO model_health_snapshots(created_at,family,status,score,details_json) VALUES(?,?,?,?,?)',(now(),family,status,str(score),json.dumps(details,sort_keys=True)))
  return {'status':status,'score':score,**details}
 def expected_edge_pct(self,family,horizon=24):
  health=self.evaluate(family);item=health['horizons'].get(str(horizon),{});return item.get('expected_up_edge_after_costs_pct')
 def all_ready(self,families):
  result={family:self.evaluate(family) for family in families};return bool(result) and all(x['status']=='READY' for x in result.values()),result
