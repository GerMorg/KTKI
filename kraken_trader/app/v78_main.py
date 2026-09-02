"""Kraken Trader v78: single stable runtime and clean operator GUI."""
import json
import os
import threading
import resource

# Core must never start its legacy background loops while this runtime owns them.
os.environ.setdefault("APP_DISABLE_PAPER_SCHEDULER", "1")
os.environ.setdefault("APP_DISABLE_RESEARCH_SCHEDULER", "1")
os.environ.setdefault("APP_DISABLE_REAL_BALANCING_SCHEDULER", "1")
os.environ.setdefault("APP_DISABLE_WEBSOCKETS", "1")
os.environ.setdefault("APP_SKIP_TEXT_REPAIR", "1")

import core
from flask import redirect, request, url_for
from automation_controller import AutomationController
from controlled_learning import ControlledLearning
from news_learning import NewsLearning
from portfolio_allocator import PortfolioAllocator
from version import APP_VERSION

app = core.app
db = core.db
controlled_learning = ControlledLearning(db)
news_learning = NewsLearning(db)
portfolio_allocator = PortfolioAllocator(db)
controller = AutomationController(
    db,
    core.pipeline,
    core.news_prefilter,
    controlled_learning,
    news_learning,
    core.run_paper_cycle,
    core.real_allocator,
)

_scheduler_lock = threading.Lock()
_scheduler_started = False
_stream_lock = threading.Lock()
_streams_started = False


def _start_controller_once():
    global _scheduler_started
    with _scheduler_lock:
        if _scheduler_started:
            return
        if controller.start_background() is not None:
            _scheduler_started = True


def _start_data_services_once():
    """Start live sockets only after the Flask app is ready and only when usable."""
    global _streams_started
    with _stream_lock:
        if _streams_started:
            return
        opts = getattr(core, "opts", {}) or {}
        public_enabled = bool(opts.get("public_websocket_enabled", False))
        private_enabled = bool(opts.get("private_websocket_readonly_enabled", False))
        has_credentials = bool(opts.get("kraken_api_key")) and bool(opts.get("kraken_api_secret"))
        try:
            if public_enabled:
                held = db.rows("SELECT display_name FROM portfolio_assets WHERE classification='HELD'")
                symbols = [
                    ("BTC" if row["display_name"] == "XBT" else row["display_name"]) + "/EUR"
                    for row in held
                    if row["display_name"] and row["display_name"] != "EUR"
                ]
                if symbols:
                    core.stream.set_symbols(symbols)
                    core.stream.start()
            if private_enabled and has_credentials:
                core.private_stream.start()
        finally:
            _streams_started = True


@app.before_request
def _runtime_guard():
    _start_controller_once()
    # WebSockets are deliberately lazy: one bad/empty credential set must not
    # keep reconnecting in a tight start-up path on a small Home Assistant host.
    _start_data_services_once()


def _json(value, default=None):
    try:
        return json.loads(value or "")
    except (TypeError, ValueError, json.JSONDecodeError):
        return default if default is not None else {}


def _strategy_rows():
    rows = []
    for raw in controlled_learning.candidates():
        row = dict(raw)
        row["parameters"] = _json(row.get("parameters_json"), {})
        row["gates"] = _json(row.get("gate_results_json"), [])
        row["gate_passed"] = sum(1 for gate in row["gates"] if gate.get("passed"))
        row["gate_total"] = len(row["gates"])
        rows.append(row)
    return rows


def _news_rows():
    rows = []
    for raw in news_learning.candidates():
        row = dict(raw)
        row["comparison"] = _json(row.get("comparison_json"), {})
        row["walk_forward"] = _json(row.get("walk_forward_json"), {})
        rows.append(row)
    return rows


