"""v77 runtime: reliable Kraken market/account dataflow and portfolio bootstrap."""
import json
import os
import threading
import time
from flask import jsonify, render_template_string

import v76_main as base
from payload_utils import as_mapping
from portfolio_sync import build_rows, normalize_asset

app = base.app
controller = base.controller
legacy = base.legacy

def _audit(event, details='', level='info'):
    try:
        legacy.db.audit(event, details, level)
    except Exception:
        pass

def _set_status(key, value):
    try:
        legacy.db.set_setting(key, value)
    except Exception:
        pass

# Account and market WebSockets are read-only data feeds. They are enabled by
# default in v77 even when an older /data/options.json explicitly omitted them.
if os.getenv('APP_DISABLE_WEBSOCKETS') != '1':
    try:
        legacy.stream.enabled = True
        legacy.private_stream.enabled = True
        legacy.restore_stream_symbols()
        legacy.private_stream.start()
    except Exception as exc:
        _audit('V77_WEBSOCKET_START_FAILED', type(exc).__name__ + ': ' + str(exc)[:300], 'error')

_last_private_balance_marker = None

def _light_rest_portfolio_sync():
    """Build a current portfolio snapshot without paginating the complete ledger."""
    balances = legacy.client.balance()
    assets = legacy.client.assets()
    pairs = legacy.client.pairs()
    known_assets = {x['asset'] for x in legacy.db.rows('SELECT asset FROM portfolio_assets')}
    names = {normalize_asset(x, assets) for x in set(balances) | known_assets}
    relevant = []
    for pair_id, pair in pairs.items():
        if normalize_asset(pair.get('base', ''), assets) in names and normalize_asset(pair.get('quote', ''), assets) == 'EUR':
            relevant.append(pair.get('altname', pair_id))
    tickers = legacy.client.ticker(relevant)
    rows, total, quality = build_rows(balances, known_assets, assets, pairs, tickers)
    legacy.db.replace_balances(balances)
    snapshot_id = legacy.db.store_portfolio(rows, total, quality)
    held_names = {
        normalize_asset(code, assets)
        for code, value in balances.items()
        if str(value) not in ('0', '0.0', '0.00')
    }
    symbols = [
        legacy.ws_asset(normalize_asset(pair.get('base', ''), assets)) + '/EUR'
        for pair in pairs.values()
        if normalize_asset(pair.get('base', ''), assets) in held_names
        and normalize_asset(pair.get('quote', ''), assets) == 'EUR'
    ]
    legacy.stream.set_symbols(symbols)
    legacy.stream.start()
    _set_status('v77_portfolio_source', 'REST')
    _set_status('v77_portfolio_last_sync', legacy.db.value('v77_portfolio_last_sync', ''))
    _audit('V77_REAL_PORTFOLIO_BOOTSTRAP', json.dumps({
        'snapshot_id': snapshot_id,
        'assets': len(rows),
        'quality': quality,
        'symbols': len(symbols),
    }, sort_keys=True))
    return snapshot_id

def _sync_private_balances():
    global _last_private_balance_marker
    rows = legacy.db.rows('SELECT asset,balance,received_at FROM private_balances ORDER BY asset')
    if not rows:
        return None
    marker = max(str(row.get('received_at') or '') for row in rows)
    if marker == _last_private_balance_marker:
        return None

    balances = {row['asset']: row['balance'] for row in rows}
    assets = legacy.client.assets()
    pairs = legacy.client.pairs()
    known_assets = {x['asset'] for x in legacy.db.rows('SELECT asset FROM portfolio_assets')}
    names = {normalize_asset(x, assets) for x in set(balances) | known_assets}
    relevant = []
    for pair_id, pair in pairs.items():
        if normalize_asset(pair.get('base', ''), assets) in names and normalize_asset(pair.get('quote', ''), assets) == 'EUR':
            relevant.append(pair.get('altname', pair_id))
    tickers = legacy.client.ticker(relevant)
    portfolio_rows, total, quality = build_rows(balances, known_assets, assets, pairs, tickers)
    legacy.db.replace_balances(balances)
    snapshot_id = legacy.db.store_portfolio(portfolio_rows, total, quality)
    held_names = {
        normalize_asset(code, assets)
        for code, value in balances.items()
        if str(value) not in ('0', '0.0', '0.00')
    }
    symbols = [
        legacy.ws_asset(normalize_asset(pair.get('base', ''), assets)) + '/EUR'
        for pair in pairs.values()
        if normalize_asset(pair.get('base', ''), assets) in held_names
        and normalize_asset(pair.get('quote', ''), assets) == 'EUR'
    ]
    legacy.stream.set_symbols(symbols)
    legacy.stream.start()
    _last_private_balance_marker = marker
    _set_status('v77_portfolio_source', 'PRIVATE_WEBSOCKET')
    _set_status('v77_portfolio_last_sync', marker)
    _audit('V77_PRIVATE_PORTFOLIO_SYNC', json.dumps({
        'snapshot_id': snapshot_id,
        'assets': len(portfolio_rows),
        'quality': quality,
        'marker': marker,
    }, sort_keys=True))
    return snapshot_id

