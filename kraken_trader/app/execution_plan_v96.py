"""v96 execution intent shared by Paper and Real.

The planner converts a canonical decision into one deterministic order intent.
Only the final adapter is allowed to simulate or submit the intent.
"""
from decimal import Decimal
from execution_confidence import execution_confidence, choose_execution
D=lambda x:Decimal(str(x or 0))

def build_execution_intent(decision,route_context,health,settings,environment,
                           existing_mode="SPOT",existing_leverage=1,
                           margin_capable=False,short_capable=False):
    delta=D(decision.get("rebalance_delta_eur"))
    current=D(decision.get("current_exposure_eur"))
    target=D(decision.get("target_exposure_eur"))
    if delta==0:
        return {"status":"NO_TRADE","action":"HOLD","reason":"TARGET_ALREADY_REACHED"}
    side="BUY" if delta>0 else "SELL"
    reducing=(abs(target)<abs(current) and target*current>=0)
    zero_exit=(target==0 and current!=0)
    selected=(route_context or {}).get("buy" if side=="BUY" else "sell",{})
    market=selected.get("market") if isinstance(selected,dict) else None
    cost=selected.get("cost") if isinstance(selected,dict) else None
    if not market or not cost:
        return {"status":"BLOCKED","action":side,"reason":"NO_VALID_EXECUTION_ROUTE"}
    direction="UP" if side=="BUY" else "DOWN"
    calibration=None
    if decision.get("increasing_risk") and margin_capable:
        calibration=(health or {}).get("directions",{}).get(direction,{})
        if calibration.get("status")!="READY":
            calibration=None
    confidence=execution_confidence(
        decision.get("score",0),health,calibration,
        regime=decision.get("regime","NEUTRAL"),direction=direction,
    )
    if reducing:
        mode=str(existing_mode or "SPOT").upper()
        leverage=D(existing_leverage or 1)
        reason="REDUCTION_USES_EXISTING_POSITION_TYPE"
    else:
        chosen=choose_execution(
            confidence,
            margin_capable,
            int(settings["decision_max_leverage"]),
            settings["decision_confidence_spot_min"],
            settings["decision_confidence_margin_2x"],
            settings["decision_confidence_margin_3x"],
            settings["decision_confidence_margin_4x"],
            settings["decision_confidence_margin_5x"],
            calibration=calibration,
        )
        mode=chosen["mode"];leverage=D(chosen["leverage"]);reason=chosen["reason"]
        if decision.get("direction")=="SHORT" and not short_capable:
            return {"status":"BLOCKED","action":side,"reason":"SHORT_NOT_SUPPORTED_BY_EXECUTION_ACCOUNT"}
    if zero_exit and reducing:
        reduce_only=True
    else:
        reduce_only=reducing
    trade_eur=min(abs(delta),D(settings["decision_max_trade_eur"]))
    selected_symbol=market.get("symbol")
    quote=str(market.get("quote_asset") or "").upper()
    return {
        "status":"READY" if mode!="BLOCKED" else "BLOCKED",
        "canonical_symbol":decision.get("symbol"),
        "execution_symbol":selected_symbol,
        "side":side,
        "trade_eur":str(trade_eur),
        "quote_asset":quote,
        "mode":mode,
        "leverage":str(leverage),
        "margin":mode=="MARGIN",
        "reduce_only":reduce_only,
        "confidence":str(confidence),
        "reason":reason,
        "route":route_context,
        "cost":cost,
        "reduction":reducing,
        "zero_exit":zero_exit,
        "economic_edge_ok":bool(decision.get("economic_gate_passed")),
        "expected_edge_after_costs_pct":decision.get("expected_edge_after_costs_pct"),
        "plan_hash":decision.get("plan_hash"),
    }
