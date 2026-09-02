"""Kraken Trader v77: single runtime, transparent learning, Austrian income-tax workspace."""
import json
import os

os.environ.setdefault('APP_DISABLE_PAPER_SCHEDULER','1')
os.environ.setdefault('APP_DISABLE_RESEARCH_SCHEDULER','1')
os.environ.setdefault('APP_DISABLE_REAL_BALANCING_SCHEDULER','1')

import main as core
from flask import jsonify, redirect, request, url_for
from automation_controller import AutomationController
from controlled_learning import ControlledLearning
from news_learning import NewsLearning
from version import APP_VERSION

app=core.app;db=core.db
controlled_learning=ControlledLearning(db);news_learning=NewsLearning(db)
controller=AutomationController(db,core.pipeline,core.news_prefilter,controlled_learning,news_learning,core.run_paper_cycle,core.real_allocator)
controller.start_background()

def _json(value,default=None):
    try:return json.loads(value or '')
    except (TypeError,ValueError,json.JSONDecodeError):return default if default is not None else {}

def _strategy_rows():
    rows=[]
    for raw in controlled_learning.candidates():
        row=dict(raw);row['parameters']=_json(row.get('parameters_json'),{});row['gates']=_json(row.get('gate_results_json'),[]);row['gate_passed']=sum(1 for x in row['gates'] if x.get('passed'));row['gate_total']=len(row['gates']);rows.append(row)
    return rows

def _news_rows():
    rows=[]
    for raw in news_learning.candidates():
        row=dict(raw);row['comparison']=_json(row.get('comparison_json'),{});row['walk_forward']=_json(row.get('walk_forward_json'),{});rows.append(row)
    return rows

def _reason(row):
    status=str(row.get('status') or '')
    if status=='PENDING':return 'Alle Gates erfüllt; wartet auf explizite Freigabe.'
    if status=='REJECTED_GATE':
        failed=[str(x.get('gate')) for x in row.get('gates',[]) if not x.get('passed')]
        return 'Nicht erfüllt: '+', '.join(failed) if failed else 'Mindestens ein Gate wurde nicht erfüllt.'
    if status=='APPROVED':return 'Freigegeben und als neue aktive Version übernommen.'
    if status.startswith('REJECTED'):return str(row.get('reason') or 'Bei erneuter Prüfung abgelehnt.')
    if status=='UNCHANGED':return 'Unveränderte Evidenz; kein neuer Kandidat erforderlich.'
    return str(row.get('reason') or 'Keine weitere Begründung gespeichert.')

def _autos():
    cfg=controller.settings();latest=controller.latest(100);names={'analysis':'Analyse / Research','news':'Nachrichten','learning':'Lernen','paper':'Paper-Handel','real':'Realhandel'};out=[]
    for key,name in names.items():
        row=next((x for x in latest if x.get('subsystem')==key),None);out.append({'key':key,'name':name,'enabled':str(cfg.get(f'automation_{key}_enabled')).lower()=='true','status':row.get('status') if row else '—','time':row.get('created_at') if row else '—','interval':cfg.get(f'automation_{key}_interval_minutes',60)})
    return cfg,out

def _deprecated_to(target):
    def view(*_args,**_kwargs):return redirect(target)
    return view

