import json, math, os, threading
from datetime import datetime, timezone

os.environ.setdefault('APP_DISABLE_PAPER_SCHEDULER','1')
os.environ.setdefault('APP_DISABLE_RESEARCH_SCHEDULER','1')
os.environ.setdefault('APP_DISABLE_REAL_BALANCING_SCHEDULER','1')

import main as legacy
from flask import request, redirect, url_for
from db import now
from automation_v67 import AutomationControllerV67, DEFAULTS
from controlled_learning import ControlledLearning
from news_learning import NewsLearning
from prefilter import MarketPrefilter
from scanner import MarketScanner
from forecast_tracker import ForecastTracker

app=legacy.app; db=legacy.db

for key,value in DEFAULTS.items():
    if not db.rows('SELECT value FROM settings WHERE key=?',(key,)):
        db.set_setting(key,getattr(legacy,'opts',{}).get(key,value))

# Keep the persistent learning basis bounded and make repeated searches over
# unchanged evidence a no-op. Indexes make the LIMIT queries cheap as history grows.
with db.con() as c:
    c.executescript('''
      CREATE INDEX IF NOT EXISTS idx_forecast_eval_time ON forecast_evaluations(evaluated_at DESC);
      CREATE INDEX IF NOT EXISTS idx_news_item_fetch ON news_items(fetched_at DESC);
      CREATE INDEX IF NOT EXISTS idx_news_ai_status ON external_news_ai_results(status,created_at DESC);
      CREATE INDEX IF NOT EXISTS idx_learning_candidates_fingerprint ON learning_candidates(family,base_version,validation_fingerprint);
    ''')

_original_cl_propose=ControlledLearning.propose
_original_nl_refresh=NewsLearning.refresh_local
_original_prefilter=MarketPrefilter.run
_original_scanner=MarketScanner.run
_original_forecast_due=ForecastTracker.evaluate_due


def _bounded_cl_evaluations(self,family):
    limit=max(50,min(5000,int(float(self.db.value('learning_max_evaluations','600')))))
    rows=self.db.rows('''SELECT f.id,f.direction,f.scanner_score,f.features_json,f.horizon_hours,
                               e.direction_correct,e.actual_return_pct
                        FROM forecast_evaluations e
                        JOIN research_forecasts f ON f.id=e.forecast_id
                        JOIN market_universe u ON u.symbol=f.symbol
                        WHERE u.category=?
                        ORDER BY e.evaluated_at DESC,f.id DESC LIMIT ?''',(family,limit))
    return list(reversed(rows))

ControlledLearning._evaluations=_bounded_cl_evaluations


def _bounded_cl_propose(self,family,min_sample=10,min_improvement=.02):
    rows=self._evaluations(family)
    if len(rows)<min_sample:return {'status':'INSUFFICIENT_DATA','sample_count':len(rows),'required':min_sample}
    active=self.active(family)
    if not active:return {'status':'NO_ACTIVE_VERSION'}
    policy=self.gate_policy(); minimum=max(3,int(self.db.value('learning_min_validation_samples','5')),len(policy['required_horizons'])*int(policy['minimum_horizon_samples']))
    validation_count=max(minimum,int(math.ceil(len(rows)*.30)))
    if validation_count>=len(rows):return _original_cl_propose(self,family,min_sample,min_improvement)
    fp=self._sample_fingerprint(rows[-validation_count:])
    old=self.db.rows('SELECT id,status,sample_count FROM learning_candidates WHERE family=? AND base_version=? AND validation_fingerprint=? ORDER BY id DESC LIMIT 1',(family,active['version'],fp))
    if old:return {'status':'UNCHANGED','candidate_id':old[0]['id'],'candidate_status':old[0]['status'],'sample_count':len(rows),'validation_count':validation_count}
    return _original_cl_propose(self,family,min_sample,min_improvement)

ControlledLearning.propose=_bounded_cl_propose


