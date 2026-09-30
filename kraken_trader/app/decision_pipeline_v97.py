"""KTKI v97 canonical decision settings and portfolio plan.

This module deliberately contains no Paper/Real execution code. It is the single
decision path used by both environments.
"""
import hashlib
import json
from datetime import datetime, timezone
from decimal import Decimal

from decision_context_v95 import ticker_map, scanner_candidates, routes_for_symbol, decision_costs
from strategy_profiles import active_profile, family_for_category
from model_health import ModelHealth
from market_regime import family_regime

D=lambda x:Decimal(str(x or 0))

DEFAULTS={
    "decision_minimum_score":"70",
    "decision_max_position_pct":"5",
    "decision_cash_reserve_pct":"20",
    "decision_min_trade_eur":"20",
    "decision_max_trade_eur":"250",
    "decision_no_trade_band_pct":"2",
    "decision_fee_bps":"40",
    "decision_fx_fee_bps":"10",
    "decision_slippage_bps":"10",
    "decision_min_edge_samples":"10",
    "decision_volatility_reference_pct":"2",
    "decision_market_data_max_age_seconds":"120",
    "decision_max_scanner_age_minutes":"120",
    "decision_max_drawdown_pct":"-25",
    "decision_full_size_edge_pct":"2",
    "decision_confirmation_runs":"2",
    "decision_min_hold_hours":"24",
    "decision_cooldown_hours":"12",
    "decision_max_turnovers_per_day":"2",
    "decision_max_actions_per_run":"1",
    "decision_max_actions_per_day":"2",
    "decision_confidence_spot_min":"65",
    "decision_confidence_margin_2x":"78",
    "decision_confidence_margin_3x":"86",
    "decision_confidence_margin_4x":"93",
    "decision_confidence_margin_5x":"97",
    "decision_allow_shorts":"false",
}

