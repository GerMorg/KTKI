"""v96 shared trade guard for Paper and Real.

The guard is environment-scoped so Paper state cannot accidentally suppress Real
and vice versa, while the rules and parameters remain identical.
"""
from datetime import datetime, timezone, timedelta
from decimal import Decimal
D=lambda x:Decimal(str(x or 0))

class TradeGuardV96:
    def __init__(self,db,environment):
        self.db=db
        self.environment=str(environment).upper()
        with self.db.con() as c:
            c.execute("""CREATE TABLE IF NOT EXISTS trade_state_v96(
                environment TEXT NOT NULL,canonical_id TEXT NOT NULL,
                last_buy_at TEXT,last_sell_at TEXT,confirm_action TEXT,
                confirm_count INTEGER NOT NULL DEFAULT 0,updated_at TEXT NOT NULL,
                PRIMARY KEY(environment,canonical_id)
            )""")
            c.execute("""CREATE TABLE IF NOT EXISTS daily_turnover_v96(
                environment TEXT NOT NULL,day TEXT NOT NULL,turnovers INTEGER NOT NULL,
                PRIMARY KEY(environment,day)
            )""")

    def canonical_id(self,symbol):
        rows=self.db.rows("SELECT canonical_id FROM market_universe WHERE symbol=? LIMIT 1",(symbol,))
        return (rows[0].get("canonical_id") if rows else None) or str(symbol)

    def check(self,symbol,action,risk_exit=False):
        cid=self.canonical_id(symbol);now_dt=datetime.now(timezone.utc)
        rows=self.db.rows(
            "SELECT * FROM trade_state_v96 WHERE environment=? AND canonical_id=?",
            (self.environment,cid)
        )
        state=rows[0] if rows else {}
        day=now_dt.date().isoformat()
        used=self.db.rows("SELECT turnovers FROM daily_turnover_v96 WHERE environment=? AND day=?",(self.environment,day))
        daily_limit=int(float(self.db.value("decision_max_turnovers_per_day","2")))
        daily_ok=not(daily_limit>0 and used and int(used[0]["turnovers"])>=daily_limit)

        if risk_exit:
            hold_ok=True;cooldown_ok=True;required=1
        else:
            hold_hours=float(self.db.value("decision_min_hold_hours","24"))
            cooldown_hours=float(self.db.value("decision_cooldown_hours","12"))
            required=int(float(self.db.value("decision_confirmation_runs","2")))
            hold_ok=True;cooldown_ok=True
            if action=="SELL" and state.get("last_buy_at"):
                try:
                    hold_ok=now_dt-datetime.fromisoformat(str(state["last_buy_at"]).replace("Z","+00:00"))>=timedelta(hours=hold_hours)
                except Exception:hold_ok=False
            if action=="BUY":
                anchor=max([x for x in (state.get("last_buy_at"),state.get("last_sell_at")) if x],default=None)
                if anchor:
                    try:cooldown_ok=now_dt-datetime.fromisoformat(str(anchor).replace("Z","+00:00"))>=timedelta(hours=cooldown_hours)
                    except Exception:cooldown_ok=False

        previous=state.get("confirm_action")
        count=(int(state.get("confirm_count") or 0)+1) if previous==action else 1
        with self.db.con() as c:
            c.execute(
                """INSERT INTO trade_state_v96(environment,canonical_id,confirm_action,confirm_count,updated_at)
                VALUES(?,?,?,?,?) ON CONFLICT(environment,canonical_id)
                DO UPDATE SET confirm_action=excluded.confirm_action,
                confirm_count=excluded.confirm_count,updated_at=excluded.updated_at""",
                (self.environment,cid,action,count,now_dt.isoformat())
            )
        return {
            "canonical_id":cid,
            "confirmation_count":count,
            "confirmation_required":required,
            "confirmation_ok":count>=required,
            "minimum_hold_ok":hold_ok,
            "cooldown_ok":cooldown_ok,
            "daily_limit_ok":daily_ok,
            "risk_exit_override":bool(risk_exit),
        }

    def record_fill(self,symbol,side):
        cid=self.canonical_id(symbol);field="last_buy_at" if side=="BUY" else "last_sell_at"
        stamp=datetime.now(timezone.utc).isoformat();day=datetime.now(timezone.utc).date().isoformat()
        with self.db.con() as c:
            c.execute(
                f"""INSERT INTO trade_state_v96(environment,canonical_id,{field},confirm_action,confirm_count,updated_at)
                VALUES(?,?,?,NULL,0,?) ON CONFLICT(environment,canonical_id)
                DO UPDATE SET {field}=excluded.{field},confirm_action=NULL,
                confirm_count=0,updated_at=excluded.updated_at""",
                (self.environment,cid,stamp,stamp)
            )
            c.execute(
                """INSERT INTO daily_turnover_v96(environment,day,turnovers)
                VALUES(?,?,1) ON CONFLICT(environment,day)
                DO UPDATE SET turnovers=turnovers+1""",
                (self.environment,day)
            )
