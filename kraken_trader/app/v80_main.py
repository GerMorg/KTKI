"""v80 runtime: reliable AI-news evaluation, bounded prefilter scoring and full automation visibility."""
import json
from flask import jsonify
import v79_main as base
from payload_utils import as_mapping

app=base.app
legacy=base.legacy
controller=base.controller

legacy.NAV_ITEMS=[
 ('/','Übersicht'),('/products','Märkte & Produkte'),('/scanner','Analyse & Research'),('/portfolio','Portfolio'),
 ('/paper','Paper-Trading'),('/controlled-learning','Kontrolliertes Lernen'),('/news-learning','Nachrichten & AI'),
 ('/automatik','Automatik'),('/backtests','Evaluation & Backtests'),('/data-quality','Datenqualität'),('/fees','Gebühren & Kosten'),
 ('/process','Systemablauf'),('/real-trading','Realhandel (gesperrt)'),('/decision-matrix','Regelmatrix'),('/tax-info','Steuerinfo AT'),
 ('/settings','Einstellungen'),('/api','API & Verbindungen'),('/audit','Audit & Ereignisse')]

def _safe(fn,default=None):
 try:return fn()
 except Exception:return default

def _dashboard_v80():
 portfolio=_safe(lambda:legacy.db.rows('SELECT total_eur,quality,created_at FROM portfolio_snapshots ORDER BY id DESC LIMIT 1'),[]) or []
 public=as_mapping(_safe(legacy.stream.status,{}),{});private=as_mapping(_safe(legacy.private_stream.status,{}),{});research=as_mapping(_safe(legacy.pipeline.latest,{}),{})
 cfg=controller.settings() if controller else {};auto_on=str(cfg.get('automation_master_enabled','false')).lower()=='true'
 ai_valid=_safe(lambda:legacy.db.rows("SELECT COUNT(*) n FROM external_news_ai_results WHERE status='VALID'"),[]) or []
 ai_invalid=_safe(lambda:legacy.db.rows("SELECT COUNT(*) n FROM external_news_ai_results WHERE status='INVALID'"),[]) or []
 pre=_safe(lambda:legacy.db.rows('SELECT status,candidate_count,market_count,created_at FROM prefilter_runs ORDER BY id DESC LIMIT 1'),[]) or []
 return legacy.page('''<h1>Kraken Trader v80</h1><p class="lead">Zentrale Oberfläche für Daten, Nachrichten-AI, Research, Lernen und Automatik.</p><div class="grid"><div class="card"><h3>Portfolio</h3><div class="metric">{{portfolio.total_eur if portfolio else '→'}} €</div><small>{{portfolio.quality if portfolio else 'Noch kein Snapshot'}}</small></div><div class="card"><h3>Marktdaten</h3><div class="metric">{{public.effective_state}}</div><small>{{public.symbol_count}} Symbole · {{public.blocked_symbol_count or 0}} isoliert</small></div><div class="card"><h3>Research</h3><div class="metric">{{research.stage or 'NONE'}}</div><small>{{research.status or 'NONE'}}</small></div><div class="card"><h3>Prefilter</h3><div class="metric">{{pre.candidate_count if pre else 0}}</div><small>{{pre.status if pre else 'NONE'}} · {{pre.market_count if pre else 0}} Märkte</small></div><div class="card"><h3>Nachrichten-AI</h3><div class="metric">{{ai_valid}}</div><small>gültig · {{ai_invalid}} ungültig/retryfähig</small></div><div class="card"><h3>Automatik</h3><div class="metric">{{'AKTIV' if auto_on else 'AUS'}}</div><small>Analyse, News+AI, Lernen, Paper und Real separat schaltbar</small></div></div><div class="card"><h2>Automatischer Gesamtprozess</h2><p>Über <a href="{{url_for('automation_v67')}}">Automatik</a> können Nachrichtenabruf inklusive externer AI-Auswertung, Research, Lernen und Paper-Handel zeitgesteuert laufen. Die automatische Lernfreigabe bleibt ein eigener Schalter. Realhandel benötigt weiterhin zusätzlich seine separaten Sicherheits-Gates.</p><p><a href="{{url_for('news_learning_page')}}">Nachrichten & AI prüfen</a> · <a href="{{url_for('scanner_page')}}">Research öffnen</a> · <a href="{{url_for('v80_health')}}">v80 Diagnose</a></p></div>''',portfolio=portfolio[0] if portfolio else None,public=public,private=private,research=research,pre=pre[0] if pre else None,ai_valid=ai_valid[0]['n'] if ai_valid else 0,ai_invalid=ai_invalid[0]['n'] if ai_invalid else 0,auto_on=auto_on)

app.view_functions['index']=_dashboard_v80

@app.get('/v80-health')
def v80_health():
 latest_ai=_safe(lambda:legacy.db.rows("SELECT news_id,created_at,status,error FROM external_news_ai_results ORDER BY created_at DESC LIMIT 20"),[]) or []
 pre=_safe(lambda:legacy.db.rows('SELECT * FROM prefilter_runs ORDER BY id DESC LIMIT 1'),[]) or []
 pre_bad=_safe(lambda:legacy.db.rows("SELECT COUNT(*) n FROM prefilter_results WHERE run_id=(SELECT id FROM prefilter_runs ORDER BY id DESC LIMIT 1) AND quality NOT IN ('VALID','CACHED')"),[]) or []
 auto=controller.settings() if controller else {};runs=_safe(lambda:controller.latest(20),[]) if controller else []
 return jsonify({'version':'0.1.0-dev.80','runtime':'v80_main','dataflow_status':legacy.db.value('v77_dataflow_status','STARTING'),'public_websocket':as_mapping(_safe(legacy.stream.status,{}),{}),'private_websocket':as_mapping(_safe(legacy.private_stream.status,{}),{}),'research':_safe(legacy.pipeline.latest,None),'prefilter':pre[0] if pre else None,'prefilter_invalid_or_pending':pre_bad[0]['n'] if pre_bad else 0,'external_ai':{'provider':legacy.external_news_ai._provider(),'resolved_model':legacy.external_news_ai._model(),'enabled':bool(legacy.external_news_ai.options.get('ai_news_enabled')),'recent':latest_ai},'automation':auto,'automation_runs':runs})