class CanonicalDecisionPlannerV97:
    def __init__(self,db):
        self.db=db
        self.ensure()

    def ensure(self):
        with self.db.con() as c:
            c.execute("""CREATE TABLE IF NOT EXISTS decision_plan_runs_v97(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                environment TEXT NOT NULL,
                plan_hash TEXT NOT NULL,
                total_eur TEXT NOT NULL,
                candidate_count INTEGER NOT NULL,
                decision_count INTEGER NOT NULL,
                settings_json TEXT NOT NULL,
                context_json TEXT NOT NULL
            )""")
            c.execute("CREATE INDEX IF NOT EXISTS idx_decision_plan_v97_hash ON decision_plan_runs_v97(plan_hash,created_at DESC)")

    def settings(self):
        out={}
        for key,default in DEFAULTS.items():
            value=self.db.value(key,default)
            out[key]=value
        for key in ("decision_minimum_score","decision_max_position_pct","decision_cash_reserve_pct","decision_min_trade_eur",
                    "decision_max_trade_eur","decision_no_trade_band_pct","decision_min_edge_samples",
                    "decision_volatility_reference_pct","decision_max_scanner_age_minutes","decision_max_drawdown_pct",
                    "decision_full_size_edge_pct","decision_confirmation_runs","decision_min_hold_hours",
                    "decision_cooldown_hours","decision_max_turnovers_per_day","decision_max_actions_per_run",
                    "decision_max_actions_per_day","decision_confidence_spot_min","decision_confidence_margin_2x",
                    "decision_confidence_margin_3x","decision_confidence_margin_4x","decision_confidence_margin_5x"):
            try: out[key]=float(out[key])
            except Exception: out[key]=float(DEFAULTS[key])
        out["decision_allow_shorts"]=str(out["decision_allow_shorts"]).lower()=="true"
        return out

    def _fresh_tickers(self,settings):
        return ticker_map(self.db,int(settings["decision_market_data_max_age_seconds"]))

    def _health(self,settings):
        mh=ModelHealth(self.db)
        return {
            family:mh.evaluate(
                family,
                require_long_horizon=False,
                max_drawdown_pct=settings["decision_max_drawdown_pct"],
            )
            for family in ("crypto_spot","xstocks","forex")
        }

    def _regimes(self,settings):
        return {
            family:family_regime(
                self.db,
                family,
                max_age_minutes=settings["decision_max_scanner_age_minutes"],
            )
            for family in ("crypto_spot","xstocks","forex")
        }

    @staticmethod
    def _candidate_profile(db,family,minimum_score):
        version,params=active_profile(db,family)
        return version,params,params.get("buy_threshold",minimum_score),params.get("avoid_threshold",35)

    def _enrich(self,settings,tickers):
        out=[]
        for row in scanner_candidates(self.db,max_age_minutes=settings["decision_max_scanner_age_minutes"]):
            row=dict(row)
            family=row.get("family") or family_for_category(row.get("category") or "crypto_spot")
            version,params,buy_threshold,avoid_threshold=self._candidate_profile(
                self.db,family,settings["decision_minimum_score"]
            )
            route=routes_for_symbol(
                self.db,row["symbol"],tickers,
                settings["decision_fee_bps"],
                settings["decision_fx_fee_bps"],
                settings["decision_slippage_bps"],
            )
            row.update({
                "family":family,
                "parameter_version":version,
                "buy_threshold":buy_threshold,
                "avoid_threshold":avoid_threshold,
                "route_context":route,
                "roundtrip_cost_pct":route.get("roundtrip_cost_pct")
                    if route.get("roundtrip_cost_pct") is not None else D(999),
            })
            out.append(row)
        return out

    def _held_rows(self,current_by_symbol,settings,tickers,enriched):
        known={str(x["symbol"]).upper() for x in enriched}
        rows=[]
        for symbol,current in current_by_symbol.items():
            symbol=str(symbol).upper()
            if D(current)==0 or symbol in known:continue
            route=routes_for_symbol(
                self.db,symbol,tickers,
                settings["decision_fee_bps"],
                settings["decision_fx_fee_bps"],
                settings["decision_slippage_bps"],
            )
            category=self.db.value("fallback_category_"+symbol,"crypto_spot")
            rows.append({
                "symbol":symbol,
                "family":family_for_category(category),
                "parameter_version":None,
                "score":0,
                "signal":"HOLD",
                "momentum_pct":0,
                "trend_pct":0,
                "volatility_pct":0,
                "spread_pct":0,
                "news_score":0,
                "buy_threshold":settings["decision_minimum_score"],
                "avoid_threshold":35,
                "route_context":route,
                "roundtrip_cost_pct":route.get("roundtrip_cost_pct")
                    if route.get("roundtrip_cost_pct") is not None else D(999),
                "quality":"VALID",
                "held_only":True,
            })
        return rows

    def _canonical_symbol(self,symbol):
        rows=self.db.rows("SELECT canonical_id FROM market_universe WHERE symbol=? LIMIT 1",(symbol,))
        cid=rows[0].get("canonical_id") if rows else None
        if cid:
            selected=self.db.rows(
                "SELECT symbol FROM market_universe WHERE canonical_id=? ORDER BY CASE WHEN quote_asset='EUR' THEN 0 ELSE 1 END,symbol LIMIT 1",
                (cid,),
            )
            if selected:return selected[0]["symbol"]
        return symbol

    def _canonical_current(self,current_by_symbol):
        out={}
        for symbol,value in (current_by_symbol or {}).items():
            canonical=self._canonical_symbol(symbol)
            out[canonical]=D(out.get(canonical,0))+D(value)
        return out

    @staticmethod
    def _plan_hash(settings,tickers,enriched,current,total,health,regimes):
        payload={
            "settings":settings,
            "tickers":tickers,
            "candidates":enriched,
            "current":current,
            "total":str(total),
            "health":health,
            "regimes":regimes,
        }
        return hashlib.sha256(
            json.dumps(payload,sort_keys=True,default=str,separators=(",",":")).encode()
        ).hexdigest()

    def build(self,total_eur,current_by_symbol,environment="PAPER",allow_short=None):
        from decision_engine_v97 import DecisionEngineV97
        settings=self.settings()
        if allow_short is None:allow_short=settings["decision_allow_shorts"]
        current_by_symbol=self._canonical_current(current_by_symbol)
        tickers=self._fresh_tickers(settings)
        health=self._health(settings)
        regimes=self._regimes(settings)
        enriched=self._enrich(settings,tickers)
        enriched.extend(self._held_rows(current_by_symbol,settings,tickers,enriched))
        route_costs={x["symbol"]:D(x["roundtrip_cost_pct"]) for x in enriched}
        decisions=DecisionEngineV97(self.db).target_rows(
            enriched,health,total_eur,current_by_symbol,settings,regimes,route_costs,allow_short=allow_short
        )
        plan_hash=self._plan_hash(settings,tickers,enriched,current_by_symbol,total_eur,health,regimes)
        by_symbol={x["symbol"]:x for x in enriched}
        ranked=[]
        for decision in decisions:
            source=by_symbol.get(decision["symbol"],{})
            decision["route_context"]=source.get("route_context",{})
            decision["parameter_version"]=source.get("parameter_version")
            delta=D(decision["rebalance_delta_eur"])
            edge=D(decision.get("expected_edge_after_costs_pct"))
            trade=D(min(abs(delta),D(settings["decision_max_trade_eur"])))
            if trade<=0:benefit=D(0)
            elif delta>0:benefit=max(D(0),edge)*trade/100
            else:benefit=max(D(0),-edge)*trade/100
            action_type=(
                "ENTRY" if D(decision["current_exposure_eur"])==0 and D(decision["target_exposure_eur"])!=0 else
                "REBALANCE_UP" if delta>0 else
                "EXIT" if D(decision["target_exposure_eur"])==0 and D(decision["current_exposure_eur"])!=0 else
                "REBALANCE_DOWN" if delta<0 else "HOLD"
            )
            decision.update({
                "action_type":action_type,
                "marginal_benefit_eur":str(benefit),
                "trade_eur_cap":str(trade),
                "plan_hash":plan_hash,
            })
            ranked.append(decision)
        ranked.sort(key=lambda x:(-D(x["marginal_benefit_eur"]),-abs(D(x["rebalance_delta_eur"])),x["symbol"]))
        payload={"settings":settings,"tickers":tickers,"candidate_count":len(enriched),"decision_count":len(ranked),"health":health,"regimes":regimes}
        with self.db.con() as c:
            c.execute(
                "INSERT INTO decision_plan_runs_v97(created_at,environment,plan_hash,total_eur,candidate_count,decision_count,settings_json,context_json) VALUES(?,?,?,?,?,?,?,?)",
                (datetime.now(timezone.utc).isoformat(),str(environment),plan_hash,str(total_eur),len(enriched),len(ranked),
                 json.dumps(settings,sort_keys=True),json.dumps(payload,sort_keys=True,default=str))
            )
        return {
            "version":"0.1.0-dev.96",
            "environment":environment,
            "plan_hash":plan_hash,
            "total_eur":str(total_eur),
            "settings":settings,
            "tickers":tickers,
            "candidates":enriched,
            "decisions":ranked,
            "health":health,
            "regimes":regimes,
        }
