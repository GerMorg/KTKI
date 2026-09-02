"""Kraken Trader v77: one active runtime, transparent learning, Austrian tax UI."""
import json
import math
import os

# The core application owns the market, paper, portfolio, tax and data services.
# Its former background schedulers are disabled; v77 owns the only scheduler.
os.environ.setdefault('APP_DISABLE_PAPER_SCHEDULER', '1')
os.environ.setdefault('APP_DISABLE_RESEARCH_SCHEDULER', '1')
os.environ.setdefault('APP_DISABLE_REAL_BALANCING_SCHEDULER', '1')

import main as core
from flask import request, redirect, url_for, jsonify
from automation_controller import AutomationController
from controlled_learning import ControlledLearning
from news_learning import NewsLearning
from version import APP_VERSION

app = core.app
db = core.db

controlled_learning = ControlledLearning(db)
news_learning = NewsLearning(db)
controller = AutomationController(
    db,
    core.pipeline,
    core.news_prefilter,
    controlled_learning,
    news_learning,
    core.run_paper_cycle,
    core.real_allocator,
)
controller.start_background()


def _remove_view(endpoint):
    """Disable deprecated duplicate UI routes without exposing parallel workflows."""
    app.view_functions.pop(endpoint, None)


for endpoint in (
    'controlled_learning_page',
    'news_learning_page',
    'automation_v67',
    'dashboard_v67',
    'analysis_v67',
    'analysis_run_v67',
    'portfolio_v67',
    'trading_v67',
):
    _remove_view(endpoint)


