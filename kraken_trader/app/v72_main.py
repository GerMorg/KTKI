"""v72 runtime: observable research stages and fault-tolerant forecast processing."""
import json
import threading
import time
from flask import jsonify
import v71_main as base

app = base.app
controller = base.base.controller
legacy = base.base.legacy

_original_pipeline_start = controller.pipeline.start


def _record_finished_analysis(job_id):
    deadline = time.time() + 1800
    last = None
    while time.time() < deadline:
        rows = legacy.db.rows('SELECT id,status,stage,progress_current,progress_total,error,details_json,finished_at FROM research_jobs WHERE id=? LIMIT 1',(job_id,))
        if not rows:
            return
        row = rows[0]
        last = row
        status = str(row.get('status','')).upper()
        if status in ('FAILED','COMPLETED'):
            if status == 'FAILED':
                details = {'job_id':job_id,'stage':row.get('stage'),'progress':f"{row.get('progress_current')}/{row.get('progress_total')}",'error':row.get('error'),'details':row.get('details_json'),'finished_at':row.get('finished_at')}
                controller._record('analysis','FAILED',details,row.get('error'))
            return
        time.sleep(1.0)
    if last:
        details={'job_id':job_id,'stage':last.get('stage'),'progress':f"{last.get('progress_current')}/{last.get('progress_total')}",'error':'Analysis monitor timeout'}
        controller._record('analysis','FAILED',details,details['error'])


def start_pipeline_v72(*args, **kwargs):
    result = _original_pipeline_start(*args, **kwargs)
    if isinstance(result, dict) and result.get('job_id'):
        threading.Thread(target=_record_finished_analysis,args=(int(result['job_id']),),daemon=True,name='research-monitor-v72').start()
    return result

controller.pipeline.start = start_pipeline_v72


@app.get('/v72-health')
def v72_health():
    cfg = controller.settings()
    job = legacy.pipeline.latest()
    latest = controller.latest(30)
    return jsonify({
        'version':'0.1.0-dev.72',
        'runtime':'v72_main',
        'paper_market_batch_source':'legacy.current_market_batch',
        'automation_master_enabled':cfg.get('automation_master_enabled') == 'true',
        'latest_research':dict(job) if job else None,
        'recent_analysis_failures':[dict(x) for x in latest if x.get('subsystem') == 'analysis' and str(x.get('status')).upper() == 'FAILED'][:10],
    })