def _reason(row):
    status = str(row.get("status") or "")
    if status == "PENDING":
        return "Alle automatischen Gates erfüllt; explizite Freigabe steht noch aus."
    if status == "REJECTED_GATE":
        failed = [str(x.get("gate")) for x in row.get("gates", []) if not x.get("passed")]
        return "Nicht erfüllt: " + ", ".join(failed) if failed else "Mindestens ein Gate wurde nicht erfüllt."
    if status == "APPROVED":
        return "Freigegeben und als neue aktive Version übernommen."
    if status.startswith("REJECTED"):
        return str(row.get("reason") or "Bei der erneuten Prüfung abgelehnt.")
    if status == "UNCHANGED":
        return "Keine belastbare Verbesserung gegenüber der aktiven Version."
    return str(row.get("reason") or "Keine weitere Begründung gespeichert.")


def _nav():
    return [
        ("/", "Übersicht"),
        ("/kraken", "Kraken"),
        ("/scanner", "Analyse"),
        ("/portfolio", "Portfolios"),
        ("/portfolio-optimierung", "Portfoliooptimierung"),
        ("/bewertung", "Bewertung"),
        ("/lernen", "Lernen"),
        ("/news-learning", "News KI"),
        ("/paper", "Paper Trading"),
        ("/real-trading", "Echtes Depot"),
        ("/automatik", "Automatisches Traden"),
        ("/tax-info", "Einkommensteuer AT"),
        ("/data-quality", "Datenqualität"),
        ("/backtests", "Backtests"),
        ("/audit", "Audit"),
        ("/systeme", "System"),
    ]


def _page(body, **ctx):
    return core.render_template("base.html", body=core.render_template_string(body, **ctx), app_version=APP_VERSION, nav=[(request.script_root + path, label) for path, label in _nav()], current_path=request.script_root + request.path)


@app.get("/")
def dashboard():
    portfolio = db.rows("SELECT total_eur,quality,created_at FROM portfolio_snapshots ORDER BY id DESC LIMIT 1")
    paper = db.rows("SELECT total_eur,quality,created_at FROM paper_snapshots ORDER BY id DESC LIMIT 1")
    analysis = core.pipeline.latest()
    families = controlled_learning.family_overview()
    candidates = _strategy_rows()
    news = _news_rows()
    pending = sum(row.get("status") == "PENDING" for row in candidates) + sum(row.get("status") == "PENDING" for row in news)
    return _page("""
    <section class="hero"><div><span class="eyebrow">KTKI {{version}}</span><h1>Kraken Trader</h1><p class="lead">Ein einziger Prozess für Kraken-Daten, News, Analyse, Bewertung, Lernen, Portfolio und Handel.</p></div><span class="safety">REALHANDEL STANDARDMÄSSIG DEAKTIVIERT</span></section>
    <div class="summary-grid">
      <div class="summary"><span>Analyse</span><b>{{analysis.stage if analysis else '—'}}</b><small>{{analysis.status if analysis else 'Noch kein Lauf'}}</small></div>
      <div class="summary"><span>Portfolio</span><b>{{portfolio[0].total_eur if portfolio else '—'}} €</b><small>{{portfolio[0].quality if portfolio else 'Noch kein Snapshot'}}</small></div>
      <div class="summary"><span>Paper</span><b>{{paper[0].total_eur if paper else '—'}} €</b><small>{{paper[0].quality if paper else 'Noch kein Snapshot'}}</small></div>
      <div class="summary"><span>Lernen</span><b>{{pending}}</b><small>offene Kandidaten</small></div>
    </div>
    <div class="process-strip">{% for item in ['Kraken','News','Analyse','Bewertung','Lernen','Portfolio','Handel'] %}<div class="process-node"><span>{{loop.index}}</span><b>{{item}}</b></div>{% if not loop.last %}<i>→</i>{% endif %}{% endfor %}</div>
    <div class="card"><h2>Aktive Lernfamilien</h2><div class="grid">{% for family in families %}<div class="learning-card"><span class="eyebrow">{{family.family}}</span><h3>aktiv v{{family.active_version}}</h3><b>{{family.pending_count}} offen</b><small>{{family.latest_status}}</small></div>{% endfor %}</div></div>
    <div class="card"><h2>Arbeitsoberflächen</h2><div class="section-actions"><a class="button" href="/kraken">Kraken & Depotdaten</a><a class="button" href="/scanner">Analyse</a><a class="button" href="/bewertung">Bewertung</a><a class="button" href="/lernen">Lernen</a><a class="button" href="/portfolio-optimierung">Portfoliooptimierung</a><a class="button" href="/automatik">Automatisches Traden</a><a class="button" href="/tax-info">Einkommensteuer AT</a></div></div>
    """, version=APP_VERSION, portfolio=portfolio, paper=paper, analysis=analysis, families=families, pending=pending)


