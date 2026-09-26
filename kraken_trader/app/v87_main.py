"""v87 runtime: user-facing real-trading blocker diagnostics.

Keeps the verified v86 runtime and adds the missing GUI layer: global execution
blockers plus the latest per-symbol decision-matrix failures are shown directly
on the Realhandel page. No secrets are rendered.
"""
from decimal import Decimal

import v86_main as base
from decision_matrix import DecisionMatrix

app = base.app
legacy = base.legacy
controller = base.controller
options = getattr(base, "options", {})


def _d(value):
    try:
        return Decimal(str(value or 0))
    except Exception:
        return Decimal(0)


def _global_blockers():
    cfg = legacy.real_allocator.settings()
    blockers = []

    if not getattr(legacy.client, "key", ""):
        blockers.append(("KRAKEN_API_KEY_MISSING", "Kraken API-Key fehlt"))
    if not getattr(legacy.client, "secret", ""):
        blockers.append(("KRAKEN_API_SECRET_MISSING", "Kraken API-Secret fehlt"))
    if legacy.db.value("real_kill_switch", "true").lower() == "true":
        blockers.append(("REAL_KILL_SWITCH_ACTIVE", "Realhandel-Kill-Switch ist aktiv"))
    if not cfg.get("enabled"):
        blockers.append(("REAL_BALANCING_DISABLED", "Automatische Real-Umschichtung ist deaktiviert"))
    if not cfg.get("automatic_execution"):
        blockers.append(("REAL_EXECUTION_DISABLED", "Automatische Real-Ausführung ist deaktiviert"))
    if cfg.get("dry_run"):
        blockers.append(("REAL_DRY_RUN", "Real-Ausführung läuft im Dry-Run"))
    if not legacy.db.value("real_balancing_automation_secret_hash", ""):
        blockers.append(("AUTOMATION_SECRET_INVALID", "Kein gültiger Automation-Secret-Hash konfiguriert"))

    max_day = max(0, int(_d(legacy.db.value("real_balancing_max_actions_per_day", "0"))))
    submitted_day = int((legacy.db.rows(
        "SELECT COUNT(*) n FROM real_trade_intents "
        "WHERE validate_only=0 AND status='SUBMITTED' AND date(created_at)=date('now')"
    ) or [{"n": 0}])[0]["n"])
    if max_day and submitted_day >= max_day:
        blockers.append((
            "DAILY_EXECUTION_LIMIT",
            f"Tägliches Umschichtungslimit erreicht ({submitted_day}/{max_day})",
        ))

    cached_balance = legacy.db.rows("SELECT COUNT(*) n FROM private_balances") or [{"n": 0}]
    if int(cached_balance[0]["n"]) == 0:
        blockers.append(("PRIVATE_BALANCE_CACHE_EMPTY", "Kein aktueller Private-Balance-Stand vorhanden"))

    return blockers, submitted_day, max_day


def _blocked_decisions():
    rows = DecisionMatrix(legacy.db).recent()
    result = []
    seen = set()
    for row in rows:
        if int(row.get("passed", 1)):
            continue
        key = (str(row.get("symbol")), str(row.get("action")), str(row.get("rule_key")))
        if key in seen:
            continue
        seen.add(key)
        result.append({
            "created_at": row.get("created_at"),
            "symbol": row.get("symbol"),
            "action": row.get("action"),
            "rule_key": row.get("rule_key"),
            "reason": row.get("reason"),
            "details": row.get("details_json") or "{}",
        })
        if len(result) >= 100:
            break
    return result


def _recent_actions():
    rows = controller.latest(50) if controller else []
    return [
        x for x in rows
        if isinstance(x, dict)
        and str(x.get("subsystem", "")).lower() == "real"
    ][:20]


