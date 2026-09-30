"""v95 runtime and compact diagnostic GUI."""
import json
from flask import jsonify, redirect, request

from automation_v67 import AutomationControllerV67
from controlled_learning import ControlledLearning
from news_learning import NewsLearning
from model_health import ModelHealth
from decision_engine_v95 import DecisionEngineV95
from decision_context_v95 import scanner_candidates
from v95_paper_engine import PaperEngineV95
from v95_real_allocator import RealPortfolioAllocatorV95
import v90_main as base

app = base.app
legacy = base.legacy
options = getattr(base, "options", {})

V95_DEFAULTS = {
    "paper_cash_reserve_pct": "20",
    "paper_no_trade_band_pct": "2",
    "decision_min_edge_samples": "10",
    "decision_volatility_reference_pct": "2",
}

def _options():
    try:
        with open("/data/options.json", encoding="utf-8") as fh:
            return json.load(fh) or {}
    except Exception:
        return {}

def _sync(db, opts):
    for key, default in V95_DEFAULTS.items():
        value = opts.get(key, default)
        normalized = "true" if value is True else "false" if value is False else str(value)
        if not db.rows("SELECT value FROM settings WHERE key=?", (key,)):
            db.set_setting(key, normalized)

opts = _options() or options
_sync(legacy.db, opts)

try:
    base.controller.stop()
except Exception:
    pass

real_allocator = RealPortfolioAllocatorV95(legacy.db, legacy.real_trade_engine)
legacy.real_allocator = real_allocator

def run_paper_cycle():
    # Same live market inputs as Real: refresh public tickers and settle due forecasts
    # before the shared DecisionEngine consumes them.
    try:
        if hasattr(legacy, "refresh_allowed_prices"):
            legacy.refresh_allowed_prices()
    except Exception:
        pass
    try:
        legacy.forecasts.evaluate_due()
    except Exception:
        pass
    engine = PaperEngineV95(
        legacy.db,
        start_eur=legacy.db.value("paper_start_eur", "1000"),
        fee_bps=float(legacy.db.value("paper_fee_bps", "40")),
        slippage_bps=float(legacy.db.value("paper_slippage_bps", "10")),
        max_position_pct=float(legacy.db.value("paper_max_position_pct", "10")),
        trade_eur=float(legacy.db.value("paper_trade_eur", "25")),
    )
    return engine.run()

controller = AutomationControllerV67(
    legacy.db,
    legacy.pipeline,
    legacy.news_prefilter,
    ControlledLearning(legacy.db),
    NewsLearning(legacy.db),
    run_paper_cycle,
    real_allocator,
)
controller.start_background()
base.controller = controller
legacy.controller = controller

legacy.NAV_ITEMS = [
    ("/", "Übersicht"),
    ("/analyse", "Analyse"),
    ("/portfolio-v95", "Portfolio"),
    ("/handel-v95", "Handel"),
    ("/lernen-v95", "Lernen"),
    ("/diagnose-v95", "Diagnose"),
    ("/prozess-v95", "Prozess"),
    ("/automatik-v95", "Automatik"),
    ("/real-trading", "Realhandel"),
    ("/tax-info", "Steuerinfo AT"),
]

def _safe(fn, default=None):
    try:
        return fn()
    except Exception:
        return default

def _health():
    mh = ModelHealth(legacy.db)
    return {
        f: mh.evaluate(
            f,
            require_long_horizon=False,
            max_drawdown_pct=float(legacy.db.value("real_balancing_max_drawdown_pct", "-25")),
        )
        for f in ("crypto_spot", "xstocks", "forex")
    }

def _decision_rows(limit=50):
    return DecisionEngineV95(legacy.db).latest(limit=limit)

def _news_status():
    rows = _safe(lambda: legacy.db.rows("SELECT source_class,last_status,last_error,consecutive_failures FROM news_sources WHERE enabled=1 ORDER BY source_class,name"), []) or []
    items = int((_safe(lambda: legacy.db.rows("SELECT COUNT(*) n FROM news_items"), [{"n":0}]) or [{"n":0}])[0]["n"])
    links = int((_safe(lambda: legacy.db.rows("SELECT COUNT(*) n FROM news_market_links"), [{"n":0}]) or [{"n":0}])[0]["n"])
    return {"items":items,"links":links,"sources":rows}

