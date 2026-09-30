"""Market regime inference used by v93 execution and portfolio sizing."""
from decimal import Decimal
D=lambda x:Decimal(str(x or 0))

def candidate_regime(momentum,trend):
    m=D(momentum);t=D(trend)
    if m>0 and t>0:return 'BULL'
    if m<0 and t<0:return 'BEAR'
    return 'MIXED'

def family_regime(db,family):
    try:rows=db.rows("SELECT signal,momentum_pct,trend_pct FROM scanner_results s JOIN market_universe u ON u.symbol=s.symbol WHERE s.quality='VALID' AND u.category=?",(family,))
    except Exception:rows=[]
    if not rows:return {'regime':'NEUTRAL','breadth':0,'avg_momentum_pct':0,'avg_trend_pct':0,'samples':0}
    buys=sum(1 for r in rows if str(r.get('signal')).upper()=='BUY')
    avoids=sum(1 for r in rows if str(r.get('signal')).upper()=='AVOID')
    n=buys+avoids
    breadth=buys/n if n else .5
    avg_m=sum(D(r.get('momentum_pct')) for r in rows)/D(len(rows))
    avg_t=sum(D(r.get('trend_pct')) for r in rows)/D(len(rows))
    if breadth>=D('.60') and avg_m>0 and avg_t>0:regime='BULL'
    elif breadth<=D('.40') and avg_m<0 and avg_t<0:regime='BEAR'
    elif avg_m>0 and avg_t>0:regime='BULL'
    elif avg_m<0 and avg_t<0:regime='BEAR'
    else:regime='NEUTRAL'
    return {'regime':regime,'breadth':float(breadth),'avg_momentum_pct':float(avg_m),'avg_trend_pct':float(avg_t),'samples':len(rows)}
