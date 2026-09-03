"""v79 runtime: stable market feed, healthy research completion, and one coherent GUI."""
import json
import os
import threading
import time
from flask import jsonify, render_template_string, request

import v78_main as base
from payload_utils import as_mapping

app = base.app
legacy = base.legacy
controller = getattr(base, 'controller', None)

# One navigation model for every page rendered through legacy.page().
legacy.NAV_ITEMS = [
    ('/', 'Übersicht'),
    ('/products', 'Märkte & Produkte'),
    ('/scanner', 'Analyse & Research'),
    ('/portfolio', 'Portfolio'),
    ('/paper', 'Paper-Trading'),
    ('/controlled-learning', 'Kontrolliertes Lernen'),
    ('/news-learning', 'Nachrichten & Lernen'),
    ('/backtests', 'Evaluation & Backtests'),
    ('/data-quality', 'Datenqualität'),
    ('/fees', 'Gebühren & Kosten'),
    ('/process', 'Systemablauf'),
    ('/real-trading', 'Realhandel (gesperrt)'),
    ('/decision-matrix', 'Regelmatrix'),
    ('/tax-info', 'Steuerinfo AT'),
    ('/settings', 'Einstellungen'),
    ('/audit', 'Audit & Ereignisse'),
]


def _safe(fn, default=None):
    try:
        return fn()
    except Exception:
        return default


def _watch_symbols(limit=100):
    cap = max(20, min(250, int(limit)))
    held = _safe(
        lambda: [
            ('BTC' if x['display_name'] == 'XBT' else x['display_name']) + '/EUR'
            for x in legacy.db.rows("SELECT display_name FROM portfolio_assets WHERE classification='HELD'")
            if x['display_name'] != 'EUR'
        ],
        [],
    ) or []
    candidates = _safe(lambda: legacy.prefilter.candidates(), []) or []
    universe = _safe(lambda: legacy.universe.symbols(None), []) or []
    ordered = []
    for symbol in list(held) + list(candidates) + list(universe):
        if symbol and symbol not in ordered and '/' in symbol:
            ordered.append(symbol)
        if len(ordered) >= cap:
            break
    return ordered


def _refresh_market_subscription():
    if os.getenv('APP_DISABLE_WEBSOCKETS') == '1':
        return
    symbols = _watch_symbols(_safe(lambda: legacy.db.value('websocket_symbol_limit', '100'), '100'))
    if symbols:
        _safe(lambda: legacy.stream.set_symbols(symbols))
        _safe(legacy.stream.start)
        _safe(lambda: legacy.db.set_setting('v79_public_symbol_target', str(len(symbols))))


def _market_subscription_loop():
    time.sleep(2.0)
    while True:
        _refresh_market_subscription()
        time.sleep(60)


_refresh_market_subscription()
if os.getenv('APP_DISABLE_WEBSOCKETS') != '1':
    threading.Thread(target=_market_subscription_loop, daemon=True, name='v79-market-subscription').start()


