"""v75 runtime: centralized research payload isolation and shared shadow services."""
from flask import jsonify
import v74_main as base
from payload_utils import as_mapping, as_mapping_list

app = base.app
controller = base.controller
legacy = base.legacy

try:
    if getattr(legacy, 'forex_shadow', None) is not None:
        controller.pipeline.shadow = legacy.forex_shadow
except Exception:
    pass

@app.get('/v75-health')
def v75_health():
    cfg = as_mapping(controller.settings(), {})
    job = legacy.pipeline.latest()
    latest = as_mapping_list(controller.latest(30))
    return jsonify({
        'version': '0.1.0-dev.75',
        'runtime': 'v75_main',
        'research_payload_isolation': True,
        'shared_forex_shadow': getattr(controller.pipeline, 'shadow', None) is not None,
        'known_unpack_errors_degrade': True,
        'latest_research': as_mapping(job, {}) if job else None,
        'recent_analysis_failures': [
            x for x in latest
            if str(x.get('subsystem')).lower() == 'analysis'
            and str(x.get('status')).upper() == 'FAILED'
        ][:10],
        'automation_master_enabled': str(cfg.get('automation_master_enabled', '')).lower() == 'true',
    })
