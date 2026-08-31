import json
import os
from datetime import datetime, timezone, timedelta

# Disable the three legacy schedulers before importing main. v67 owns one
# scheduler so that research, learning, paper and real balancing cannot drift.
os.environ.setdefault('APP_DISABLE_PAPER_SCHEDULER', '1')
os.environ.setdefault('APP_DISABLE_RESEARCH_SCHEDULER', '1')
os.environ.setdefault('APP_DISABLE_REAL_BALANCING_SCHEDULER', '1')

import main as legacy
from flask import render_template_string, request, redirect, url_for

from automation_v67 import AutomationControllerV67, DEFAULTS as AUTOMATION_DEFAULTS
from controlled_learning import ControlledLearning
from news_learning import NewsLearning
from forecast_tracker import ForecastTracker
from prefilter import MarketPrefilter
from scanner import MarketScanner

app = legacy.app
db = legacy.db


def _seed_v67_settings():
    # Do not overwrite existing user settings. These are deliberately narrow
    # operational controls rather than the large legacy option surface.
    option_values = getattr(legacy, 'opts', {}) or {}
    for key, default in AUTOMATION_DEFAULTS.items():
        if db.rows('SELECT value FROM settings WHERE key=?', (key,)):
            continue
        value = option_values.get(key, default)
        db.set_setting(key, value)


_seed_v67_settings()


# ---------------------------------------------------------------------------
# Performance layer
# ---------------------------------------------------------------------------
# The historical learning implementations are useful but their sample bases
# are unbounded. v67 keeps a recent, deterministic training horizon and avoids
# repeating an identical candidate search when the evidence has not changed.

_original_cl_evaluations = ControlledLearning._evaluations
_original_cl_propose = ControlledLearning.propose
_original_nl_samples = NewsLearning._samples


def _bounded_cl_evaluations(self, family):
    limit = max(50, min(5000, int(float(self.db.value('learning_max_evaluations', '600')))))
    cols = {x['name'] for x in self.db.rows('PRAGMA table_info(research_forecasts)')}
    features = 'f.features_json' if 'features_json' in cols else "'{}' AS features_json"
    horizon = 'f.horizon_hours' if 'horizon_hours' in cols else '0 AS horizon_hours'
    rows = self.db.rows(
        f"SELECT f.id,f.direction,f.scanner_score,{features},{horizon},"
        "e.direction_correct,e.actual_return_pct "
        "FROM forecast_evaluations e "
        "JOIN research_forecasts f ON f.id=e.forecast_id "
        "JOIN market_universe u ON u.symbol=f.symbol "
        "WHERE u.category=? "
        "ORDER BY e.evaluated_at DESC, f.id DESC LIMIT ?",
        (family, limit))
    return list(reversed(rows))


ControlledLearning._evaluations = _bounded_cl_evaluations


def _bounded_cl_propose(self, family, min_sample=10, min_improvement=.02):
    rows = self._evaluations(family)
    total = len(rows)
    if total < min_sample:
        return {'status': 'INSUFFICIENT_DATA', 'sample_count': total, 'required': min_sample}
    active = self.active(family)
    if not active:
        return {'status': 'NO_ACTIVE_VERSION'}
    policy = self.gate_policy()
    minimum_validation = max(
        3,
        int(self.db.value('learning_min_validation_samples', '5')),
        len(policy['required_horizons']) * int(policy['minimum_horizon_samples']))
    validation_count = max(minimum_validation, int(__import__('math').ceil(total * .30)))
    if validation_count >= total:
        return _original_cl_propose(self, family, min_sample, min_improvement)
    validation_rows = rows[-validation_count:]
    fingerprint = self._sample_fingerprint(validation_rows)
    existing = self.db.rows(
        "SELECT id,status,sample_count FROM learning_candidates "
        "WHERE family=? AND base_version=? AND validation_fingerprint=? "
        "ORDER BY id DESC LIMIT 1",
        (family, active['version'], fingerprint))
    if existing:
        return {
            'status': 'UNCHANGED',
            'candidate_id': existing[0]['id'],
            'candidate_status': existing[0]['status'],
            'sample_count': total,
            'validation_count': validation_count,
        }
    return _original_cl_propose(self, family, min_sample, min_improvement)