def _process_status():
    public = _safe(legacy.stream.status, {}) or {}
    private = _safe(legacy.private_stream.status, {}) or {}
    research = _safe(legacy.pipeline.latest, {}) or {}
    health = _health()
    paper = _safe(lambda: legacy.db.rows("SELECT * FROM paper_snapshots ORDER BY id DESC LIMIT 1"), []) or []
    real = _decision_rows(20)
    return {
        "market":public,
        "private":private,
        "research":research,
        "news":_news_status(),
        "health":health,
        "paper":paper[0] if paper else None,
        "decisions":real,
    }

def _dashboard():
    p = _process_status()
    auto = controller.settings()
    latest = p["decisions"][:12]
    real_enabled = str(auto.get("automation_real_enabled","false")).lower() == "true"
    real_execute = str(auto.get("automation_real_execute_enabled","false")).lower() == "true"
    live = real_enabled and real_execute
    return legacy.page(
        '''<section class="hero">
<div><span class="eyebrow">KTKI v95</span><h1>Kraken Trader</h1>
<p class="lead">Ein Prozess von Kraken-Daten und Nachrichten über Bewertung und Lernen bis zur Zielposition und Order.</p></div>
<strong class="hero-state">{{ "REALHANDEL FREIGEGEBEN" if live else "REALHANDEL BLOCKIERT" }}</strong>
</section>
<div class="summary-grid">
<div class="summary"><span>Marktdaten</span><b>{{market.effective_state or "—"}}</b><small>{{market.symbol_count or 0}} Symbole</small></div>
<div class="summary"><span>Research</span><b>{{research.stage or "—"}}</b><small>{{research.status or "—"}} · {{research.progress_current or 0}}/{{research.progress_total or 0}}</small></div>
<div class="summary"><span>News</span><b>{{news.items}}</b><small>{{news.links}} Marktverknüpfungen · 48h-Fenster</small></div>
<div class="summary"><span>Paper</span><b>{{paper.total_eur|float if paper else "—"}} €</b><small>{{paper.quality if paper else "Noch kein Snapshot"}}</small></div>
</div>
<div class="process-strip">
{% for x in ["Kraken","News","Analyse","Lernen","Target","Order"] %}<div class="process-node"><span>{{loop.index}}</span><b>{{x}}</b></div>{% if not loop.last %}<i>→</i>{% endif %}{% endfor %}
</div>
<div class="card"><h2>Letzte Handelsentscheidungen</h2>
<table><tr><th>Zeit</th><th>Symbol</th><th>Aktion</th><th>Regime</th><th>Edge nach Kosten</th><th>Target</th><th>Delta</th><th>Status</th></tr>
{% for x in latest %}<tr><td>{{x.created_at}}</td><td>{{x.symbol}}</td><td>{{x.action}}</td><td>{{x.regime}}</td><td>{{x.expected_edge_after_costs_pct or "—"}} %</td><td>{{x.target_exposure_eur}} €</td><td>{{x.delta_eur}} €</td><td>{{x.status}}</td></tr>{% else %}<tr><td colspan="8">Noch keine v95-Entscheidung gespeichert.</td></tr>{% endfor %}</table></div>
<div class="split">
<div class="card"><h2>Modellqualität</h2>{% for family,h in health.items() %}<div class="allocation"><div><b>{{family}}</b><small>{{h.status}} · H24 {{h.samples}} Samples</small></div><strong>{{h.quality_score}} / 100</strong></div>{% endfor %}</div>
<div class="card"><h2>Steuerinfo</h2><p>Die bestehende österreichische Steuerinformation bleibt als eigene Fachseite erhalten. v95 vermischt Steuerberechnung nicht mit der Handelsentscheidung.</p><p><a href="{{request.script_root}}/tax-info">Steuerinfo AT öffnen →</a></p></div>
</div>''',
        market=p["market"], research=p["research"], news=p["news"], paper=p["paper"],
        health=p["health"], latest=latest, live=live, auto=auto
    )