def _bounded_nl_samples(self):
    limit=max(50,min(5000,int(float(self.db.value('news_learning_max_samples','600')))))
    rows=self.db.rows('''SELECT n.id,n.title,n.summary,s.source_class,a.result_json,COALESCE(n.published_at,n.fetched_at,a.created_at) observed_at
                        FROM news_items n JOIN news_sources s ON s.name=n.source_name
                        JOIN external_news_ai_results a ON a.news_id=n.id
                        WHERE a.status='VALID' ORDER BY observed_at DESC,n.id DESC LIMIT ?''',(limit,))
    rows.reverse();out=[]
    for row in rows:
        try: teacher=json.loads(row.pop('result_json') or '{}')
        except Exception: continue
        row['teacher']=teacher;row['target']=self._teacher(teacher);out.append(row)
    return out

NewsLearning._samples=_bounded_nl_samples


def _bounded_nl_refresh(self):
    active=self.active()
    if not active:return {'status':'NO_ACTIVE_VERSION','evaluated':0}
    params=json.loads(active['parameters_json']);limit=max(100,min(10000,int(float(self.db.value('news_local_eval_max_items','1000')))))
    rows=self.db.rows('SELECT n.id,n.title,n.summary,s.source_class FROM news_items n JOIN news_sources s ON s.name=n.source_name ORDER BY n.fetched_at DESC,n.id DESC LIMIT ?',(limit,))
    with self.db.con() as c:
        for row in rows:
            score=self._local(row,params)
            c.execute('''INSERT INTO news_local_evaluations(news_id,evaluated_at,model_version,score,details_json)
                         VALUES(?,?,?,?,?) ON CONFLICT(news_id) DO UPDATE SET evaluated_at=excluded.evaluated_at,model_version=excluded.model_version,score=excluded.score,details_json=excluded.details_json''',
                      (row['id'],now(),active['version'],str(score),json.dumps({'parameters':params},sort_keys=True)))
    return {'status':'VALID','evaluated':len(rows),'version':active['version'],'limit':limit}

NewsLearning.refresh_local=_bounded_nl_refresh


def _compact_prefilter(self,top=8):
    top=max(1,min(int(top),int(float(self.db.value('analysis_top_per_category','5')))))
    return _original_prefilter(self,top)
MarketPrefilter.run=_compact_prefilter


def _compact_scanner(self,symbols,interval=60,limit=None,delay_seconds=None):
    cap=max(1,min(100,int(float(self.db.value('analysis_max_symbols','20')))))
    bounded=list(dict.fromkeys(symbols or []))[:cap]
    delay=max(0.0,float(self.db.value('analysis_max_delay_seconds','0.35')))
    return _original_scanner(self,bounded,interval,min(limit or len(bounded),len(bounded)),min(delay,max(0.0,float(delay_seconds if delay_seconds is not None else delay))))
MarketScanner.run=_compact_scanner

# Evaluate oldest due forecasts first in bounded batches; the rest remain OPEN for
# the next cycle, preventing an ever-growing open queue from blocking the UI.
def _bounded_forecast_due(self):
    limit=max(100,min(5000,int(float(self.db.value('forecast_due_batch_limit','1000')))))
    rows=self.db.rows("SELECT id FROM research_forecasts WHERE status='OPEN' ORDER BY created_at ASC,id ASC LIMIT ?",(limit,))
    if len(rows)<limit:return _original_forecast_due(self)
    original=self.db.rows
    def rows_proxy(q,p=()):
        if 'FROM research_forecasts WHERE status' in ' '.join(str(q).split()).lower():
            return original("SELECT * FROM research_forecasts WHERE status='OPEN' ORDER BY created_at ASC,id ASC LIMIT ?",(limit,))
        return original(q,p)
    self.db.rows=rows_proxy
    try:return _original_forecast_due(self)
    finally:self.db.rows=original
ForecastTracker.evaluate_due=_bounded_forecast_due

controller=AutomationControllerV67(db,legacy.pipeline,legacy.news_prefilter,ControlledLearning(db),NewsLearning(db),legacy.run_paper_cycle,legacy.real_allocator)
controller.start_background()

legacy.NAV_ITEMS=[('/', 'Übersicht'),('/analyse','1 Analyse'),('/portfolio-modern','2 Portfolio'),('/handel','3 Handel'),('/lernen-modern','4 Lernen'),('/automatik','5 Automatik'),('/parameter','Parameter')]


def _f(v):
    try:return float(v)
    except (TypeError,ValueError):return 0.0

