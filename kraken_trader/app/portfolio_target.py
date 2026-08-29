"""Deterministic risk-aware portfolio targets.

The scanner score is conviction/ranking, never a probability. Execution costs
are included as a penalty and are re-evaluated again by the execution router.
"""
from decimal import Decimal
D=lambda x:Decimal(str(x or 0))

def build_targets(candidates,total_eur,cash_reserve_pct=20,max_position_pct=10,buy_threshold=62,min_target_eur=20):
 total=D(total_eur);reserve=max(D(0),min(D(100),D(cash_reserve_pct)))/100;budget=total*(1-reserve);cap=max(D(0),D(max_position_pct))/100;minimum=D(min_target_eur)
 ranked=[]
 for row in candidates:
  score=D(row.get('score'));vol=max(D('0.25'),abs(D(row.get('volatility_pct') or 0)));threshold=D(row.get('buy_threshold') or buy_threshold);cost=max(D(0),D(row.get('roundtrip_cost_pct') or 0));conviction=max(D(0),score-threshold)/vol/(D(1)+cost)
  if score>=threshold and conviction>0:ranked.append((conviction,str(row.get('symbol')),row))
 ranked.sort(key=lambda x:(x[0],x[1]),reverse=True)
 if not ranked or budget<=0:return []
 denom=sum(D(x[0]) for x in ranked);targets=[]
 for conviction,symbol,row in ranked:
  raw=budget*D(conviction)/denom if denom else D(0);target=min(raw,budget*cap)
  targets.append({'symbol':symbol,'score':str(row.get('score')),'volatility_pct':str(row.get('volatility_pct')),'roundtrip_cost_pct':str(row.get('roundtrip_cost_pct') or 0),'target_exposure_eur':str(target),'target_weight_pct':str(target/total*100 if total else 0),'conviction':str(conviction)})
 for _ in range(len(targets)+1):
  used=sum(D(x['target_exposure_eur']) for x in targets);left=budget-used;uncapped=[x for x in targets if D(x['target_exposure_eur'])<budget*cap-D('0.00000001')]
  if left<=0 or not uncapped:break
  denom=sum(D(x['conviction']) for x in uncapped);changed=False
  for x in uncapped:
   room=budget*cap-D(x['target_exposure_eur']);add=min(room,left*D(x['conviction'])/denom) if denom else D(0)
   if add>0:x['target_exposure_eur']=str(D(x['target_exposure_eur'])+add);x['target_weight_pct']=str(D(x['target_exposure_eur'])/total*100 if total else 0);changed=True
  if not changed:break
 return [x for x in targets if D(x['target_exposure_eur'])>=minimum]
