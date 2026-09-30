"""v95 shared market/route context for Paper and Real."""

from decimal import Decimal
from execution_router import choose_route
from strategy_profiles import family_for_category

D = lambda x: Decimal(str(x or 0))


def ticker_map(db):
    return {
        x["symbol"]: {
            "b": [x["bid"] or x["last"]],
            "a": [x["ask"] or x["last"]],
            "c": [x["last"]],
        }
        for x in db.rows("SELECT symbol,last,bid,ask FROM live_prices")
    }


def alternatives(db, symbol):
    rows = db.rows(
        "SELECT symbol,asset_class,category,base_asset,quote_asset,source_key,ordermin,costmin "
        "FROM market_universe WHERE canonical_id=(SELECT canonical_id FROM market_universe WHERE symbol=? LIMIT 1) "
        "AND quote_asset IN ('EUR','USD')",
        (symbol,),
    )
    return [dict(x) for x in rows]


def routes_for_symbol(
    db,
    symbol,
    tickers,
    fee_bps,
    fx_fee_bps,
    slippage_bps,
):
    alts = alternatives(db, symbol)
    buy_selected, buy_route = choose_route(
        alts, tickers, 100, fee_bps, fx_fee_bps, slippage_bps, "buy"
    )
    sell_selected, sell_route = choose_route(
        alts, tickers, 100, fee_bps, fx_fee_bps, slippage_bps, "sell"
    )
    if buy_route.get("status") != "VALID" or sell_route.get("status") != "VALID":
        return {
            "status": "INCOMPLETE",
            "alternatives": alts,
            "buy": buy_route,
            "sell": sell_route,
            "roundtrip_cost_pct": None,
        }
    return {
        "status": "VALID",
        "alternatives": alts,
        "buy": {"selected": buy_selected, **buy_route},
        "sell": {"selected": sell_selected, **sell_route},
        "roundtrip_cost_pct": D(buy_route["selected"]["total_cost_pct"])
        + D(sell_route["selected"]["total_cost_pct"]),
    }


def scanner_candidates(db, allowed_symbols=None):
    cols = {x["name"] for x in db.rows("PRAGMA table_info(scanner_results)")}
    news = "s.news_score" if "news_score" in cols else "0 AS news_score"
    rows = db.rows(
        f"""SELECT s.symbol,s.score,s.momentum_pct,s.trend_pct,s.volatility_pct,
                   s.spread_pct,s.signal,s.quality,{news},
                   u.category,u.base_asset,u.quote_asset,u.canonical_id
            FROM scanner_results s
            LEFT JOIN market_universe u ON u.symbol=s.symbol
            WHERE s.quality IN ('VALID','CACHED')
            ORDER BY CAST(s.score AS REAL) DESC"""
    )
    allowed = {str(x).upper() for x in (allowed_symbols or []) if str(x).strip()}
    out = []
    for row in rows:
        symbol = str(row["symbol"]).upper()
        if allowed and symbol not in allowed:
            continue
        category = row.get("category") or "crypto_spot"
        out.append(
            {
                **row,
                "symbol": symbol,
                "family": family_for_category(category),
                "score": row.get("score") or 0,
                "momentum_pct": row.get("momentum_pct") or 0,
                "trend_pct": row.get("trend_pct") or 0,
                "volatility_pct": row.get("volatility_pct") or 0,
                "spread_pct": row.get("spread_pct") or 0,
                "news_score": row.get("news_score") or 0,
            }
        )
    return out


def decision_costs(db):
    return (
        db.value("decision_fee_bps", db.value("real_fee_bps", db.value("paper_fee_bps", "40"))),
        db.value("decision_fx_fee_bps", db.value("real_fx_fee_bps", db.value("paper_fx_fee_bps", "10"))),
        db.value("decision_slippage_bps", db.value("real_slippage_bps", db.value("paper_slippage_bps", "10"))),
    )