@app.get('/')
def dashboard():
    cfg,autos=_autos();families=controlled_learning.family_overview();strategy=_strategy_rows();news=_news_rows();analysis=core.pipeline.latest();paper=db.rows('SELECT total_eur,quality FROM paper_snapshots ORDER BY id DESC LIMIT 1');pending=sum(x.get('status')=='PENDING' for x in strategy)+sum(x.get('status')=='PENDING' for x in news)
    return core.page('''<section class="hero"><div><span class="eyebrow">KTKI v77</span><h1>Kraken Trader</h1><p class="lead">Ein aktiver Prozess für Daten, Analyse, Lernen, Paper-Handel und österreichische Steuerprüfung.</p></div><strong class="hero-state">{{'AUTOMATIK AKTIV' if cfg.automation_master_enabled=='true' else 'AUTOMATIK AUS'}}</strong></section><div class="summary-grid"><div class="summary"><span>Analyse</span><b>{{analysis.stage if analysis else '—'}}</b><small>{{analysis.status if analysis else 'Keine Analyse'}}</small></div><div class="summary"><span>Paper</span><b>{{paper.total_eur|float if paper else '—'}} €</b><small>{{paper.quality if paper else 'Noch kein Snapshot'}}</small></div><div class="summary"><span>Lernkandidaten</span><b>{{pending}}</b><small>offen / freigabepflichtig</small></div><div class="summary"><span>Steuer</span><b>AT</b><small><a href="/tax-info">Einkommensteuer öffnen</a></small></div></div><div class="process-strip">{% for s in ['Daten','Analyse','Lernen','Portfolio','Handel'] %}<div class="process-node"><span>{{loop.index}}</span><b>{{s}}</b></div>{% if not loop.last %}<i>→</i>{% endif %}{% endfor %}</div><div class="automation-grid">{% for x in autos %}<div class="automation-card"><div><b>{{x.name}}</b><span class="status {{'on' if x.enabled else 'off'}}">{{'AN' if x.enabled else 'AUS'}}</span></div><strong>{{x.status}}</strong><small>{{x.time}}</small></div>{% endfor %}</div><div class="card"><h2>Lernstatus</h2><div class="grid">{% for x in families %}<div class="learning-card"><span class="eyebrow">{{x.family}}</span><h3>aktiv v{{x.active_version or '—'}}</h3><b>{{x.pending_count}} offen</b><small>{{x.latest_status}}</small></div>{% endfor %}</div></div>''',cfg=cfg,autos=autos,analysis=analysis,paper=(paper[0] if paper else None),pending=pending,families=families)