@app.get("/kraken")
def kraken_page():
    opts = getattr(core, "opts", {}) or {}
    stream = core.stream.status()
    private = core.private_stream.status()
    return _page("""
    <span class="eyebrow">Kraken</span><h1>Kraken & Depotdaten</h1><p class="lead">REST bleibt der verlässliche Grundpfad. WebSockets starten nur bei sinnvoller Konfiguration und gültigen Zugangsdaten.</p>
    <div class="summary-grid"><div class="summary"><span>API</span><b>{{'KONFIGURIERT' if credentials else 'NICHT KONFIGURIERT'}}</b><small>Private Funktionen</small></div><div class="summary"><span>Public Stream</span><b>{{stream.effective_state}}</b><small>{{stream.symbol_count}} Symbole</small></div><div class="summary"><span>Private Stream</span><b>{{private.effective_state}}</b><small>Read-only</small></div><div class="summary"><span>Realhandel</span><b>{{'AN' if opts.get('real_trading_enabled') else 'AUS'}}</b><small>zusätzliche Gates aktiv</small></div></div>
    <div class="card"><h2>Datenpfad</h2><div class="process-strip"><div class="process-node"><b>Kraken REST</b></div><i>→</i><div class="process-node"><b>Marktuniversum</b></div><i>→</i><div class="process-node"><b>Analyse</b></div><i>→</i><div class="process-node"><b>Bewertung</b></div><i>→</i><div class="process-node"><b>Portfolio / Handel</b></div></div></div>
    """, opts=opts, credentials=bool(opts.get("kraken_api_key") and opts.get("kraken_api_secret")), stream=stream, private=private)


@app.get("/portfolio-optimierung")
def portfolio_optimization_page():
    snap = db.rows("SELECT total_eur,quality,created_at FROM portfolio_snapshots ORDER BY id DESC LIMIT 1")
    total = float(snap[0]["total_eur"]) if snap and snap[0].get("total_eur") is not None else 0.0
    try:
        plans = portfolio_allocator.plans(total)
        error = None
    except Exception as exc:
        plans = []
        error = type(exc).__name__ + ": " + str(exc)[:300]
    return _page("""
    <span class="eyebrow">Portfolio</span><h1>Portfoliooptimierung</h1><p class="lead">Die Optimierung erzeugt Zielgewichtsvorschläge aus validierten Analysesignalen; sie sendet keine Orders.</p>
    {% if error %}<div class="card error">Optimierung aktuell nicht verfügbar: {{error}}</div>{% endif %}
    <div class="table-card"><table><tr><th>Symbol</th><th>Kategorie</th><th>Konfidenz</th><th>Ziel %</th><th>Ziel EUR</th><th>Hebel</th></tr>{% for x in plans %}<tr><td>{{x.symbol}}</td><td>{{x.category}}</td><td>{{x.confidence}}</td><td>{{x.target_pct}}</td><td>{{x.target_exposure_eur}}</td><td>{{x.leverage}}</td></tr>{% else %}<tr><td colspan="6">Noch keine validierten BUY-Signale für einen Optimierungsplan.</td></tr>{% endfor %}</table></div>
    """, plans=plans, error=error)


