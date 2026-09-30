"""Shared family-level market regime inference for v95."""
from datetime import datetime, timezone, timedelta
from decimal import Decimal
D=lambda x:Decimal(str(x or 0))

def candidate_regime(momentum,trend):
    m=D(momentum); t=D(trend)
    if m>0 and t>0:return 'BULL'
    if m<0 and t<0:return 'BEAR'
    return 'MIXED'

def family_regime(db,family,max_age_minutes=120):
    cutoff=(datetime.now(timezone.utc)-timedelta(minutes=float(max_age_minutes))).isoformat()
    try:
        rows=db.rows(
            """SELECT signal,momentum_pct,trend_pct FROM scanner_results s
               JOIN market_universe u ON u.symbol=s.symbol
               WHERE s.quality='VALID' AND u.category=? AND s.scanned_at>=?""",
            (family,cutoff),
        )
    except Exception:
        rows=[]
    if not rows:
        return {'regime':'NEUTRAL','breadth':0,'avg_momentum_pct':0,'avg_trend_pct':0,'samples':0}
    valid_n=len(rows)
    buys=sum(1 for r in rows if str(r.get('signal')).upper()=='BUY')
    avoids=sum(1 for r in rows if str(r.get('signal')).upper()=='AVOID')
    breadth=buys/valid_n
    avg_m=sum(D(r.get('momentum_pct')) for r in rows)/D(valid_n)
    avg_t=sum(D(r.get('trend_pct')) for r in rows)/D(valid_n)
    if breadth>=D('.60') and avg_m>0 and avg_t>0:regime='BULL'
    elif breadth<=D('.40') and avg_m<0 and avg_t<0:regime='BEAR'
    elif avg_m>0 and avg_t>0:regime='BULL'
    elif avg_m<0 and avg_t<0:regime='BEAR'
    else:regime='NEUTRAL'
    return {'regime':regime,'breadth':float(breadth),'avg_momentum_pct':float(avg_m),'avg_trend_pct':float(avg_t),'samples':valid_n,'buy_count':buys,'avoid_count':avoids}