def v87_real_trading():
    blockers, submitted_day, max_day = _global_blockers()
    blocked = _blocked_decisions()
    actions = _recent_actions()
    cfg = legacy.real_allocator.settings()

    return legacy.page(
        '''<h1>Realhandel</h1>
<p class="lead">Strikt getrennt vom Paper-Handel. Diese Seite zeigt jetzt unmittelbar,
warum die automatische Real-Ausführung blockiert ist.</p>

<div class="grid">
  <div class="card">
    <h3>Ausführung</h3>
    <div class="metric">{{ "FREIGEGEBEN" if real_cfg.automatic_execution and not real_cfg.dry_run else "BLOCKIERT" }}</div>
    <small>Balancing {{ "aktiv" if real_cfg.enabled else "aus" }} · Dry-Run {{ "an" if real_cfg.dry_run else "aus" }}</small>
  </div>
  <div class="card">
    <h3>Tageslimit</h3>
    <div class="metric">{{ submitted_day }}{% if max_day %} / {{ max_day }}{% endif %}</div>
    <small>bereits eingereichte Realaufträge heute</small>
  </div>
  <div class="card">
    <h3>Blockierungen</h3>
    <div class="metric">{{ blockers|length + blocked|length }}</div>
    <small>{{ blockers|length }} globale · {{ blocked|length }} Regelprüfungen</small>
  </div>
</div>

<div class="card">
  <h2>Warum wird nicht ausgeführt?</h2>
  {% if blockers %}
    <table>
      <tr><th>Code</th><th>Blockierungsgrund</th></tr>
      {% for code, reason in blockers %}
        <tr><td><code>{{ code }}</code></td><td>{{ reason }}</td></tr>
      {% endfor %}
    </table>
  {% else %}
    <p>Keine globalen Blockierungsgründe erkannt.</p>
  {% endif %}
</div>

<div class="card">
  <h2>Blockierte Kandidaten / Regelprüfungen</h2>
  {% if blocked %}
    <table>
      <tr><th>Zeit</th><th>Symbol</th><th>Aktion</th><th>Regel</th><th>Grund</th></tr>
      {% for x in blocked %}
        <tr>
          <td>{{ x.created_at }}</td>
          <td>{{ x.symbol }}</td>
          <td>{{ x.action }}</td>
          <td><code>{{ x.rule_key }}</code></td>
          <td>{{ x.reason }}</td>
        </tr>
      {% endfor %}
    </table>
  {% else %}
    <p>Noch keine blockierte Regelprüfung gespeichert.</p>
  {% endif %}
</div>

<div class="card">
  <h2>Letzte Real-Automatikläufe</h2>
  {% if actions %}
    <table>
      <tr><th>Zeit</th><th>Status</th><th>Aktionen</th></tr>
      {% for x in actions %}
        <tr>
          <td>{{ x.created_at or x.timestamp or "—" }}</td>
          <td>{{ x.status or "—" }}</td>
          <td><pre>{{ x.actions|tojson(indent=2) if x.actions is defined else x|tojson(indent=2) }}</pre></td>
        </tr>
      {% endfor %}
    </table>
  {% else %}
    <p>Noch kein Real-Automatiklauf vorhanden.</p>
  {% endif %}
</div>

<div class="card">
  <h2>Manuelle Realorder</h2>
  <p>Die manuelle Validierung und das zeitlich begrenzte Scharfschalten bleiben über die bestehende Realhandel-Funktion erhalten.</p>
  <p><a href="{{ request.path }}?manual=1">Manuelle Orderoberfläche öffnen</a></p>
</div>''',
        real_cfg=cfg,
        blockers=blockers,
        blocked=blocked,
        actions=actions,
        submitted_day=submitted_day,
        max_day=max_day,
    )


_original_real_trade_view = app.view_functions.get("real_trade.view")
if _original_real_trade_view is not None:
    def _v87_real_trade_route():
        if getattr(__import__("flask").request, "method", "GET") == "POST":
            return _original_real_trade_view()
        if getattr(__import__("flask").request, "args", {}).get("manual") == "1":
            return _original_real_trade_view()
        return v87_real_trading()

    app.view_functions["real_trade.view"] = _v87_real_trade_route


@app.get("/v87-health")
def v87_health():
    blockers, submitted_day, max_day = _global_blockers()
    return {
        "version": "0.1.0-dev.87",
        "runtime": "v87_main",
        "blockers": [{"code": code, "reason": reason} for code, reason in blockers],
        "blocked_decisions": _blocked_decisions()[:100],
        "daily_execution": {"submitted": submitted_day, "limit": max_day},
        "real": legacy.real_allocator.settings(),
        "recent_real_runs": _recent_actions(),
    }

# Legacy health routes keep the v86 diagnostic payload, while the new v87
# endpoint is canonical for the GUI's blocker view.