@app.get("/bewertung")
def evaluation_page():
    summary = db.rows("SELECT COUNT(*) total, SUM(CASE WHEN direction_correct=1 THEN 1 ELSE 0 END) correct FROM forecast_evaluations")
    open_count = db.rows("SELECT COUNT(*) n FROM research_forecasts WHERE status='OPEN'")
    recent = db.rows("SELECT e.evaluated_at,f.symbol,f.family,f.model_version,f.horizon_hours,e.actual_return_pct,e.direction_correct,e.timing_error_seconds FROM forecast_evaluations e JOIN research_forecasts f ON f.id=e.forecast_id ORDER BY e.evaluated_at DESC LIMIT 50")
    model_health = db.rows("SELECT version,status,created_at,parent_version,reason FROM model_weights ORDER BY created_at DESC LIMIT 20")
    return _page("""
    <span class="eyebrow">Qualität</span><h1>Bewertung</h1><p class="lead">Hier wird sichtbar, wie Prognosen auf abgeschlossenen Marktdaten abgeschnitten haben. Bewertung und Lernen sind getrennt vom aktiven Handel.</p>
    <div class="summary-grid"><div class="summary"><span>Bewertet</span><b>{{summary[0].total if summary else 0}}</b><small>abgeschlossene Forecasts</small></div><div class="summary"><span>Trefferquote</span><b>{% if summary and summary[0].total %}{{'%.1f'|format((summary[0].correct or 0) / summary[0].total * 100)}} %{% else %}—{% endif %}</b><small>Richtung korrekt</small></div><div class="summary"><span>Offen</span><b>{{open_count[0].n if open_count else 0}}</b><small>warte auf Bewertungszeitpunkt</small></div><div class="summary"><span>Modelle</span><b>{{model_health|length}}</b><small>versionierte Gewichte</small></div></div>
    <div class="table-card"><table><tr><th>Zeit</th><th>Symbol</th><th>Familie</th><th>Horizont</th><th>Return</th><th>Richtung</th><th>Timing</th></tr>{% for x in recent %}<tr><td>{{x.evaluated_at}}</td><td>{{x.symbol}}</td><td>{{x.family}}</td><td>{{x.horizon_hours}} h</td><td>{{x.actual_return_pct}}</td><td>{{'KORREKT' if x.direction_correct else 'FALSCH'}}</td><td>{{x.timing_error_seconds}} s</td></tr>{% else %}<tr><td colspan="7">Noch keine abgeschlossenen Bewertungen.</td></tr>{% endfor %}</table></div>
    """, summary=summary, open_count=open_count, recent=recent, model_health=model_health)


