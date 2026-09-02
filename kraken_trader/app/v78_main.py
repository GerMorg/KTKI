"""v78 runtime: resilient GUI shell and research recovery."""
import json
import v77_main as base
from flask import render_template_string, request

app = base.app
legacy = base.legacy


def _safe(fn, default=None):
    try:
        return fn()
    except Exception:
        return default


def _status_snapshot():
    portfolio = _safe(lambda: legacy.db.rows('SELECT total_eur,quality,created_at FROM portfolio_snapshots ORDER BY id DESC LIMIT 1'), []) or []
    public = _safe(lambda: legacy.stream.status(), {}) or {}
    private = _safe(lambda: legacy.private_stream.status(), {}) or {}
    research = _safe(lambda: legacy.pipeline.latest(), None)
    return portfolio, public, private, research


def _dashboard():
    portfolio, public, private, research = _status_snapshot()
    html = '''<!doctype html><html lang="de"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Kraken Trader v78</title><link rel="stylesheet" href="{{ script_root }}/static/style.css"><link rel="stylesheet" href="{{ script_root }}/static/v70.css"></head><body><div class="shell"><header class="top"><div class="brand"><div><strong>Kraken Trader</strong> <small>v78</small></div><span class="safety">REALHANDEL STANDARDMÄSSIG DEAKTIVIERT</span></div><nav class="nav"><a class="active" href="{{ script_root }}/">Übersicht</a><a href="{{ script_root }}/portfolio">Portfolio</a><a href="{{ script_root }}/products">Produkte</a><a href="{{ script_root }}/scanner">Analyse</a><a href="{{ script_root }}/paper">Paper-Handel</a><a href="{{ script_root }}/real-trading">Realhandel</a><a href="{{ script_root }}/process">Ablauf & Systeme</a><a href="{{ script_root }}/controlled-learning">Lernen</a><a href="{{ script_root }}/news-learning">Nachrichten-Lernen</a><a href="{{ script_root }}/fees">Gebühren</a><a href="{{ script_root }}/data-quality">Datenqualität</a><a href="{{ script_root }}/backtests">Backtests</a><a href="{{ script_root }}/decision-matrix">Regelmatrix</a><a href="{{ script_root }}/settings">Einstellungen</a><a href="{{ script_root }}/tax-info">Steuerinfo AT</a><a href="{{ script_root }}/audit">Audit</a></nav></header><main><h1>Übersicht</h1><p class="lead">Stabile Arbeitsoberfläche für Kraken-Daten, Analyse, Simulation und kontrolliertes Lernen.</p><div class="grid"><div class="card"><h3>Realportfolio</h3><div class="metric">{{ portfolio[0].total_eur if portfolio else '→' }} €</div><small>{{ portfolio[0].quality if portfolio else 'Noch kein Snapshot' }}</small></div><div class="card"><h3>Marktdaten</h3><div class="metric">{{ public.get('state','STOPPED') }}</div><small>{{ public.get('symbol_count',0) }} Symbole</small></div><div class="card"><h3>Kontodaten</h3><div class="metric">{{ private.get('state','STOPPED') }}</div><small>{{ private.get('last_message_at') or 'Noch keine Nachricht' }}</small></div><div class="card"><h3>Analyse</h3><div class="metric">{{ research.get('status','NONE') if research else 'NONE' }}</div><small>{{ research.get('stage','→') if research else 'Noch kein Lauf' }} · {{ research.get('progress_current',0) }}/{{ research.get('progress_total',0) }}</small></div></div><div class="card"><h2>Datenfluss</h2><p>REST initialisiert das Realportfolio. Öffentliche und private WebSockets aktualisieren Markt- und Kontodaten. Die Analyse kann bei einem einzelnen fehlerhaften Datenanbieter weiterarbeiten und Kandidaten für die Detailanalyse wiederherstellen.</p><p><a href="{{ script_root }}/v78-health">v78-Diagnose öffnen</a> · <a href="{{ script_root }}/scanner">Analyse starten</a> · <a href="{{ script_root }}/portfolio">Portfolio prüfen</a></p></div></main></div></body></html>'''
    return render_template_string(html, portfolio=portfolio, public=public, private=private, research=dict(research or {}), script_root=request.script_root)


app.view_functions['index'] = _dashboard


@app.get('/v78-health')
def v78_health():
    portfolio, public, private, research = _status_snapshot()
    watchlist = _safe(lambda: legacy.db.rows("SELECT symbol,category,prefilter_score,status FROM research_watchlist ORDER BY CAST(prefilter_score AS REAL) DESC LIMIT 50"), []) or []
    details = {}
    if research and research.get('details_json'):
        try:
            details = json.loads(research['details_json'])
        except Exception:
            details = {'parse_error': True}
    return {
        'version': '0.1.0-dev.78',
        'runtime': 'v78_main',
        'latest_research': research,
        'research_details': details,
        'watchlist_count': len(watchlist),
        'watchlist_preview': watchlist,
        'portfolio': portfolio[0] if portfolio else None,
        'public_websocket': public,
        'private_websocket': private,
        'dataflow_status': _safe(lambda: legacy.db.value('v77_dataflow_status', 'STARTING'), 'STARTING'),
    }


@app.post('/v78-analysis/repair')
def v78_analysis_repair():
    try:
        legacy.universe.sync()
    except Exception:
        pass
    try:
        legacy.prefilter.run(int(float(legacy.db.value('analysis_max_symbols', '20'))))
    except Exception as exc:
        legacy.db.audit('V78_PREFILTER_REPAIR_FAILED', type(exc).__name__ + ': ' + str(exc)[:300], 'warning')
    candidates = _safe(lambda: legacy.prefilter.candidates(), []) or []
    if candidates:
        try:
            legacy.scanner.run(candidates, 60, limit=len(candidates), delay_seconds=min(float(legacy.db.value('scanner_delay_seconds', '1.05')), 0.35))
        except Exception as exc:
            legacy.db.audit('V78_SCANNER_REPAIR_FAILED', type(exc).__name__ + ': ' + str(exc)[:300], 'warning')
    return {'status': 'COMPLETED', 'candidate_count': len(candidates)}