def _chart(values):
    vals=[_f(x) for x in values]
    if not vals:return '<svg viewBox="0 0 800 220" class="chart"><text x="24" y="115">Noch keine Historie</text></svg>'
    lo,hi=min(vals),max(vals)
    if hi==lo:lo-=1;hi+=1
    pts=[]
    for i,v in enumerate(vals):
        x=28+744*i/max(1,len(vals)-1);y=24+170*(1-(v-lo)/(hi-lo));pts.append(f'{x:.1f},{y:.1f}')
    return f'<svg viewBox="0 0 800 220" class="chart" role="img" aria-label="Portfolioverlauf"><line x1="28" y1="194" x2="772" y2="194" class="chart-axis"/><polyline points="{" ".join(pts)}" class="chart-line" fill="none"/><circle cx="{pts[-1].split(",")[0]}" cy="{pts[-1].split(",")[1]}" r="4" class="chart-dot"/><text x="28" y="16" class="chart-label">Min {lo:.2f} €</text><text x="772" y="16" text-anchor="end" class="chart-label">Max {hi:.2f} €</text><text x="772" y="214" text-anchor="end" class="chart-value">Aktuell {vals[-1]:.2f} €</text></svg>'

def _autos():
    cfg=controller.settings();latest=controller.latest(100);names={'analysis':'Analyse / Research','news':'Nachrichten','learning':'Lernen & Freigabe','paper':'Paper-Handel','real':'Realhandel'};out=[]
    for k,n in names.items():
        x=next((r for r in latest if r['subsystem']==k),None);out.append({'key':k,'name':n,'enabled':str(cfg['automation_'+k+'_enabled']).lower()=='true','status':x['status'] if x else '—','time':x['created_at'] if x else '—'})
    return cfg,out

@app.get('/v67-dashboard')
def dashboard_v67():
    cfg,auto=_autos();job=legacy.pipeline.latest();portfolio=legacy.db.rows('SELECT total_eur,quality FROM portfolio_snapshots ORDER BY id DESC LIMIT 1');paper=legacy.db.rows('SELECT total_eur,quality FROM paper_snapshots ORDER BY id DESC LIMIT 1')
    return legacy.page('''<section class="hero"><div><span class="eyebrow">KTKI v67</span><h1>Kraken Trader</h1><p class="lead">Chronologischer Prozess von Daten über Analyse und Lernen bis zum Handel.</p></div><strong class="hero-state">{{'AUTOMATIK AKTIV' if cfg.automation_master_enabled=='true' else 'AUTOMATIK AUS'}}</strong></section><div class="summary-grid"><div class="summary"><span>Realportfolio</span><b>{{portfolio.total_eur|float if portfolio else '—'}} €</b><small>{{portfolio.quality if portfolio else '—'}}</small></div><div class="summary"><span>Paper</span><b>{{paper.total_eur|float if paper else '—'}} €</b><small>{{paper.quality if paper else '—'}}</small></div><div class="summary"><span>Analyse</span><b>{{job.stage if job else '—'}}</b><small>{{job.progress_current if job else 0}} / {{job.progress_total if job else 0}}</small></div><div class="summary"><span>Live</span><b>{{'AKTIV' if cfg.automation_real_enabled=='true' and cfg.automation_real_execute_enabled=='true' else 'BLOCKIERT'}}</b><small>Kill-Switch / Limits separat</small></div></div><div class="process-strip">{% for s in ['Daten','Analyse','Lernen','Portfolio','Handel'] %}<div class="process-node"><span>{{loop.index}}</span><b>{{s}}</b></div>{% if not loop.last %}<i>→</i>{% endif %}{% endfor %}</div><div class="automation-grid">{% for x in auto %}<div class="automation-card"><div><b>{{x.name}}</b><span class="status {{'on' if x.enabled else 'off'}}">{{'AN' if x.enabled else 'AUS'}}</span></div><strong>{{x.status}}</strong><small>{{x.time}}</small></div>{% endfor %}</div>''',cfg=cfg,auto=auto,job=job,portfolio=(portfolio[0] if portfolio else None),paper=(paper[0] if paper else None))

app.view_functions['index']=dashboard_v67