@app.get("/lernen")
def learning_page():
    families = controlled_learning.family_overview()
    strategy = _strategy_rows()
    news = _news_rows()
    family = request.args.get("family", "forex")
    allowed = {item["family"] for item in families}
    if family not in allowed:
        family = "forex"
    active = controlled_learning.active(family)
    active_params = _json(active.get("parameters_json"), {}) if active else {}
    metrics = controlled_learning.metrics(family=family)
    selected = [item for item in strategy if item.get("family") == family]
    return _page("""
    <div class="section-head"><div><span class="eyebrow">Lernen</span><h1>Lernzyklus</h1><p class="lead">Ein Kandidat darf nur über nachvollziehbare Gates und eine dokumentierte Entscheidung die aktive Version verändern.</p></div><form method="post" action="/lernen/run"><button>Lernlauf jetzt ausführen</button></form></div>
    <div class="grid">{% for f in families %}<div class="learning-card"><span class="eyebrow">{{f.family}}</span><h3>aktiv v{{f.active_version}}</h3><b>{{f.pending_count}} offen</b><small>Letzter Kandidat #{{f.latest_candidate_id or '—'}} · {{f.latest_status}}</small></div>{% endfor %}</div>
    <div class="card"><div class="section-actions">{% for f in families %}<a class="button secondary" href="/lernen?family={{f.family}}">{{f.family}}</a>{% endfor %}</div></div>
    {% for x in selected %}<div class="card"><div class="grid"><div><span class="pill">{{x.status}}</span><h3>Kandidat #{{x.id}}</h3><p>Basis v{{x.base_version}} · {{x.sample_count}} Samples</p></div><div><b>Trefferquote</b><br>Aktiv {{'%.2f'|format(x.active_accuracy|float*100)}} %<br>Kandidat {{'%.2f'|format(x.candidate_accuracy|float*100)}} %<br>Δ {{'%.2f'|format(x.improvement|float*100)}} pp</div><div><b>Automatische Entscheidung</b><br>{{reason(x)}}</div></div><details><summary>Gates {{x.gate_passed}} / {{x.gate_total}}</summary><table><tr><th>Gate</th><th>Horizont</th><th>Status</th><th>Ist</th><th>Soll</th></tr>{% for g in x.gates %}<tr><td>{{g.gate}}</td><td>{{g.horizon_hours or 'alle'}}</td><td class="{{'ok' if g.passed else 'error'}}">{{'BESTANDEN' if g.passed else 'NICHT BESTANDEN'}}</td><td>{{g.actual}}</td><td>{{g.required}}</td></tr>{% endfor %}</table></details><details><summary>Parametervergleich</summary><table><tr><th>Parameter</th><th>Aktiv</th><th>Kandidat</th><th>Δ</th></tr>{% for key,value in x.parameters.items() %}<tr><td>{{key}}</td><td>{{active_params.get(key,'—')}}</td><td>{{value}}</td><td>{{('%+.4f'|format(value|float-active_params.get(key,value)|float)) if value is number else '—'}}</td></tr>{% endfor %}</table></details>{% if x.status=='PENDING' %}<form method="post" action="/lernen/decision"><input type="hidden" name="candidate_id" value="{{x.id}}"><input type="hidden" name="family" value="{{x.family}}"><button name="action" value="approve">Explizit freigeben</button><button name="action" value="reject" class="danger">Ablehnen</button></form>{% endif %}</div>{% else %}<div class="card">Für {{family}} gibt es noch keinen Kandidaten.</div>{% endfor %}
    <h2>Gesamthistorie</h2><div class="table-card"><table><tr><th>Zeit</th><th>Familie</th><th>Status</th><th>Samples</th><th>Verbesserung</th><th>Grund</th></tr>{% for x in strategy %}<tr><td>{{x.created_at}}</td><td>{{x.family}}</td><td>{{x.status}}</td><td>{{x.sample_count}}</td><td>{{'%.4f'|format(x.improvement|float)}}</td><td>{{reason(x)}}</td></tr>{% else %}<tr><td colspan="6">Keine Strategie-Kandidaten.</td></tr>{% endfor %}</table></div>
    <h2>News-Lernen</h2><div class="table-card"><table><tr><th>Zeit</th><th>Status</th><th>Samples</th><th>Verbesserung</th><th>Grund</th></tr>{% for x in news %}<tr><td>{{x.created_at}}</td><td>{{x.status}}</td><td>{{x.sample_count}}</td><td>{{x.improvement}}</td><td>{{x.reason}}</td></tr>{% else %}<tr><td colspan="5">Keine News-Kandidaten.</td></tr>{% endfor %}</table></div>
    <h2>Horizontmetriken</h2><div class="table-card"><table><tr><th>Kandidat</th><th>Horizont</th><th>Samples</th><th>Coverage aktiv / Kandidat</th><th>Netto aktiv / Kandidat</th><th>Drawdown aktiv / Kandidat</th></tr>{% for x in metrics %}<tr><td>{{x.candidate_id}}</td><td>{{x.horizon_hours}} h</td><td>{{x.sample_count}}</td><td>{{x.active_coverage}} / {{x.candidate_coverage}}</td><td>{{x.active_net_return}} / {{x.candidate_net_return}}</td><td>{{x.active_max_drawdown}} / {{x.candidate_max_drawdown}}</td></tr>{% else %}<tr><td colspan="6">Keine Horizontmetriken.</td></tr>{% endfor %}</table></div>
    """, families=families, strategy=strategy, news=news, family=family, selected=selected, active=active, active_params=active_params, metrics=metrics, reason=_reason)


