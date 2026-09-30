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
  equity=peak=100.0;worst=0.0
  for value in values:
   equity+=float(value)
   peak=max(peak,equity)
   if peak>0:worst=min(worst,(equity-peak)/peak)
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
  pnls=[];up_raw=[];up_net=[];down_raw=[];down_net=[];hits=0;directional=0
  for r in rows:
   try:features=json.loads(r.get('features_json') or '{}')
   except Exception:features={}
   cost=float(features.get('estimated_roundtrip_cost_pct') or 0)
   actual=float(r.get('actual_return_pct') or 0)
   direction=str(r.get('direction') or 'FLAT').upper()
   pnl=self._direction_pnl(direction,actual,cost)
   pnls.append(pnl)
   if direction=='UP':
    up_raw.append(actual);up_net.append(pnl);directional+=1;hits+=int(pnl>0)
   elif direction=='DOWN':
    down_raw.append(-actual);down_net.append(pnl);directional+=1;hits+=int(pnl>0)
  n=len(pnls);mean_edge=sum(pnls)/n if n else None
  ordered=sorted(pnls);median=ordered[n//2] if n and n%2 else ((ordered[n//2-1]+ordered[n//2])/2 if n else None)
  worst=min(pnls) if pnls else None
  dd=self._drawdown(pnls) if pnls else None
  return {
   'samples':n,'directional_samples':directional,
   'hit_rate':hits/directional if directional else None,
   'model_net_return_pct':sum(pnls),
   'mean_edge_after_costs_pct':mean_edge,
   'median_edge_after_costs_pct':median,
   'worst_sample_pct':worst,
   'no_position_return_pct':0.0,
   'buy_hold_return_sum_pct':sum(float(r.get('actual_return_pct') or 0) for r in rows),
   'excess_vs_no_position_pct':mean_edge,
   'expected_up_edge_raw_pct':sum(up_raw)/len(up_raw) if up_raw else None,
   'expected_up_edge_after_costs_pct':sum(up_net)/len(up_net) if up_net else None,
   'expected_down_edge_raw_pct':sum(down_raw)/len(down_raw) if down_raw else None,
   'expected_down_edge_after_costs_pct':sum(down_net)/len(down_net) if down_net else None,
   'max_drawdown_pct':dd,
   'forecast_sequence_drawdown_pct':dd,
   'drawdown_semantics':'FORECAST_SAMPLE_SEQUENCE_ONLY; NOT PORTFOLIO_EQUITY',
  }
 def margin_calibration(self,family,direction,horizon=24,min_samples=20,max_drawdown_pct=-25.0):
  direction=str(direction).upper();rows=self._rows(family,horizon,direction);pnls=[]
  for r in rows:
   try:f=json.loads(r.get('features_json') or '{}')
   except Exception:f={}
   actual=float(r.get('actual_return_pct') or 0);cost=float(f.get('estimated_roundtrip_cost_pct') or 0);pnls.append(self._direction_pnl(direction,actual,cost))
  samples=len(pnls);wins=sum(int(x>0) for x in pnls);net=sum(pnls);mean_edge=net/samples if samples else None;worst=min(pnls) if pnls else None;dd=self._drawdown(pnls) if pnls else None
  ready=samples>=int(min_samples) and mean_edge is not None and mean_edge>0 and (worst is None or worst>=float(max_drawdown_pct))
  reason='READY' if ready else ('INSUFFICIENT_SAMPLES' if samples<int(min_samples) else ('NON_POSITIVE_MEAN_EDGE' if mean_edge is None or mean_edge<=0 else 'WORST_SAMPLE_LIMIT'))
  return {'family':family,'direction':direction,'horizon_hours':int(horizon),'samples':samples,'wins':wins,'win_rate':wins/samples if samples else None,'net_return_pct':net,'mean_edge_after_costs_pct':mean_edge,'worst_sample_pct':worst,'max_drawdown_pct':dd,'required_samples':int(min_samples),'required_net_return_pct':0.0,'required_max_drawdown_pct':float(max_drawdown_pct),'status':'READY' if ready else 'NOT_READY','reason':reason}
 def _direction_quality(self,item,min_samples):
  samples=float(item.get('samples') or 0);win=float(item.get('win_rate') or 0);edge=float(item.get('mean_edge_after_costs_pct') or 0)
  sample_score=min(1.0,samples/max(1,min_samples));win_score=max(0.0,min(1.0,win));edge_score=max(0.0,min(1.0,0.5+edge/4.0))
  return round(100*(0.25*sample_score+0.45*win_score+0.30*edge_score),4)

 def evaluate(self,family,min_samples=20,min_net_return_pct=0.0,max_drawdown_pct=-25.0,require_long_horizon=True):
  try:max_drawdown_pct=float(max_drawdown_pct)
  except (TypeError,ValueError):max_drawdown_pct=-25.0
  details={'family':family,'samples':0,'horizons':{},'gates':[],'execution_gate':'H24_ONLY','long_horizon_required':False}
  for horizon in self.REQUIRED_HORIZONS:
   rows=self._rows(family,horizon);m=self._metrics(rows);details['horizons'][str(horizon)]=m
   mean=m['mean_edge_after_costs_pct']
   details['gates'] += [
    {'name':f'H{horizon}_SAMPLES','passed':m['samples']>=min_samples,'actual':m['samples'],'required':min_samples},
    {'name':f'H{horizon}_MEAN_EDGE','passed':mean is not None and mean>=min_net_return_pct,'actual':mean,'required':min_net_return_pct},
    {'name':f'H{horizon}_DRAWDOWN','passed':m['max_drawdown_pct'] is None or m['max_drawdown_pct']>=max_drawdown_pct,'actual':m['max_drawdown_pct'],'required':max_drawdown_pct},
   ]
  h24=details['horizons']['24'];details['samples']=h24['samples']
  up=self.margin_calibration(family,'UP',24,min_samples,max_drawdown_pct);down=self.margin_calibration(family,'DOWN',24,min_samples,max_drawdown_pct)
  # Preserve the historical round-trip cost used to produce the edge. This allows
  # the decision engine to convert net historical edge back to gross and subtract
  # the current route cost exactly once.
  for item in (up,down):
   rows=self._rows(family,24,item['direction']);costs=[]
   for r in rows:
    try:f=json.loads(r.get('features_json') or '{}');costs.append(float(f.get('estimated_roundtrip_cost_pct') or 0))
    except Exception:pass
   item['historical_roundtrip_cost_pct']=sum(costs)/len(costs) if costs else 0.0
  details['directions']={'UP':up,'DOWN':down}
  details['quality_score_by_direction']={'UP':self._direction_quality(up,min_samples),'DOWN':self._direction_quality(down,min_samples)}
  up_evidence=up['status']=='READY'
  evidence=up_evidence
  risk_state='OK'
  if h24['max_drawdown_pct'] is not None and h24['max_drawdown_pct']<max_drawdown_pct:risk_state='CAUTION'
  if h24['samples']<min_samples:risk_state='INSUFFICIENT_DATA'
  if h24['mean_edge_after_costs_pct'] is not None and h24['mean_edge_after_costs_pct']<=min_net_return_pct and h24['samples']>=min_samples:risk_state='WEAK'
  sample_factor=min(1.0,h24['samples']/max(1,min_samples))
  edge_factor=max(0.0,min(1.0,0.5+(float(h24['mean_edge_after_costs_pct'] or 0)/2.0)))
  hit_factor=float(h24['hit_rate'] or 0.5)
  quality=100*(0.25*sample_factor+0.45*edge_factor+0.30*hit_factor)
  if risk_state=='INSUFFICIENT_DATA':quality=max(50.0,quality)
  details['quality_score']=round(quality,4);details['risk_state']=risk_state
  details['gates'].append({'name':'POSITIVE_MEAN_EDGE','passed':evidence,'actual':h24['mean_edge_after_costs_pct'],'required':f'>= {min_net_return_pct}'})
  h168gates=[g for g in details['gates'] if g['name'].startswith('H168_')]
  details['h168_advisory_ready']=h24['samples']>=min_samples and all(g['passed'] for g in h168gates)
  details['h168_advisory_reason']='READY' if details['h168_advisory_ready'] else f"H168 advisory: {details['horizons']['168']['samples']}/{min_samples} Samples bzw. Validierung offen"
  status='READY' if evidence else ('INSUFFICIENT_DATA' if up['samples']<min_samples else 'WEAK')
  details['status']=status;details['score']=details['quality_score']
  with self.db.con() as c:c.execute('INSERT INTO model_health_snapshots(created_at,family,status,score,details_json) VALUES(?,?,?,?,?)',(now(),family,status,str(details['quality_score']),json.dumps(details,sort_keys=True)))
  return details
 def expected_edge_pct(self,family,horizon=24,after_costs=False):
  h=self.evaluate(family,require_long_horizon=False);item=h['horizons'].get(str(horizon),{});return item.get('expected_up_edge_after_costs_pct' if after_costs else 'expected_up_edge_raw_pct')
 def all_ready(self,families):
  result={f:self.evaluate(f,require_long_horizon=False) for f in families};return bool(result) and all(x['status']=='READY' for x in result.values()),result
