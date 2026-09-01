"""v70 runtime: hardened automation boundaries and clearer portfolio charts."""
from flask import jsonify

import v68_main as wrapper

app = wrapper.app
v67 = wrapper.base
legacy = v67.legacy
controller = v67.controller


def as_mapping(value, default=None):
    """Return a dict-shaped result so scheduler boundaries can safely use .get()."""
    if isinstance(value, dict):
        return value
    if isinstance(value, list):
        mappings = [item for item in value if isinstance(item, dict)]
        return mappings[0] if len(mappings) == 1 else {"status": "COMPLETED", "items": mappings}
    if value is None:
        return dict(default or {"status": "COMPLETED"})
    return {"status": "COMPLETED", "value": value}


def normalize_kraken_payload(value):
    if isinstance(value, dict):
        return value
    if isinstance(value, list):
        merged = {}
        for item in value:
            if isinstance(item, dict):
                merged.update(item)
        return merged
    return {}


def current_market_batch_v70():
    """Use the real market source in main.py, not a wrapper namespace that does not expose it."""
    try:
        result = legacy.current_market_batch()
    except Exception as exc:
        legacy.db.audit('PAPER_MARKET_BATCH_FAILED', type(exc).__name__, 'error')
        return []
    return list(dict.fromkeys(str(x) for x in (result or []) if x)) if isinstance(result, (tuple, list)) else []


def refresh_allowed_prices_v70():
    symbols = current_market_batch_v70()
    if any(str(x).endswith('/USD') for x in symbols) and 'EUR/USD' not in symbols:
        symbols.append('EUR/USD')
    if not symbols:
        return {"status": "NO_SYMBOLS", "saved": 0}
    received = __import__('db').now()
    saved = 0
    groups = {}
    for symbol in symbols:
        row = legacy.db.rows('SELECT asset_class FROM market_universe WHERE symbol=? LIMIT 1', (symbol,))
        groups.setdefault(row[0]['asset_class'] if row else 'currency', []).append(symbol)
    for asset_class, batch in groups.items():
        try:
            try:
                payload = legacy.client.ticker(batch, asset_class)
            except TypeError:
                payload = legacy.client.ticker(batch)
            payload = normalize_kraken_payload(payload)
        except Exception as exc:
            legacy.db.audit('PAPER_PRICE_REFRESH_FAILED', asset_class + ': ' + type(exc).__name__, 'error')
            continue
        for requested in batch:
            wanted = requested.replace('BTC/', 'XBT/').replace('/', '')
            item = None
            for key, value in payload.items():
                compact = str(key).replace('X', '').replace('Z', '').replace('/', '')
                if requested.replace('BTC', 'XBT').replace('/', '') in compact or wanted in str(key):
                    item = value
                    break
            if item is None and len(payload) == 1:
                item = next(iter(payload.values()))
            if isinstance(item, list):
                item = next((x for x in item if isinstance(x, dict)), None)
            if not isinstance(item, dict):
                continue
            close = item.get('c') or []
            bid = item.get('b') or []
            ask = item.get('a') or []
            last = str(close[0] if isinstance(close, (list, tuple)) and close else item.get('last') or '')
            bid_v = str(bid[0] if isinstance(bid, (list, tuple)) and bid else item.get('bid') or '')
            ask_v = str(ask[0] if isinstance(ask, (list, tuple)) and ask else item.get('ask') or '')
            if not last:
                continue
            openp = legacy.D(item.get('o'))
            change = str(((legacy.D(last) - openp) / openp * 100) if openp else legacy.D(0))
            legacy.db.upsert_live_price({'symbol': requested, 'last': last, 'bid': bid_v, 'ask': ask_v, 'change_pct': change, 'received_at': received})
            saved += 1
    legacy.stream.set_symbols(symbols)
    legacy.stream.start()
    return {"status": "COMPLETED", "saved": saved, "symbols": len(symbols)}


def run_paper_cycle_v70():
    refresh = refresh_allowed_prices_v70()
    legacy.configure_engine(legacy.paper_engine)
    legacy.forecasts.evaluate_due()
    result = as_mapping(legacy.paper_engine.run())
    result.setdefault('price_refresh', refresh)
    return result