def _analysis():
    job = _safe(legacy.pipeline.latest, {}) or {}
    rows = scanner_candidates(legacy.db)[:40]
    return legacy.page(
        '''<div class="section-head"><div><span class="eyebrow">Analyse</span><h1>Analyse</h1><p class="lead">Nur aktuelle valide Kandidaten gelangen in die gemeinsame Entscheidungsbasis.</p></div></div>
<div class="card"><h2>Pipeline</h2><p><b>{{job.stage or "—"}}</b> · {{job.status or "—"}} · {{job.progress_current or 0}}/{{job.progress_total or 0}}</p><p>{{job.details_json or "—"}}</p></div>
<div class="card"><h2>Aktuelle Kandidaten</h2><table><tr><th>Symbol</th><th>Signal</th><th>Score</th><th>Momentum</th><th>Trend</th><th>Volatilität</th><th>News</th><th>Qualität</th></tr>{% for x in rows %}<tr><td>{{x.symbol}}</td><td>{{x.signal}}</td><td>{{x.score}}</td><td>{{x.momentum_pct}}%</td><td>{{x.trend_pct}}%</td><td>{{x.volatility_pct}}%</td><td>{{x.news_score}}</td><td>{{x.quality}}</td></tr>{% endfor %}</table></div>''',
        job=job, rows=rows
    )

def _portfolio():
    real = _safe(lambda: legacy.db.rows("SELECT created_at,total_eur,quality FROM portfolio_snapshots ORDER BY id DESC LIMIT 100"), []) or []
    paper = _safe(lambda: legacy.db.rows("SELECT created_at,total_eur,quality FROM paper_snapshots ORDER BY id DESC LIMIT 100"), []) or []
    pos = _safe(lambda: legacy.db.rows("SELECT symbol,quantity,avg_cost_eur FROM paper_positions ORDER BY symbol"), []) or []
    return legacy.page(
        '''<span class="eyebrow">Portfolio</span><h1>Portfolio</h1><p class="lead">Zielposition, aktuelles Portfolio und Paper-Equity bleiben getrennt nachvollziehbar.</p>
<div class="chart-grid"><div class="chart-card"><b>Paper-Equity</b>{{paper_chart|safe}}</div><div class="chart-card"><b>Real-Portfolio</b>{{real_chart|safe}}</div></div>
<div class="split"><div class="card"><h2>Paperpositionen</h2>{% for x in pos %}<div class="allocation"><div><b>{{x.symbol}}</b><small>{{x.quantity}}</small></div><strong>{{x.avg_cost_eur}} €</strong></div>{% else %}<span class="muted">Keine Positionen.</span>{% endfor %}</div>
<div class="card"><h2>Letzter Ziel-/Orderstatus</h2>{% for x in decisions[:15] %}<div class="allocation"><div><b>{{x.symbol}}</b><small>{{x.action}} · {{x.execution_symbol or "—"}}</small></div><strong>{{x.target_exposure_eur}} €</strong></div>{% else %}<span class="muted">Noch keine Entscheidung.</span>{% endfor %}</div></div>''',
        paper_chart=legacy._chart([x["total_eur"] for x in reversed(paper)]), real_chart=legacy._chart([x["total_eur"] for x in reversed(real)]), pos=pos, decisions=_decision_rows(30)
    )