@app.get('/lernen')
def learning_page():
    families=controlled_learning.family_overview();strategy=_strategy_rows();news=_news_rows();family=request.args.get('family','forex');allowed={x['family'] for x in families};family=family if family in allowed else 'forex';selected=[x for x in strategy if x.get('family')==family];active=controlled_learning.active(family);active_params=_json(active.get('parameters_json'),{}) if active else {};metrics=controlled_learning.metrics(family=family)
    return core.page('''<div class="section-head"><div><span class="eyebrow">Lernen</span><h1>Lernzyklus & Kandidaten</h1><p class="lead">Training, Holdout, Kandidaten, Gates und automatische Entscheidungen werden nachvollziehbar protokolliert.</p></div><form method="post" action="{{url_for('learning_run')}}"><button>Lernlauf jetzt ausführen</button></form></div><div class="grid">{% for f in families %}<div class="learning-card"><span class="eyebrow">{{f.family}}</span><h3>Aktiv v{{f.active_version}}</h3><b>{{f.pending_count}} offen</b><small>Letzter Kandidat #{{f.latest_candidate_id or '—'}} · {{f.latest_status}}</small></div>{% endfor %}</div><div class="card"><h2>{{family}} – Kandidaten</h2><div class="section-actions">{% for f in families %}<a class="button secondary" href="{{url_for('learning_page',family=f.family)}}">{{f.family}}</a>{% endfor %}</div></div>{% for x in selected %}<div class="card"><div class="grid"><div><span class="pill">{{x.status}}</span><h3>Kandidat #{{x.id}}</h3><p>Basis v{{x.base_version}} · Holdout {{x.sample_count}}</p></div><div><b>Trefferquote</b><br>Aktiv {{'%.2f'|format(x.active_accuracy|float*100)}} %<br>Kandidat {{'%.2f'|format(x.candidate_accuracy|float*100)}} %<br>Δ {{'%.2f'|format(x.improvement|float*100)}} pp</div><div><b>Automatische Entscheidung</b><br>{{learning_reason(x)}}</div></div><details><summary>Gates {{x.gate_passed}} / {{x.gate_total}}</summary><table><tr><th>Gate</th><th>Horizont</th><th>Status</th><th>Ist</th><th>Soll</th></tr>{% for g in x.gates %}<tr><td>{{g.gate}}</td><td>{{g.horizon_hours or 'alle'}}</td><td class="{{'ok' if g.passed else 'error'}}">{{'BESTANDEN' if g.passed else 'NICHT BESTANDEN'}}</td><td>{{g.actual}}</td><td>{{g.required}}</td></tr>{% endfor %}</table></details><details><summary>Parametervergleich</summary><table><tr><th>Parameter</th><th>Aktiv</th><th>Kandidat</th><th>Δ</th></tr>{% for key,value in x.parameters.items() %}<tr><td>{{key}}</td><td>{{active_params.get(key,'—')}}</td><td>{{value}}</td><td>{{'%+.4f'|format(value|float-active_params.get(key,value)|float)}}</td></tr>{% endfor %}</table></details>{% if x.status=='PENDING' %}<form method="post" action="{{url_for('learning_decide')}}"><input type="hidden" name="candidate_id" value="{{x.id}}"><input type="hidden" name="family" value="{{x.family}}"><button name="action" value="approve">Explizit freigeben</button><button class="danger" name="action" value="reject">Ablehnen</button></form>{% endif %}</div>{% else %}<div class="card">Noch kein Kandidat für {{family}}.</div>{% endfor %}<h2>Alle Strategie-Kandidaten</h2><div class="table-card"><table><tr><th>Zeit</th><th>Familie</th><th>Status</th><th>Samples</th><th>Verbesserung</th><th>Grund</th></tr>{% for x in strategy %}<tr><td>{{x.created_at}}</td><td>{{x.family}}</td><td>{{x.status}}</td><td>{{x.sample_count}}</td><td>{{'%.4f'|format(x.improvement|float)}}</td><td>{{learning_reason(x)}}</td></tr>{% else %}<tr><td colspan="6">Keine Kandidaten vorhanden.</td></tr>{% endfor %}</table></div><h2>Nachrichten-Lernen</h2><div class="table-card"><table><tr><th>Zeit</th><th>Status</th><th>Samples</th><th>Verbesserung</th><th>Grund</th></tr>{% for x in news %}<tr><td>{{x.created_at}}</td><td>{{x.status}}</td><td>{{x.sample_count}}</td><td>{{x.improvement}}</td><td>{{x.reason}}</td></tr>{% else %}<tr><td colspan="5">Keine Nachrichten-Kandidaten vorhanden.</td></tr>{% endfor %}</table></div><h2>Horizontmetriken</h2><div class="table-card"><table><tr><th>Kandidat</th><th>Horizont</th><th>Samples</th><th>Coverage aktiv / Kandidat</th><th>Netto aktiv / Kandidat</th><th>Drawdown aktiv / Kandidat</th></tr>{% for x in metrics %}<tr><td>{{x.candidate_id}}</td><td>{{x.horizon_hours}} h</td><td>{{x.sample_count}}</td><td>{{x.active_coverage}} / {{x.candidate_coverage}}</td><td>{{x.active_net_return}} / {{x.candidate_net_return}}</td><td>{{x.active_max_drawdown}} / {{x.candidate_max_drawdown}}</td></tr>{% else %}<tr><td colspan="6">Keine Metriken vorhanden.</td></tr>{% endfor %}</table></div>''',families=families,strategy=strategy,news=news,family=family,selected=selected,active=active,active_params=active_params,metrics=metrics,learning_reason=_reason)

@app.post('/lernen/run')
def learning_run():
    try:
        result=controller.run_learning(automatic=False,auto_approve=False)
        db.audit('V77_LEARNING_MANUAL_RUN',json.dumps({'status':result.get('status'),'strategy':result.get('strategy'),'news':result.get('news')},sort_keys=True),'info')
    except Exception as exc:
        db.audit('V77_LEARNING_MANUAL_RUN_FAILED',type(exc).__name__+': '+str(exc)[:500],'error')
    return redirect(url_for('learning_page'))

@app.post('/lernen/decision')
def learning_decide():
    cid=int(request.form.get('candidate_id'));family=request.form.get('family','forex');action=request.form.get('action','reject');result=controlled_learning.decide(cid,action);db.audit('V77_LEARNING_DECISION',json.dumps({'candidate_id':cid,'family':family,'action':action,'result':result},sort_keys=True),'info');return redirect(url_for('learning_page',family=family))