@app.get('/analyse')
def analysis_v67():
    job=legacy.pipeline.latest();rows=legacy.db.rows('SELECT w.symbol,w.category,w.prefilter_score,s.score,s.signal,s.quality FROM research_watchlist w LEFT JOIN scanner_results s ON s.symbol=w.symbol ORDER BY CAST(w.prefilter_score AS REAL) DESC LIMIT 30')
    return legacy.page('''<div class="section-head"><div><span class="eyebrow">1 Analyse</span><h1>Analyse</h1><p class="lead">Nur aktuelle Kandidaten werden tief analysiert. Umfang ist begrenzt; historische Lernbasis wird separat gekappt.</p></div><form method="post" action="{{url_for('analysis_run_v67')}}"><button>Jetzt analysieren</button></form></div><div class="timeline">{% for x in stages %}<div class="timeline-item {{'current' if job and job.stage==x[0] else ''}}"><span>{{loop.index}}</span><div><b>{{x[0]}}</b><small>{{x[1]}}</small></div></div>{% endfor %}</div><div class="card"><b>{{job.status if job else '—'}}</b> · {{job.stage if job else '—'}} · {{job.progress_current if job else 0}}/{{job.progress_total if job else 0}}</div><div class="table-card"><table><tr><th>Produkt</th><th>Kategorie</th><th>Prefilter</th><th>Score</th><th>Signal</th><th>Qualität</th></tr>{% for x in rows %}<tr><td>{{x.symbol}}</td><td>{{x.category}}</td><td>{{x.prefilter_score}}</td><td>{{x.score or '—'}}</td><td>{{x.signal or '—'}}</td><td>{{x.quality or '—'}}</td></tr>{% else %}<tr><td colspan="6" class="muted">Noch keine Kandidaten.</td></tr>{% endfor %}</table></div>''',job=job,rows=rows,stages=[('UNIVERSE','Märkte synchronisieren'),('NEWS_AND_PREFILTER','Nachrichten, Ticker, Vorfilter'),('DEEP_SCAN','Detailscan'),('FORECAST_SNAPSHOT','Forecasts'),('LEARNING_CANDIDATES','Lernkandidaten'),('DONE','Fertig')])

@app.post('/analyse/run')
def analysis_run_v67():
    legacy.pipeline.start();return redirect(url_for('analysis_v67'))

@app.get('/portfolio-modern')
def portfolio_v67():
    real=legacy.db.rows('SELECT created_at,total_eur FROM portfolio_snapshots ORDER BY id ASC LIMIT 180');paper=legacy.db.rows('SELECT created_at,total_eur FROM paper_snapshots ORDER BY id ASC LIMIT 180');hold=legacy.db.rows('SELECT display_name,amount,eur_value,classification FROM portfolio_assets ORDER BY CAST(COALESCE(eur_value,0) AS REAL) DESC LIMIT 25');positions=legacy.paper_engine.positions()
    return legacy.page('''<span class="eyebrow">2 Portfolio</span><h1>Portfolio</h1><p class="lead">Wertentwicklung und Zusammensetzung, jeweils mit Zeitverlauf.</p><div class="chart-grid"><div class="chart-card"><b>Realportfolio</b>{{real_chart|safe}}</div><div class="chart-card"><b>Paper-Portfolio</b>{{paper_chart|safe}}</div></div><div class="split"><div class="card"><h2>Realpositionen</h2>{% for x in hold %}<div class="allocation"><div><b>{{x.display_name}}</b><small>{{x.classification}} · {{x.amount}}</small></div><strong>{{x.eur_value|float}} €</strong></div>{% else %}<span class="muted">Keine Positionen.</span>{% endfor %}</div><div class="card"><h2>Paperpositionen</h2>{% for x in positions %}<div class="allocation"><div><b>{{x.symbol}}</b><small>{{x.quantity}}</small></div><strong>{{x.avg_cost_eur}}</strong></div>{% else %}<span class="muted">Keine Positionen.</span>{% endfor %}</div></div>''',real_chart=_chart([x['total_eur'] for x in real]),paper_chart=_chart([x['total_eur'] for x in paper]),hold=hold,positions=positions)