def _handel():
    decisions = _decision_rows(80)
    return legacy.page(
        '''<span class="eyebrow">Handel</span><h1>Order-Entscheidungen</h1><p class="lead">Jede Order entsteht aus derselben v95-Entscheidung. Angezeigt werden Steuer- und Risikoinformationen, nicht nur BUY/SELL.</p>
<div class="card"><h2>Decision Ledger</h2><table><tr><th>Zeit</th><th>Umgebung</th><th>Symbol</th><th>Aktion</th><th>Regime</th><th>Brutto-Edge</th><th>Edge nach Kosten</th><th>Current</th><th>Target</th><th>Delta</th><th>Ausführung</th><th>Status</th></tr>{% for x in decisions %}<tr><td>{{x.created_at}}</td><td>{{x.environment}}</td><td>{{x.symbol}}</td><td>{{x.action}}</td><td>{{x.regime}}</td><td>{{x.expected_edge_gross_pct or "—"}}</td><td>{{x.expected_edge_after_costs_pct or "—"}}</td><td>{{x.current_exposure_eur}}</td><td>{{x.target_exposure_eur}}</td><td>{{x.delta_eur}}</td><td>{{x.execution_symbol or "—"}} · {{x.execution_mode or "—"}} · {{x.leverage or "1"}}x</td><td>{{x.status}}</td></tr>{% else %}<tr><td colspan="12">Noch keine v95-Entscheidung.</td></tr>{% endfor %}</table></div>''',
        decisions=decisions
    )

def _lernen():
    cl=ControlledLearning(legacy.db); nl=NewsLearning(legacy.db)
    fam=cl.family_overview()
    pending=cl.candidates()
    news_pending=nl.candidates()
    return legacy.page(
        '''<span class="eyebrow">Lernen</span><h1>Lernen & Freigaben</h1><p class="lead">Learning verändert den aktiven Parameterstand erst nach den bestehenden Gates und der expliziten Freigabe. H24 ist operativ, H168 bleibt Validierung.</p>
<div class="learning-grid">{% for x in fam %}<div class="learning-card"><span class="eyebrow">{{x.family}}</span><h3>Aktiv v{{x.active_version or "—"}}</h3><b>{{x.pending_count}} offen</b><small>{{x.latest_status}}</small></div>{% endfor %}<div class="learning-card"><span class="eyebrow">news</span><h3>Aktiv v{{news_active.version if news_active else "—"}}</h3><b>{{news_pending|length}} offen</b><small>Nachrichten-Lernen</small></div></div>
<div class="card"><h2>Strategie-Kandidaten</h2><table><tr><th>ID</th><th>Familie</th><th>Status</th><th>Samples</th><th>Verbesserung</th><th>Grund</th></tr>{% for x in pending[:40] %}<tr><td>{{x.id}}</td><td>{{x.family}}</td><td>{{x.status}}</td><td>{{x.sample_count}}</td><td>{{x.improvement}}</td><td>{{x.reason}}</td></tr>{% endfor %}</table></div>
<div class="card"><h2>Nachrichten-Kandidaten</h2><table><tr><th>ID</th><th>Status</th><th>Samples</th><th>Verbesserung</th><th>Grund</th></tr>{% for x in news_pending[:30] %}<tr><td>{{x.id}}</td><td>{{x.status}}</td><td>{{x.sample_count}}</td><td>{{x.improvement}}</td><td>{{x.reason}}</td></tr>{% endfor %}</table></div>''',
        fam=fam, pending=pending, news_pending=news_pending, news_active=nl.active()
    )