# Harden every scheduler boundary that historically assumed a dict-shaped return.
_original_pipeline_start = controller.pipeline.start
_original_news_collect = controller.news_prefilter.collect
_original_real_run = controller.real_allocator.run

def _safe_pipeline_start(*args, **kwargs):
    return as_mapping(_original_pipeline_start(*args, **kwargs))

def _safe_news_collect(*args, **kwargs):
    return as_mapping(_original_news_collect(*args, **kwargs))

def _safe_real_run(*args, **kwargs):
    return as_mapping(_original_real_run(*args, **kwargs))

controller.pipeline.start = _safe_pipeline_start
controller.news_prefilter.collect = _safe_news_collect
controller.real_allocator.run = _safe_real_run
controller.run_paper_cycle = run_paper_cycle_v70


def chart_v70(values):
    import math
    vals = []
    for item in values or []:
        try:
            value = float(item)
            if math.isfinite(value):
                vals.append(value)
        except (TypeError, ValueError):
            continue
    if not vals:
        return '<svg viewBox="0 0 960 330" class="chart chart-empty" role="img" aria-label="Keine Portfoliohistorie"><rect x="0" y="0" width="960" height="330" class="chart-bg"/><text x="480" y="165" text-anchor="middle" class="chart-empty-label">Noch keine Portfoliohistorie</text></svg>'
    width, height = 960, 330
    left, right, top, bottom = 78, 26, 34, 54
    lo, hi = min(vals), max(vals)
    pad = max((hi - lo) * 0.12, abs(hi) * 0.01, 1.0)
    lo -= pad; hi += pad
    plot_w, plot_h = width-left-right, height-top-bottom
    def xy(i, value):
        return left + plot_w*i/max(1, len(vals)-1), top + plot_h*(1-(value-lo)/(hi-lo))
    points = [xy(i,v) for i,v in enumerate(vals)]
    line = ' '.join(f'{x:.1f},{y:.1f}' for x,y in points)
    baseline = height-bottom
    area = ' '.join([f'{points[0][0]:.1f},{baseline:.1f}']+[f'{x:.1f},{y:.1f}' for x,y in points]+[f'{points[-1][0]:.1f},{baseline:.1f}'])
    grid_y = [top, top+plot_h/3, top+2*plot_h/3, baseline]
    grid = ''.join(f'<line x1="{left}" y1="{y:.1f}" x2="{width-right}" y2="{y:.1f}" class="chart-gridline"/>' for y in grid_y)
    ylabels = ''.join(f'<text x="{left-12}" y="{y+4:.1f}" text-anchor="end" class="chart-axis-label">{v:.2f} €</text>' for y,v in [(grid_y[0],hi),(grid_y[1],hi-(hi-lo)/3),(grid_y[2],hi-2*(hi-lo)/3),(grid_y[3],lo)])
    xlabels = ''
    for idx in sorted(set([0, (len(vals)-1)//3, 2*(len(vals)-1)//3, len(vals)-1])):
        x,_ = points[idx]; xlabels += f'<text x="{x:.1f}" y="{height-18}" text-anchor="middle" class="chart-axis-label">{idx+1}</text>'
    return f'<svg viewBox="0 0 {width} {height}" class="chart" role="img" aria-label="Portfolio-Wertentwicklung"><rect x="0" y="0" width="{width}" height="{height}" rx="14" class="chart-bg"/>{grid}{ylabels}{xlabels}<polygon points="{area}" class="chart-area"/><polyline points="{line}" class="chart-line" fill="none"/><circle cx="{points[-1][0]:.1f}" cy="{points[-1][1]:.1f}" r="6" class="chart-dot"/><text x="{left}" y="20" class="chart-title">Wertentwicklung</text><text x="{width-right}" y="20" text-anchor="end" class="chart-value">Aktuell {vals[-1]:.2f} €</text></svg>'

v67._chart = chart_v70

@app.get('/v70-health')
def v70_health():
    cfg = controller.settings()
    latest = controller.latest(20)
    return jsonify({'version':'0.1.0-dev.70','paper_market_batch':'legacy.current_market_batch','recent_failures':[dict(x) for x in latest if str(x['status']).upper()=='FAILED'],'automation_master_enabled':cfg.get('automation_master_enabled')=='true'})
