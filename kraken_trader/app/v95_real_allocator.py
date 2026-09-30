"""v95 Real execution adapter for the shared DecisionEngineV95."""

import json
import secrets
import threading
from decimal import Decimal
from db import now
from model_health import ModelHealth
from execution_confidence import execution_confidence, choose_execution
from decision_engine_v95 import DecisionEngineV95
from decision_context_v95 import ticker_map, scanner_candidates, routes_for_symbol, alternatives, decision_costs
from market_regime import family_regime
from strategy_profiles import family_for_category

D = lambda x: Decimal(str(x or 0))


def safe_json(value):
    return json.dumps(value, sort_keys=True, default=str)


class RealPortfolioAllocatorV95:
    def __init__(self, db, trade_engine):
        from real_portfolio_allocator import RealPortfolioAllocator
        self.base = RealPortfolioAllocator(db, trade_engine)
        self.db = db
        self.trade_engine = trade_engine
        self.lock = threading.Lock()

    def _existing_execution(self, symbol, cfg):
        try:
            rows=self.db.rows('SELECT side,leverage FROM real_margin_positions WHERE symbol=? LIMIT 1',(symbol,))
        except Exception:
            rows=[]
        if rows and cfg['margin_enabled']:
            lev=D(rows[0].get('leverage') or cfg['margin_default_leverage'])
            return {'mode':'MARGIN','leverage':min(lev,cfg['margin_max_leverage']),'reason':'EXISTING_MARGIN_POSITION_ROUTING'}
        return {'mode':'SPOT','leverage':D(1),'reason':'EXISTING_SPOT_POSITION_ROUTING'}

    def settings(self):
        return self.base.settings()

    def balances(self):
        return self.base.balances()

    def _asset(self, code):
        return self.base._asset(code)

    def _current_eur(self):
        current, total = self.base._current_eur()
        if not self.settings()["margin_enabled"]:
            return current, total
        try:
            self.trade_engine.refresh_margin_state()
            account=self.db.rows("SELECT equity FROM real_margin_account WHERE id=1 LIMIT 1")
            if account and D(account[0].get("equity"))>0:
                total=D(account[0]["equity"])
            positions=self.db.rows("SELECT symbol,side,current_value FROM real_margin_positions")
            mt=ticker_map(self.db, int(float(self.db.value("decision_market_data_max_age_seconds","120"))))
            for pos in positions:
                value=D(pos.get("current_value") or 0)
                if value<=0:
                    continue
                symbol=str(pos.get("symbol") or "")
                quote=symbol.rsplit("/",1)[-1].upper()
                if quote=="USD":
                    fx=mt.get("EUR/USD") or {}
                    rate=D((fx.get("c") or [0])[0])
                    if rate>0:
                        value=value/rate
                    else:
                        continue
                asset=self._asset(symbol.split("/",1)[0])
                current[asset]=current.get(asset,D(0)) + (value if str(pos.get("side")).lower()=="buy" else -value)
        except Exception:
            pass
        return current, total

    def _fee_values(self):
        return decision_costs(self.db)

    def _held_symbols(self, tickers, current):
        symbols = []
        for asset, value in current.items():
            if value == 0 or asset in ("EUR", "USD"):
                continue
            rows = self.db.rows(
                "SELECT symbol FROM market_universe WHERE base_asset IN (?,?) "
                "AND quote_asset='EUR' ORDER BY symbol LIMIT 1",
                (asset, "XBT" if asset == "BTC" else asset),
            )
            if rows:
                symbols.append(rows[0]["symbol"])
        return symbols

    @staticmethod
    def _current_map_for_symbol(current, symbol):
        asset = symbol.split("/", 1)[0].upper().replace("XBT", "BTC")
        return current.get(asset, D(0))

    def _volume_price(self, symbol, side, trade_eur, tickers):
        t = tickers.get(symbol) or {}
        bid = D((t.get("b") or [0])[0])
        ask = D((t.get("a") or [0])[0])
        last = D((t.get("c") or [0])[0])
        price = ask if side == "buy" else bid
        if price <= 0:
            price = last
        if price <= 0:
            raise ValueError("Kein Ausführungspreis für " + symbol)
        quote = symbol.rsplit("/", 1)[-1].upper()
        eur_notional = D(trade_eur)
        if quote == "USD":
            fx = tickers.get("EUR/USD") or {}
            rate = D(((fx.get("b") if side == "buy" else fx.get("a")) or [0])[0])
            if rate <= 0:
                rate = D((fx.get("c") or [0])[0])
            if rate <= 0:
                raise ValueError("EUR/USD fehlt")
            eur_notional *= rate
        return eur_notional / price, price

    def _record(self, engine, environment, decision, execution_symbol, execution_mode, leverage, status, reason):
        engine.record(
            environment,
            decision,
            execution_symbol=execution_symbol,
            execution_mode=execution_mode,
            leverage=leverage,
            status=status,
            reason=reason,
        )

    def run(self, automatic=False, approval_token=None):
        if not self.lock.acquire(False):
            return {"status": "BUSY"}
        run_id = None
        try:
            cfg = self.settings()
            if automatic and not cfg["enabled"]:
                return {"status": "DISABLED"}

            try:
                self.base._refresh_private_balances()
            except Exception:
                pass
            current, total = self._current_eur()
            tickers = ticker_map(self.db, int(float(self.db.value('decision_market_data_max_age_seconds','120'))))
            fee_bps, fx_fee_bps, slippage_bps = self._fee_values()
            families = ("crypto_spot", "xstocks", "forex")
            health = ModelHealth(self.db)
            health_by = {
                family: health.evaluate(
                    family,
                    require_long_horizon=False,
                    max_drawdown_pct=float(self.db.value('decision_max_drawdown_pct','-25')),
                )
                for family in families
            }
            regimes = {family: family_regime(self.db, family, max_age_minutes=int(float(self.db.value('decision_max_scanner_age_minutes','120')))) for family in families}

            candidates = scanner_candidates(self.db, cfg["allowed_symbols"], max_age_minutes=int(float(self.db.value('decision_max_scanner_age_minutes','120'))))
            enriched = []
            for row in candidates:
                route = routes_for_symbol(self.db, row["symbol"], tickers, fee_bps, fx_fee_bps, slippage_bps)
                row = dict(row)
                row["route_context"] = route
                row["roundtrip_cost_pct"] = route.get("roundtrip_cost_pct") if route.get("roundtrip_cost_pct") is not None else D(999)
                cat = row.get("category") or "crypto_spot"
                family = family_for_category(cat)
                row["family"] = family
                profile_rows = self.db.rows(
                    "SELECT parameters_json FROM parameter_family_versions "
                    "WHERE family=? AND status='ACTIVE' ORDER BY version DESC LIMIT 1",
                    (family,),
                )
                params = {}
                if profile_rows:
                    try: params = json.loads(profile_rows[0]["parameters_json"])
                    except Exception: params = {}
                row["buy_threshold"] = params.get("buy_threshold", cfg["minimum_score"])
                row["avoid_threshold"] = params.get("avoid_threshold", 35)
                enriched.append(row)

            existing_symbols = {x["symbol"] for x in enriched}
            for symbol in self._held_symbols(tickers, current):
                if symbol in existing_symbols:
                    continue
                route = routes_for_symbol(self.db, symbol, tickers, fee_bps, fx_fee_bps, slippage_bps)
                enriched.append({
                    "symbol": symbol,
                    "score": 0,
                    "momentum_pct": 0,
                    "trend_pct": 0,
                    "volatility_pct": 0,
                    "spread_pct": 0,
                    "news_score": 0,
                    "signal": "HOLD",
                    "quality": "VALID",
                    "family": family_for_category("crypto_spot"),
                    "buy_threshold": cfg["minimum_score"],
                    "avoid_threshold": 35,
                    "roundtrip_cost_pct": route.get("roundtrip_cost_pct") if route.get("roundtrip_cost_pct") is not None else D(999),
                    "route_context": route,
                })

            engine = DecisionEngineV95(self.db)
            allow_short = bool(cfg["margin_enabled"] and cfg["margin_allow_shorts"])
            current_by = {row["symbol"]: self._current_map_for_symbol(current, row["symbol"]) for row in enriched}
            route_costs = {row["symbol"]: D(row["roundtrip_cost_pct"]) for row in enriched}
            decisions = engine.target_rows(
                enriched,
                health_by,
                total,
                current_by,
                {
                    "minimum_score": D(self.db.value("decision_minimum_score","70")),
                    "max_position_pct": D(self.db.value("decision_max_position_pct","5")),
                    "cash_reserve_pct": D(self.db.value("decision_cash_reserve_pct","20")),
                    "volatility_reference_pct": D(self.db.value("decision_volatility_reference_pct", "2")),
                },
                regimes,
                route_costs,
                allow_short=allow_short,
            )

            with self.db.con() as c:
                cur = c.execute(
                    "INSERT INTO real_allocation_runs(created_at,status,automatic,settings_json,details_json) VALUES(?,?,?,?,?)",
                    (now(), "RUNNING", int(automatic), safe_json(cfg), "{}"),
                )
                run_id = cur.lastrowid

            submitted_today = int(self.db.rows(
                "SELECT COUNT(*) n FROM real_allocation_actions "
                "WHERE status='SUBMITTED' AND date(created_at)=date('now')"
            )[0]["n"])
            capacity = min(cfg["max_actions_per_run"], max(0, cfg["max_actions_per_day"] - submitted_today))
            actions = []

            for decision in sorted(
                decisions,
                key=lambda x: abs(D(x["rebalance_delta_eur"])),
                reverse=True,
            ):
                delta = D(decision["rebalance_delta_eur"])
                if abs(delta) < cfg["min_trade_eur"]:
                    continue
                if abs(delta) / max(D(1), total) * 100 < cfg["no_trade_band_pct"]:
                    continue

                symbol = decision["symbol"]
                cand = next((x for x in enriched if x["symbol"] == symbol), None)
                if not cand:
                    continue
                side = "buy" if delta > 0 else "sell"
                route_key = "buy" if side == "buy" else "sell"
                route_ctx = cand["route_context"].get(route_key) or {}
                selected = route_ctx.get("market")
                cost = route_ctx.get("cost") or {}
                if not selected or route_ctx.get("status") != "VALID":
                    self._record(engine, "REAL", decision, None, "BLOCKED", 0, "BLOCKED", "NO_VALID_EXECUTION_ROUTE")
                    continue

                execution_symbol = selected["symbol"]
                family = cand["family"]
                h = health_by[family]
                reducing = abs(D(decision["target_exposure_eur"])) < abs(D(decision["current_exposure_eur"])) and D(decision["target_exposure_eur"]) * D(decision["current_exposure_eur"]) >= 0
                if reducing:
                    confidence = execution_confidence(
                        decision["score"], h, None, regime=decision["regime"],
                        direction="UP" if side == "buy" else "DOWN",
                    )
                    execution = self._existing_execution(execution_symbol, cfg)
                    execution["confidence"] = str(confidence)
                else:
                    calibration = (
                        health.margin_calibration(
                            family, "UP" if side == "buy" else "DOWN", 24, 20, cfg["max_drawdown_pct"]
                        )
                        if cfg["margin_enabled"]
                        else {"status": "READY", "direction": "SPOT"}
                    )
                    confidence = execution_confidence(
                        decision["score"], h, calibration if calibration.get("status") == "READY" else None,
                        regime=decision["regime"], direction="UP" if side == "buy" else "DOWN",
                    )
                    execution = choose_execution(
                        confidence, cfg["margin_enabled"], cfg["margin_max_leverage"],
                        cfg["confidence_spot_min"], cfg["confidence_margin_2x"],
                        cfg["confidence_margin_3x"], cfg["confidence_margin_4x"],
                        cfg["confidence_margin_5x"],
                        calibration=calibration if calibration.get("status") == "READY" else None,
                    )
                risk_reduction = reducing
                is_exit = risk_reduction and D(decision["target_exposure_eur"]) == 0
                if execution["mode"] == "BLOCKED":
                    self._record(engine, "REAL", decision, execution_symbol, execution["mode"], execution["leverage"], "BLOCKED", execution["reason"])
                    continue

                trade_eur = min(abs(delta), cfg["max_trade_eur"])
                volume, price = self._volume_price(execution_symbol, side, trade_eur, tickers)
                meta = next((x for x in alternatives(self.db, symbol) if x.get("symbol") == execution_symbol), {})
                order_ok = (
                    (not meta.get("ordermin") or volume >= D(meta.get("ordermin")))
                    and (not meta.get("costmin") or volume * price >= D(meta.get("costmin")))
                )
                if not order_ok:
                    self._record(engine, "REAL", decision, execution_symbol, execution["mode"], execution["leverage"], "BLOCKED", "KRAKEN_ORDER_CONSTRAINT")
                    continue

                ctx = {
                    "canonical_id": symbol,
                    "confirmation_count": 1,
                    "confirmation_required": 1,
                    "minimum_hold_ok": True,
                    "cooldown_ok": True,
                    "daily_limit_ok": True,
                    "improvement_after_costs": str(max(D(0), D(decision["expected_edge_after_costs_pct"] or 0)) * trade_eur / 100),
                    "economic_edge_ok": bool(decision.get("economic_gate_passed")) and (risk_reduction or D(decision.get("expected_edge_after_costs_pct") or 0)>0),
                    "exit_risk_override": risk_reduction,
                    "execution_confidence": str(confidence),
                    "execution_mode": execution["mode"],
                    "execution_leverage": str(execution["leverage"]),
                    "execution_confidence_ok": execution["mode"] != "BLOCKED",
                    "execution_confidence_reason": execution["reason"],
                    "tax_loss_ok": True,
                    "data_fresh": execution_symbol in tickers,
                    "model_health_ok": True,
                    "model_health_details": {"role": "QUALITY_AND_SIZING", "health": h},
                    "route_cost_ok": True,
                    "route_cost_details": cost,
                    "quote_funding_ok": True,
                    "portfolio_risk_ok": True,
                    "portfolio_risk_details": {"target_eur": decision["target_exposure_eur"], "total_eur": str(total)},
                    "order_constraints_ok": True,
                    "order_constraints_details": {"volume": str(volume), "price": str(price)},
                    "real_trading_enabled": self.trade_engine.enabled(),
                    "real_kill_switch_clear": self.db.value("real_kill_switch", "true").lower() != "true",
                    "real_limits_ok": trade_eur <= cfg["max_trade_eur"],
                    "real_balance_ok": total > 0,
                }
                matrix = __import__("decision_matrix").DecisionMatrix(self.db).evaluate(symbol, side.upper(), ctx, "REAL")
                status = "BLOCKED"
                intent = None
                reason = matrix["blocker"]

                if automatic and cfg["dry_run"]:
                    status = "DRY_RUN"
                    reason = "DRY_RUN_CANONICAL_DECISION"
                elif automatic and cfg["automatic_execution"] and matrix["allowed"]:
                    secret = self.db.value("real_balancing_automation_secret", "")
                    result = self.trade_engine.submit(
                        execution_symbol,
                        side,
                        str(volume),
                        "limit",
                        str(price),
                        secrets.token_hex(16),
                        approval_token,
                        False,
                        secret,
                        leverage=execution["leverage"],
                        margin=(execution["mode"] == "MARGIN"),
                        reduce_only=risk_reduction,
                    )
                    status = result.get("status")
                    intent = result.get("client_order_id")
                    reason = result.get("status", "")
                elif matrix["allowed"]:
                    status = "PROPOSED"
                    reason = "ORDER_READY_BUT_AUTOMATIC_EXECUTION_DISABLED"

                self._record(engine, "REAL", decision, execution_symbol, execution["mode"], execution["leverage"], status, reason)
                with self.db.con() as c:
                    c.execute(
                        "INSERT INTO real_allocation_actions(run_id,created_at,symbol,side,current_eur,target_eur,difference_eur,status,decision_json,order_intent_id,error) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                        (run_id, now(), symbol, side, decision["current_exposure_eur"], decision["target_exposure_eur"], decision["rebalance_delta_eur"], status, safe_json({"canonical": decision, "matrix": matrix, "route": cand["route_context"]}), intent, None),
                    )
                actions.append({"symbol":symbol,"execution_symbol":execution_symbol,"side":side,"status":status,"decision":decision,"execution":execution,"matrix":matrix})
                if status == "SUBMITTED":
                    capacity -= 1
                    if capacity <= 0:
                        break

            with self.db.con() as c:
                c.execute(
                    "UPDATE real_allocation_runs SET finished_at=?,status=?,details_json=? WHERE id=?",
                    (now(), "COMPLETED", safe_json({"decisions":decisions,"actions":actions,"model_health":health_by,"regimes":regimes}), run_id),
                )
            return {
                "status": "COMPLETED",
                "run_id": run_id,
                "decisions": decisions,
                "actions": actions,
                "model_health": health_by,
                "regimes": regimes,
            }
        except Exception as exc:
            if run_id:
                with self.db.con() as c:
                    c.execute(
                        "UPDATE real_allocation_runs SET finished_at=?,status=?,error=? WHERE id=?",
                        (now(), "FAILED", type(exc).__name__ + ": " + str(exc)[:500], run_id),
                    )
            return {"status": "FAILED", "error": type(exc).__name__ + ": " + str(exc)[:500]}
        finally:
            self.lock.release()
