"""v66 autonomous trading orchestration.

Coordinates validated model output, v65 portfolio optimization, cost-aware
routing, Decision Matrix checks and the deterministic Digital Twin. This
module prepares an auditable decision; it never submits a Kraken order.
"""
from dataclasses import dataclass, field, asdict
from math import isfinite
from typing import Any, Dict, List, Optional

try:
    from .autonomous_portfolio_v65 import AssetView, Holding, DecisionPolicy, AutonomousPortfolioEngine, DigitalTwin
    from .execution_router import choose_route
except ImportError:
    from autonomous_portfolio_v65 import AssetView, Holding, DecisionPolicy, AutonomousPortfolioEngine, DigitalTwin
    from execution_router import choose_route

@dataclass(frozen=True)
class ModelInput:
    model_id: str
    valid: bool
    expected_return_pct: float
    volatility_pct: float
    confidence: float
    validation_status: str = "VALID"
    assets: List[Dict[str, Any]] = field(default_factory=list)

@dataclass
class OrchestrationResult:
    status: str
    reason: str
    portfolio: Dict[str, Any]
    actions: List[Dict[str, Any]]
    twin: Optional[Dict[str, Any]] = None
    decision_context: Dict[str, Any] = field(default_factory=dict)

class AutonomousOrchestratorV66:
    def __init__(self, policy=None, decision_matrix=None):
        self.policy = policy or DecisionPolicy()
        self.engine = AutonomousPortfolioEngine(self.policy)
        self.decision_matrix = decision_matrix

    @staticmethod
    def _field(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    @classmethod
    def _models_ready(cls, models):
        ready = []
        for model in models:
            status = str(cls._field(model, "validation_status", "")).upper()
            valid = cls._field(model, "valid", False)
            try:
                confidence = float(cls._field(model, "confidence", 0))
                expected = float(cls._field(model, "expected_return_pct", 0))
            except (TypeError, ValueError):
                continue
            if bool(valid) and status == "VALID" and isfinite(confidence) and confidence > 0 and isfinite(expected) and expected > 0:
                ready.append(model)
        return ready

    @classmethod
    def _assets(cls, models):
        out = []
        for model in models:
            rows = cls._field(model, "assets", [])
            if not isinstance(rows, (list, tuple)):
                continue
            for row in rows:
                if not isinstance(row, dict):
                    continue
                try:
                    expected = float(row["expected_return_pct"])
                    volatility = float(row["volatility_pct"])
                    score = float(row.get("score", 0))
                    if not all(isfinite(v) for v in (expected, volatility, score)) or volatility < 0:
                        continue
                    currency = str(row.get("currency", "EUR")).upper()
                    if currency not in {"EUR", "USD"}:
                        continue
                    out.append(AssetView(str(row["symbol"]), score, expected, volatility, currency))
                except (KeyError, TypeError, ValueError):
                    continue
        return out

    def decide(self, models, portfolio, route_options=None, tickers=None, eurusd=None, trade_context="PAPER"):
        models = list(models or [])
        portfolio = dict(portfolio or {})
        route_options = route_options or {}
        tickers = tickers or {}
        ready = self._models_ready(models)
        if not ready:
            return OrchestrationResult("BLOCKED", "Kein Modell mit bestandener Validierung verfügbar", {}, [])
        assets = self._assets(ready)
        if not assets:
            return OrchestrationResult("BLOCKED", "Validierte Modelle liefern keine handelbaren Assets", {}, [])
        try:
            total = float(portfolio.get("total_eur", 0))
        except (TypeError, ValueError):
            return OrchestrationResult("BLOCKED", "Ungültiger Portfolio-Gesamtwert", {}, [])
        if not isfinite(total) or total <= 0:
            return OrchestrationResult("BLOCKED", "Portfolio-Gesamtwert ist nicht positiv", {}, [])
        holdings = []
        for row in portfolio.get("holdings", []):
            if isinstance(row, Holding):
                holdings.append(row)
                continue
            if not isinstance(row, dict):
                continue
            try:
                currency = str(row.get("currency", "EUR")).upper()
                if currency not in {"EUR", "USD"}:
                    continue
                value = float(row["value_eur"])
                if isfinite(value) and value >= 0:
                    holdings.append(Holding(str(row["symbol"]), value, currency))
            except (KeyError, TypeError, ValueError):
                continue
        plan = self.engine.rebalance(total, holdings, assets)
        if plan.get("status") != "PLAN_READY":
            return OrchestrationResult("BLOCKED", plan.get("status", "Ungültiges Portfolio"), plan, [])
        for action in plan.get("actions", []):
            if action.get("side") != "BUY":
                continue
            alternatives = route_options.get(action.get("symbol"), [])
            if not alternatives:
                action["route_status"] = "MISSING_ROUTE_OPTIONS"
                continue
            try:
                selected, details = choose_route(alternatives, tickers, float(action["notional_eur"]), self.policy.trading_fee_bps, self.policy.fx_fee_bps, self.policy.slippage_bps, "buy")
            except (KeyError, TypeError, ValueError):
                selected, details = None, {"error": "Ungültige Routingdaten"}
            action["route_status"] = "VALID" if selected else "BLOCKED_NO_VALID_ROUTE"
            action["route_details"] = details
            if selected:
                action["selected_route"] = selected.get("symbol")
                action["currency"] = str(selected.get("quote_asset") or action.get("currency", "EUR")).upper()
                action["route_cost_eur"] = float(details["selected"]["total_cost_eur"])
        blocked = [a for a in plan.get("actions", []) if a.get("side") == "BUY" and a.get("route_status") != "VALID"]
        context = {
            "data_fresh": bool(portfolio.get("data_fresh", False)),
            "confirmation_count": int(portfolio.get("confirmation_count", 1)),
            "confirmation_required": int(portfolio.get("confirmation_required", 1)),
            "minimum_hold_ok": bool(portfolio.get("minimum_hold_ok", True)),
            "cooldown_ok": bool(portfolio.get("cooldown_ok", True)),
            "daily_limit_ok": bool(portfolio.get("daily_limit_ok", True)),
            "tax_loss_ok": bool(portfolio.get("tax_loss_ok", True)),
            "model_health_ok": True,
            "model_health_details": {"models": [str(self._field(m, "model_id", "unknown")) for m in ready]},
            "portfolio_risk_ok": bool(portfolio.get("portfolio_risk_ok", True)),
            "portfolio_risk_details": portfolio.get("portfolio_risk_details", {}),
            "route_cost_ok": not blocked,
            "route_cost_details": {"blocked": blocked},
            "quote_funding_ok": bool(portfolio.get("quote_funding_ok", True)),
            "quote_funding_details": portfolio.get("quote_funding_details", {}),
            "real_trading_enabled": bool(portfolio.get("real_trading_enabled", False)),
            "real_kill_switch_clear": bool(portfolio.get("real_kill_switch_clear", False)),
            "real_limits_ok": bool(portfolio.get("real_limits_ok", True)),
            "real_balance_ok": bool(portfolio.get("real_balance_ok", True)),
        }
        if blocked:
            return OrchestrationResult("BLOCKED", "Mindestens eine Kaufroute ist nicht validiert", plan, plan["actions"], decision_context=context)
        if self.decision_matrix:
            check = self.decision_matrix.evaluate("PORTFOLIO", "REBALANCE", context, trade_context)
            if not check.get("allowed"):
                return OrchestrationResult("BLOCKED", check.get("blocker", "Decision Matrix blockiert"), plan, plan["actions"], decision_context=check)
        try:
            eur_balance = float(portfolio.get("eur_balance", 0))
            usd_balance = float(portfolio.get("usd_balance", 0))
        except (TypeError, ValueError):
            return OrchestrationResult("BLOCKED", "Ungültige Währungsbestände", plan, plan["actions"], decision_context=context)
        twin = DigitalTwin(self.policy).execute(plan, eur_balance, usd_balance, eurusd)
        if twin.get("status") != "SIMULATED":
            return OrchestrationResult("BLOCKED", "Digital Twin hat die Ausführung blockiert", plan, plan["actions"], twin, context)
        return OrchestrationResult("READY", "Modell, Portfolio, Routing, Decision Matrix und Digital Twin erfolgreich geprüft", plan, plan["actions"], twin, context)

    @staticmethod
    def serialize(result):
        return asdict(result)