def _diagnose():
    p=_process_status()
    blocked=_safe(lambda: legacy.db.rows("SELECT created_at,symbol,action,rule_key,reason FROM decision_rule_evaluations WHERE passed=0 ORDER BY id DESC LIMIT 100"),[]) or []
    market_diag=_safe(lambda: legacy.history.diagnostics(), []) or []
    return legacy.page(
        '''<span class="eyebrow">Diagnose</span><h1>Gesamtsystem-Diagnose</h1><p class="lead">Die Diagnose beantwortet zuerst: Sind Daten aktuell? Wurde bewertet? Warum wurde gehandelt oder blockiert?</p>
<div class="grid"><div class="card"><h3>Public Kraken</h3><div class="metric">{{p.market.effective_state}}</div><small>{{p.market.last_message_at or "—"}}</small></div><div class="card"><h3>Private Kraken</h3><div class="metric">{{p.private.effective_state}}</div><small>{{p.private.last_message_at or "—"}}</small></div><div class="card"><h3>News</h3><div class="metric">{{p.news.items}}</div><small>{{p.news.links}} Verknüpfungen</small></div><div class="card"><h3>Entscheidungen</h3><div class="metric">{{p.decisions|length}}</div><small>letzte v95-Snapshots</small></div></div>
<div class="card"><h2>Model Health – korrekt interpretiert</h2><p>Die folgenden Werte sind Forecast-Qualität. Sie sind ausdrücklich <b>keine Depot-Rendite</b>.</p>{% for f,h in p.health.items() %}<div class="allocation"><div><b>{{f}}</b><small>H24 {{h.mean_edge_after_costs_pct}}% · Hit {{(h.horizons["24"].hit_rate*100) if h.horizons["24"].hit_rate is not none else "—"}}% · Worst {{h.horizons["24"].worst_sample_pct}}%</small></div><strong>{{h.quality_score}} / 100</strong></div>{% endfor %}</div>
<div class="card"><h2>Blockierte Entscheidungen</h2><table><tr><th>Zeit</th><th>Symbol</th><th>Aktion</th><th>Regel</th><th>Grund</th></tr>{% for x in blocked %}<tr><td>{{x.created_at}}</td><td>{{x.symbol}}</td><td>{{x.action}}</td><td>{{x.rule_key}}</td><td>{{x.reason}}</td></tr>{% else %}<tr><td colspan="5">Keine gespeicherte Blockierung.</td></tr>{% endfor %}</table></div>
<div class="card"><h2>Kraken-Marktdaten-Diagnose</h2><table><tr><th>Symbol</th><th>Ticker</th><th>OHLC</th><th>Punkte</th><th>Letzter Fehler</th></tr>{% for x in market_diag[:60] %}<tr><td>{{x.symbol}}</td><td>{{x.ticker_status}}</td><td>{{x.ohlc_status}}</td><td>{{x.ohlc_points}}</td><td>{{x.error_reason or "—"}}</td></tr>{% endfor %}</table></div>''',
        p=p, blocked=blocked, market_diag=market_diag
    )

def _automatik():
    cfg=controller.settings()
    return legacy.page(
        '''<span class="eyebrow">Automatik</span><h1>Automatik</h1><p class="lead">Betriebs- und Handelsparameter liegen in der Home-Assistant-Konfiguration. Diese Seite zeigt nur den laufenden Zustand.</p>
<div class="automation-grid">{% for k,n in items %}<div class="automation-card"><b>{{n}}</b><span class="status {{'on' if cfg["automation_"+k+"_enabled"]=="true" else "off"}}">{{"AN" if cfg["automation_"+k+"_enabled"]=="true" else "AUS"}}</span><small>{{cfg["automation_"+k+"_interval_minutes"]}} min</small></div>{% endfor %}</div>
<div class="card"><h2>Real-Sicherheit</h2><p>Real-Execute: <b>{{cfg.automation_real_execute_enabled}}</b>. Zusätzlich gelten Kill-Switch, API-Freigabe, Limits, Balance, Margin- und Kraken-Orderregeln.</p><p><a href="{{request.script_root}}/real-trading">Realhandel & Blockierungen →</a></p></div>''',
        cfg=cfg, items=[("news","Nachrichten"),("analysis","Analyse"),("learning","Lernen"),("paper","Paper"),("real","Real")]
    )

def _chart(values):
    vals=[]
    for value in values or []:
        try:
            vals.append(float(value))
        except (TypeError,ValueError):
            pass
    if not vals:
        return '<svg viewBox="0 0 800 180" class="chart"><text x="24" y="90">Noch keine Historie</text></svg>'
    lo,hi=min(vals),max(vals)
    if hi==lo:
        lo-=1
        hi+=1
    pts=[]
    for i,v in enumerate(vals):
        x=28+744*i/max(1,len(vals)-1)
        y=24+128*(1-(v-lo)/(hi-lo))
        pts.append(f"{x:.1f},{y:.1f}")
    return f'<svg viewBox="0 0 800 180" class="chart" role="img" aria-label="Portfolioverlauf"><line x1="28" y1="152" x2="772" y2="152" class="chart-axis"/><polyline points="{" ".join(pts)}" class="chart-line" fill="none"/><text x="28" y="16" class="chart-label">{hi:.2f} €</text><text x="28" y="174" class="chart-label">{lo:.2f} €</text><text x="772" y="16" text-anchor="end" class="chart-value">{vals[-1]:.2f} €</text></svg>'

