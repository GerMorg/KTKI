"""v98 shared execution intent with pair-aware margin capability."""
import json
from execution_plan_v96 import build_execution_intent as _build

def pair_margin_capable(route_context, side):
    side_key="buy" if str(side).upper()=="BUY" else "sell"
    market=(route_context or {}).get(side_key,{}).get("market") or {}
    raw=market.get("leverage_buy_json" if side_key=="buy" else "leverage_sell_json") or "[]"
    try:
        values=json.loads(raw) if isinstance(raw,str) else raw
    except Exception:
        values=[]
    if not values:
        try:
            meta=json.loads(market.get("metadata_json") or "{}")
            values=meta.get("leverage_buy" if side_key=="buy" else "leverage_sell") or []
        except Exception:
            values=[]
    return any(str(x).replace(":1","").strip() not in ("","1","1.0") for x in values)

def build_execution_intent(*args, **kwargs):
    route=kwargs.get("route_context")
    if route is None and len(args)>=2:
        route=args[1]
    # Positional signature in v96: (..., environment, existing_mode,
    # existing_leverage, margin_capable, short_capable)
    if len(args)>=9:
        args=list(args)
        side=(args[0].get("rebalance_delta_eur") if isinstance(args[0],dict) else 0)
        actual_side="BUY" if float(side or 0)>0 else "SELL"
        if args[0].get("current_exposure_eur") is not None:
            requested_margin=bool(args[7])
            reducing=abs(float(args[0].get("target_exposure_eur") or 0))<abs(float(args[0].get("current_exposure_eur") or 0))
            if requested_margin and not reducing and not pair_margin_capable(route,actual_side):
                args[7]=False
        return _build(*args, **kwargs)
    return _build(*args, **kwargs)
