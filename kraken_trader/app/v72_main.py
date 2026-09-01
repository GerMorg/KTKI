"""v72 runtime: observable research stages and fault-tolerant forecast processing."""
import json
import threading
import time
from flask import jsonify
import v71_main as base
from paper_engine import PaperEngine
from portfolio_allocator import PortfolioAllocator
from decision_matrix import DecisionMatrix
from execution_router import _find as _router_find

app = base.app
controller = base.base.controller
legacy = base.base.legacy


def _mapping(value, default=None):
    if isinstance(value, dict):
        return value
    if isinstance(value, list):
        mappings = [x for x in value if isinstance(x, dict)]
        if len(mappings) == 1:
            return mappings[0]
        return dict(default or {'status': 'COMPLETED', 'items': mappings})
    if value is None:
        return dict(default or {'status': 'COMPLETED'})
    return {'status': 'COMPLETED', 'value': value}


def _mapping_list(value):
    if isinstance(value, dict):
        return [value]
    if isinstance(value, list):
        out = []
        for item in value:
            if isinstance(item, dict):
                out.append(item)
            elif isinstance(item, list):
                out.extend(x for x in item if isinstance(x, dict))
        return out
    return []


# Final defensive payload boundary for the paper stack. These wrappers are intentionally
# installed in the v72 runtime so every possible paper caller receives mappings even
# when a legacy/third-party component unexpectedly returns a list.
_original_paper_execute = PaperEngine.execute
_original_allocator_plans = PortfolioAllocator.plans
_original_decision_evaluate = DecisionMatrix.evaluate
_original_router_find = _router_find


def _paper_execute_v72(self, symbol, side, gross, reason, decision):
    return _original_paper_execute(self, symbol, side, gross, reason, _mapping(decision, {'action': side}))


def _allocator_plans_v72(self, total):
    raw = _original_allocator_plans(self, total)
    return _mapping_list(raw)


def _decision_evaluate_v72(self, symbol, action, context, trade_context='PAPER'):
    return _original_decision_evaluate(self, symbol, action, _mapping(context, {}), trade_context)


def _router_find_v72(tickers, *keys):
    return _original_router_find(_mapping(tickers, {}), *keys)


PaperEngine.execute = _paper_execute_v72
PortfolioAllocator.plans = _allocator_plans_v72
DecisionMatrix.evaluate = _decision_evaluate_v72

_original_pipeline_start = controller.pipeline.start


def _record_finished_analysis(job_id):
    deadline = time.time() + 1800
    last = None
    while time.time() < deadline:
        rows = legacy.db.rows('SELECT id,status,stage,progress_current,progress_total,error,details_json,finished_at FROM research_jobs WHERE id=? LIMIT 1',(job_id,))
        if not rows:
            return
        row = _mapping(rows[0], {})
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
    result = _mapping(result)
    if result.get('job_id'):
        threading.Thread(target=_record_finished_analysis,args=(int(result['job_id']),),daemon=True,name='research-monitor-v72').start()
    return result

controller.pipeline.start = start_pipeline_v72


@app.get('/v72-health')
def v72_health():
    cfg = _mapping(controller.settings(), {})
    job = legacy.pipeline.latest()
    latest = _mapping_list(controller.latest(30))
    return jsonify({
        'version':'0.1.0-dev.72',
        'runtime':'v72_main',
        'paper_market_batch_source':'legacy.current_market_batch',
        'automation_master_enabled':str(cfg.get('automation_master_enabled','')).lower() == 'true',
        'latest_research':_mapping(job, {}) if job else None,
        'recent_analysis_failures':[x for x in latest if str(x.get('subsystem')).lower() == 'analysis' and str(x.get('status')).upper() == 'FAILED'][:10],
    })