@app.get("/analyse")
def analyse_v95():
    return _analysis()

@app.get("/portfolio-v95")
def portfolio_v95():
    return _portfolio()

@app.get("/handel-v95")
def handel_v95():
    return _handel()

@app.get("/lernen-v95")
def lernen_v95():
    return _lernen()

@app.get("/diagnose-v95")
def diagnose_v95():
    return _diagnose()

@app.get("/automatik-v95")
def automatik_v95():
    return _automatik()

@app.get("/prozess-v95")
def prozess_v95():
    return legacy.page(
        '''<span class="eyebrow">Prozess</span><h1>End-to-End-Ablauf</h1><p class="lead">Dies ist der verbindliche v95-Datenweg.</p>
<div class="flow">{% for s in steps %}<div class="card"><div class="flowstep"><span class="num">{{loop.index}}</span><div><h3>{{s.title}}</h3><p>{{s.text}}</p></div></div></div>{% endfor %}</div>''',
        steps=[
            {"title":"1. Kraken Market Data","text":"WebSocket-Ticker plus REST/Cache für Ticker und abgeschlossene OHLC-Kerzen; Datenqualität entscheidet, ob ein Markt valide ist."},
            {"title":"2. Nachrichten","text":"Quellen werden gesammelt, klassifiziert, lokal/extern bewertet und nur mit frischem Zeitfenster in Marktverknüpfungen übernommen."},
            {"title":"3. Prefilter & Scanner","text":"Liquidität, Spread, Momentum, Trend, Volatilität und News werden zu einem Kandidaten-Score; BUY/ HOLD/ AVOID werden getrennt interpretiert."},
            {"title":"4. Forecast & Evaluation","text":"H24/H168 Forecasts werden gegen abgeschlossene Kerzen bewertet; Long- und Downside-Evidenz werden getrennt."},
            {"title":"5. Controlled Learning","text":"Parameter werden auf zeitlichem Holdout gegen die aktive Version geprüft. AVOID bedeutet Long/Flat, nicht automatisch Short."},
            {"title":"6. DecisionEngineV95","text":"Ein gemeinsamer deterministischer Prozess berechnet Richtung, Modelqualität, Regime, Kosten, Expected Edge und Zielposition."},
            {"title":"7. Rebalancing","text":"Target minus Current ergibt das konkrete Delta. HOLD hält, AVOID reduziert Long-Ziele auf null, SHORT ist nur mit expliziter Margin-Short-Freigabe möglich."},
            {"title":"8. Execution","text":"Nur die letzte Schicht unterscheidet sich: Paper simuliert den Kraken-Fill; Real nutzt das konkrete günstigste Kraken-Ausführungspaar plus die normalen Sicherheits-Gates."},
            {"title":"9. Nachkontrolle & Steuer","text":"Portfolio-/Execution-Events, Audit und die separate österreichische Steuerinfo liefern Nachweis und steuerliche Auswertung."},
        ]
    )

@app.get("/v95-health")
def v95_health():
    return jsonify({
        "version":"0.1.0-dev.95",
        "runtime":"v95_main",
        "architecture":"SHARED_DECISION_ENGINE_PAPER_REAL",
        "economic_gate":"EXPECTED_GROSS_EDGE - FULL_ENTRY_EXIT_ROUTE_COST > 0",
        "model_health":"QUALITY_AND_SIZING_NOT_PORTFOLIO_RETURN",
        "news":"FRESH_48H_DECAYED_AND_IN_SCANNER",
        "rebalancing":"TARGET_MINUS_CURRENT",
        "tax_info":request.script_root+"/tax-info",
        "process":_process_status(),
    })

app.view_functions["index"] = _dashboard