ControlledLearning.propose = _bounded_cl_propose


def _bounded_nl_samples(self):
    limit = max(50, min(5000, int(float(self.db.value('news_learning_max_samples', '600')))))
    cols = {x['name'] for x in self.db.rows('PRAGMA table_info(news_items)')}
    time_expr = "COALESCE(n.published_at,n.fetched_at,a.created_at)" if {'published_at', 'fetched_at'}.issubset(cols) else 'a.created_at'
    rows = self.db.rows(
        f"SELECT n.id,n.title,n.summary,s.source_class,a.result_json,{time_expr} AS observed_at "
        "FROM news_items n JOIN news_sources s ON s.name=n.source_name "
        "JOIN external_news_ai_results a ON a.news_id=n.id "
        "WHERE a.status='VALID' ORDER BY observed_at DESC,n.id DESC LIMIT ?",
        (limit,))
    rows.reverse()
    out = []
    for row in rows:
        try:
            teacher = json.loads(row.pop('result_json') or '{}')
        except Exception:
            continue
        row['teacher'] = teacher
        row['target'] = self._teacher(teacher)
        out.append(row)
    return out


NewsLearning._samples = _bounded_nl_samples


def _bounded_nl_refresh_local(self):
    active = self.active()
    if not active:
        return {'status': 'NO_ACTIVE_VERSION', 'evaluated': 0}
    params = json.loads(active['parameters_json'])
    limit = max(100, min(10000, int(float(self.db.value('news_local_eval_max_items', '1000')))))
    rows = self.db.rows(
        'SELECT n.id,n.title,n.summary,s.source_class FROM news_items n '
        'JOIN news_sources s ON s.name=n.source_name ORDER BY n.fetched_at DESC,n.id DESC LIMIT ?',
        (limit,))
    with self.db.con() as c:
        for row in rows:
            score = self._local(row, params)
            c.execute(
                'INSERT INTO news_local_evaluations(news_id,evaluated_at,model_version,score,details_json) '
                'VALUES(?,?,?,?,?) ON CONFLICT(news_id) DO UPDATE SET evaluated_at=excluded.evaluated_at,'
                'model_version=excluded.model_version,score=excluded.score,details_json=excluded.details_json',
                (row['id'], legacy.db.now() if hasattr(legacy.db, 'now') else __import__('db').now(),
                 active['version'], str(score), json.dumps({'parameters': params}, sort_keys=True)))
    return {'status': 'VALID', 'evaluated': len(rows), 'version': active['version'], 'limit': limit}


# Avoid relying on a db module function accidentally shadowed by imports.
_bounded_nl_refresh_local.__globals__['legacy'] = legacy
NewsLearning.refresh_local = _bounded_nl_refresh_local

_original_scanner_run = MarketScanner.run
_original_prefilter_run = MarketPrefilter.run


def _compact_prefilter_run(self, top=8):
    compact_top = max(1, min(int(top), int(float(self.db.value('analysis_top_per_category', '5')))))
    return _original_prefilter_run(self, compact_top)


MarketPrefilter.run = _compact_prefilter_run


def _compact_scanner_run(self, symbols, interval=60, limit=None, delay_seconds=None):
    max_symbols = max(1, min(200, int(float(self.db.value('analysis_max_symbols', '20')))))
    bounded = list(dict.fromkeys(symbols or []))[:max_symbols]
    configured_delay = float(self.db.value('analysis_max_delay_seconds', '0.35'))
    requested_delay = configured_delay if delay_seconds is None else float(delay_seconds)
    return _original_scanner_run(self, bounded, interval, min(limit or len(bounded), len(bounded)), min(requested_delay, configured_delay))


MarketScanner.run = _compact_scanner_run


# Bound due forecast evaluation to the oldest open records first. This keeps
# one stalled batch from turning every paper/research cycle into an O(N) walk.
_original_forecast_evaluate_due = ForecastTracker.evaluate_due


