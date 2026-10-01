"""v98 Paper adapter.

The canonical planner and execution intent are identical to Real. This adapter
only simulates the resulting fill/accounting.
"""
import json
from decimal import Decimal
from model_health import ModelHealth
from paper_engine import PaperEngine
from decision_pipeline_v98 import CanonicalDecisionPlannerV98
from execution_plan_v98 import build_execution_intent
from order_math_v98 import volume_for_eur, order_constraints
from trade_guard_v98 import TradeGuardV98
from decision_matrix import DecisionMatrix
from trade_thresholds_v98 import trade_thresholds

D=lambda x:Decimal(str(x or 0))

class PaperEngineV98(PaperEngine):
    def __init__(self, *args, runtime=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.runtime = runtime

    def _position_mode(self,symbol):
        rows=self.db.rows("SELECT leverage FROM paper_position_risk WHERE symbol=? LIMIT 1",(symbol,))
        if rows and self.db.value("paper_leverage_enabled","false").lower()=="true":
            lev=max(1,int(float(rows[0].get("leverage") or 1)))
            return "MARGIN",lev
        return "SPOT",1

    def run(self):
        self.consolidate_canonical_positions()
        if self.runtime is not None:
            self.runtime.prepare()
        active=self.db.value("automation_enabled","false").lower()=="true"
        cash,pv,total,missing=self.equity()
        planner=CanonicalDecisionPlannerV98(self.db)
        settings=planner.settings()
        available_quotes={"EUR"} if cash>0 else set()
        current={}
        for p in self.positions():
            try:
                px=self.price(p["symbol"])
                if px:current[p["symbol"]]=D(p["quantity"])*D(px["last"])
            except Exception:
                continue
        plan=planner.build(total,current_by_symbol=current,environment="PAPER",available_quotes=available_quotes)
        guard=TradeGuardV98(self.db,"PAPER")
        matrix=DecisionMatrix(self.db)
        actions=[];submitted=0;skips=[];evaluated_candidates=len(plan['decisions'])
        execution_capacity=int(settings["decision_max_actions_per_run"])
        for decision in plan["decisions"]:
            if submitted>=execution_capacity:break
            delta=D(decision["rebalance_delta_eur"])
            threshold=trade_thresholds(
                delta,decision["current_exposure_eur"],total,
                settings["decision_min_trade_eur"],settings["decision_no_trade_band_pct"]
            )
            if not threshold["allowed"]:
                skips.append({"symbol":decision["symbol"],**threshold})
                continue
            intent=build_execution_intent(
                decision,
                decision.get("route_context"),
                plan["health"].get(decision.get("family"),{}),
                {
                    "decision_max_leverage":int(float(self.db.value("paper_max_leverage","3"))),
                    "decision_confidence_spot_min":settings["decision_confidence_spot_min"],
                    "decision_confidence_margin_2x":settings["decision_confidence_margin_2x"],
                    "decision_confidence_margin_3x":settings["decision_confidence_margin_3x"],
                    "decision_confidence_margin_4x":settings["decision_confidence_margin_4x"],
                    "decision_confidence_margin_5x":settings["decision_confidence_margin_5x"],
                    "decision_max_trade_eur":settings["decision_max_trade_eur"],
                },
                "PAPER",
                *self._position_mode(decision["symbol"]),
                margin_capable=self.db.value("paper_leverage_enabled","false").lower()=="true",
                short_capable=False,
            )
            if intent["status"]!="READY":
                planner_engine=__import__("decision_engine_v98").DecisionEngineV98(self.db)
                planner_engine.record("PAPER",decision,intent.get("execution_symbol"),intent.get("mode"),intent.get("leverage"),"BLOCKED",intent["reason"])
                actions.append({"decision":decision,"intent":intent,"status":"BLOCKED","reason":intent["reason"]})
                continue
            volume,price,quote=volume_for_eur(plan["tickers"],intent["execution_symbol"],intent["side"],intent["trade_eur"])
            meta=next((x for x in decision["route_context"].get("alternatives",[]) if x.get("symbol")==intent["execution_symbol"]),{})
            constraints=order_constraints(meta,volume,price)
            risk_exit=bool(intent["zero_exit"] or intent["reduction"])
            guard_state=guard.check(decision["symbol"],intent["side"],risk_exit=risk_exit)
            common={
                **guard_state,
                "canonical_id":guard_state["canonical_id"],
                "improvement_after_costs":str(max(D(0),D(decision.get("expected_edge_after_costs_pct") or 0))*D(intent["trade_eur"])/100),
                "economic_edge_ok":bool(intent["economic_edge_ok"]),
                "model_health_data_ok":bool(plan["health"].get(decision.get("family"),{}).get("status")),
                "model_health_details":plan["health"].get(decision.get("family"),{}),
                "route_cost_ok":decision.get("route_context",{}).get("status")=="VALID",
                "route_cost_details":decision.get("route_context",{}),
                "quote_funding_ok":True,
                "portfolio_risk_ok":abs(D(decision["target_exposure_eur"]))<=total*D(settings["decision_max_position_pct"])/100,
                "portfolio_risk_details":{"target_eur":decision["target_exposure_eur"],"total_eur":str(total)},
                "order_constraints_ok":constraints["ok"],
                "order_constraints_details":constraints,
                "data_fresh":intent["execution_symbol"] in plan["tickers"],
                "tax_loss_ok":True,
            }
            risk=matrix.evaluate(decision["symbol"],intent["side"],common,"PAPER")
            if not risk["allowed"]:
                __import__("decision_engine_v98").DecisionEngineV98(self.db).record("PAPER",decision,intent["execution_symbol"],intent["mode"],intent["leverage"],"BLOCKED",risk["blocker"])
                actions.append({"decision":decision,"intent":intent,"matrix":risk,"status":"BLOCKED","reason":risk["blocker"]})
                continue
            status="PROPOSED"
            trade_id=None
            reason="ORDER_READY_BUT_AUTOMATIC_EXECUTION_DISABLED"
            if active:
                try:
                    collateral=D(intent["trade_eur"])/D(intent["leverage"]) if intent["margin"] and intent["side"]=="BUY" else D(intent["trade_eur"])
                    trade_id=self.execute(intent["execution_symbol"],intent["side"],collateral,"v98 canonical execution",{
                        **decision,"plan_hash":plan["plan_hash"],"execution_symbol":intent["execution_symbol"],
                        "execution_mode":intent["mode"],"execution_leverage":str(intent["leverage"]),
                        "reduce_only":intent["reduce_only"],"quote":quote,
                    })
                    guard.record_fill(decision["symbol"],intent["side"])
                    status="SUBMITTED"
                    submitted+=1
                    reason="PAPER_FILL_SIMULATED"
                except Exception as exc:
                    status="FAILED"
                    reason=type(exc).__name__+":"+str(exc)[:240]
            __import__("decision_engine_v98").DecisionEngineV98(self.db).record("PAPER",decision,intent["execution_symbol"],intent["mode"],intent["leverage"],status,reason)
            actions.append({"decision":decision,"intent":intent,"matrix":risk,"status":status,"reason":reason,"trade_id":trade_id})
        self.snapshot()
        self.db.audit("PAPER_V98_CANONICAL_RUN",json.dumps({
            "plan_hash":plan["plan_hash"],"decisions":len(plan["decisions"]),
            "actions":len(actions),"executed":sum(1 for x in actions if x["status"]=="SUBMITTED"),
        },sort_keys=True))
        return {**plan,"status":"COMPLETED","actions":actions,"skips":skips}
