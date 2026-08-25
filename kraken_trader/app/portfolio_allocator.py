import json
from decimal import Decimal
D=lambda x:Decimal(str(x or 0))
class PortfolioAllocator:
 def __init__(self,db):self.db=db
 def _leverage(self,symbol,confidence):
  if self.db.value('paper_leverage_enabled','false')!='true':return 1
  rows=self.db.rows('SELECT leverage_buy_json FROM market_universe WHERE symbol=? LIMIT 1',(symbol,));available=[]
  if rows:
   try:available=sorted({int(x) for x in json.loads(rows[0]['leverage_buy_json'] or '[]')})
   except Exception:available=[]
  cap=max(1,int(float(self.db.value('paper_max_leverage','3'))));permitted=[x for x in available if 1<=x<=cap]
  return max(permitted or [1]) if confidence>=D('.8') else max([x for x in permitted if x<=2] or [1])
 def plans(self,total):
  total=D(total);mn=D(self.db.value('paper_min_position_pct','2'))/100;mx=D(self.db.value('paper_max_position_pct','10'))/100;out=[]
  rows=self.db.rows("SELECT w.symbol,s.score,s.volatility_pct FROM research_watchlist w JOIN scanner_results s ON s.symbol=w.symbol WHERE w.status='ANALYZED' AND s.quality='VALID'")
  for x in rows:
   confidence=max(D(0),min(D(1),D(x['score'])/100/(1+D(x.get('volatility_pct'))/10)));target=max(mn,min(mx,confidence*mx));out.append({'symbol':x['symbol'],'confidence':str(confidence),'target_pct':str(target*100),'target_exposure_eur':str(total*target),'leverage':self._leverage(x['symbol'],confidence)})
  return out