def _dashboard():
    portfolio = _safe(
        lambda: legacy.db.rows(
            'SELECT total_eur,quality,created_at FROM portfolio_snapshots ORDER BY id DESC LIMIT 1'
        ),
        [],
    ) or []
    public = as_mapping(_safe(legacy.stream.status, {}), {})
    private = as_mapping(_safe(legacy.private_stream.status, {}), {})
    research = as_mapping(_safe(legacy.pipeline.latest, {}), {})
    prefilter = _safe(
        lambda: legacy.db.rows(
            "SELECT id,status,market_count,candidate_count,news_items,details_json,created_at FROM prefilter_runs ORDER BY id DESC LIMIT 1"
        ),
        [],
    ) or []
    prefilter_row = prefilter[0] if prefilter else {}
    try:
        prefilter_details = json.loads(prefilter_row.get('details_json') or '{}')
    except Exception:
        prefilter_details = {}
    html = '''<!doctype html><html lang="de"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Kraken Trader v79</title><link rel="stylesheet" href="{{ script_root }}/static/style.css"><link rel="stylesheet" href="{{ script_root }}/static/v70.css"></head><body><div class="shell"><header class="top"><div class="brand"><strong>Kraken Trader</strong> <small>v79</small></div><span class="safety">REALHANDEL STANDARDMÄSSIG DEAKTIVIERT</span><nav class="nav">{% for href,label in nav %}<a href="{{script_root}}{{href}}">{{label}}</a>{% endfor %}</nav></header><main><h1>Übersicht</h1><p class="lead">Einheitliche Oberfläche für Marktdaten, Research, Portfolio, Simulation und kontrolliertes Lernen.</p><div class="grid"><div class="card"><h3>Realportfolio</h3><div class="metric">{{portfolio[0].total_eur if portfolio else '→'}} €</div><small>{{portfolio[0].quality if portfolio else 'Noch kein Snapshot'}}</small></div><div class="card"><h3>Marktdaten</h3><div class="metric">{{public.get('effective_state','STOPPED')}}</div><small>{{public.get('symbol_count',0)}} abonnierte Symbole · Ziel {{target_symbols}}</small></div><div class="card"><h3>Kontodaten</h3><div class="metric">{{private.get('effective_state','STOPPED')}}</div><small>{{private.get('last_message_at') or 'Noch keine Nachricht'}}</small></div><div class="card"><h3>Research</h3><div class="metric">{{research.get('stage','NONE')}}</div><small>{{research.get('status','NONE')}} · {{research.get('progress_current',0)}}/{{research.get('progress_total',0)}}</small></div><div class="card"><h3>Prefilter</h3><div class="metric">{{prefilter_row.get('candidate_count',0)}}</div><small>{{prefilter_row.get('status','NOCH NICHT AUSGEFÜHRT')}} · {{prefilter_row.get('market_count',0)}} Märkte</small></div></div><div class="card"><h2>Aktueller Arbeitszustand</h2><p><b>Marktfeed:</b> {{public.get('effective_state','STOPPED')}}. Ungültige Einzelpaare dürfen die übrigen WebSocket-Abonnements nicht mehr unterbrechen.</p><p><b>Research:</b> {{research.get('stage','NONE')}}. Payload-Fehler werden auf der tatsächlich betroffenen Stufe isoliert; ein erfolgreich abgeschlossener Lauf wird nicht künstlich als DEGRADED beendet.</p><p><b>Prefilter:</b> {{prefilter_row.get('candidate_count',0)}} Kandidaten. Falls Live-Ticker fehlen, werden aktuelle/cached Marktdaten nachvollziehbar weiterverwendet; eine reine Recovery-Liste wird separat gekennzeichnet.</p><p><a href="{{script_root}}/v79-health">v79-Diagnose öffnen</a> · <a href="{{script_root}}/scanner">Analyse öffnen</a> · <a href="{{script_root}}/products">Märkte prüfen</a></p></div></main></div></body></html>'''
    nav = [(href, label) for href, label in legacy.NAV_ITEMS]
    return render_template_string(
        html,
        portfolio=portfolio,
        public=public,
        private=private,
        research=research,
        prefilter_row=prefilter_row,
        prefilter_details=prefilter_details,
        target_symbols=legacy.db.value('websocket_symbol_limit', '100'),
        nav=nav,
        script_root=request.script_root,
    )


app.view_functions['index'] = _dashboard


@app.get('/v79-health')
def v79_health():
    portfolio = _safe(
        lambda: legacy.db.rows(
            'SELECT total_eur,quality,created_at,priced_asset_count,unpriced_asset_count FROM portfolio_snapshots ORDER BY id DESC LIMIT 1'
        ),
        [],
    ) or []
    research = _safe(legacy.pipeline.latest, None)
    watchlist = _safe(
        lambda: legacy.db.rows(
            "SELECT symbol,category,prefilter_score,status FROM research_watchlist ORDER BY CASE WHEN status='RECOVERED' THEN 1 ELSE 0 END, CAST(prefilter_score AS REAL) DESC LIMIT 50"
        ),
        [],
    ) or []
    prefilter = _safe(
        lambda: legacy.db.rows(
            "SELECT id,status,market_count,candidate_count,news_items,details_json,created_at FROM prefilter_runs ORDER BY id DESC LIMIT 1"
        ),
        [],
    ) or []
    prefilter_results = _safe(
        lambda: legacy.db.rows(
            "SELECT symbol,category,score,liquidity_score,spread_score,momentum_score,news_score,quality FROM prefilter_results WHERE run_id=(SELECT id FROM prefilter_runs ORDER BY id DESC LIMIT 1) ORDER BY CAST(score AS REAL) DESC LIMIT 30"
        ),
        [],
    ) or []
    return jsonify({
        'version': '0.1.0-dev.79',
        'runtime': 'v79_main',
        'research': research,
        'research_quality': (research or {}).get('details_json') if research else None,
        'watchlist_count': len(watchlist),
        'watchlist_preview': watchlist,
        'prefilter': prefilter[0] if prefilter else None,
        'prefilter_results': prefilter_results,
        'portfolio': portfolio[0] if portfolio else None,
        'public_websocket': as_mapping(_safe(legacy.stream.status, {}), {}),
        'private_websocket': as_mapping(_safe(legacy.private_stream.status, {}), {}),
        'market_subscription_target': int(float(legacy.db.value('websocket_symbol_limit', '100'))),
        'dataflow_status': legacy.db.value('v77_dataflow_status', 'STARTING'),
    })


@app.post('/v79-analysis/repair')
def v79_analysis_repair():
    errors = []
    try:
        legacy.universe.sync()
    except Exception as exc:
        errors.append('universe: ' + type(exc).__name__ + ': ' + str(exc)[:200])
    try:
        result = legacy.prefilter.run(int(float(legacy.db.value('prefilter_top_per_category', '8'))))
    except Exception as exc:
        result = {'status': 'DEGRADED', 'candidates': 0}
        errors.append('prefilter: ' + type(exc).__name__ + ': ' + str(exc)[:200])
    _refresh_market_subscription()
    return jsonify({'status': 'COMPLETED' if not errors else 'COMPLETED_WITH_WARNINGS', 'prefilter': result, 'errors': errors})
