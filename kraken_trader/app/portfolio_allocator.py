import json
from decimal import Decimal
D=lambda x:Decimal(str(x or 0))
class PortfolioAllocator:
 def __init__(self,db):self.db=db
 def market(self,symbol):
  r=self.db.rows('SELECT * FROM market_universe WHERE symbol=? ORDER BY asset_class DESC LIMIT 1',(symbol,));return r[0] if r else {}
 def confidence(self,scan):
  if not scan or scan.get('quality')!='VALID':return D(0)
  score=D(scan.get('score'))/100
  vol=D(scan.get('volatility_pct'));spread=D(scan.get('spread_pct'))
  penalty=min(D('.35'),vol/100)+min(D('.20'),spread/5)
  return max(D(0),min(D(1),score-penalty))
 def leverage(self,symbol,confidence):
  if self.db.value('paper_leverage_enabled','false')!='true':return 1
  try:levels=sorted({int(x) for x in json.loads(self.market(symbol).get('leverage_buy_json') or '[]') if int(x)>=1})
  except Exception:levels=[]
  cap=int(D(self.db.value('paper_max_leverage','3')))
  allowed=[x for x in levels if x<=cap]
  if confidence<D('.72') or not allowed:return 1
  desired=2 if confidence<D('.86') else (3 if confidence<D('.94') else cap)
  return max([1]+[x for x in allowed if x<=desired])
 def target(self,symbol,scan,total):
  conf=self.confidence(scan);vol=max(D('.5'),D((scan or {}).get('volatility_pct')))
  floor=D(self.db.value('paper_min_position_pct','2'))/100;cap=D(self.db.value('paper_max_position_pct','10'))/100
  raw=(conf*conf)/(D(1)+vol/10);pct=min(cap,max(D(0),raw*cap*D('1.8')))
  if pct<floor:pct=D(0)
  lev=self.leverage(symbol,conf)
  return {'symbol':symbol,'confidence':str(conf),'target_pct':str(pct),'target_exposure_eur':str(total*pct),'leverage':lev,'volatility_pct':str(vol)}
 def plans(self,total):
  rows=self.db.rows("SELECT w.symbol,s.* FROM research_watchlist w JOIN scanner_results s ON s.symbol=w.symbol WHERE w.status='ANALYZED' AND s.quality='VALID' ORDER BY CAST(s.score AS REAL) DESC")
  return [self.target(x['symbol'],x,total) for x in rows]
