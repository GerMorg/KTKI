"""v69 runtime wrapper: harden Paper automation, expose tax GUI, and render real charts."""
import v68_main as wrapper
from flask import redirect, url_for

app = wrapper.app
core = wrapper.base


def _normalize_ticker_payload(payload):
    if isinstance(payload, dict):
        return payload
    if isinstance(payload, list):
        merged = {}
        for item in payload:
            if isinstance(item, dict):
                merged.update(item)
        return merged
    return {}


def refresh_allowed_prices_v69():
    symbols = list(core.current_market_batch())
    if any(x.endswith('/USD') for x in symbols) and 'EUR/USD' not in symbols:
        symbols.append('EUR/USD')
    if not symbols:
        return 0
    received = __import__('db').now(); saved = 0; groups = {}
    for symbol in symbols:
        row = core.db.rows('SELECT asset_class FROM market_universe WHERE symbol=? LIMIT 1', (symbol,))
        groups.setdefault(row[0]['asset_class'] if row else 'currency', []).append(symbol)
    for asset_class, batch in groups.items():
        try:
            try: payload = core.client.ticker(batch, asset_class)
            except TypeError: payload = core.client.ticker(batch)
            payload = _normalize_ticker_payload(payload)
        except Exception as exc:
            core.db.audit('PAPER_PRICE_REFRESH_FAILED', asset_class + ': ' + type(exc).__name__, 'error'); continue
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
            openp = core.D(item.get('o')); change = str(((core.D(last) - openp) / openp * 100) if openp else core.D(0))
            core.db.upsert_live_price({'symbol': requested, 'last': last, 'bid': bid_v, 'ask': ask_v, 'change_pct': change, 'received_at': received}); saved += 1
    core.stream.set_symbols(symbols); core.stream.start(); return saved


def run_paper_cycle_v69():
    refresh_allowed_prices_v69(); core.configure_engine(core.paper_engine); core.forecasts.evaluate_due(); result = core.paper_engine.run()
    return {'status': 'COMPLETED', 'actions': result} if isinstance(result, list) else (result or {'status': 'COMPLETED'})


def chart_v69(values):
    vals = []
    for item in values or []:
        try: vals.append(float(item))
        except (TypeError, ValueError): continue
    if not vals:
        return '<svg viewBox="0 0 900 300" class="chart"><text x="30" y="150" class="chart-empty">Noch keine Portfoliohistorie</text></svg>'
    width, height, left, right, top, bottom = 900, 300, 56, 24, 30, 42
    lo, hi = min(vals), max(vals); pad = max((hi-lo)*0.12, abs(hi)*0.01, 1.0); lo -= pad; hi += pad
    def xy(i, v):
        x = left + (width-left-right)*i/max(1,len(vals)-1); y = top + (height-top-bottom)*(1-(v-lo)/(hi-lo)); return x,y
    points = [xy(i,v) for i,v in enumerate(vals)]
    line = ' '.join(f'{x:.1f},{y:.1f}' for x,y in points)
    area = ' '.join([f'{left},{height-bottom}']+[f'{x:.1f},{y:.1f}' for x,y in points]+[f'{points[-1][0]:.1f},{height-bottom}'])
    grid = ''.join(f'<line x1="{left}" y1="{y}" x2="{width-right}" y2="{y}" class="chart-gridline"/>' for y in (top,(top+height-bottom)/2,height-bottom))
    labels = f'<text x="{left}" y="18" class="chart-label">{hi:.2f} €</text><text x="{left}" y="{height-8}" class="chart-label">{lo:.2f} €</text><text x="{width-right}" y="18" text-anchor="end" class="chart-value">Aktuell {vals[-1]:.2f} €</text>'
    return f'<svg viewBox="0 0 {width} {height}" class="chart" role="img" aria-label="Portfolio-Wertentwicklung">{grid}<polygon points="{area}" class="chart-area"/><polyline points="{line}" class="chart-line" fill="none"/>{labels}</svg>'

core._chart = chart_v69
core.refresh_allowed_prices = refresh_allowed_prices_v69
core.run_paper_cycle = run_paper_cycle_v69
core.controller.run_paper_cycle = run_paper_cycle_v69
core.NAV_ITEMS = [('/', 'Übersicht'),('/analyse','1 Analyse'),('/portfolio-modern','2 Portfolio'),('/handel','3 Handel'),('/lernen-modern','4 Lernen'),('/automatik','5 Automatik'),('/tax-info','6 Steuer'),('/parameter','Parameter')]

@app.get('/steuer')
def tax_ui_v69():
    return redirect(url_for('at_tax_v63.tax_info'))