def _num(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _json(value, default=None):
    try:
        parsed = json.loads(value or '')
        return parsed
    except (TypeError, ValueError, json.JSONDecodeError):
        return default if default is not None else {}


def _candidate_view(row):
    item = dict(row)
    item['parameters'] = _json(item.get('parameters_json'), {})
    item['gates'] = _json(item.get('gate_results_json'), [])
    item['gate_passed'] = sum(1 for gate in item['gates'] if gate.get('passed'))
    item['gate_total'] = len(item['gates'])
    return item


def _news_candidate_view(row):
    item = dict(row)
    item['comparison'] = _json(item.get('comparison_json'), {})
    item['walk_forward'] = _json(item.get('walk_forward_json'), {})
    return item


def _learning_snapshot():
    families = controlled_learning.family_overview()
    strategy = [_candidate_view(x) for x in controlled_learning.candidates()]
    news = [_news_candidate_view(x) for x in news_learning.candidates()]
    latest_runs = controller.latest(100)
    latest_learning = next((x for x in latest_runs if x.get('subsystem') == 'learning'), None)
    return families, strategy, news, latest_learning


def _learning_reason(candidate):
    status = str(candidate.get('status') or '')
    if status == 'PENDING':
        return 'Alle Gates erfüllt; Kandidat wartet auf explizite Freigabe.'
    if status == 'REJECTED_GATE':
        failed = [g.get('gate') for g in candidate.get('gates', []) if not g.get('passed')]
        return 'Nicht erfüllt: ' + ', '.join(str(x) for x in failed) if failed else 'Mindestens ein Gate wurde nicht erfüllt.'
    if status == 'APPROVED':
        return 'Explizit freigegeben und als neue aktive Version übernommen.'
    if status.startswith('REJECTED'):
        return str(candidate.get('reason') or 'Bei erneuter Prüfung abgelehnt.')
    if status == 'UNCHANGED':
        return 'Unveränderte Evidenz: kein neuer Kandidat notwendig.'
    return str(candidate.get('reason') or 'Keine zusätzliche Begründung gespeichert.')


def _learning_run_summary(result):
    if not isinstance(result, dict):
        return result
    out = {'status': result.get('status')}
    for key in ('training_count', 'validation_count', 'sample_count', 'candidate_id', 'improvement', 'reason', 'missing'):
        if key in result:
            out[key] = result[key]
    if 'gate_results' in result:
        out['gates'] = result['gate_results']
    return out


@app.get('/')
def dashboard():
    families, strategy, news, latest_learning = _learning_snapshot()
    latest_analysis = core.pipeline.latest()
    portfolio = db.rows('SELECT total_eur,quality,created_at FROM portfolio_snapshots ORDER BY id DESC LIMIT 1')
    paper = db.rows('SELECT total_eur,quality,created_at FROM paper_snapshots ORDER BY id DESC LIMIT 1')
    pending = sum(1 for x in strategy if x.get('status') == 'PENDING') + sum(1 for x in news if x.get('status') == 'PENDING')
    return core.page('''
      <section class="hero"><div><span class="eyebrow">KTKI v77</span><h1>Kraken Trader</h1>
      <p class="lead">Ein aktiver Prozess von Marktdaten über Analyse und Lernen bis Paper-Handel und Steuerprüfung.</p></div>
      <strong class="hero-state">{{ 'AUTOMATIK AKTIV' if cfg.automation_master_enabled=='true' else 'AUTOMATIK AUS' }}</strong></section>
      <div class="summary-grid">
        <div class="summary"><span>Analyse</span><b>{{analysis.stage if analysis else '—'}}</b><small>{{analysis.status if analysis else 'Keine Analyse'}}</small></div>
        <div class="summary"><span>Paper</span><b>{{paper.total_eur|float if paper else '—'}} €</b><small>{{paper.quality if paper else 'Noch kein Snapshot'}}</small></div>
        <div class="summary"><span>Lernkandidaten</span><b>{{pending}}</b><small>wartet auf Entscheidung</small></div>
        <div class="summary"><span>Steuerjahr</span><b>AT</b><small><a href="{{url_for('tax_info')}}">Einkommensteuer öffnen</a></small></div>
      </div>
      <div class="process-strip">{% for s in ['Daten','Analyse','Lernen','Portfolio','Handel'] %}<div class="process-node"><span>{{loop.index}}</span><b>{{s}}</b></div>{% if not loop.last %}<i>→</i>{% endif %}{% endfor %}</div>
      <div class="automation-grid">{% for x in autos %}<div class="automation-card"><div><b>{{x.name}}</b><span class="status {{'on' if x.enabled else 'off'}}">{{'AN' if x.enabled else 'AUS'}}</span></div><strong>{{x.status}}</strong><small>{{x.time}}</small></div>{% endfor %}</div>
      <div class="card"><h2>Lernstatus</h2><p>{{'Letzter Lernlauf: '+latest_learning.created_at if latest_learning else 'Noch kein Lernlauf protokolliert.'}}</p><div class="grid">{% for x in families %}<div class="learning-card"><span class="eyebrow">{{x.family}}</span><h3>aktiv v{{x.active_version or '—'}}</h3><b>{{x.pending_count}} offen</b><small>{{x.latest_status}}</small></div>{% endfor %}</div></div>
    ''', cfg=controller.settings(), autos=_autos()[1], analysis=latest_analysis,
       paper=(paper[0] if paper else None), pending=pending, families=families,
       latest_learning=latest_learning)


@app.get('/lernen')
def learning_page():
    families, strategy, news, latest_learning = _learning_snapshot()
    selected_family = request.args.get('family', 'forex')
    selected_family = selected_family if selected_family in [x['family'] for x in families] else 'forex'
    selected = [x for x in strategy if x.get('family') == selected_family]
    metrics = controlled_learning.metrics(family=selected_family)
    active = controlled_learning.active(selected_family)
    active_params = _json(active.get('parameters_json'), {}) if active else {}
    news_active = news_learning.active()
    return core.page('''
      <div class="section-head"><div><span class="eyebrow">Lernen</span><h1>Lernzyklus & Kandidaten</h1><p class="lead">Jeder Lauf zeigt Datenbasis, Holdout, Parameteränderung, Gate-Ergebnisse und die automatische Entscheidung.</p></div><form method="post" action="{{url_for('learning_run')}}"><button>Lernlauf jetzt ausführen</button></form></div>
      {% if result %}<div class="card"><h3>{{result.status}}</h3><pre>{{result | tojson(indent=2)}}</pre></div>{% endif %}
      <div class="grid">{% for f in families %}<div class="learning-card"><span class="eyebrow">{{f.family}}</span><h3>Aktiv v{{f.active_version}}</h3><b>{{f.pending_count}} offene</b><small>Letzter Kandidat: #{{f.latest_candidate_id or '—'}} · {{f.latest_status}}</small></div>{% endfor %}<div class="learning-card"><span class="eyebrow">news</span><h3>Aktiv v{{news_active.version if news_active else '—'}}</h3><b>{{news|selectattr('status','equalto','PENDING')|list|length}} offen</b><small>Nachrichten-Lernen</small></div></div>
      <div class="card"><h2>Strategie-Kandidaten: {{selected_family}}</h2><p>Aktive Parameter bleiben unverändert, bis ein Kandidat explizit freigegeben wird.</p><div class="section-actions">{% for f in families %}<a class="button secondary" href="{{url_for('learning_page',family=f.family)}}">{{f.family}}</a>{% endfor %}</div></div>
      {% for x in selected %}<div class="card"><div class="grid"><div><span class="pill">{{x.status}}</span><h3>Kandidat #{{x.id}}</h3><p>Basis v{{x.base_version}} · Holdout {{x.sample_count}} · {{x.training_count if x.training_count is defined else '—'}} Training</p></div><div><b>Trefferquote</b><br>Aktiv {{'%.2f'|format(x.active_accuracy|float*100)}} %<br>Kandidat {{'%.2f'|format(x.candidate_accuracy|float*100)}} %<br>Verbesserung {{'%.2f'|format(x.improvement|float*100)}} pp</div><div><b>Entscheidung</b><br>{{learning_reason(x)}}</div></div><details><summary>Gate-Prüfung ({{x.gate_passed}} / {{x.gate_total}})</summary><table><tr><th>Gate</th><th>Horizont</th><th>Status</th><th>Ist</th><th>Soll</th></tr>{% for g in x.gates %}<tr><td>{{g.gate}}</td><td>{{g.horizon_hours or 'alle'}}</td><td class="{{'ok' if g.passed else 'error'}}">{{'BESTANDEN' if g.passed else 'NICHT BESTANDEN'}}</td><td>{{g.actual}}</td><td>{{g.required}}</td></tr>{% endfor %}</table></details><details><summary>Parametervergleich</summary><table><tr><th>Parameter</th><th>Aktiv</th><th>Kandidat</th><th>Δ</th></tr>{% for key,value in x.parameters.items() %}<tr><td>{{key}}</td><td>{{active_params.get(key,'—')}}</td><td>{{value}}</td><td>{{'%+.4f'|format(value|float-active_params.get(key,value)|float)}}</td></tr>{% endfor %}</table></details>{% if x.status=='PENDING' %}<form method="post" action="{{url_for('learning_decide')}}"><input type="hidden" name="candidate_id" value="{{x.id}}"><input type="hidden" name="family" value="{{x.family}}"><button name="action" value="approve">Explizit freigeben</button><button class="danger" name="action" value="reject">Ablehnen</button></form>{% endif %}</div>{% else %}<div class="card">Noch keine Kandidaten für {{selected_family}}.</div>{% endfor %}
      <h2>Historische Kandidaten / automatische Entscheidungen</h2><div class="table-card"><table><tr><th>Zeit</th><th>Familie</th><th>Status</th><th>Stichprobe</th><th>Verbesserung</th><th>Begründung</th></tr>{% for x in strategy %}<tr><td>{{x.created_at}}</td><td>{{x.family}}</td><td>{{x.status}}</td><td>{{x.sample_count}}</td><td>{{'%.4f'|format(x.improvement|float)}}</td><td>{{learning_reason(x)}}</td></tr>{% else %}<tr><td colspan="6">Keine Kandidaten vorhanden.</td></tr>{% endfor %}</table></div>
      <h2>Horizontmetriken</h2><div class="table-card"><table><tr><th>Kandidat</th><th>Horizont</th><th>Samples</th><th>Coverage aktiv / Kandidat</th><th>Netto aktiv / Kandidat</th><th>Drawdown aktiv / Kandidat</th></tr>{% for x in metrics %}<tr><td>{{x.candidate_id}}</td><td>{{x.horizon_hours}} h</td><td>{{x.sample_count}}</td><td>{{x.active_coverage}} / {{x.candidate_coverage}}</td><td>{{x.active_net_return}} / {{x.candidate_net_return}}</td><td>{{x.active_max_drawdown}} / {{x.candidate_max_drawdown}}</td></tr>{% else %}<tr><td colspan="6">Keine Metriken vorhanden.</td></tr>{% endfor %}</table></div>
    ''', families=families, strategy=strategy, news=news, selected=selected, selected_family=selected_family,
       metrics=metrics, active=active, active_params=active_params, news_active=news_active,
       latest_learning=latest_learning, result=None, learning_reason=_learning_reason)


@app.post('/lernen/run')
def learning_run():
    try:
        result = controller.run_learning(automatic=False, auto_approve=False)
        db.audit('V77_LEARNING_MANUAL_RUN', json.dumps(_learning_run_summary(result), sort_keys=True), 'info')
    except Exception as exc:
        result = {'status':'ERROR','error':type(exc).__name__+': '+str(exc)[:500]}
        db.audit('V77_LEARNING_MANUAL_RUN_FAILED', json.dumps(result, sort_keys=True), 'error')
    return redirect(url_for('learning_page'))


@app.post('/lernen/decision')
def learning_decide():
    candidate_id = int(request.form.get('candidate_id'))
    family = request.form.get('family', 'forex')
    action = request.form.get('action', 'reject')
    result = controlled_learning.decide(candidate_id, action)
    db.audit('V77_LEARNING_DECISION', json.dumps({'candidate_id':candidate_id,'family':family,'action':action,'result':result}, sort_keys=True), 'info')
    return redirect(url_for('learning_page', family=family))


@app.route('/automatik', methods=['GET','POST'])
def automation_page():
    if request.method == 'POST':
        form = request.form
        boolean_keys = ['automation_master_enabled','automation_analysis_enabled','automation_news_enabled','automation_learning_enabled','automation_learning_auto_approve_enabled','automation_paper_enabled','automation_real_enabled','automation_real_execute_enabled']
        for key in boolean_keys:
            db.set(key, 'true' if form.get(key) else 'false')
        interval_keys = ['automation_tick_minutes','automation_analysis_interval_minutes','automation_news_interval_minutes','automation_learning_interval_minutes','automation_paper_interval_minutes','automation_real_interval_minutes']
        for key in interval_keys:
            if key in form:
                try: db.set(key, max(1, min(1440, int(float(form[key])))))
                except (TypeError, ValueError): pass
        if form.get('run_now'):
            controller.run_once(force=True)
        db.audit('V77_AUTOMATION_SETTINGS_CHANGED', json.dumps(controller.settings(), sort_keys=True), 'info')
        return redirect(url_for('automation_page'))
    cfg, rows = _autos()
    return core.page('''<span class="eyebrow">Automatik</span><h1>Automatik</h1><p class="lead">Ein gemeinsamer Scheduler. Die einzelnen Prozesse können unabhängig freigegeben werden.</p><form method="post"><div class="card master-card"><div><h2>Gesamtautomatik</h2><small>Der Master-Schalter muss für automatische Läufe aktiv sein.</small></div><label class="switch"><input type="checkbox" name="automation_master_enabled" {{'checked' if cfg.automation_master_enabled=='true'}}><span></span></label></div><div class="automation-settings">{% for x in rows %}<div class="automation-setting"><div><b>{{x.name}}</b><small>{{x.key}}</small></div><label class="switch"><input type="checkbox" name="automation_{{x.key}}_enabled" {{'checked' if x.enabled}}><span></span></label><label>Intervall<input type="number" min="1" max="1440" name="automation_{{x.key}}_interval_minutes" value="{{x.interval}}"></label></div>{% endfor %}</div><div class="card"><h2>Automatische Lernfreigabe</h2><label class="checkline"><input type="checkbox" name="automation_learning_auto_approve_enabled" {{'checked' if cfg.automation_learning_auto_approve_enabled=='true'}}> Nur bei erneut bestandenen Gates automatisch aktivieren</label></div><div class="section-actions"><button>Speichern</button><button class="secondary" name="run_now" value="1">Jetzt aktivierte Läufe ausführen</button></div></form><div class="card"><h2>Letzte Ausführungen</h2><div class="table-card"><table><tr><th>Zeit</th><th>Subsystem</th><th>Status</th><th>Fehler</th></tr>{% for x in latest %}<tr><td>{{x.created_at}}</td><td>{{x.subsystem}}</td><td>{{x.status}}</td><td>{{x.error or '—'}}</td></tr>{% else %}<tr><td colspan="4">Noch keine Läufe.</td></tr>{% endfor %}</table></div></div>''', cfg=cfg, rows=rows, latest=controller.latest(100))


def _autos():
    cfg = controller.settings()
    latest = controller.latest(100)
    names = {'analysis':'Analyse / Research','news':'Nachrichten','learning':'Lernen & Freigabe','paper':'Paper-Handel','real':'Realhandel'}
    out=[]
    for key,name in names.items():
        row=next((x for x in latest if x['subsystem']==key),None)
        out.append({'key':key,'name':name,'enabled':str(cfg[f'automation_{key}_enabled']).lower()=='true','status':row['status'] if row else '—','time':row['created_at'] if row else '—','interval':cfg.get(f'automation_{key}_interval_minutes',60)})
    return cfg,out


@app.get('/v77-health')
def health():
    cfg, autos = _autos()
    families, strategy, news, latest_learning = _learning_snapshot()
    return jsonify({
        'version': APP_VERSION,
        'runtime': 'v77_main',
        'single_runtime': True,
        'single_scheduler': True,
        'legacy_runtime_wrappers_exposed': False,
        'tax_gui': True,
        'learning_transparency': True,
        'learning_families': families,
        'latest_learning_run': latest_learning,
        'recent_automation': autos,
        'active_learning_candidates': sum(1 for x in strategy if x.get('status') == 'PENDING'),
        'active_news_candidates': sum(1 for x in news if x.get('status') == 'PENDING'),
        'automation_master_enabled': str(cfg.get('automation_master_enabled')).lower() == 'true',
    })


# Public navigation: the tax page is the Austrian income-tax workspace.
core.NAV_ITEMS = [
    ('/', 'Übersicht'),
    ('/portfolio', 'Portfolio'),
    ('/scanner', 'Analyse'),
    ('/lernen', 'Lernen'),
    ('/automatik', 'Automatik'),
    ('/tax-info', 'Einkommensteuer AT'),
    ('/paper', 'Paper-Handel'),
    ('/data-quality', 'Datenqualität'),
    ('/backtests', 'Backtests'),
    ('/audit', 'Audit'),
]
