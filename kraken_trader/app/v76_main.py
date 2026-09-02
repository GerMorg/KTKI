"""v76 runtime: unified research failure quarantine and diagnostics."""
from flask import jsonify
import v75_main as base
from payload_utils import as_mapping, as_mapping_list

app = base.app
controller = base.controller
legacy = base.legacy

try:
    if getattr(legacy, 'forex_shadow', None) is not None:
        controller.pipeline.shadow = legacy.forex_shadow
except Exception:
    pass

@app.get('/v76-health')
def v76_health():
    cfg = as_mapping(controller.settings(), {})
    job = legacy.pipeline.latest()
    latest = as_mapping_list(controller.latest(50))
    failures = [x for x in latest if str(x.get('subsystem')).lower() == 'analysis' and str(x.get('status')).upper() == 'FAILED']
    quarantined = [x for x in latest if str(x.get('subsystem')).lower() == 'analysis' and 'QUARANTINED' in str(x.get('details_json') or '').upper()]
    return jsonify({
        'version': '0.1.0-dev.76',
        'runtime': 'v76_main',
        'research_payload_isolation': True,
        'research_shape_error_quarantine': True,
        'shared_forex_shadow': getattr(controller.pipeline, 'shadow', None) is not None,
        'latest_research': as_mapping(job, {}) if job else None,
        'recent_analysis_failures': failures[:10],
        'recent_shape_quarantines': quarantined[:10],
        'automation_master_enabled': str(cfg.get('automation_master_enabled', '')).lower() == 'true',
    })
