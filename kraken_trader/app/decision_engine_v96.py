"""v96 canonical portfolio decision engine.

Target sizing is economic: conviction controls direction, directional historical
edge controls whether new risk is allowed, model quality/regime/volatility scale
the size, and route cost is subtracted once.
"""
import json
from decimal import Decimal
from db import now

D=lambda x:Decimal(str(x or 0))

class DecisionEngineV96:
    def __init__(self,db):
        self.db=db

    @staticmethod
    def clamp(v,lo=0,hi=1):
        return max(D(lo),min(D(hi),D(v)))

    @staticmethod
    def direction(row,allow_short=False):
        signal=str(row.get("signal") or "").upper()
        m=D(row.get("momentum_pct"));t=D(row.get("trend_pct"))
        if signal=="BUY" and m>0 and t>0:return "LONG"
        if signal=="AVOID" and m<0 and t<0 and allow_short:return "SHORT"
        if signal=="HOLD":return "HOLD"
        if signal=="AVOID":return "FLAT"
        return "FLAT"

    @staticmethod
    def regime_factor(regime,direction):
        r=str(regime or "NEUTRAL").upper()
        if direction=="LONG":
            return {"BULL":D("1"),"NEUTRAL":D(".70"),"MIXED":D(".55"),"BEAR":D(".30")}.get(r,D(".50"))
        if direction=="SHORT":
            return {"BEAR":D("1"),"NEUTRAL":D(".70"),"MIXED":D(".55"),"BULL":D(".30")}.get(r,D(".50"))
        return D(0)

    def _empirical_edge(self,symbol,direction,limit=40):
        if not self.db or not symbol:return None
        wanted="UP" if direction=="LONG" else "DOWN"
        try:
            rows=self.db.rows(
                "SELECT e.actual_return_pct FROM research_forecasts f "
                "JOIN forecast_evaluations e ON e.forecast_id=f.id "
                "WHERE f.symbol=? AND f.horizon_hours=24 AND f.direction=? "
                "ORDER BY f.id DESC LIMIT ?",
                (symbol,wanted,int(limit)),
            )
        except Exception:return None
        minimum=int(float(self.db.value("decision_min_edge_samples","10")))
        if len(rows)<minimum:return None
        vals=[]
        for row in rows:
            actual=D(row.get("actual_return_pct"))
            vals.append(actual if wanted=="UP" else -actual)
        return sum(vals)/D(len(vals)) if vals else None

    def gross_edge(self,row,direction,health):
        explicit=row.get("expected_edge_pct")
        if explicit not in (None,""):
            try:return D(explicit)
            except Exception:pass
        empirical=self._empirical_edge(row.get("symbol"),direction)
        if empirical is not None:return empirical
        dkey="UP" if direction=="LONG" else "DOWN"
        item=(health or {}).get("directions",{}).get(dkey,{})
        mean=item.get("mean_edge_after_costs_pct")
        if mean is not None:
            # health mean is already after historical costs; add the configured
            # route cost back before the engine subtracts the current route cost.
            historical_cost=D(item.get("historical_roundtrip_cost_pct") or 0)
            return D(mean)+historical_cost
        return None

    @staticmethod
    def directional_quality(health,direction):
        dkey="UP" if direction=="LONG" else "DOWN"
        q=(health or {}).get("quality_score_by_direction",{}).get(dkey)
        if q is not None:return D(q)
        return D((health or {}).get("quality_score",50))

    def build(self,row,health,total,current_eur,roundtrip_cost_pct,regime,config,existing=False,allow_short=False):
        direction=self.direction(row,allow_short)
        current=D(current_eur)
        total=D(total)
        max_position=max(D("0"),D(config.get("decision_max_position_pct",5)))/100
        budget=total*(1-max(D("0"),min(D("100"),D(config.get("decision_cash_reserve_pct",20))))/100)
        score=D(row.get("score"))
        threshold=D(row.get("buy_threshold",config.get("decision_minimum_score",70)))
        avoid_threshold=D(row.get("avoid_threshold",35))
        conviction=(
            self.clamp((score-threshold)/max(D(1),D(100)-threshold))
            if direction=="LONG"
            else self.clamp((avoid_threshold-score)/max(D(1),avoid_threshold))
            if direction=="SHORT"
            else D(0)
        )
        qscore=self.directional_quality(health,direction) if direction in ("LONG","SHORT") else D(50)
        quality_factor=D(".60")+D(".40")*self.clamp(qscore/100)
        risk_state=str((health or {}).get("risk_state","OK")).upper()
        risk_factor={"OK":D("1"),"CAUTION":D(".70"),"WEAK":D(".45"),"INSUFFICIENT_DATA":D(".30")}.get(risk_state,D(".50"))
        quality_factor*=risk_factor
        regime_factor=self.regime_factor(regime,direction)
        volatility=max(D(".25"),abs(D(row.get("volatility_pct") or 0)))
        vol_ref=max(D(".25"),D(config.get("decision_volatility_reference_pct",2)))
        volatility_factor=min(D(1),vol_ref/volatility)
        gross=self.gross_edge(row,direction,health) if direction in ("LONG","SHORT") else None
        route_cost=D(roundtrip_cost_pct)
        net=(gross-route_cost) if gross is not None else None
        full_size_edge=max(D(".1"),D(config.get("decision_full_size_edge_pct",2)))
        edge_factor=self.clamp(max(D(0),net)/full_size_edge) if net is not None else D(0)
        strength=conviction*quality_factor*regime_factor*volatility_factor*edge_factor
        target=(
            total*max_position*strength if direction=="LONG"
            else -total*max_position*strength if direction=="SHORT"
            else (D(1) if current>0 else D(-1))*min(abs(current),budget*max_position)
                if direction=="HOLD" and current!=0
                else D(0)
        )
        delta=target-current
        action="BUY" if delta>0 else "SELL" if delta<0 else "HOLD"
        increasing=(abs(target)>abs(current)) or (target*current<0)
        reduction=(abs(target)<abs(current)) and (target*current>=0)
        economic_ok=(
            direction=="HOLD"
            or reduction
            or (delta==0 and current!=0)
            or (net is not None and net>0)
        )
        benefit=D(0)
        trade_cap=min(abs(delta),D(config.get("decision_max_trade_eur",250)))
        if delta>0 and net is not None:benefit=max(D(0),net)*trade_cap/100
        elif delta<0 and net is not None:benefit=max(D(0),-net)*trade_cap/100
        action_type=(
            "ENTRY" if delta>0 and current==0 else
            "REBALANCE_UP" if delta>0 else
            "EXIT" if target==0 and current!=0 else
            "REBALANCE_DOWN" if delta<0 else
            "HOLD"
        )
        return {
            "symbol":row.get("symbol"),
            "direction":direction,
            "signal":row.get("signal"),
            "family":row.get("family","crypto_spot"),
            "score":str(score),
            "buy_threshold":str(threshold),
            "avoid_threshold":str(avoid_threshold),
            "quality_score":str(qscore),
            "quality_role":"DIRECTIONAL_SIZING",
            "regime":regime,
            "regime_factor":str(regime_factor),
            "volatility_pct":str(volatility),
            "volatility_factor":str(volatility_factor),
            "conviction":str(conviction),
            "expected_edge_gross_pct":str(gross) if gross is not None else None,
            "roundtrip_cost_pct":str(route_cost),
            "expected_edge_after_costs_pct":str(net) if net is not None else None,
            "edge_factor":str(edge_factor),
            "target_exposure_eur":str(target),
            "current_exposure_eur":str(current),
            "rebalance_delta_eur":str(delta),
            "action":action,
            "action_type":action_type,
            "marginal_benefit_eur":str(benefit),
            "economic_gate_passed":bool(economic_ok),
            "edge_status":"KNOWN_POSITIVE" if net is not None and net>0 else "KNOWN_NON_POSITIVE" if net is not None else "UNKNOWN",
            "news_score":str(row.get("news_score") or 0),
            "plan_hash":None,
            "decision_basis":{
                "score":"DIRECTIONAL_CONVICTION",
                "edge":"DIRECTIONAL_H24_EXPECTED_RETURN",
                "quality":"DIRECTIONAL_MODEL_QUALITY",
                "regime":"RISK_ALIGNMENT",
                "volatility":"RISK_SCALING",
                "costs":"CURRENT_ENTRY_PLUS_ESTIMATED_EXIT",
                "news":"SIGNED_FEATURE_IN_SCANNER",
            },
            "existing_position":bool(existing),
            "increasing_risk":bool(increasing),
        }

    def target_rows(self,rows,health_by_family,total,current_by_symbol,config,regime_by_family,route_costs,allow_short=False):
        decisions=[]
        for row in rows:
            family=row.get("family","crypto_spot")
            decisions.append(self.build(
                row,
                health_by_family.get(family,{}),
                total,
                current_by_symbol.get(row.get("symbol"),0),
                route_costs.get(row.get("symbol"),999),
                regime_by_family.get(family,{}).get("regime","NEUTRAL"),
                config,
                row.get("symbol") in current_by_symbol,
                allow_short,
            ))
        budget=D(total)*(1-max(D(0),min(D(100),D(config.get("decision_cash_reserve_pct",20))))/100)
        holds=[x for x in decisions if x["direction"]=="HOLD"]
        variable=[x for x in decisions if x["direction"] in ("LONG","SHORT")]
        fixed=sum(abs(D(x["target_exposure_eur"])) for x in holds)
        if fixed>budget and fixed>0:
            factor=budget/fixed
            for x in holds:
                target=D(x["target_exposure_eur"])*factor
                current=D(x["current_exposure_eur"])
                x["target_exposure_eur"]=str(target);x["rebalance_delta_eur"]=str(target-current)
                x["action"]="BUY" if target>current else "SELL" if target<current else "HOLD"
        fixed=sum(abs(D(x["target_exposure_eur"])) for x in holds)
        remaining=max(D(0),budget-fixed)
        gross=sum(abs(D(x["target_exposure_eur"])) for x in variable)
        if gross>remaining and gross>0:
            factor=remaining/gross
            for x in variable:
                target=D(x["target_exposure_eur"])*factor
                current=D(x["current_exposure_eur"])
                x["target_exposure_eur"]=str(target);x["rebalance_delta_eur"]=str(target-current)
                x["action"]="BUY" if target>current else "SELL" if target<current else "HOLD"
        for x in decisions:
            x["portfolio_target_budget_eur"]=str(budget)
            x["portfolio_target_abs_before_normalization"]=x["target_exposure_eur"]
        return decisions

    def record(self,environment,decision,execution_symbol=None,execution_mode=None,leverage=1,status="PROPOSED",reason=""):
        if not self.db:return
        with self.db.con() as c:
            c.execute(
                """CREATE TABLE IF NOT EXISTS decision_snapshots(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,created_at TEXT NOT NULL,
                    environment TEXT NOT NULL,symbol TEXT NOT NULL,action TEXT NOT NULL,
                    direction TEXT NOT NULL,target_exposure_eur TEXT NOT NULL,current_exposure_eur TEXT NOT NULL,
                    delta_eur TEXT NOT NULL,expected_edge_gross_pct TEXT,
                    expected_edge_after_costs_pct TEXT,quality_score TEXT,regime TEXT,news_score TEXT,
                    execution_symbol TEXT,execution_mode TEXT,leverage TEXT,status TEXT NOT NULL,
                    reason TEXT NOT NULL,decision_json TEXT NOT NULL,plan_hash TEXT,
                    action_type TEXT,marginal_benefit_eur TEXT
                )"""
            )
            cols={x["name"] for x in c.execute("PRAGMA table_info(decision_snapshots)").fetchall()}
            for name,definition in [("plan_hash","TEXT"),("action_type","TEXT"),("marginal_benefit_eur","TEXT")]:
                if name not in cols:c.execute(f"ALTER TABLE decision_snapshots ADD COLUMN {name} {definition}")
            c.execute(
                """INSERT INTO decision_snapshots(
                created_at,environment,symbol,action,direction,target_exposure_eur,current_exposure_eur,
                delta_eur,expected_edge_gross_pct,expected_edge_after_costs_pct,quality_score,regime,news_score,
                execution_symbol,execution_mode,leverage,status,reason,decision_json,plan_hash,action_type,marginal_benefit_eur)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (now(),environment,decision.get("symbol"),decision.get("action"),decision.get("direction"),
                 decision.get("target_exposure_eur","0"),decision.get("current_exposure_eur","0"),
                 decision.get("rebalance_delta_eur","0"),decision.get("expected_edge_gross_pct"),
                 decision.get("expected_edge_after_costs_pct"),decision.get("quality_score"),decision.get("regime"),
                 decision.get("news_score"),execution_symbol,execution_mode,str(leverage),status,reason,
                 json.dumps(decision,sort_keys=True,default=str),decision.get("plan_hash"),decision.get("action_type"),
                 decision.get("marginal_benefit_eur","0"))
            )
