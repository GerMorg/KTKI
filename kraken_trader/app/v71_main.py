"""v71 runtime entrypoint: use the hardened v70 stack with shared automation boundaries."""
from flask import jsonify
import v70_main as base

app = base.app

@app.get('/v71-health')
def v71_health():
    controller = base.controller
    cfg = controller.settings()
    latest = controller.latest(20)
    return jsonify({
        'version': '0.1.0-dev.71',
        'runtime': 'v71_main',
        'paper_market_batch_source': 'legacy.current_market_batch',
        'automation_master_enabled': cfg.get('automation_master_enabled') == 'true',
        'recent_failures': [dict(x) for x in latest if str(x['status']).upper() == 'FAILED'],
    })
