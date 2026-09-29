"""v90 runtime: configurable model drawdown and dedicated existing-position risk exits."""
import v88_main as base

app = base.app
legacy = base.legacy
controller = base.controller
options = getattr(base, "options", {})


def v90_health():
    payload = base.v88_health()
    cfg = legacy.real_allocator.settings()
    payload = {
        **payload,
        "version": "0.1.0-dev.90",
        "runtime": "v90_main",
        "real_execution_model_health_gate": "H24_ONLY",
        "h168_role": "ADVISORY",
        "real_execution_max_drawdown_pct": str(cfg.get("max_drawdown_pct", "-25")),
        "existing_position_exit": {
            "enabled": True,
            "model_health_entry_gate_bypassed": True,
            "positive_after_costs_entry_gate_bypassed": True,
            "reason": "Held position without active BUY signal follows the dedicated exit-risk path.",
        },
    }
    return payload


if "v90_health" not in app.view_functions:
    app.add_url_rule("/v90-health", "v90_health", v90_health)
