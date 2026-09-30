"""v95 canonical portfolio decision engine shared by Paper and Real."""

import json
from decimal import Decimal
from db import now

D = lambda x: Decimal(str(x or 0))


class DecisionEngineV95:
    def __init__(self, db):
        self.db = db
        if db is not None:
            with db.con() as c:
                c.execute(
                    """CREATE TABLE IF NOT EXISTS decision_snapshots(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL,
                    environment TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    action TEXT NOT NULL,
                    direction TEXT NOT NULL,
                    target_exposure_eur TEXT NOT NULL,
                    current_exposure_eur TEXT NOT NULL,
                    delta_eur TEXT NOT NULL,
                    expected_edge_gross_pct TEXT,
                    expected_edge_after_costs_pct TEXT,
                    quality_score TEXT,
                    regime TEXT,
                    news_score TEXT,
                    execution_symbol TEXT,
                    execution_mode TEXT,
                    leverage TEXT,
                    status TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    decision_json TEXT NOT NULL
                    )"""
                )
                c.execute(
                    "CREATE INDEX IF NOT EXISTS idx_decision_snapshots_time "
                    "ON decision_snapshots(created_at DESC, id DESC)"
                )

    @staticmethod
    def clamp(v, lo=0, hi=1):
        return max(D(lo), min(D(hi), D(v)))

    @staticmethod
    def direction(row, allow_short=False):
        signal = str(row.get("signal") or "").upper()
        momentum = D(row.get("momentum_pct"))
        trend = D(row.get("trend_pct"))
        if signal == "BUY" and momentum > 0 and trend > 0:
            return "LONG"
        if signal == "AVOID" and momentum < 0 and trend < 0 and allow_short:
            return "SHORT"
        if signal == "HOLD":
            return "HOLD"
        return "FLAT"

    @staticmethod
    def regime_factor(regime, direction):
        regime = str(regime or "NEUTRAL").upper()
        if direction == "LONG":
            return {"BULL": D("1"), "NEUTRAL": D(".75"), "MIXED": D(".55"), "BEAR": D(".25")}.get(regime, D(".5"))
        if direction == "SHORT":
            return {"BEAR": D("1"), "NEUTRAL": D(".75"), "MIXED": D(".55"), "BULL": D(".25")}.get(regime, D(".5"))
        return D(0)

    def symbol_gross_edge(self, symbol, direction, limit=30):
        if self.db is None or not symbol:
            return None
        wanted = "UP" if direction == "LONG" else "DOWN"
        try:
            rows = self.db.rows(
                "SELECT e.actual_return_pct FROM research_forecasts f "
                "JOIN forecast_evaluations e ON e.forecast_id=f.id "
                "WHERE f.symbol=? AND f.horizon_hours=24 AND f.direction=? "
                "ORDER BY f.id DESC LIMIT ?",
                (symbol, wanted, int(limit)),
            )
        except Exception:
            return None
        minimum = int(float(self.db.value("decision_min_edge_samples", "10"))) if self.db is not None else 10
        if len(rows) < max(1, minimum):
            return None
        values = []
        for row in rows:
            actual = D(row.get("actual_return_pct"))
            values.append(actual if wanted == "UP" else -actual)
        return sum(values) / D(len(values)) if values else None

    def gross_edge(self, row, direction):
        explicit = row.get("expected_edge_pct")
        if explicit not in (None, ""):
            try:
                return D(explicit)
            except Exception:
                pass
        return self.symbol_gross_edge(row.get("symbol"), direction)

    def build(
        self,
        row,
        health,
        total,
        current_eur,
        roundtrip_cost_pct,
        regime,
        config,
        existing=False,
        allow_short=False,
    ):
        direction = self.direction(row, allow_short=allow_short)
        score = D(row.get("score"))
        threshold = D(row.get("buy_threshold", config.get("minimum_score", 70)))
        avoid_threshold = D(row.get("avoid_threshold", 35))
        quality = self.clamp(D(health.get("quality_score", 50)) / 100)
        regime_factor = self.regime_factor(regime, direction)
        volatility = max(D(".25"), abs(D(row.get("volatility_pct") or 0)))
        volatility_reference = max(D(".25"), D(config.get("volatility_reference_pct", 2)))
        volatility_factor = min(D(1), volatility_reference / volatility)
        if direction == "LONG":
            signal_strength = self.clamp((score - threshold) / max(D(1), D(100) - threshold))
        elif direction == "SHORT":
            signal_strength = self.clamp((avoid_threshold - score) / max(D(1), avoid_threshold))
        else:
            signal_strength = D(0)
        quality_factor = D(".70") + D(".30") * quality
        cost_factor = D(1) / (D(1) + max(D(0), D(roundtrip_cost_pct)) / D(100))
        gross_edge = self.gross_edge(row, direction) if direction != "FLAT" else None
        edge_after_costs = (
            gross_edge - D(roundtrip_cost_pct)
            if gross_edge is not None
            else None
        )

        sizing_strength = (
            signal_strength
            * quality_factor
            * regime_factor
            * volatility_factor
            * cost_factor
            if direction != "FLAT"
            else D(0)
        )
        budget = max(D(0), D(total)) * (
            1 - max(D(0), min(D(100), D(config.get("cash_reserve_pct", 20)))) / 100
        )
        max_position = max(D(0), D(config.get("max_position_pct", 5))) / 100
        target_abs = max(D(0), D(total)) * max_position * sizing_strength
        current = D(current_eur)
        target = (
            target_abs
            if direction == "LONG"
            else -target_abs
            if direction == "SHORT"
            else current
            if direction == "HOLD"
            else D(0)
        )
        delta = target - current

        if direction in ("LONG", "SHORT"):
            action = "BUY" if delta > 0 else "SELL" if delta < 0 else "HOLD"
        elif direction == "HOLD":
            action = "HOLD"
        else:
            action = "SELL" if current > 0 else "HOLD"

        # Positive edge is required when exposure is increased. Reducing an
        # existing exposure is risk-reducing and remains allowed even with weak edge.
        exposure_reduction = abs(target) < abs(current)
        same_sign_reduction = exposure_reduction and (target == 0 or target * current > 0)
        increasing_or_flip = abs(target) > abs(current) or (target * current < 0)
        economic_ok = (
            direction == "HOLD"
            or same_sign_reduction
            or (not increasing_or_flip and target == current)
            or (edge_after_costs is not None and edge_after_costs > 0)
        )

        return {
            "symbol": row.get("symbol"),
            "direction": direction,
            "signal": row.get("signal"),
            "score": str(score),
            "buy_threshold": str(threshold),
            "quality_score": str(quality * 100),
            "avoid_threshold": str(avoid_threshold),
            "regime": regime,
            "regime_factor": str(regime_factor),
            "volatility_pct": str(volatility),
            "volatility_factor": str(volatility_factor),
            "signal_strength": str(signal_strength),
            "quality_factor": str(quality_factor),
            "cost_factor": str(cost_factor),
            "roundtrip_cost_pct": str(D(roundtrip_cost_pct)),
            "expected_edge_gross_pct": str(gross_edge) if gross_edge is not None else None,
            "expected_edge_after_costs_pct": str(edge_after_costs) if edge_after_costs is not None else None,
            "news_score": str(row.get("news_score") or 0),
            "target_exposure_eur": str(target),
            "current_exposure_eur": str(current),
            "rebalance_delta_eur": str(delta),
            "action": action,
            "economic_gate_passed": bool(economic_ok),
            "edge_status": (
                "KNOWN_POSITIVE"
                if edge_after_costs is not None and edge_after_costs > 0
                else "KNOWN_NON_POSITIVE"
                if edge_after_costs is not None
                else "UNKNOWN"
            ),
            "quality_role": "SIZING_AND_CONFIDENCE",
            "decision_basis": {
                "score": "CONVICTION",
                "model_quality": "SIZING_AND_CONFIDENCE",
                "regime": "RISK_ALIGNMENT",
                "costs": "ROUNDTRIP_ENTRY_PLUS_ESTIMATED_EXIT",
                "news": "ALREADY_INCLUDED_IN_SCANNER_SCORE; NO_UNCALIBRATED_EDGE_ADDITION",
            },
        }

    def target_rows(
        self,
        rows,
        health_by_family,
        total,
        current_by_symbol,
        config,
        regime_by_family,
        route_costs,
        allow_short=False,
    ):
        decisions = []
        for row in rows:
            family = row.get("family", "crypto_spot")
            health = health_by_family.get(family, {})
            regime = regime_by_family.get(family, {}).get("regime", "NEUTRAL")
            decisions.append(
                self.build(
                    row,
                    health,
                    total,
                    current_by_symbol.get(row.get("symbol"), 0),
                    route_costs.get(row.get("symbol"), 999),
                    regime,
                    config,
                    row.get("symbol") in current_by_symbol,
                    allow_short=allow_short,
                )
            )
        # Portfolio-wide normalization: individual caps alone can still
        # over-allocate when many candidates qualify. Scale absolute targets
        # together so the reserved cash budget remains a hard portfolio limit.
        budget=max(D(0),D(total))*(
            1-max(D(0),min(D(100),D(config.get("cash_reserve_pct",20))))/100
        )
        gross=sum(abs(D(x.get("target_exposure_eur"))) for x in decisions)
        if gross>budget and gross>0:
            factor=budget/gross
            for x in decisions:
                target=D(x.get("target_exposure_eur"))*factor
                current=D(x.get("current_exposure_eur"))
                x["target_exposure_eur"]=str(target)
                x["rebalance_delta_eur"]=str(target-current)
                if x["direction"] in ("LONG","SHORT"):
                    x["action"]="BUY" if target-current>0 else "SELL" if target-current<0 else "HOLD"
            for x in decisions:
                x["portfolio_budget_scale"]=str(factor)
        else:
            for x in decisions:
                x["portfolio_budget_scale"]="1"
        return decisions

    def record(
        self,
        environment,
        decision,
        execution_symbol=None,
        execution_mode=None,
        leverage=1,
        status="PROPOSED",
        reason="",
    ):
        if self.db is None:
            return
        with self.db.con() as c:
            c.execute(
                """INSERT INTO decision_snapshots(
                   created_at,environment,symbol,action,direction,target_exposure_eur,
                   current_exposure_eur,delta_eur,expected_edge_gross_pct,
                   expected_edge_after_costs_pct,quality_score,regime,news_score,
                   execution_symbol,execution_mode,leverage,status,reason,decision_json)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    now(),
                    str(environment),
                    decision.get("symbol") or "",
                    decision.get("action") or "HOLD",
                    decision.get("direction") or "FLAT",
                    decision.get("target_exposure_eur") or "0",
                    decision.get("current_exposure_eur") or "0",
                    decision.get("rebalance_delta_eur") or "0",
                    decision.get("expected_edge_gross_pct"),
                    decision.get("expected_edge_after_costs_pct"),
                    decision.get("quality_score"),
                    decision.get("regime"),
                    decision.get("news_score"),
                    execution_symbol,
                    execution_mode,
                    str(leverage),
                    status,
                    reason,
                    json.dumps(decision, sort_keys=True, default=str),
                ),
            )

    def latest(self, environment=None, limit=50):
        q = "SELECT * FROM decision_snapshots"
        args = []
        if environment:
            q += " WHERE environment=?"
            args.append(str(environment))
        q += " ORDER BY id DESC LIMIT ?"
        args.append(max(1, min(200, int(limit))))
        try:
            return self.db.rows(q, tuple(args))
        except Exception:
            return []
