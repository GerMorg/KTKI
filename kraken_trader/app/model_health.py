"""Directional model quality and calibration for autonomous execution.

v93 treats health as evidence used for sizing and leverage, not as a global
entry prohibition. H24 is the operational horizon; H168 is validation/advisory.
"""
import json
from db import now

class ModelHealth:
 REQUIRED_HORIZONS=(24,168)
 def __init__(self,db):self.db=db;self.ensure()
 def ensure(self):
  with self.db.con() as c:c.execute("CREATE TABLE IF NOT EXISTS model_health_snapshots(id INTEGER PRIMARY KEY AUTOINCREMENT,created_at TEXT NOT NULL,family TEXT NOT NULL,status TEXT NOT NULL,score TEXT NOT NULL,details_json TEXT NOT NULL)")
 @staticmethod
 def _drawdown(values):
  # Forecast samples are not sequential invested returns. Use additive P&L,
  # matching model_net_return, rather than compounding independent forecasts.
  equity=peak=0.0;worst=0.0
  for value in values:
   equity+=float(value)
   peak=max(peak,equity)
   if peak>0:worst=min(worst,(equity-peak)/max(1.0,abs(peak)))
  return worst*100
 @staticmethod
 def _direction_pnl(direction,actual,cost):
  direction=str(direction or 'FLAT').upper()
  if direction=='UP':return actual-cost
  if direction=='DOWN':return -actual-cost
  return 0.0
 def _rows(self,family,horizon=None,direction=None):
  q="SELECT f.horizon_hours,f.direction,f.features_json,e.actual_return_pct,e.direction_correct FROM research_forecasts f JOIN forecast_evaluations e ON e.forecast_id=f.id WHERE f.family=?"
  args=[family]
  if horizon is not None:q+=" AND f.horizon_hours=?";args.append(int(horizon))
  if direction is not None:q+=" AND f.direction=?";args.append(str(direction).upper())
  q+=" ORDER BY f.id"
  try:return self.db.rows(q,tuple(args))
  except Exception:return []
 def _metrics(self,rows):
  pnls=[];raw=[];hits=0
  for r in rows:
   try:features=json.loads(r.get('features_json') or '{}')
   except Exception:features={}
   cost=float(features.get('estimated_roundtrip_cost_pct') or 0)
   actual=float(r.get('actual_return_pct') or 0)
   direction=str(r.get('direction') or 'FLAT').upper()
   pnl=self._direction_pnl(direction,actual,cost)
   pnls.append(pnl)
   if direction=='UP':raw.append(actual)
   if direction in ('UP','DOWN'):hits+=int(pnl>0)
  n=len(pnls);net=sum(pnls);dd=self._drawdown(pnls) if pnls else None
  return {'samples':n,'hit_rate':hits/n if n else None,'model_net_return_pct':net,'no_position_return_pct':0.0,'buy_hold_return_sum_pct':sum(float(r.get('actual_return_pct') or 0) for r in rows),'excess_vs_no_position_pct':net,'expected_up_edge_raw_pct':sum(raw)/len(raw) if raw else None,'expected_up_edge_after_costs_pct':(sum(self._direction_pnl('UP',float(r.get('actual_return_pct') or 0),float((json.loads(r.get('features_json') or '{}')).get('estimated_roundtrip_cost_pct') or 0)) for r in rows if str(r.get('direction')).upper()=='UP')/len(raw) if raw else None),'max_drawdown_pct':dd}
 def margin_calibration(self,family,direction,horizon=24,min_samples=20,max_drawdown_pct=-25.0):
  direction=str(direction).upper();rows=self._rows(family,horizon,direction);pnls=[]
  for r in rows:
   try:f=json.loads(r.get('features_json') or '{}')
   except Exception:f={}
   actual=float(r.get('actual_return_pct') or 0);cost=float(f.get('estimated_roundtrip_cost_pct') or 0);pnls.append(self._direction_pnl(direction,actual,cost))
  dd=self._drawdown(pnls) if pnls else None;samples=len(pnls);wins=sum(int(x>0) for x in pnls);net=sum(pnls)
  ready=samples>=int(min_samples) and net>0 and (dd is None or dd>=float(max_drawdown_pct))
  return {'family':family,'direction':direction,'horizon_hours':int(horizon),'samples':samples,'wins':wins,'win_rate':wins/samples if samples else None,'net_return_pct':net,'max_drawdown_pct':dd,'required_samples':int(min_samples),'required_net_return_pct':0.0,'required_max_drawdown_pct':float(max_drawdown_pct),'status':'READY' if ready else 'NOT_READY','reason':'READY' if ready else ('INSUFFICIENT_SAMPLES' if samples<int(min_samples) else ('NEGATIVE_NET_RETURN' if net<=0 else 'DRAWDOWN_LIMIT'))}
 def evaluate(self,family,min_samples=20,min_net_return_pct=0.0,max_drawdown_pct=-25.0,require_long_horizon=True):
  try:max_drawdown_pct=float(max_drawdown_pct)
  except (TypeError,ValueError):max_drawdown_pct=-25.0
  details={'family':family,'samples':0,'horizons':{},'gates':[],'execution_gate':'H24_ONLY','long_horizon_required':False}
  for horizon in self.REQUIRED_HORIZONS:
   rows=self._rows(family,horizon);m=self._metrics(rows);details['horizons'][str(horizon)]=m;details['gates'] += [
    {'name':f'H{horizon}_SAMPLES','passed':m['samples']>=min_samples,'actual':m['samples'],'required':min_samples},
    {'name':f'H{horizon}_NET_RETURN','passed':m['model_net_return_pct']>=min_net_return_pct,'actual':m['model_net_return_pct'],'required':min_net_return_pct},
    {'name':f'H{horizon}_DRAWDOWN','passed':m['max_drawdown_pct'] is None or m['max_drawdown_pct']>=max_drawdown_pct,'actual':m['max_drawdown_pct'],'required':max_drawdown_pct},
   ]
  h24=details['horizons']['24'];details['samples']=h24['samples']
  up=self.margin_calibration(family,'UP',24,min_samples,max_drawdown_pct)
  down=self.margin_calibration(family,'DOWN',24,min_samples,max_drawdown_pct)
  details['directions']={'UP':up,'DOWN':down}
  evidence=(h24['model_net_return_pct']>0 and h24['samples']>=min_samples)
  risk_state='OK'
  if h24['max_drawdown_pct'] is not None and h24['max_drawdown_pct']<max_drawdown_pct:risk_state='CAUTION'
  if h24['samples']<min_samples:risk_state='INSUFFICIENT_DATA'
  if h24['model_net_return_pct']<=min_net_return_pct and h24['samples']>=min_samples:risk_state='WEAK'
  # Quality is continuous and used by confidence/target sizing.
  sample_factor=min(1.0,h24['samples']/max(1,min_samples))
  net_factor=max(0.0,min(1.0,0.5+h24['model_net_return_pct']/100))
  dd_factor=1.0 if h24['max_drawdown_pct'] is None else max(0.0,min(1.0,(h24['max_drawdown_pct']-max_drawdown_pct)/max(1.0,abs(max_drawdown_pct))))
  quality=100*(0.25*sample_factor+0.45*net_factor+0.30*dd_factor)
  if risk_state=='INSUFFICIENT_DATA':quality=max(50.0,quality)
  details['quality_score']=round(quality,4);details['risk_state']=risk_state
  details['gates'].append({'name':'POSITIVE_VS_NO_POSITION','passed':evidence,'actual':h24['excess_vs_no_position_pct'],'required':'> 0'})
  details['h168_advisory_ready']=h24['samples']>=min_samples and all(g['passed'] for g in details['gates'] if g['name'].startswith('H168_'))
  details['h168_advisory_reason']='READY' if details['h168_advisory_ready'] else f"H168 advisory: {details['horizons']['168']['samples']}/{min_samples} Samples bzw. Validierung offen"
  # Status describes evidence quality, never an autonomous entry gate.
  status='READY' if evidence else ('INSUFFICIENT_DATA' if h24['samples']<min_samples else 'WEAK')
  details['status']=status;details['score']=details['quality_score']
  with self.db.con() as c:c.execute('INSERT INTO model_health_snapshots(created_at,family,status,score,details_json) VALUES(?,?,?,?,?)',(now(),family,status,str(details['quality_score']),json.dumps(details,sort_keys=True)))
  return details
 def expected_edge_pct(self,family,horizon=24,after_costs=False):
  h=self.evaluate(family,require_long_horizon=False);item=h['horizons'].get(str(horizon),{});return item.get('expected_up_edge_after_costs_pct' if after_costs else 'expected_up_edge_raw_pct')
 def all_ready(self,families):
  result={f:self.evaluate(f,require_long_horizon=False) for f in families};return bool(result) and all(x['status']=='READY' for x in result.values()),result