@app.post("/lernen/run")
def learning_run():
    try:
        result = controller.run_learning(automatic=False, auto_approve=False)
        db.audit("LEARNING_MANUAL_RUN", json.dumps({"status": result.get("status"), "strategy": result.get("strategy"), "news": result.get("news")}, sort_keys=True), "info")
    except Exception as exc:
        db.audit("LEARNING_MANUAL_RUN_FAILED", type(exc).__name__ + ": " + str(exc)[:500], "error")
    return redirect(url_for("learning_page"))


@app.post("/lernen/decision")
def learning_decision():
    try:
        candidate_id = int(request.form.get("candidate_id", "0"))
        family = request.form.get("family", "forex")
        action = request.form.get("action", "reject")
        result = controlled_learning.decide(candidate_id, action)
        db.audit("LEARNING_DECISION", json.dumps({"candidate_id": candidate_id, "family": family, "action": action, "result": result}, sort_keys=True), "info")
        return redirect(url_for("learning_page", family=family))
    except (TypeError, ValueError) as exc:
        db.audit("LEARNING_DECISION_FAILED", type(exc).__name__ + ": " + str(exc), "error")
        return redirect(url_for("learning_page"))


@app.route("/automatik", methods=["GET", "POST"])
def automation_page():
    if request.method == "POST":
        form = request.form
        for key in ["automation_master_enabled", "automation_analysis_enabled", "automation_news_enabled", "automation_learning_enabled", "automation_learning_auto_approve_enabled", "automation_paper_enabled", "automation_real_enabled", "automation_real_execute_enabled"]:
            db.set_setting(key, "true" if form.get(key) else "false")
        for key in ["automation_tick_minutes", "automation_analysis_interval_minutes", "automation_news_interval_minutes", "automation_learning_interval_minutes", "automation_paper_interval_minutes", "automation_real_interval_minutes"]:
            if key not in form:
                continue
            try:
                db.set(key, max(1, min(1440, int(float(form[key])))))
            except (TypeError, ValueError):
                pass
        if form.get("run_now"):
            controller.run_once(force=True)
        db.audit("AUTOMATION_SETTINGS_CHANGED", json.dumps(controller.settings(), sort_keys=True), "info")
        return redirect(url_for("automation_page"))
    return _page("""
    <span class="eyebrow">Automatik</span><h1>Automatisches Traden</h1><p class="lead">Genau ein Scheduler verwaltet Nachrichten, Analyse, Lernen, Paper und Realhandel. Realhandel bleibt zusätzlich technisch gegated.</p>
    <form method="post"><div class="card master-card"><div><h2>Gesamtautomatik</h2><p class="muted">Ein Master-Schalter für alle automatischen Prozesse.</p></div><label class="switch"><input type="checkbox" name="automation_master_enabled" {{'checked' if cfg.automation_master_enabled=='true'}}><span></span></label></div>
    <div class="automation-settings">{% for x in autos %}<div class="automation-setting"><div><b>{{x.name}}</b><small>{{x.key}}</small></div><label class="switch"><input type="checkbox" name="automation_{{x.key}}_enabled" {{'checked' if x.enabled}}><span></span></label><label>Intervall<input type="number" min="1" max="1440" name="automation_{{x.key}}_interval_minutes" value="{{x.interval}}"></label></div>{% endfor %}</div>
    <div class="card"><label class="checkline"><input type="checkbox" name="automation_learning_auto_approve_enabled" {{'checked' if cfg.automation_learning_auto_approve_enabled=='true'}}> Lernkandidaten nur bei erneut bestandenen Gates automatisch aktivieren</label></div>
    <div class="section-actions"><button>Speichern</button><button class="secondary" name="run_now" value="1">Jetzt ausführen</button></div></form>
    <div class="card"><h2>Ausführungshistorie</h2><div class="table-card"><table><tr><th>Zeit</th><th>Subsystem</th><th>Status</th><th>Fehler</th></tr>{% for x in latest %}<tr><td>{{x.created_at}}</td><td>{{x.subsystem}}</td><td>{{x.status}}</td><td>{{x.error or '—'}}</td></tr>{% else %}<tr><td colspan="4">Noch keine Läufe.</td></tr>{% endfor %}</table></div></div>
    """, cfg=controller.settings(), autos=[{"key": key, "name": name, "enabled": controller.enabled(key), "interval": controller.minutes(controller.settings().get("automation_" + key + "_interval_minutes", 60))} for key, name in [("analysis", "Analyse"), ("news", "News"), ("learning", "Lernen"), ("paper", "Paper Trading"), ("real", "Realhandel")]], latest=controller.latest(100))