def _bounded_forecast_evaluate_due(self):
    limit = max(100, min(5000, int(float(self.db.value('forecast_due_batch_limit', '1000')))))
    rows = self.db.rows(
        "SELECT * FROM research_forecasts WHERE status='OPEN' ORDER BY created_at ASC,id ASC LIMIT ?",
        (limit,))
    if len(rows) < limit:
        return _original_forecast_evaluate_due(self)
    # Temporarily constrain the query used by the original method. The query
    # itself is reconstructed here to avoid mutating global database state.
    import types
    original_rows = self.db.rows
    def bounded_rows(q, p=()):
        normalized = ' '.join(str(q).split()).upper()
        if normalized.startswith('SELECT * FROM RESEARCH_FORECASTS WHERE STATUS='):
            return rows
        return original_rows(q, p)
    self.db.rows = bounded_rows
    try:
        return _original_forecast_evaluate_due(self)
    finally:
        self.db.rows = original_rows


ForecastTracker.evaluate_due = _bounded_forecast_evaluate_due


# ---------------------------------------------------------------------------
# Unified automation controller
# ---------------------------------------------------------------------------
controller = AutomationControllerV67(
    db=legacy.db,
    pipeline=legacy.pipeline,
    news_prefilter=legacy.news_prefilter,
    controlled_learning=ControlledLearning(legacy.db),
    news_learning=NewsLearning(legacy.db),
    run_paper_cycle=legacy.run_paper_cycle,
    real_allocator=legacy.real_allocator,
)

controller.start_background()


# ---------------------------------------------------------------------------
# Presentation helpers
# ---------------------------------------------------------------------------
legacy.NAV_ITEMS = [
    ('/', 'Übersicht'),
    ('/analyse', '1 Analyse'),
    ('/portfolio-modern', '2 Portfolio'),
    ('/handel', '3 Handel'),
    ('/lernen-modern', '4 Lernen'),
    ('/automatik', '5 Automatik'),
    ('/parameter', 'Parameter'),
]


def _safe_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _svg_line(values, width=900, height=260, padding=28):
    vals = [_safe_float(v) for v in values]
    if not vals:
        return '<svg viewBox="0 0 900 260" role="img"><text x="30" y="130">Noch keine Historie vorhanden</text></svg>'
    lo, hi = min(vals), max(vals)
    if abs(hi - lo) < 1e-12:
        lo -= 1
        hi += 1
    inner_w = width - 2 * padding
    inner_h = height - 2 * padding
    points = []
    for i, value in enumerate(vals):
        x = padding + (inner_w * i / max(1, len(vals) - 1))
        y = padding + inner_h * (1 - (value - lo) / (hi - lo))
        points.append(f'{x:.1f},{y:.1f}')
    last = vals[-1]
    return (
        f'<svg class="chart" viewBox="0 0 {width} {height}" role="img" aria-label="Portfolioverlauf">'
        f'<line x1="{padding}" y1="{height-padding}" x2="{width-padding}" y2="{height-padding}" class="chart-axis"/>'
        f'<polyline points="{" ".join(points)}" class="chart-line" fill="none"/>'
        f'<circle cx="{points[-1].split(",")[0]}" cy="{points[-1].split(",")[1]}" r="4" class="chart-dot"/>'
        f'<text x="{padding}" y="18" class="chart-label">Min {lo:.2f} €</text>'
        f'<text x="{width-padding}" y="18" text-anchor="end" class="chart-label">Max {hi:.2f} €</text>'
        f'<text x="{width-padding}" y="{height-6}" text-anchor="end" class="chart-value">Aktuell {last:.2f} €</text>'
        '</svg>')


def _automation_rows():
    cfg = controller.settings()
    labels = {
        'analysis': 'Analyse / Research',
        'news': 'Nachrichten',
        'learning': 'Lernen & Freigabe',
        'paper': 'Paper-Handel',
        'real': 'Realhandel',
    }
    intervals = {k: cfg['automation_' + k + '_interval_minutes'] for k in labels}
    rows = []
    for key, label in labels.items():
        latest = controller.latest(100)
        item = next((x for x in latest if x['subsystem'] == key), None)
        rows.append({
            'key': key,
            'label': label,
            'enabled': str(cfg['automation_' + key + '_enabled']).lower() == 'true',
            'interval': intervals[key],
            'status': item['status'] if item else 'NOCH NICHT GELAUFEN',
            'time': item['created_at'] if item else '—',
            'error': item.get('error') if item else '',
        })
    return rows


