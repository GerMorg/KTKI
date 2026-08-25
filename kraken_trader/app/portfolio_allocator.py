import json
from decimal import Decimal
D=lambda x:Decimal(str(x or 0))
class PortfolioAllocator:
 def __init__(self,db):self.db=db
 def _leverage(self,symbol,confidence):
  if self.db.value('paper_leverage_enabled','false')!='true':return 1
  row=self.db.rows('SELECT leverage_buy_json FROM market_universe WHERE symbol=? LIMIT 1',(symbol,));available=[]
  if row:
   try:available=sorted({int(x) for x in json.loads(row[0]['leverage_buy_json'] or '[]') if int(x)>=1})
   except Exception:available=[]
  cap=max(1,int(float(self.db.value('paper_max_leverage','3'))));permitted=[x for x in available if x<=cap]
  if not permitted:return 1
  target=1 if confidence<D('.65') else (2 if confidence<D('.8') else cap)
  return max([x for x in permitted if x<=target] or [1])
 def plans(self,total_equity):
  total=D(total_equity);minpct=D(self.db.value('paper_min_position_pct','2'))/100;maxpct=D(self.db.value('paper_max_position_pct','10'))/100
  rows=self.db.rows("""SELECT w.symbol,w.prefilter_score,s.score,s.volatility_pct,s.quality FROM research_watchlist w JOIN scanner_results s ON s.symbol=w.symbol WHERE w.status='ANALYZED' AND s.quality='VALID' ORDER BY CAST(s.score AS REAL) DESC""");raw=[]
  for x in rows:
   score=max(D(0),min(D(100),D(x['score'])))/100;vol=max(D(0),D(x.get('volatility_pct')));risk=D(1)/(D(1)+vol/10);confidence=score*risk
   if confidence<=0:continue
   raw.append((x,confidence))
  denom=sum((c for _,c in raw),D(0));out=[]
  for x,confidence in raw:
   share=confidence/denom if denom else D(0);target=max(minpct,min(maxpct,share));lev=self._leverage(x['symbol'],confidence);exposure=total*target
   out.append({'symbol':x['symbol'],'confidence':str(confidence),'target_pct':str(target*100),'target_exposure_eur':str(exposure),'leverage':lev,'scanner_score':x['score'],'volatility_pct':x.get('volatility_pct')})
  return out