@app.get('/handel')
def trading_v67():
    cash,pv,total,missing=legacy.paper_engine.equity();dec=legacy.db.rows('SELECT created_at,symbol,action,score,executed,reason FROM paper_decisions ORDER BY id DESC LIMIT 25');cfg,_=_autos()
    return legacy.page('''<span class="eyebrow">3 Handel</span><h1>Handel</h1><p class="lead">Ausführung folgt der Portfolioentscheidung und bleibt durch bestehende Gates geschützt.</p><div class="summary-grid"><div class="summary"><span>Paperwert</span><b>{{total|float}} €</b><small>Cash {{cash|float}} €</small></div><div class="summary"><span>Paperpositionen</span><b>{{pv|float}} €</b></div><div class="summary"><span>Paper-Automatik</span><b>{{'AN' if cfg.automation_paper_enabled=='true' else 'AUS'}}</b></div><div class="summary"><span>Real-Automatik</span><b>{{'AN' if cfg.automation_real_enabled=='true' else 'AUS'}}</b><small>{{'Ausführung möglich' if cfg.automation_real_execute_enabled=='true' else 'Dry-Run / blockiert'}}</small></div></div><div class="table-card"><table><tr><th>Zeit</th><th>Produkt</th><th>Aktion</th><th>Score</th><th>Ausgeführt</th><th>Grund</th></tr>{% for x in dec %}<tr><td>{{x.created_at}}</td><td>{{x.symbol}}</td><td>{{x.action}}</td><td>{{x.score}}</td><td>{{'JA' if x.executed else 'NEIN'}}</td><td>{{x.reason}}</td></tr>{% else %}<tr><td colspan="6" class="muted">Noch keine Entscheidungen.</td></tr>{% endfor %}</table></div>''',cash=cash,pv=pv,total=total,missing=missing,dec=dec,cfg=cfg)

@app.get('/lernen-modern')
def learning_v67():
    cl=ControlledLearning(db);nl=NewsLearning(db);families=cl.family_overview();pending=[x for x in cl.candidates() if x.get('status')=='PENDING'];news_pending=len([x for x in nl.candidates() if x.get('status')=='PENDING'])
    return legacy.page('''<span class="eyebrow">4 Lernen</span><h1>Lernen</h1><p class="lead">Parametersuche und Nachrichtenlernen laufen automatisch über begrenzte, aktuelle Stichproben. Die Freigabe ist separat schaltbar.</p><div class="learning-grid">{% for x in families %}<div class="learning-card"><span class="eyebrow">{{x.family}}</span><h3>Aktiv v{{x.active_version or '—'}}</h3><b>{{x.pending_count}} offene Kandidaten</b><small>{{x.latest_status}}</small></div>{% endfor %}<div class="learning-card"><span class="eyebrow">news</span><h3>Nachrichten</h3><b>{{news_pending}} offene Kandidaten</b><small>Aktiv v{{news_active.version if news_active else '—'}}</small></div></div><div class="card"><div class="process-strip compact"><div class="process-node"><span>1</span><b>Samples</b></div><i>→</i><div class="process-node"><span>2</span><b>Suche</b></div><i>→</i><div class="process-node"><span>3</span><b>Holdout</b></div><i>→</i><div class="process-node"><span>4</span><b>Freigabe</b></div></div></div>''',families=families,news_pending=news_pending,news_active=nl.active(),pending=pending)

