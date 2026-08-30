"""v65 end-to-end adapter: validated model output -> portfolio plan -> Digital Twin.

This module deliberately has no Kraken/order side effects. It is the single
composition point for autonomous portfolio decisions before any future live gate.
"""
from autonomous_portfolio_v65 import AssetView, Holding, DecisionPolicy, AutonomousPortfolioEngine, DigitalTwin
from execution_router import choose_route


def build_assets(model_outputs):
    if not isinstance(model_outputs, list):
        raise TypeError("model_outputs must be a list")
    assets=[]
    for row in model_outputs:
        if not isinstance(row, dict):
            raise TypeError("each model output must be a dictionary")
        if not row.get("model_valid", False):
            continue
        symbol=str(row.get("symbol") or "").strip()
        if not symbol:
            continue
        try:
            assets.append(AssetView(symbol, float(row["score"]), float(row["expected_return_pct"]), float(row["volatility_pct"]), str(row.get("currency","EUR")).upper()))
        except (KeyError, TypeError, ValueError):
            continue
    return assets


def build_plan(model_outputs, total_eur, holdings, policy=None, route_options=None, tickers=None):
    assets=build_assets(model_outputs)
    engine=AutonomousPortfolioEngine(policy)
    holding_objects=[h if isinstance(h,Holding) else Holding(str(h["symbol"]),float(h["value_eur"]),str(h.get("currency","EUR")).upper()) for h in (holdings or [])]
    plan=engine.rebalance(float(total_eur),holding_objects,assets)
    route_options=route_options or {}; tickers=tickers or {}
    for action in plan.get("actions",[]):
        if action.get("side")!="BUY": continue
        alternatives=route_options.get(action["symbol"],[])
        if not alternatives: continue
        selected,details=choose_route(alternatives,tickers,action["notional_eur"],engine.policy.trading_fee_bps,engine.policy.fx_fee_bps,engine.policy.slippage_bps,"buy")
        if selected is None:
            action["route_status"]="BLOCKED_NO_VALID_ROUTE"
            action["route_details"]=details
            continue
        action["currency"]=str(selected.get("quote_asset") or action.get("currency","EUR")).upper()
        action["selected_route"]=selected.get("symbol")
        action["route_cost_eur"]=float(details["selected"]["total_cost_eur"])
        action["route_status"]="VALID"
    return plan


def simulate_end_to_end(model_outputs,total_eur,holdings,eur_balance,usd_balance=0.0,fx_rate_eur_per_usd=None,policy=None,route_options=None,tickers=None):
    plan=build_plan(model_outputs,total_eur,holdings,policy,route_options,tickers)
    blocked=[a for a in plan.get("actions",[]) if a.get("side")=="BUY" and a.get("route_status")=="BLOCKED_NO_VALID_ROUTE"]
    if blocked:
        return {"status":"BLOCKED_NO_VALID_ROUTE","plan":plan,"simulation":None}
    simulation=DigitalTwin(policy).execute(plan,eur_balance,usd_balance,fx_rate_eur_per_usd)
    return {"status":simulation.get("status"),"plan":plan,"simulation":simulation}