def _dashboard_data():
    portfolio = legacy.db.rows('SELECT total_eur,quality,created_at FROM portfolio_snapshots ORDER BY id DESC LIMIT 1')
    paper = legacy.db.rows('SELECT total_eur,quality,created_at FROM paper_snapshots ORDER BY id DESC LIMIT 1')
    job = legacy.pipeline.latest()
    cfg = controller.settings()
    return portfolio[0] if portfolio else None, paper[0] if paper else None, job, cfg


# ---------------------------------------------------------------------------
# Modern dashboard
# ---------------------------------------------------------------------------
@app.get('/v67-dashboard')
def dashboard_v67():
    portfolio, paper, job, cfg = _dashboard_data()
    auto = _automation_rows()
    return legacy.page("""
    <section class="hero"><div><span class="eyebrow">KTKI v67</span><h1>Kraken Trader Control Center</h1><p class="lead">Ein Prozessbild von Marktdaten über Analyse und Lernen bis zum Handel. Automatik wird ausschließlich über die einzelnen Schalter gesteuert.</p></div><div class="hero-state"><span class="state-dot"></span>{{'AUTOMATIK AKTIV' if cfg.automation_master_enabled=='true' else 'AUTOMATIK AUS'}}</div></section>
    <div class="summary-grid">
      <div class="summary"><span>Realportfolio</span><b>{{'%.2f'|format(portfolio.total_eur|float) if portfolio else '—'}} €</b><small>{{portfolio.quality if portfolio else 'Noch kein Snapshot'}}</small></div>
      <div class="summary"><span>Paper</span><b>{{'%.2f'|format(paper.total_eur|float) if paper else '—'}} €</b><small>{{paper.quality if paper else 'Noch kein Snapshot'}}</small></div>
      <div class="summary"><span>Analyse</span><b>{{job.stage if job else '—'}}</b><small>{{job.progress_current if job else 0}} / {{job.progress_total if job else 0}}</small></div>
      <div class="summary"><span>Live-Orders</span><b>{{'AKTIV' if cfg.automation_real_enabled=='true' and cfg.automation_real_execute_enabled=='true' else 'BLOCKIERT'}}</b><small>Kill-Switch und Limits bleiben separat wirksam</small></div>
    </div>
    <div class="process-strip">{% for s in ['Daten','Analyse','Lernen','Portfolio','Handel'] %}<div class="process-node"><span>{{loop.index}}</span><b>{{s}}</b></div>{% if not loop.last %}<div class="process-arrow">→</div>{% endif %}{% endfor %}</div>
    <div class="section-head"><div><span class="eyebrow">Laufzustand</span><h2>Automationen</h2></div><a class="button secondary" href="{{url_for('automation_v67')}}">Steuern</a></div>
    <div class="automation-grid">{% for x in auto %}<div class="automation-card"><div><b>{{x.label}}</b><span class="status {{'on' if x.enabled else 'off'}}">{{'AN' if x.enabled else 'AUS'}}</span></div><strong>{{x.status}}</strong><small>Intervall {{x.interval}} min · {{x.time}}</small>{% if x.error %}<span class="error">{{x.error}}</span>{% endif %}</div>{% endfor %}</div>
    """, portfolio=portfolio, paper=paper, job=job, cfg=cfg, auto=auto)


# Keep root clean while preserving the legacy route under /v67-dashboard.
@app.get('/')
def dashboard_root():
    return dashboard_v67()


