"""v95 shared market/route context for Paper and Real."""

from decimal import Decimal
from datetime import datetime, timezone
from execution_router import choose_route
from strategy_profiles import family_for_category

D = lambda x: Decimal(str(x or 0))


def ticker_map(db, max_age_seconds=120):
    out={}
    now=datetime.now(timezone.utc)
    for x in db.rows("SELECT symbol,last,bid,ask,received_at FROM live_prices"):
        try:
            age=(now-datetime.fromisoformat(str(x.get("received_at")).replace("Z","+00:00")).astimezone(timezone.utc)).total_seconds()
        except Exception:
            age=float("inf")
        if age>float(max_age_seconds):
            continue
        out[x["symbol"]]={
            "b":[x["bid"] or x["last"]],
            "a":[x["ask"] or x["last"]],
            "c":[x["last"]],
            "received_at":x.get("received_at"),
        }
    return out


def alternatives(db, symbol):
    rows = db.rows(
        "SELECT symbol,asset_class,category,base_asset,quote_asset,source_key,ordermin,costmin "
        "FROM market_universe WHERE canonical_id=(SELECT canonical_id FROM market_universe WHERE symbol=? LIMIT 1) "
        "AND quote_asset IN ('EUR','USD')",
        (symbol,),
    )
    return [dict(x) for x in rows]


def routes_for_symbol(db, symbol, tickers, fee_bps, fx_fee_bps, slippage_bps):
    # Choose one canonical execution market for both entry and exit. This keeps
    # Paper position accounting and Real balance routing semantically identical:
    # a position is not allowed to move between EUR/USD quote markets silently.
    alts=alternatives(db,symbol)
    ranked=[]
    from execution_router import route_cost
    for market in alts:
        buy=route_cost(market,tickers,100,fee_bps,fx_fee_bps,slippage_bps,'buy')
        sell=route_cost(market,tickers,100,fee_bps,fx_fee_bps,slippage_bps,'sell')
        if buy.get('valid') and sell.get('valid'):
            total=D(buy['total_cost_pct'])+D(sell['total_cost_pct'])
            ranked.append((total,str(market.get('symbol')),market,buy,sell))
    ranked.sort(key=lambda x:(x[0],x[1]))
    if not ranked:
        return {'status':'INCOMPLETE','alternatives':alts,'buy':{'status':'NO_VALID_ROUTE'},'sell':{'status':'NO_VALID_ROUTE'},'roundtrip_cost_pct':None}
    _,_,market,buy,sell=ranked[0]
    return {
        'status':'VALID','alternatives':alts,
        'buy':{'status':'VALID','market':market,'cost':buy},
        'sell':{'status':'VALID','market':market,'cost':sell},
        'roundtrip_cost_pct':D(buy['total_cost_pct'])+D(sell['total_cost_pct']),
        'route_selection':'MINIMIZE_ENTRY_PLUS_EXIT_COST_ON_ONE_MARKET',
        'ranked':[
            {'symbol':symbol,'roundtrip_cost_pct':str(cost)} for cost,symbol,_,_,_ in ranked
        ],
    }

def scanner_candidates(db, allowed_symbols=None, max_age_minutes=120):
    cols={x["name"] for x in db.rows("PRAGMA table_info(scanner_results)")}
    news="s.news_score" if "news_score" in cols else "0 AS news_score"
    rows=db.rows(
        f"""SELECT s.symbol,s.score,s.momentum_pct,s.trend_pct,s.volatility_pct,
                   s.spread_pct,s.signal,s.quality,s.scanned_at,{news},
                   u.category,u.base_asset,u.quote_asset,u.canonical_id
            FROM scanner_results s
            LEFT JOIN market_universe u ON u.symbol=s.symbol
            WHERE s.quality IN ('VALID','CACHED')
            ORDER BY CAST(s.score AS REAL) DESC"""
    )
    allowed={str(x).upper() for x in (allowed_symbols or []) if str(x).strip()}
    by_canonical={}
    now=datetime.now(timezone.utc)
    for row in rows:
        symbol=str(row["symbol"]).upper()
        if allowed and symbol not in allowed:
            continue
        try:
            age=(now-datetime.fromisoformat(str(row.get("scanned_at")).replace("Z","+00:00")).astimezone(timezone.utc)).total_seconds()/60
        except Exception:
            age=float("inf")
        if age>float(max_age_minutes):
            continue
        cid=row.get("canonical_id") or symbol
        if cid in by_canonical:
            continue
        category=row.get("category") or "crypto_spot"
        by_canonical[cid]={
            **row,
            "symbol":symbol,
            "family":family_for_category(category),
            "score":row.get("score") or 0,
            "momentum_pct":row.get("momentum_pct") or 0,
            "trend_pct":row.get("trend_pct") or 0,
            "volatility_pct":row.get("volatility_pct") or 0,
            "spread_pct":row.get("spread_pct") or 0,
            "news_score":row.get("news_score") or 0,
        }
    return list(by_canonical.values())

def decision_costs(db):
    return (
        db.value("decision_fee_bps", db.value("real_fee_bps", db.value("paper_fee_bps", "40"))),
        db.value("decision_fx_fee_bps", db.value("real_fx_fee_bps", db.value("paper_fx_fee_bps", "10"))),
        db.value("decision_slippage_bps", db.value("real_slippage_bps", db.value("paper_slippage_bps", "10"))),
    )
