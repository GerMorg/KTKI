"""Deterministic portfolio target calculation.

Raw scanner scores are conviction ranks, not probabilities. Targets therefore
use score distance above the buy threshold divided by volatility, then
normalize across candidates and enforce cash/max-position constraints.
"""
from decimal import Decimal
D=lambda x:Decimal(str(x or 0))

def build_targets(candidates,total_eur,cash_reserve_pct=20,max_position_pct=10,buy_threshold=62,min_target_eur=20):
 total=D(total_eur);reserve=max(D(0),min(D(100),D(cash_reserve_pct)))/100;budget=total*(1-reserve);cap=max(D(0),D(max_position_pct))/100;min_eur=D(min_target_eur)
 ranked=[]
 for row in candidates:
  score=D(row.get('score'));vol=max(D('0.25'),abs(D(row.get('volatility_pct') or 0)));cost=D(row.get('roundtrip_cost_pct') or 0);threshold=D(row.get('buy_threshold') or buy_threshold);conv=max(D(0),score-threshold);risk_adjusted=conv/vol
  if score<threshold or risk_adjusted<=0:continue
  ranked.append((risk_adjusted,str(row.get('symbol')),row,cost))
 ranked.sort(reverse=True)
 if not ranked or budget<=0:return []
 weights=[];remaining=budget
 for _,_,row,cost in ranked:
  raw=ranked[ranked.index((_,_,row,cost))][0] if False else D(0)
 # allocate capped normalized risk scores in stable order
 denom=sum(x[0] for x in ranked)
 for risk,_,row,cost in ranked:
  weight=D(risk)/D(denom) if denom else D(0);target=min(budget*weight,budget*cap);weights.append({'symbol':row['symbol'],'score':str(row.get('score')),'volatility_pct':str(row.get('volatility_pct')),'roundtrip_cost_pct':str(cost),'target_weight_pct':str(target/budget*100 if budget else 0),'target_exposure_eur':str(target),'conviction':str(risk)})
 # Iteratively redistribute unused budget among uncapped assets.
 for _ in range(5):
  used=sum(D(x['target_exposure_eur']) for x in weights);left=budget-used
  if left<=min_eur:break
  uncapped=[x for x in weights if D(x['target_exposure_eur'])<budget*cap]
  if not uncapped:break
  denom=sum(D(x['conviction']) for x in uncapped)
  for x in uncapped:
   add=min(left*D(x['conviction'])/denom,budget*cap-D(x['target_exposure_eur'])) if denom else D(0);x['target_exposure_eur']=str(D(x['target_exposure_eur'])+add);x['target_weight_pct']=str(D(x['target_exposure_eur'])/total*100 if total else 0)
 return [x for x in weights if D(x['target_exposure_eur'])>=min_eur]