@app.get('/analyse')
def analysis_v67():
    job = legacy.pipeline.latest()
    watchlist = legacy.db.rows(
        "SELECT w.symbol,w.category,w.prefilter_score,w.status,s.score,s.signal,s.quality "
        "FROM research_watchlist w LEFT JOIN scanner_results s ON s.symbol=w.symbol "
        "ORDER BY CAST(w.prefilter_score AS REAL) DESC LIMIT 30")
    return legacy.page("""
    <div class="section-head"><div><span class="eyebrow">Schritt 1</span><h1>Analyse</h1><p class="lead">Daten → Vorfilter → Detailscan → Forecast. Die Analysebasis ist begrenzt und dedupliziert, damit ältere Historie die aktuellen Läufe nicht immer weiter verlangsamt.</p></div><form method="post" action="{{url_for('analysis_run_v67')}}"><button>Jetzt analysieren</button></form></div>
    <div class="timeline">{% for stage,detail in stages %}<div class="timeline-item {{'current' if job and job.stage==stage else ''}}"><span>{{loop.index}}</span><div><b>{{stage}}</b><small>{{detail}}</small></div></div>{% endfor %}</div>
    <div class="card"><div class="section-head"><div><h2>Letzter Lauf</h2><small>{{job.created_at if job else 'Noch kein Lauf'}}</small></div><b>{{job.status if job else '—'}}</b></div>{% if job %}<div class="progress"><i style="width:{{(job.progress_current / job.progress_total * 100) if job.progress_total else 0}}%"></i></div><p>{{job.stage}} · {{job.progress_current}} / {{job.progress_total}}</p>{% if job.error %}<p class="error">{{job.error}}</p>{% endif %}{% endif %}</div>
    <div class="section-head"><div><h2>Aktuelle Kandidaten</h2><small>Nur die für den nächsten Prozessschritt relevanten Märkte.</small></div></div>
    <div class="table-card"><table><tr><th>Produkt</th><th>Kategorie</th><th>Prefilter</th><th>Score</th><th>Signal</th><th>Qualität</th></tr>{% for x in watchlist %}<tr><td><b>{{x.symbol}}</b></td><td>{{x.category}}</td><td>{{x.prefilter_score}}</td><td>{{x.score or '—'}}</td><td><span class="tag">{{x.signal or '—'}}</span></td><td>{{x.quality or '—'}}</td></tr>{% endfor %}</table></div>
    """, job=job, watchlist=watchlist, stages=[
        ('UNIVERSE','Produkte und Märkte synchronisieren'),
        ('NEWS_AND_PREFILTER','Nachrichten, Ticker und Kandidatenvorfilter'),
        ('DEEP_SCAN','Abgeschlossene OHLC-Kerzen analysieren'),
        ('FORECAST_SNAPSHOT','Forecasts und spätere Auswertung vorbereiten'),
        ('LEARNING_CANDIDATES','Lernkandidaten anhand des begrenzten Samples berechnen'),
        ('DONE','Lauf vollständig abgeschlossen'),
    ])


@app.post('/analyse/run')
def analysis_run_v67():
    result = legacy.pipeline.start()
    legacy.db.audit('V67_ANALYSIS_MANUAL_RUN', json.dumps(result, sort_keys=True))
    return redirect(url_for('analysis_v67'))


@app.get('/portfolio-modern')
def portfolio_v67():
    real_history = legacy.db.rows('SELECT created_at,total_eur FROM portfolio_snapshots ORDER BY id ASC LIMIT 180')
    paper_history = legacy.db.rows('SELECT created_at,total_eur FROM paper_snapshots ORDER BY id ASC LIMIT 180')
    holdings = legacy.db.rows('SELECT display_name,amount,eur_price,eur_value,classification FROM portfolio_assets ORDER BY CAST(COALESCE(eur_value,0) AS REAL) DESC LIMIT 30')
    paper_positions = legacy.paper_engine.positions()
    return legacy.page("""
    <div class="section-head"><div><span class="eyebrow">Schritt 2</span><h1>Portfolio</h1><p class="lead">Entwicklung vor Allokation: Gesamtwert, Zusammensetzung und Paper-Depot werden chronologisch statt in langen Rohdatentabellen dargestellt.</p></div></div>
    <div class="chart-grid"><div class="chart-card"><div><b>Realportfolio</b><small>{{real_history|length}} Snapshots</small></div>{{real_chart|safe}}</div><div class="chart-card"><div><b>Paper-Portfolio</b><small>{{paper_history|length}} Snapshots</small></div>{{paper_chart|safe}}</div></div>
    <div class="split"><div class="card"><h2>Aktuelle Positionen</h2><div class="allocation-list">{% for x in holdings %}<div class="allocation"><div><b>{{x.display_name}}</b><small>{{x.classification}} · {{x.amount}}</small></div><strong>{{'%.2f'|format(x.eur_value|float)}} €</strong></div>{% endfor %}</div></div><div class="card"><h2>Paper-Positionen</h2><div class="allocation-list">{% for x in paper_positions %}<div class="allocation"><div><b>{{x.symbol}}</b><small>{{x.quantity}}</small></div><strong>{{x.avg_cost_eur}} €</strong></div>{% else %}<p class="muted">Keine Positionen.</p>{% endfor %}</div></div></div>
    """, real_history=real_history, paper_history=paper_history, real_chart=_svg_line([x['total_eur'] for x in real_history]), paper_chart=_svg_line([x['total_eur'] for x in paper_history]), holdings=holdings, paper_positions=paper_positions)


