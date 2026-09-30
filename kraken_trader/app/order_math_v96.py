"""v96 common Kraken order math used by Paper and Real."""
from decimal import Decimal
D=lambda x:Decimal(str(x or 0))

def live_price(tickers,symbol,side):
    t=(tickers or {}).get(symbol) or {}
    bid=D((t.get("b") or [0])[0]);ask=D((t.get("a") or [0])[0]);last=D((t.get("c") or [0])[0])
    price=ask if side=="BUY" else bid
    if price<=0:price=last
    if price<=0:raise ValueError("NO_FRESH_EXECUTION_PRICE")
    return price

def volume_for_eur(tickers,symbol,side,trade_eur):
    price=live_price(tickers,symbol,side)
    quote=str(symbol.rsplit("/",1)[-1]).upper()
    notional=D(trade_eur)
    if quote=="USD":
        fx=(tickers or {}).get("EUR/USD") or {}
        rate=D(((fx.get("b") if side=="BUY" else fx.get("a")) or [0])[0])
        if rate<=0:rate=D((fx.get("c") or [0])[0])
        if rate<=0:raise ValueError("NO_FRESH_EUR_USD_PRICE")
        notional*=rate
    return notional/price,price,quote

def order_constraints(meta,volume,price):
    ordermin=D(meta.get("ordermin"))
    costmin=D(meta.get("costmin"))
    ok=(ordermin<=0 or D(volume)>=ordermin) and (costmin<=0 or D(volume)*D(price)>=costmin)
    return {
        "ok":ok,
        "volume":str(volume),
        "price":str(price),
        "ordermin":str(ordermin),
        "costmin":str(costmin),
        "notional":str(D(volume)*D(price)),
    }
