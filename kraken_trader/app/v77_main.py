"""v77 runtime: reliable Kraken market/account dataflow and portfolio bootstrap."""
import json
import os
import threading
import time
from flask import jsonify

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


# Read-only market/account feeds are always enabled by the v77 runtime unless
# the container explicitly disables all WebSockets for diagnostics.
if os.getenv('APP_DISABLE_WEBSOCKETS') != '1':
    try:
        legacy.stream.enabled = True
        legacy.private_stream.enabled = True
        legacy.restore_stream_symbols()
        legacy.private_stream.start()
        _audit('V77_WEBSOCKETS_ENABLED')
    except Exception as exc:
        _audit('V77_WEBSOCKET_START_FAILED', type(exc).__name__ + ': ' + str(exc)[:300], 'error')

_last_private_balance_marker = None


def _held_symbols(balances, assets, pairs):
    held_names = {
        normalize_asset(code, assets)
        for code, value in balances.items()
        if str(value) not in ('0', '0.0', '0.00')
    }
    return [
        legacy.ws_asset(normalize_asset(pair.get('base', ''), assets)) + '/EUR'
        for pair in pairs.values()
        if normalize_asset(pair.get('base', ''), assets) in held_names
        and normalize_asset(pair.get('quote', ''), assets) == 'EUR'
    ]


def _portfolio_from_balances(balances, source):
    assets = legacy.client.assets()
    pairs = legacy.client.pairs()
    known_assets = {row['asset'] for row in legacy.db.rows('SELECT asset FROM portfolio_assets')}
    names = {normalize_asset(code, assets) for code in set(balances) | known_assets}
    relevant = [
        pair.get('altname', pair_id)
        for pair_id, pair in pairs.items()
        if normalize_asset(pair.get('base', ''), assets) in names
        and normalize_asset(pair.get('quote', ''), assets) == 'EUR'
    ]
    tickers = legacy.client.ticker(relevant) if relevant else {}
    rows, total, quality = build_rows(balances, known_assets, assets, pairs, tickers)
    legacy.db.replace_balances(balances)
    snapshot_id = legacy.db.store_portfolio(rows, total, quality)
    symbols = _held_symbols(balances, assets, pairs)
    legacy.stream.set_symbols(symbols)
    legacy.stream.start()
    _set_status('v77_portfolio_source', source)
    _set_status('v77_portfolio_last_sync', legacy.db.now() if hasattr(legacy.db, 'now') else '')
    _audit('V77_PORTFOLIO_SNAPSHOT', json.dumps({
        'snapshot_id': snapshot_id,
        'source': source,
        'assets': len(rows),
        'quality': quality,
        'total_eur': total,
    }, sort_keys=True))
    return snapshot_id


def _light_rest_portfolio_sync():
    """Bootstrap a current portfolio without downloading the full ledger."""
    balances = legacy.client.balance()
    return _portfolio_from_balances(balances, 'REST')


def _sync_private_balances():
    global _last_private_balance_marker
    rows = legacy.db.rows(
        'SELECT asset,balance,received_at FROM private_balances ORDER BY asset'
    )
    if not rows:
        return None
    marker = max(str(row.get('received_at') or '') for row in rows)
    if marker == _last_private_balance_marker:
        return None
    balances = {row['asset']: row['balance'] for row in rows}
    snapshot_id = _portfolio_from_balances(balances, 'PRIVATE_WEBSOCKET')
    _last_private_balance_marker = marker
    _set_status('v77_portfolio_last_sync', marker)
    _audit('V77_PRIVATE_BALANCE_APPLIED', json.dumps({
        'snapshot_id': snapshot_id,
        'marker': marker,
        'assets': len(balances),
    }, sort_keys=True))
    return snapshot_id


def _startup_dataflow():
    # Network calls run outside the WSGI import path so Gunicorn can finish booting.
    time.sleep(1.0)
    if os.getenv('APP_DISABLE_WEBSOCKETS') == '1':
        _set_status('v77_dataflow_status', 'DISABLED_BY_ENV')
        return
    _set_status('v77_dataflow_status', 'BOOTSTRAPPING')
    try:
        snapshot_id = _light_rest_portfolio_sync()
        _set_status('v77_dataflow_status', 'READY')
        _set_status('v77_rest_last_error', '')
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
        try:
            interval = max(60, int(float(legacy.db.value('v77_rest_fallback_minutes', '5')) * 60))
        except Exception:
            interval = 300
        time.sleep(interval)
        try:
            _light_rest_portfolio_sync()
            _set_status('v77_rest_last_error', '')
        except Exception as exc:
            _set_status('v77_rest_last_error', type(exc).__name__ + ': ' + str(exc)[:500])
            _audit('V77_REST_FALLBACK_FAILED', type(exc).__name__ + ': ' + str(exc)[:500], 'warning')


threading.Thread(target=_startup_dataflow, daemon=True, name='v77-kraken-dataflow').start()


@app.get('/v77-health')
def v77_health():
    portfolio = legacy.db.rows(
        'SELECT total_eur,quality,created_at,priced_asset_count,unpriced_asset_count '
        'FROM portfolio_snapshots ORDER BY id DESC LIMIT 1'
    )
    private_rows = legacy.db.rows(
        'SELECT COUNT(*) AS count,MAX(received_at) AS received_at FROM private_balances'
    )
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
    portfolio = legacy.db.rows(
        'SELECT total_eur,quality,created_at FROM portfolio_snapshots ORDER BY id DESC LIMIT 1'
    )
    private = legacy.private_stream.status()
    public = legacy.stream.status()
    return legacy.page(
        '<h1>Kraken Trader v77</h1>'
        '<p class="lead">Kraken REST liefert Bootstrap/Fallback. Der öffentliche WebSocket liefert Marktdaten, der private Read-only WebSocket Kontostände und Ausführungen.</p>'
        '<div class="grid">'
        '<div class="card"><h3>Realportfolio</h3><div class="metric">{{ portfolio[0].total_eur if portfolio else "→" }} €</div><small>{{ portfolio[0].quality if portfolio else "Noch kein Snapshot" }}</small></div>'
        '<div class="card"><h3>Privater Kraken-Feed</h3><div class="metric">{{ private.effective_state }}</div><small>{{ private.last_message_at or "Noch keine Nachricht" }}</small></div>'
        '<div class="card"><h3>Marktdaten</h3><div class="metric">{{ public.effective_state }}</div><small>{{ public.symbol_count }} Symbole</small></div>'
        '<div class="card"><h3>v77 Datenfluss</h3><div class="metric">{{ dataflow }}</div><small>Quelle: {{ source }}</small></div>'
        '</div>'
        '<div class="card"><h2>Automatischer Datenaufbau</h2><p>Beim Start wird der aktuelle Kraken-Kontostand einmal über REST gelesen. Danach werden private WebSocket-Balance-Snapshots übernommen. Ein langsamer REST-Fallback dient der Selbstheilung bei WebSocket-Ausfällen. Die Live-Order-Gates bleiben unverändert.</p></div>',
        portfolio=portfolio,
        private=private,
        public=public,
        dataflow=legacy.db.value('v77_dataflow_status', 'STARTING'),
        source=legacy.db.value('v77_portfolio_source', 'NONE'),
    )


# Reuse the v76 root URL without registering a duplicate Flask rule.
app.view_functions['index'] = _v77_dashboard