@app.get('/handel')
def trading_v67():
    cash,pv,total,missing = legacy.paper_engine.equity()
    paper_decisions = legacy.db.rows('SELECT created_at,symbol,action,score,executed,reason FROM paper_decisions ORDER BY id DESC LIMIT 25')
    real_runs = legacy.db.rows('SELECT created_at,status,automatic,details_json,error FROM real_allocation_runs ORDER BY id DESC LIMIT 10')
    return legacy.page("""
    <div class="section-head"><div><span class="eyebrow">Schritt 3</span><h1>Handel</h1><p class="lead">Paper und Realhandel folgen demselben Prozessbild. Die Ausführung selbst bleibt durch bestehende Risiko-, Limit- und Kill-Switch-Regeln geschützt.</p></div></div>
    <div class="summary-grid"><div class="summary"><span>Paper-Gesamtwert</span><b>{{'%.2f'|format(total|float)}} €</b><small>Cash {{'%.2f'|format(cash|float)}} €</small></div><div class="summary"><span>Paper Positionen</span><b>{{'%.2f'|format(pv|float)}} €</b><small>{{'LIVE-DATEN' if not missing else 'UNVOLLSTÄNDIG'}}</small></div><div class="summary"><span>Paper-Automatik</span><b>{{'AN' if cfg.automation_paper_enabled=='true' else 'AUS'}}</b><small>einzeln schaltbar</small></div><div class="summary"><span>Real-Automatik</span><b>{{'AN' if cfg.automation_real_enabled=='true' else 'AUS'}}</b><small>{{'Ausführung erlaubt' if cfg.automation_real_execute_enabled=='true' else 'Nur Dry-Run / blockiert'}}</small></div></div>
    <div class="section-head"><div><h2>Letzte Entscheidungen</h2></div><a class="button secondary" href="{{url_for('automation_v67')}}">Automatik steuern</a></div>
    <div class="table-card"><table><tr><th>Zeit</th><th>Produkt</th><th>Aktion</th><th>Score</th><th>Ausgeführt</th><th>Grund</th></tr>{% for x in paper_decisions %}<tr><td>{{x.created_at}}</td><td>{{x.symbol}}</td><td>{{x.action}}</td><td>{{x.score}}</td><td>{{'JA' if x.executed else 'NEIN'}}</td><td>{{x.reason}}</td></tr>{% else %}<tr><td colspan="6" class="muted">Noch keine Entscheidungen.</td></tr>{% endfor %}</table></div>
    <details><summary>Real-Automationsläufe</summary><div class="table-card"><table><tr><th>Zeit</th><th>Status</th><th>Automatisch</th><th>Fehler</th></tr>{% for x in real_runs %}<tr><td>{{x.created_at}}</td><td>{{x.status}}</td><td>{{'JA' if x.automatic else 'NEIN'}}</td><td>{{x.error or '—'}}</td></tr>{% else %}<tr><td colspan="4" class="muted">Noch keine Läufe.</td></tr>{% endfor %}</table></div></details>
    """, cash=cash, pv=pv, total=total, missing=missing, paper_decisions=paper_decisions, real_runs=real_runs, cfg=controller.settings())