@app.route('/automatik',methods=['GET','POST'])
def automation_v67():
    if request.method=='POST':
        form=request.form
        for key in ['automation_master_enabled','automation_analysis_enabled','automation_news_enabled','automation_learning_enabled','automation_learning_auto_approve_enabled','automation_paper_enabled','automation_real_enabled','automation_real_execute_enabled']:
            db.set(key,'true' if form.get(key) else 'false')
        for key in ['automation_tick_minutes','automation_analysis_interval_minutes','automation_news_interval_minutes','automation_learning_interval_minutes','automation_paper_interval_minutes','automation_real_interval_minutes']:
            if key in form:
                try:db.set(key,max(1,min(1440,int(float(form[key])))))
                except (TypeError,ValueError):pass
        if form.get('run_now'):controller.run_once(force=True)
        db.audit('V67_AUTOMATION_SETTINGS_CHANGED');return redirect(url_for('automation_v67'))
    cfg,rows=_autos();return legacy.page('''<span class="eyebrow">5 Automatik</span><h1>Automatik</h1><p class="lead">Jeder Automatismus ist unabhängig schaltbar. Ein gemeinsamer Scheduler ersetzt die drei alten Scheduler.</p><form method="post"><div class="card master-card"><div><h2>Gesamtautomatik</h2><small>Nur dieser Schalter gibt die einzelnen Automatismen frei.</small></div><label class="switch"><input type="checkbox" name="automation_master_enabled" {{'checked' if cfg.automation_master_enabled=='true'}}><span></span></label></div><div class="automation-settings">{% for x in rows %}<div class="automation-setting"><div><b>{{x.name}}</b><small>{{x.key}}</small></div><label class="switch"><input type="checkbox" name="automation_{{x.key}}_enabled" {{'checked' if x.enabled}}><span></span></label><label>Intervall<input type="number" min="1" max="1440" name="automation_{{x.key}}_interval_minutes" value="{{x.interval}}"></label></div>{% endfor %}</div><div class="card"><h2>Automatische Lernfreigabe</h2><label class="checkline"><input type="checkbox" name="automation_learning_auto_approve_enabled" {{'checked' if cfg.automation_learning_auto_approve_enabled=='true'}}> Nur bei erneut bestandenen Gates automatisch aktivieren</label></div><div class="section-actions"><button>Speichern</button><button class="secondary" name="run_now" value="1">Jetzt aktivierte Läufe anstoßen</button></div></form><div class="card"><h2>Historie</h2><div class="table-card"><table><tr><th>Zeit</th><th>Subsystem</th><th>Status</th><th>Fehler</th></tr>{% for x in latest %}<tr><td>{{x.created_at}}</td><td>{{x.subsystem}}</td><td>{{x.status}}</td><td>{{x.error or '—'}}</td></tr>{% endfor %}</table></div></div>''',cfg=cfg,rows=[dict(x,interval=cfg['automation_'+x['key']+'_interval_minutes']) for x in rows],latest=controller.latest(40))

@app.route('/parameter',methods=['GET','POST'])
def parameter_v67():
    fields={'analysis_top_per_category':(1,25),'analysis_max_symbols':(1,100),'analysis_max_delay_seconds':(0,10),'learning_max_evaluations':(50,5000),'news_learning_max_samples':(50,5000),'news_local_eval_max_items':(100,10000),'forecast_due_batch_limit':(100,5000)}
    if request.method=='POST':
        for k,(lo,hi) in fields.items():
            if k not in request.form:continue
            try:v=max(lo,min(hi,float(request.form[k])));db.set(k,int(v) if v.is_integer() else v)
            except (TypeError,ValueError):pass
        db.audit('V67_GENERAL_PARAMETERS_CHANGED');return redirect(url_for('parameter_v67'))
    return legacy.page('''<span class="eyebrow">Parameter</span><h1>Allgemeine Betriebsparameter</h1><p class="lead">Nur Analyseumfang und Lernfenster. Die Fach- und Sicherheitsregeln bleiben unverändert.</p><form method="post"><div class="settings-grid"><div class="card"><h3>Analyse</h3><label>Kandidaten je Kategorie<input name="analysis_top_per_category" value="{{cfg.analysis_top_per_category}}" type="number"></label><label>Maximale Märkte<input name="analysis_max_symbols" value="{{cfg.analysis_max_symbols}}" type="number"></label><label>Maximale Pause je Markt (s)<input name="analysis_max_delay_seconds" value="{{cfg.analysis_max_delay_seconds}}" type="number" step=".05"></label></div><div class="card"><h3>Lernen</h3><label>Strategie-Samples<input name="learning_max_evaluations" value="{{cfg.learning_max_evaluations}}" type="number"></label><label>Nachrichten-Samples<input name="news_learning_max_samples" value="{{cfg.news_learning_max_samples}}" type="number"></label><label>Lokale Nachrichten-Auswertung<input name="news_local_eval_max_items" value="{{cfg.news_local_eval_max_items}}" type="number"></label></div><div class="card"><h3>Forecast</h3><label>Fällige Forecasts pro Lauf<input name="forecast_due_batch_limit" value="{{cfg.forecast_due_batch_limit}}" type="number"></label></div></div><button>Speichern</button></form>''',cfg=controller.settings())