def _startup_dataflow():
    # Let Gunicorn finish importing the WSGI application before making network calls.
    time.sleep(1.0)
    if os.getenv('APP_DISABLE_WEBSOCKETS') == '1':
        _set_status('v77_dataflow_status', 'DISABLED_BY_ENV')
        return
    _set_status('v77_dataflow_status', 'BOOTSTRAPPING')
    try:
        snapshot_id = _light_rest_portfolio_sync()
        _set_status('v77_dataflow_status', 'READY')
        _set_status('v77_rest_last_success', legacy.db.value('v77_rest_last_success', ''))
        _audit('V77_DATAFLOW_READY', json.dumps({'snapshot_id': snapshot_id}, sort_keys=True))
    except Exception as exc:
        _set_status('v77_dataflow_status', 'DEGRADED')
        _set_status('v77_rest_last_error', type(exc).__name__ + ': ' + str(exc)[:500])
        _audit('V77_DATAFLOW_BOOTSTRAP_FAILED', type(exc).__name__ + ': ' + str(exc)[:500], 'error')
    while True:
        try:
            _sync_private_balances()
        except Exception as exc:
            _set_status('v77_private_sync_error', type(exc).__name__ + ': ' + str(exc)[:500])
        # REST is a recovery path, not the primary update stream.
        try:
            interval = max(60, int(float(legacy.db.value('v77_rest_fallback_minutes', '5')) * 60))
        except Exception:
            interval = 300
        time.sleep(interval)
        try:
            _light_rest_portfolio_sync()
            _set_status('v77_rest_last_error', '')
            _set_status('v77_rest_last_success', legacy.db.value('v77_portfolio_last_sync', ''))
        except Exception as exc:
            _set_status('v77_rest_last_error', type(exc).__name__ + ': ' + str(exc)[:500])
            _audit('V77_REST_FALLBACK_FAILED', type(exc).__name__ + ': ' + str(exc)[:500], 'warning')

threading.Thread(target=_startup_dataflow, daemon=True, name='v77-kraken-dataflow').start()

@app.get('/v77-health')
def v77_health():
    portfolio = legacy.db.rows('SELECT total_eur,quality,created_at,priced_asset_count,unpriced_asset_count FROM portfolio_snapshots ORDER BY id DESC LIMIT 1')
    private_rows = legacy.db.rows('SELECT COUNT(*) AS count,MAX(received_at) AS received_at FROM private_balances')
    return jsonify({
        'version': '0.1.0-dev.77',
        'runtime': 'v77_main',
        'dataflow_status': legacy.db.value('v77_dataflow_status', 'STARTING'),
        'public_websocket': as_mapping(legacy.stream.status(), {}),
        'private_websocket': as_mapping(legacy.private_stream.status(), {}),
        'private_balance_count': private_rows[0]['count'] if private_rows else 0,
        'private_balance_last_received_at': private_rows[0]['received_at'] if private_rows else None,
        'latest_portfolio': portfolio[0] if portfolio else None,
        'portfolio_source': legacy.db.value('v77_portfolio_source', 'NONE'),
        'rest_last_error': legacy.db.value('v77_rest_last_error', ''),
    })

def _v77_dashboard():
    portfolio = legacy.db.rows('SELECT total_eur,quality,created_at FROM portfolio_snapshots ORDER BY id DESC LIMIT 1')
    private = legacy.private_stream.status()
    public = legacy.stream.status()
    return legacy.page(render_template_string('''
    <h1>Kraken Trader v77</h1>
    <p class="lead">Zentrale Datenbasis: Kraken REST für Bootstrap und Fallback, öffentlicher WebSocket für Marktdaten, privater Read-only WebSocket für Kontostände und Ausführungen.</p>
    <div class="grid">
      <div class="card"><h3>Realportfolio</h3><div class="metric">{{ portfolio[0].total_eur if portfolio else '→' }} €</div><small>{{ portfolio[0].quality if portfolio else 'Noch kein Snapshot' }} · {{ portfolio[0].created_at if portfolio else '→' }}</small></div>
      <div class="card"><h3>Privater Kraken-Feed</h3><div class="metric">{{ private.effective_state }}</div><small>{{ private.last_message_at or 'Noch keine Nachricht' }}</small></div>
      <div class="card"><h3>Marktdaten</h3><div class="metric">{{ public.effective_state }}</div><small>{{ public.symbol_count }} Symbole</small></div>
      <div class="card"><h3>v77 Datenfluss</h3><div class="metric">{{ dataflow }}</div><small>Quelle Realportfolio: {{ source }}</small></div>
    </div>
    <div class="card"><h2>Was wird jetzt automatisch gemacht?</h2><p>Beim Start wird der Kontostand einmal über REST eingelesen, damit das Realportfolio auch ohne vorhandenen WebSocket-Snapshot sofort entstehen kann. Danach liefert der private Kraken-WebSocket laufende Balance-/Execution-Daten; Änderungen erzeugen neue Portfolio-Snapshots. Zusätzlich läuft ein langsamer REST-Fallback zur Selbstheilung, falls der WebSocket ausfällt.</p></div>
    <div class="card"><a href="{{ url_for('api_status') }}">Kraken-API und WebSocket prüfen</a> · <a href="{{ url_for('portfolio') }}">Realportfolio öffnen</a> · <a href="{{ url_for('scanner_page') }}">Analyse</a></div>
    ''', portfolio=portfolio, private=private, public=public, dataflow=legacy.db.value('v77_dataflow_status','STARTING'), source=legacy.db.value('v77_portfolio_source','NONE'))

# Keep the canonical / URL while replacing only its view function, avoiding a second rule.
app.view_functions['index'] = _v77_dashboard
