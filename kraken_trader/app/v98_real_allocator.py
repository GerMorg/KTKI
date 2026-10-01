"""v98 Real adapter using the exact same canonical decision and execution plan as Paper."""
import json
import secrets
from decimal import Decimal

from v95_real_allocator import RealPortfolioAllocatorV95
from decision_pipeline_v98 import CanonicalDecisionPlannerV98
from execution_plan_v98 import build_execution_intent
from order_math_v98 import volume_for_eur, order_constraints
from trade_guard_v98 import TradeGuardV98
from decision_matrix import DecisionMatrix
from trade_thresholds_v98 import trade_thresholds
from decision_engine_v98 import DecisionEngineV98

D=lambda x:Decimal(str(x or 0))

class RealPortfolioAllocatorV98(RealPortfolioAllocatorV95):
    def __init__(self, db, trade_engine, runtime=None):
        super().__init__(db, trade_engine)
        self.runtime = runtime

    def _current_by_symbol(self,current):
        out={}
        for asset,value in current.items():
            if asset in ("EUR","USD") or D(value)==0:continue
            rows=self.db.rows(
                "SELECT symbol FROM market_universe WHERE base_asset IN (?,?) "
                "AND quote_asset IN ('EUR','USD') ORDER BY CASE WHEN quote_asset='EUR' THEN 0 ELSE 1 END,symbol LIMIT 1",
                (asset,"XBT" if asset=="BTC" else asset),
            )
            if rows:out[rows[0]["symbol"]]=D(value)
        return out

    def _existing_mode(self,symbol):
        rows=self.db.rows("SELECT side,leverage FROM real_margin_positions WHERE symbol=? LIMIT 1",(symbol,))
        if rows and self.settings()["margin_enabled"]:
            return "MARGIN",D(rows[0].get("leverage") or 1)
        return "SPOT",D(1)

    def run(self,automatic=False,approval_token=None):
        if not self.lock.acquire(False):return {"status":"BUSY"}
        run_id=None
        try:
            cfg=self.settings()
            if automatic and not cfg["enabled"]:return {"status":"DISABLED"}
            if self.runtime is not None:
                self.runtime.prepare()
            try:self._refresh_private_balances()
            except Exception:pass
            current,total=self._current_eur()
            current_by=self._current_by_symbol(current)
            available_quotes=set()
            if D(self._quote_balance("EUR"))>0: available_quotes.add("EUR")
            if D(self._quote_balance("USD"))>0: available_quotes.add("USD")
            planner=CanonicalDecisionPlannerV98(self.db)
            settings=planner.settings()
            plan=planner.build(
                total,
                current_by_symbol=current_by,
                environment="REAL",
                allow_short=settings["decision_allow_shorts"],
                available_quotes=available_quotes,
            )
            guard=TradeGuardV98(self.db,"REAL")
            matrix=DecisionMatrix(self.db)
            engine=DecisionEngineV98(self.db)

            with self.db.con() as c:
                cur=c.execute(
                    "INSERT INTO real_allocation_runs(created_at,status,automatic,settings_json,details_json) VALUES(?,?,?,?,?)",
                    (self.db.now() if hasattr(self.db,"now") else __import__("db").now(),"RUNNING",int(automatic),
                     json.dumps(settings,sort_keys=True),json.dumps({"plan_hash":plan["plan_hash"]},sort_keys=True))
                )
                run_id=cur.lastrowid

            submitted_today=int(self.db.rows(
                "SELECT COUNT(*) n FROM real_allocation_actions WHERE status='SUBMITTED' AND date(created_at)=date('now')"
            )[0]["n"])
            execution_capacity=min(
                int(settings["decision_max_actions_per_run"]),
                max(0,int(settings["decision_max_actions_per_day"])-submitted_today),
            )
            actions=[];submitted=0;skips=[];evaluated_candidates=len(plan['decisions'])

            for decision in plan["decisions"]:
                delta=D(decision["rebalance_delta_eur"])
                threshold=trade_thresholds(
                    delta,decision["current_exposure_eur"],total,
                    settings["decision_min_trade_eur"],settings["decision_no_trade_band_pct"]
                )
                if not threshold["allowed"]:
                    skips.append({"symbol":decision["symbol"],**threshold})
                    continue

                route=decision.get("route_context") or {}
                existing_mode,existing_leverage=self._existing_mode(decision["symbol"])
                intent=build_execution_intent(
                    decision,route,plan["health"].get(decision.get("family"),{}),
                    {
                        "decision_max_leverage":int(cfg["margin_max_leverage"]),
                        "decision_confidence_spot_min":settings["decision_confidence_spot_min"],
                        "decision_confidence_margin_2x":settings["decision_confidence_margin_2x"],
                        "decision_confidence_margin_3x":settings["decision_confidence_margin_3x"],
                        "decision_confidence_margin_4x":settings["decision_confidence_margin_4x"],
                        "decision_confidence_margin_5x":settings["decision_confidence_margin_5x"],
                        "decision_max_trade_eur":settings["decision_max_trade_eur"],
                    },
                    "REAL",
                    existing_mode,existing_leverage,
                    margin_capable=bool(cfg["margin_enabled"]),
                    short_capable=bool(cfg["margin_enabled"] and cfg["margin_allow_shorts"]),
                )
                if intent["status"]!="READY":
                    engine.record("REAL",decision,None,None,0,"BLOCKED",intent["reason"])
                    actions.append({"decision":decision,"intent":intent,"status":"BLOCKED","reason":intent["reason"]})
                    skips.append({"symbol":decision["symbol"],"reason":intent["reason"]})
                    continue

                volume,price,quote=volume_for_eur(plan["tickers"],intent["execution_symbol"],intent["side"],intent["trade_eur"])
                meta=next((x for x in route.get("alternatives",[]) if x.get("symbol")==intent["execution_symbol"]),{})
                constraints=order_constraints(meta,volume,price)
                risk_reduction=bool(intent["reduction"])
                guard_state=guard.check(decision["symbol"],intent["side"],risk_exit=bool(intent["zero_exit"] or risk_reduction))
                quote_funding_ok=True
                funding_details={"required":False,"quote":quote}
                if intent["side"]=="BUY":
                    required_quote=D(volume)*D(price)
                    asset=quote
                    if quote=="EUR":
                        bal=D(self.db.rows("SELECT COALESCE(SUM(balance),0) AS v FROM private_balances WHERE UPPER(asset) IN ('EUR','ZEUR')")[0]["v"])
                    elif quote=="USD":
                        bal=D(self.db.rows("SELECT COALESCE(SUM(balance),0) AS v FROM private_balances WHERE UPPER(asset) IN ('USD','ZUSD')")[0]["v"])
                    else:bal=D(0)
                    fee=D(self.db.value("real_fee_bps","40"))/10000
                    required_quote*=1+fee
                    quote_funding_ok=bal>=required_quote or intent["margin"]
                    funding_details={"required":True,"asset":asset,"required":str(required_quote),"available":str(bal),"margin":bool(intent["margin"])}
                    if quote=="USD" and not quote_funding_ok and self.db.value("real_allow_auto_fx_funding","false").lower()=="true":
                        funding_details["auto_funding_requested"]=True

                common={
                    **guard_state,
                    "improvement_after_costs":str(max(D(0),D(decision.get("expected_edge_after_costs_pct") or 0))*D(intent["trade_eur"])/100),
                    "economic_edge_ok":bool(intent["economic_edge_ok"]),
                    "model_health_data_ok":bool(plan["health"].get(decision.get("family"),{}).get("status")),
                    "model_health_details":plan["health"].get(decision.get("family"),{}),
                    "route_cost_ok":route.get("status")=="VALID",
                    "route_cost_details":route,
                    "quote_funding_ok":quote_funding_ok,
                    "quote_funding_details":funding_details,
                    "portfolio_risk_ok":abs(D(decision["target_exposure_eur"]))<=total*D(settings["decision_max_position_pct"])/100,
                    "portfolio_risk_details":{"target_eur":decision["target_exposure_eur"],"budget_eur":decision["portfolio_target_budget_eur"]},
                    "order_constraints_ok":constraints["ok"],
                    "order_constraints_details":constraints,
                    "data_fresh":intent["execution_symbol"] in plan["tickers"],
                    "tax_loss_ok":True,
                    "real_trading_enabled":self.trade_engine.enabled(),
                    "real_kill_switch_clear":self.db.value("real_kill_switch","true").lower()!="true",
                    "real_limits_ok":D(intent["trade_eur"])<=D(settings["decision_max_trade_eur"]),
                    "real_balance_ok":True,
                }
                check=matrix.evaluate(decision["symbol"],intent["side"],common,"REAL")
                status="BLOCKED";reason=check["blocker"];intent_id=None
                live=automatic and bool(cfg["automatic_execution"]) and not bool(cfg["dry_run"])
                secret=self.db.value("real_balancing_automation_secret","")
                if automatic and cfg["dry_run"]:
                    status="DRY_RUN";reason="DRY_RUN_CANONICAL_PLAN"
                elif live and not check["allowed"]:
                    status="BLOCKED";reason=check["blocker"]
                elif live and check["allowed"]:
                    try:
                        self.trade_engine.preflight(
                            intent["execution_symbol"],intent["side"],str(volume),
                            "limit",str(price),leverage=intent["leverage"],
                            margin=intent["margin"],reduce_only=intent["reduce_only"],
                        )
                        result=self.trade_engine.submit(
                            intent["execution_symbol"],intent["side"],str(volume),
                            "limit",str(price),secrets.token_hex(16),
                            approval_token,False,secret,
                            leverage=intent["leverage"],margin=intent["margin"],
                            reduce_only=intent["reduce_only"],
                        )
                        status=result.get("status","FAILED");intent_id=result.get("client_order_id")
                        reason="REAL_ORDER_SUBMITTED" if status=="SUBMITTED" else status
                    except Exception as exc:
                        status="FAILED";reason=type(exc).__name__+":"+str(exc)[:300]
                elif check["allowed"]:
                    status="PROPOSED";reason="ORDER_READY_BUT_AUTOMATIC_EXECUTION_DISABLED"

                engine.record("REAL",decision,intent["execution_symbol"],intent["mode"],intent["leverage"],status,reason)
                with self.db.con() as c:
                    c.execute(
                        "INSERT INTO real_allocation_actions(run_id,created_at,symbol,side,current_eur,target_eur,difference_eur,status,decision_json,order_intent_id,error) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                        (run_id,__import__("db").now(),decision["symbol"],intent["side"],decision["current_exposure_eur"],
                         decision["target_exposure_eur"],decision["rebalance_delta_eur"],status,
                         json.dumps({"decision":decision,"intent":intent,"matrix":check,"funding":funding_details},
                                    sort_keys=True,default=str),intent_id,None)
                    )
                actions.append({"decision":decision,"intent":intent,"matrix":check,"status":status,"reason":reason})
                if status=="SUBMITTED":
                    guard.record_fill(decision["symbol"],intent["side"])
                    submitted+=1
                    if submitted>=execution_capacity:break

            final="COMPLETED" if all(x["status"] not in ("FAILED",) for x in actions) else "PARTIAL"
            with self.db.con() as c:
                c.execute(
                    "UPDATE real_allocation_runs SET finished_at=?,status=?,details_json=? WHERE id=?",
                    (__import__("db").now(),final,json.dumps({"plan_hash":plan["plan_hash"],"evaluated_candidates":evaluated_candidates,"actions":actions,"skips":skips,"skipped_count":len(skips),"execution_capacity":execution_capacity},sort_keys=True,default=str),run_id)
                )
            self.db.audit("REAL_V98_CANONICAL_RUN",json.dumps({"plan_hash":plan["plan_hash"],"status":final,"actions":len(actions)}), "warning" if automatic else "info","REAL")
            return {**plan,"status":final,"run_id":run_id,"actions":actions,"skips":skips}
        except Exception as exc:
            if run_id:
                with self.db.con() as c:c.execute(
                    "UPDATE real_allocation_runs SET finished_at=?,status=?,error=? WHERE id=?",
                    (__import__("db").now(),"FAILED",type(exc).__name__+":"+str(exc)[:500],run_id))
            self.db.audit("REAL_V98_FAILED",type(exc).__name__+":"+str(exc)[:500],"error","REAL")
            return {"status":"FAILED","error":type(exc).__name__+":"+str(exc)[:500]}
        finally:self.lock.release()
