"""v66 autonomous trading orchestration.

Safety-first orchestration: planning and Digital-Twin validation happen before
any optional real execution. The orchestrator itself never places an order.
"""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

@dataclass
class ModelInput:
    model_id: str
    valid: bool
    expected_return: float
    risk: float
    confidence: float
    assets: Dict[str, float] = field(default_factory=dict)

@dataclass
class OrchestrationResult:
    status: str
    reason: str
    portfolio: Dict[str, float]
    actions: List[Dict[str, Any]]
    twin: Optional[Dict[str, Any]] = None
    decision_context: Dict[str, Any] = field(default_factory=dict)

class AutonomousOrchestratorV66:
    """Coordinates validated model output into a safe, auditable decision."""
    def __init__(self, optimizer, router, digital_twin, decision_matrix=None):
        self.optimizer = optimizer
        self.router = router
        self.digital_twin = digital_twin
        self.decision_matrix = decision_matrix

    def decide(self, models: List[ModelInput], portfolio: Dict[str, Any], trade_context="PAPER"):
        valid = [m for m in models if m.valid and m.confidence > 0 and m.expected_return > 0]
        if not valid:
            return OrchestrationResult("BLOCKED", "Kein validiertes Modell mit positivem Erwartungswert", {}, [])
        assets = {}
        for m in valid:
            for symbol, score in m.assets.items():
                assets[symbol] = max(assets.get(symbol, 0.0), float(score))
        if not assets:
            return OrchestrationResult("BLOCKED", "Validierte Modelle liefern keine handelbaren Assets", {}, [])
        # Keep optimizer contract isolated; callers may supply the existing v64 optimizer.
        target = self.optimizer.optimize(assets, portfolio) if hasattr(self.optimizer, "optimize") else assets
        actions = self._actions(portfolio.get("positions", {}), target)
        context = {
            "data_fresh": bool(portfolio.get("data_fresh", False)),
            "model_health_ok": True,
            "model_health_details": {"models": [m.model_id for m in valid]},
            "portfolio_risk_ok": bool(portfolio.get("portfolio_risk_ok", True)),
            "real_trading_enabled": bool(portfolio.get("real_trading_enabled", False)),
            "real_kill_switch_clear": bool(portfolio.get("real_kill_switch_clear", False)),
        }
        if self.decision_matrix:
            check = self.decision_matrix.evaluate("PORTFOLIO", "REBALANCE", context, trade_context)
            if not check["allowed"]:
                return OrchestrationResult("BLOCKED", check["blocker"], target, actions, decision_context=check)
        twin = self.digital_twin.simulate(actions, portfolio) if hasattr(self.digital_twin, "simulate") else None
        if twin is None:
            return OrchestrationResult("BLOCKED", "Digital-Twin-Prüfung nicht verfügbar", target, actions, decision_context=context)
        if isinstance(twin, dict) and twin.get("status") in ("BLOCKED", "ERROR", "FAILED"):
            return OrchestrationResult("BLOCKED", twin.get("reason", "Digital-Twin hat die Ausführung blockiert"), target, actions, twin, context)
        return OrchestrationResult("READY", "Digital-Twin erfolgreich durchlaufen", target, actions, twin, context)

    @staticmethod
    def _actions(current, target):
        symbols = sorted(set(current) | set(target))
        return [{"symbol": s, "side": "BUY" if float(target.get(s, 0)) > float(current.get(s, 0)) else "SELL",
                 "target_weight": float(target.get(s, 0)), "current_weight": float(current.get(s, 0))}
                for s in symbols if abs(float(target.get(s, 0)) - float(current.get(s, 0))) > 0]
