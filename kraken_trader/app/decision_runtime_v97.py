"""Shared v97 preparation context for Paper and Real decision runs.

Both environments call this object before planning. It refreshes the same Kraken
market-price cache and settles due forecasts; a short reuse window prevents two
back-to-back Paper/Real runs from seeing different prepared market inputs.
"""
from datetime import datetime, timezone

class DecisionRuntimeV97:
    def __init__(self, db, refresh_market=None, evaluate_forecasts=None):
        self.db = db
        self.refresh_market = refresh_market
        self.evaluate_forecasts = evaluate_forecasts
        self._prepared_at = None
        self._last_result = None
        self._ensure()

    def _ensure(self):
        with self.db.con() as c:
            c.execute("""CREATE TABLE IF NOT EXISTS decision_runtime_runs_v97(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                reused INTEGER NOT NULL,
                market_refresh_count INTEGER NOT NULL,
                forecasts_evaluated INTEGER NOT NULL,
                status TEXT NOT NULL,
                details_json TEXT NOT NULL
            )""")

    def prepare(self, force=False):
        now = datetime.now(timezone.utc)
        try:
            reuse = float(self.db.value("decision_shared_context_reuse_seconds", "10"))
        except (TypeError, ValueError):
            reuse = 10.0
        if (
            not force
            and self._prepared_at is not None
            and self._last_result is not None
            and (now - self._prepared_at).total_seconds() <= max(0.0, reuse)
        ):
            result = dict(self._last_result)
            result["reused"] = True
            with self.db.con() as c:
                c.execute(
                    "INSERT INTO decision_runtime_runs_v97(created_at,reused,market_refresh_count,forecasts_evaluated,status,details_json) VALUES(?,?,?,?,?,?)",
                    (now.isoformat(), 1, int(result["market_refresh_count"]), int(result["forecasts_evaluated"]), result["status"], "{}"),
                )
            return result

        market_count = 0
        forecast_count = 0
        warnings = []
        try:
            if callable(self.refresh_market):
                value = self.refresh_market()
                market_count = int(value or 0)
        except Exception as exc:
            warnings.append("MARKET_REFRESH_" + type(exc).__name__)
        try:
            if callable(self.evaluate_forecasts):
                value = self.evaluate_forecasts()
                forecast_count = int(value or 0)
        except Exception as exc:
            warnings.append("FORECAST_EVALUATION_" + type(exc).__name__)

        status = "READY" if not warnings else "READY_WITH_WARNINGS"
        result = {
            "status": status,
            "reused": False,
            "market_refresh_count": market_count,
            "forecasts_evaluated": forecast_count,
            "warnings": warnings,
            "prepared_at": now.isoformat(),
        }
        self._prepared_at = now
        self._last_result = dict(result)
        with self.db.con() as c:
            c.execute(
                "INSERT INTO decision_runtime_runs_v97(created_at,reused,market_refresh_count,forecasts_evaluated,status,details_json) VALUES(?,?,?,?,?,?)",
                (now.isoformat(), 0, market_count, forecast_count, status, str(result)),
            )
        return result