@app.route('/automatik',methods=['GET','POST'])
def automation_page():
    if request.method=='POST':
        form=request.form
        for key in ['automation_master_enabled','automation_analysis_enabled','automation_news_enabled','automation_learning_enabled','automation_learning_auto_approve_enabled','automation_paper_enabled','automation_real_enabled','automation_real_execute_enabled']:db.set(key,'true' if form.get(key) else 'false')
        for key in ['automation_tick_minutes','automation_analysis_interval_minutes','automation_news_interval_minutes','automation_learning_interval_minutes','automation_paper_interval_minutes','automation_real_interval_minutes']:
            try:
                if key in form:db.set(key,max(1,min(1440,int(float(form[key])))))
            except (TypeError,ValueError):pass
        if form.get('run_now'):controller.run_once(force=True)
        db.audit('V77_AUTOMATION_SETTINGS_CHANGED',json.dumps(controller.settings(),sort_keys=True),'info');return redirect(url_for('automation_page'))
    cfg,autos=_autos();return core.page('''<span class="eyebrow">Automatik</span><h1>Automatik</h1><p class="lead">Genau ein Scheduler verwaltet Analyse, Nachrichten-Lernen, Lernen, Paper und Realhandel.</p><form method="post"><div class="card master-card"><h2>Gesamtautomatik</h2><label class="switch"><input type="checkbox" name="automation_master_enabled" {{'checked' if cfg.automation_master_enabled=='true'}}><span></span></label></div><div class="automation-settings">{% for x in autos %}<div class="automation-setting"><div><b>{{x.name}}</b><small>{{x.key}}</small></div><label class="switch"><input type="checkbox" name="automation_{{x.key}}_enabled" {{'checked' if x.enabled}}><span></span></label><label>Intervall<input type="number" min="1" max="1440" name="automation_{{x.key}}_interval_minutes" value="{{x.interval}}"></label></div>{% endfor %}</div><div class="card"><label class="checkline"><input type="checkbox" name="automation_learning_auto_approve_enabled" {{'checked' if cfg.automation_learning_auto_approve_enabled=='true'}}> Lernkandidaten nur bei erneut bestandenen Gates automatisch aktivieren</label></div><div class="section-actions"><button>Speichern</button><button class="secondary" name="run_now" value="1">Jetzt aktivierte Läufe ausführen</button></div></form><div class="card"><h2>Ausführungshistorie</h2><table><tr><th>Zeit</th><th>Subsystem</th><th>Status</th><th>Fehler</th></tr>{% for x in latest %}<tr><td>{{x.created_at}}</td><td>{{x.subsystem}}</td><td>{{x.status}}</td><td>{{x.error or '—'}}</td></tr>{% else %}<tr><td colspan="4">Noch keine Läufe.</td></tr>{% endfor %}</table></div>''',cfg=cfg,autos=autos,latest=controller.latest(100))

@app.get('/v77-health')
def health():
    cfg,autos=_autos();families=controlled_learning.family_overview();strategy=_strategy_rows();news=_news_rows();latest_learning=next((x for x in controller.latest(100) if x.get('subsystem')=='learning'),None)
    return jsonify({'version':APP_VERSION,'runtime':'v77_main','single_runtime':True,'single_scheduler':True,'legacy_runtime_wrappers_exposed':False,'tax_gui':True,'learning_transparency':True,'learning_families':families,'latest_learning_run':latest_learning,'recent_automation':autos,'active_learning_candidates':sum(x.get('status')=='PENDING' for x in strategy),'active_news_candidates':sum(x.get('status')=='PENDING' for x in news),'automation_master_enabled':str(cfg.get('automation_master_enabled')).lower()=='true'})

# Replace old view functions with redirects so no second learning/automation UI can execute.
for endpoint,target in {'controlled_learning_page':'/lernen','news_learning_page':'/lernen','automation_v67':'/automatik','dashboard_v67':'/','analysis_v67':'/scanner','analysis_run_v67':'/scanner','portfolio_v67':'/portfolio','trading_v67':'/paper','learning_v67':'/lernen'}.items():
    app.view_functions[endpoint]=_deprecated_to(target)

core.NAV_ITEMS=[('/', 'Übersicht'),('/scanner','Analyse'),('/portfolio','Portfolio'),('/lernen','Lernen'),('/automatik','Automatik'),('/tax-info','Einkommensteuer AT'),('/paper','Paper-Handel'),('/data-quality','Datenqualität'),('/backtests','Backtests'),('/audit','Audit')]
