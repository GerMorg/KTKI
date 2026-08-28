from decimal import Decimal
import json
D=lambda x:Decimal(str(x or 0))
class PortfolioAllocator:
 def __init__(self,db):self.db=db
 def plans(self,total):
  total=D(total);maxpct=D(self.db.value('paper_max_position_pct','10'))/100;minpct=D(self.db.value('paper_min_position_pct','2'))/100;out=[]
  rows=self.db.rows("SELECT w.symbol,w.category,s.score,s.volatility_pct,s.signal,s.quality FROM research_watchlist w JOIN scanner_results s ON s.symbol=w.symbol WHERE w.status='ANALYZED' AND s.quality='VALID' AND s.signal='BUY' ORDER BY CAST(s.score AS REAL) DESC")
  for row in rows:
   confidence=max(D(0),min(D(1),D(row['score'])/100));target_pct=min(maxpct,max(minpct,maxpct*confidence));lev=1
   if self.db.value('paper_leverage_enabled','false')=='true':
    market=self.db.rows('SELECT leverage_buy_json FROM market_universe WHERE symbol=? LIMIT 1',(row['symbol'],))
    if market:
     allowed=[int(x) for x in json.loads(market[0]['leverage_buy_json'] or '[]') if int(x)<=int(float(self.db.value('paper_max_leverage','3')))]
     if allowed:lev=max(allowed)
   out.append({'symbol':row['symbol'],'category':row['category'],'confidence':str(confidence),'target_pct':str(target_pct*100),'target_exposure_eur':str(total*target_pct),'leverage':lev,'scanner_signal':row['signal']})
  return out


