"""Shared v98 order-threshold semantics for Paper and Real."""

from decimal import Decimal

D=lambda x:Decimal(str(x or 0))

def trade_thresholds(delta,current,total,min_trade_eur,no_trade_band_pct):
    delta=D(delta); current=D(current); total=D(total)
    minimum=D(min_trade_eur)
    band=D(no_trade_band_pct)
    if delta==0:
        return {"allowed":False,"reason":"TARGET_ALREADY_REACHED"}
    if abs(delta)<minimum:
        return {"allowed":False,"reason":"BELOW_MIN_TRADE","minimum_eur":str(minimum),"delta_eur":str(delta)}
    # The configured no-trade band is hysteresis around an existing position.
    # A fresh entry is not compared against a percentage of the whole portfolio.
    if current!=0 and band>0:
        relative=abs(delta)/max(D(1),abs(current))*100
        if relative<band:
            return {"allowed":False,"reason":"REBALANCE_HYSTERESIS","relative_delta_pct":str(relative),"required_pct":str(band)}
    return {"allowed":True}