@app.get('/lernen-modern')
def learning_v67():
    cl = ControlledLearning(legacy.db)
    nl = NewsLearning(legacy.db)
    families = []
    for item in cl.family_overview():
        families.append(item)
    return legacy.page("""
    <div class="section-head"><div><span class="eyebrow">Schritt 4</span><h1>Lernen</h1><p class="lead">Strategieparameter und Nachrichtenmodell werden automatisch gesucht und geprüft. Die Aktivierung bleibt ein eigener, einzeln schaltbarer Automatikschritt.</p></div></div>
    <div class="learning-grid">{% for x in families %}<div class="learning-card"><span class="eyebrow">{{x.family}}</span><h3>Aktiv v{{x.active_version or '—'}}</h3><b>{{x.pending_count}} offene Kandidaten</b><small>Letzter Kandidat #{{x.latest_candidate_id or '—'}} · {{x.latest_status}}</small></div>{% endfor %}<div class="learning-card"><span class="eyebrow">news</span><h3>Aktiv v{{news_active.version if news_active else '—'}}</h3><b>{{news_pending}} offene Kandidaten</b><small>Lokales Nachrichtenmodell</small></div></div>
    <div class="card"><div class="section-head"><div><h2>Automatikstatus</h2><small>Lernsuche, Freigabe und Datenumfang werden zentral unter Automatik gesteuert.</small></div><a class="button" href="{{url_for('automation_v67')}}">Steuern</a></div><div class="process-strip compact"><div class="process-node"><span>1</span><b>Samples</b></div><div class="process-arrow">→</div><div class="process-node"><span>2</span><b>Suche</b></div><div class="process-arrow">→</div><div class="process-node"><span>3</span><b>Holdout</b></div><div class="process-arrow">→</div><div class="process-node"><span>4</span><b>Freigabe</b></div></div></div>
    <details><summary>Offene Kandidaten</summary><div class="table-card"><table><tr><th>Art</th><th>ID</th><th>Familie</th><th>Status</th><th>Basis</th></tr>{% for x in candidates %}<tr><td>{{x.kind}}</td><td>#{{x.id}}</td><td>{{x.family or 'news'}}</td><td>{{x.status}}</td><td>{{x.base_version}}</td></tr>{% endfor %}</table></div></details>
    """, families=families, news_active=nl.active(), news_pending=len([x for x in nl.candidates() if x.get('status')=='PENDING']), candidates=[{'kind':'strategy',**x} for x in cl.candidates() if x.get('status')=='PENDING']+ [{'kind':'news',**x} for x in nl.candidates() if x.get('status')=='PENDING'])


@app.route('/automatik', methods=['GET','POST'])
def automation_v67():
    if request.method == 'POST':
        form = request.form
        keys = ['automation_master_enabled','automation_analysis_enabled','automation_news_enabled','automation_learning_enabled','automation_learning_auto_approve_enabled','automation_paper_enabled','automation_real_enabled','automation_real_execute_enabled']
        for key in keys:
            db.set(key, 'true' if form.get(key) else 'false')
        for key in ['automation_tick_minutes','automation_analysis_interval_minutes','automation_news_interval_minutes','automation_learning_interval_minutes','automation_paper_interval_minutes','automation_real_interval_minutes']:
            if key in form:
                try:
                    value = max(1, min(1440, int(float(form.get(key)))))
                except (TypeError, ValueError):
                    continue
                db.set(key, value)
        db.audit('V67_AUTOMATION_SETTINGS_CHANGED', json.dumps({k: db.value(k) for k in keys}, sort_keys=True))
        if form.get('run_now'):
            controller.run_once(force=True)
        return redirect(url_for('automation_v67'))
    return legacy.page("""
    <div class="section-head"><div><span class="eyebrow">Schritt 5</span><h1>Automatik</h1><p class="lead">Hier wird nur gesteuert, <em>was</em> automatisch läuft. Die fachlichen Regeln, Limits und Freigabegates bleiben im jeweiligen Prozess.</p></div></div>
    <form method="post"><div class="card master-card"><div><span class="eyebrow">Master-Schalter</span><h2>Gesamtautomatik</h2><small>Schaltet die unten aktivierten Subsysteme gemeinsam frei.</small></div><label class="switch"><input type="checkbox" name="automation_master_enabled" {{'checked' if cfg.automation_master_enabled=='true'}}><span></span></label></div>
    <div class="automation-settings">{% for row in rows %}<div class="automation-setting"><div><b>{{row.label}}</b><small>{{row.key}}</small></div><label class="switch"><input type="checkbox" name="automation_{{row.key}}_enabled" {{'checked' if row.enabled}}><span></span></label><label>Intervall<input type="number" min="1" max="1440" name="automation_{{row.key}}_interval_minutes" value="{{row.interval}}"></label></div>{% endfor %}</div>
    <div class="card"><h2>Lernen</h2><label class="checkline"><input type="checkbox" name="automation_learning_auto_approve_enabled" {{'checked' if cfg.automation_learning_auto_approve_enabled=='true'}}> Nach bestandenen Gates Kandidaten automatisch aktivieren</label><p class="warning">Die Aktivierung wird erst nach der bestehenden erneuten Gate-Prüfung durchgeführt; veraltete oder veränderte Samples werden abgewiesen.</p></div>
    <div class="card"><h2>Zentraler Takt</h2><label>Scheduler-Takt in Minuten<input type="number" min="1" max="60" name="automation_tick_minutes" value="{{cfg.automation_tick_minutes}}"></label></div>
    <div class="section-actions"><button>Speichern</button><button name="run_now" value="1" class="secondary">Jetzt alle fälligen Läufe anstoßen</button></div></form>
    <div class="card"><h2>Letzte Automationsläufe</h2><div class="table-card"><table><tr><th>Zeit</th><th>Subsystem</th><th>Status</th><th>Fehler</th></tr>{% for x in latest %}<tr><td>{{x.created_at}}</td><td>{{x.subsystem}}</td><td>{{x.status}}</td><td>{{x.error or '—'}}</td></tr>{% endfor %}</table></div></div>
    """, cfg=controller.settings(), rows=_automation_rows(), latest=controller.latest(40))