@app.get("/systeme")
def systems_page():
    modules = [
        ("Kraken", "/kraken", "REST + optionale Public/Private Streams"),
        ("News KI & Schnittstellen", "/news-learning", "News-Quellen, externe AI und lokales News-Lernen"),
        ("Analyse", "/scanner", "Prefilter, Scanner und Research-Pipeline"),
        ("Bewertung", "/bewertung", "Forecasts, Holdout und Modellgesundheit"),
        ("Lernen", "/lernen", "Strategie- und News-Kandidaten mit Gates"),
        ("Paper Trading", "/paper", "Simuliertes Depot und Risikoregeln"),
        ("Echtes Depot", "/real-trading", "Read-only Depot und technisch gegatete Orders"),
        ("Portfoliooptimierung", "/portfolio-optimierung", "Zielgewichte ohne direkte Orderwirkung"),
        ("Automatisches Traden", "/automatik", "Ein zentraler Scheduler"),
        ("Einkommensteuer AT", "/tax-info", "Österreichische Steuerarbeitsfläche"),
    ]
    rss = db.rows("SELECT COUNT(*) n FROM news_items") if "news_items" in {r.get("name") for r in db.rows("SELECT name FROM sqlite_master WHERE type='table'")} else [{"n": 0}]
    return _page("""
    <span class="eyebrow">Architektur</span><h1>Systemübersicht</h1><p class="lead">Jedes fachliche System hat einen sichtbaren Platz. Hintergrundarbeit ist auf einen Scheduler begrenzt; WebSockets werden nicht blind beim Prozessstart verbunden.</p>
    <div class="grid">{% for name,path,role in modules %}<div class="card"><span class="eyebrow">System</span><h3>{{name}}</h3><p class="muted">{{role}}</p><a class="button secondary" href="{{path}}">Öffnen</a></div>{% endfor %}</div>
    <div class="summary-grid"><div class="summary"><span>News-Datensätze</span><b>{{news_count}}</b><small>lokal gespeichert</small></div><div class="summary"><span>Scheduler</span><b>1</b><small>AutomationController</small></div><div class="summary"><span>WebSockets</span><b>lazy</b><small>nur bei sinnvoller Konfiguration</small></div><div class="summary"><span>Realhandel</span><b>AUS</b><small>Default</small></div></div>
    """, modules=modules, news_count=int(rss[0]["n"]) if rss else 0)


@app.get("/v78-health")
def health():
    rss = resource.getrusage(resource.RUSAGE_SELF)
    return {
        "version": APP_VERSION,
        "runtime": "v78_main",
        "scheduler_count": 1 if _scheduler_started else 0,
        "streams_started": _streams_started,
        "rss_max_kib": rss.ru_maxrss,
        "load_available": getattr(os, "getloadavg", lambda: None)(),
        "learning_families": [x["family"] for x in controlled_learning.family_overview()],
        "pending_strategy": sum(x.get("status") == "PENDING" for x in _strategy_rows()),
        "pending_news": sum(x.get("status") == "PENDING" for x in _news_rows()),
        "automation_master_enabled": controller.settings().get("automation_master_enabled"),
        "real_trading_enabled": core.db.value("real_trading_enabled", "false"),
    }
