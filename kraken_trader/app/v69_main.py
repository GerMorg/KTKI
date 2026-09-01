"""v69 runtime wrapper: stable v68 + hardened Paper automation and GUI fixes."""
import v68_main as base
from flask import redirect, url_for
app = base.app

def _normalize_ticker_payload(payload):
    if isinstance(payload, dict): return payload
    if isinstance(payload, list):
        merged = {}
        for item in payload:
            if isinstance(item, dict): merged.update(item)
        return merged
    return {}

def refresh_allowed_prices_v69():
    symbols = list(base.current_market_batch())
    if any(x.endswith('/USD') for x in symbols) and 'EUR/USD' not in symbols: symbols.append('EUR/USD')
    if not symbols: return 0
    received = __import__('db').now(); saved = 0; groups = {}
    for symbol in symbols:
        row = base.db.rows('SELECT asset_class FROM market_universe WHERE symbol=? LIMIT 1', (symbol,))
        groups.setdefault(row[0]['asset_class'] if row else 'currency', []).append(symbol)
    for asset_class, batch in groups.items():
        try:
            try: payload = base.client.ticker(batch, asset_class)
            except TypeError: payload = base.client.ticker(batch)
            payload = _normalize_ticker_payload(payload)
        except Exception as exc:
            base.db.audit('PAPER_PRICE_REFRESH_FAILED', asset_class + ': ' + type(exc).__name__, 'error'); continue
        for requested in batch:
            wanted = requested.replace('BTC/', 'XBT/').replace('/', ''); item = None
            for key, value in payload.items():
                compact = str(key).replace('X', '').replace('Z', '').replace('/', '')
                if requested.replace('BTC', 'XBT').replace('/', '') in compact or wanted in str(key): item = value; break
            if item is None and len(payload) == 1: item = next(iter(payload.values()))
            if isinstance(item, list): item = next((x for x in item if isinstance(x, dict)), None)
            if not isinstance(item, dict): continue
            close, bid, ask = item.get('c') or [], item.get('b') or [], item.get('a') or []
            last = str(close[0] if isinstance(close, (list, tuple)) and close else item.get('last') or '')
            bid_v = str(bid[0] if isinstance(bid, (list, tuple)) and bid else item.get('bid') or '')
            ask_v = str(ask[0] if isinstance(ask, (list, tuple)) and ask else item.get('ask') or '')
            if not last: continue
            openp = base.D(item.get('o')); change = str(((base.D(last) - openp) / openp * 100) if openp else base.D(0))
            base.db.upsert_live_price({'symbol': requested, 'last': last, 'bid': bid_v, 'ask': ask_v, 'change_pct': change, 'received_at': received}); saved += 1
    base.stream.set_symbols(symbols); base.stream.start(); return saved

def run_paper_cycle_v69():
    refresh_allowed_prices_v69(); base.configure_engine(base.paper_engine); base.forecasts.evaluate_due(); result = base.paper_engine.run()
    return {'status': 'COMPLETED', 'actions': result} if isinstance(result, list) else (result or {'status': 'COMPLETED'})

base.refresh_allowed_prices = refresh_allowed_prices_v69
base.controller.run_paper_cycle = run_paper_cycle_v69
base.legacy.NAV_ITEMS = [('/', 'Übersicht'),('/analyse','1 Analyse'),('/portfolio-modern','2 Portfolio'),('/handel','3 Handel'),('/lernen-modern','4 Lernen'),('/automatik','5 Automatik'),('/tax-info','6 Steuer'),('/parameter','Parameter')]

@app.get('/steuer')
def tax_ui_v69(): return redirect(url_for('at_tax_v63.tax_info'))