@app.route('/parameter', methods=['GET','POST'])
def parameter_v67():
    if request.method == 'POST':
        fields = {
            'analysis_top_per_category': (1, 25),
            'analysis_max_symbols': (1, 100),
            'analysis_max_delay_seconds': (0, 10),
            'learning_max_evaluations': (50, 5000),
            'news_learning_max_samples': (50, 5000),
            'news_local_eval_max_items': (100, 10000),
            'forecast_due_batch_limit': (100, 5000),
        }
        for key, (lo, hi) in fields.items():
            if key not in request.form: continue
            try: value=max(lo,min(hi,float(request.form[key])))
            except (TypeError,ValueError): continue
            db.set(key,int(value) if value.is_integer() else value)
        db.audit('V67_GENERAL_PARAMETERS_CHANGED')
        return redirect(url_for('parameter_v67'))
    cfg=controller.settings()
    return legacy.page("""
    <div class="section-head"><div><span class="eyebrow">Parameter</span><h1>Allgemeine Betriebsparameter</h1><p class="lead">Nur die Stellgrößen, die den Umfang und die Taktung bestimmen. Fachlogik und Sicherheitsregeln bleiben im System.</p></div></div>
    <form method="post"><div class="settings-grid"><div class="card"><h3>Analyse</h3><label>Kandidaten je Kategorie<input name="analysis_top_per_category" type="number" min="1" max="25" value="{{cfg.analysis_top_per_category}}"></label><label>Maximale Märkte pro Detailscan<input name="analysis_max_symbols" type="number" min="1" max="100" value="{{cfg.analysis_max_symbols}}"></label><label>Maximale Pause je Markt (s)<input name="analysis_max_delay_seconds" type="number" step=".05" min="0" max="10" value="{{cfg.analysis_max_delay_seconds}}"></label></div><div class="card"><h3>Lernen</h3><label>Strategie-Samples<input name="learning_max_evaluations" type="number" min="50" max="5000" value="{{cfg.learning_max_evaluations}}"></label><label>Nachrichten-Samples<input name="news_learning_max_samples" type="number" min="50" max="5000" value="{{cfg.news_learning_max_samples}}"></label><label>Lokale Nachrichten-Auswertung<input name="news_local_eval_max_items" type="number" min="100" max="10000" value="{{cfg.news_local_eval_max_items}}"></label></div><div class="card"><h3>Forecast</h3><label>Fällige Forecasts pro Durchlauf<input name="forecast_due_batch_limit" type="number" min="100" max="5000" value="{{cfg.forecast_due_batch_limit}}"></label></div></div><button>Parameter speichern</button></form>
    """, cfg=cfg)
