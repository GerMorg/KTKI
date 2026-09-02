"""v74 runtime: fail-soft deep scan and defensive external payload handling."""
import json
import threading
import time
from flask import jsonify
import v71_main as base
from payload_utils import as_mapping, as_mapping_list
from paper_engine import PaperEngine
from portfolio_allocator import PortfolioAllocator
from decision_matrix import DecisionMatrix
from scanner import MarketScanner
from forex_shadow import ForexShadow
import execution_router as execution_router_module

app = base.app
controller = base.base.controller
legacy = base.base.legacy
_original_paper_execute = PaperEngine.execute
_original_allocator_plans = PortfolioAllocator.plans
_original_decision_evaluate = DecisionMatrix.evaluate
_original_router_find = execution_router_module._find
_original_scanner_run = MarketScanner.run
_original_shadow_run = ForexShadow.run

def _paper_execute_v74(self, symbol, side, gross, reason, decision):
    return _original_paper_execute(self, symbol, side, gross, reason, as_mapping(decision, {'action': side}))

def _allocator_plans_v74(self, total):
    return as_mapping_list(_original_allocator_plans(self, total))

def _decision_evaluate_v74(self, symbol, action, context, trade_context='PAPER'):
    return _original_decision_evaluate(self, symbol, action, as_mapping(context, {}), trade_context)

def _router_find_v74(tickers, *keys):
    return _original_router_find(as_mapping(tickers, {}), *keys)

def _scanner_run_v74(self, symbols, interval=60, limit=None, delay_seconds=None):
    safe_symbols = list(symbols or [])
    try:
        return as_mapping(_original_scanner_run(self, safe_symbols, interval, limit, delay_seconds), {'status': 'COMPLETED', 'processed': 0})
    except Exception as exc:
        error = type(exc).__name__ + ': ' + str(exc)[:500]
        try:
            self.db.audit('DEEP_SCAN_DEGRADED', json.dumps({'error': error, 'symbols': len(safe_symbols)}, sort_keys=True), 'error')
        except Exception:
            pass
        return {'status': 'DEGRADED', 'processed': 0, 'error': error, 'results': []}

def _shadow_run_v74(self, symbols=None):
    safe_symbols = list(symbols or [])
    try:
        return as_mapping(_original_shadow_run(self, safe_symbols), {'status': 'SHADOW_ONLY', 'snapshots': 0, 'symbols': 0})
    except Exception as exc:
        error = type(exc).__name__ + ': ' + str(exc)[:500]
        try:
            self.db.audit('FOREX_SHADOW_DEGRADED', json.dumps({'error': error, 'symbols': len(safe_symbols)}, sort_keys=True), 'error')
        except Exception:
            pass
        return {'status': 'DEGRADED', 'snapshots': 0, 'symbols': 0, 'error': error}

PaperEngine.execute = _paper_execute_v74
PortfolioAllocator.plans = _allocator_plans_v74
DecisionMatrix.evaluate = _decision_evaluate_v74
execution_router_module._find = _router_find_v74
MarketScanner.run = _scanner_run_v74
ForexShadow.run = _shadow_run_v74
_original_pipeline_start = controller.pipeline.start

def _record_finished_analysis(job_id):
    deadline = time.time() + 1800
    last = None
    while time.time() < deadline:
        rows = legacy.db.rows('SELECT id,status,stage,progress_current,progress_total,error,details_json,finished_at FROM research_jobs WHERE id=? LIMIT 1', (job_id,))
        if not rows:
            return
        row = as_mapping(rows[0], {})
        last = row
        status = str(row.get('status', '')).upper()
        if status in ('FAILED', 'COMPLETED'):
            if status == 'FAILED':
                details = {'job_id': job_id, 'stage': row.get('stage'), 'progress': f"{row.get('progress_current')}/{row.get('progress_total')}", 'error': row.get('error'), 'details': row.get('details_json'), 'finished_at': row.get('finished_at')}
                controller._record('analysis', 'FAILED', details, row.get('error'))
            return
        time.sleep(1.0)
    if last:
        details = {'job_id': job_id, 'stage': last.get('stage'), 'progress': f"{last.get('progress_current')}/{last.get('progress_total')}", 'error': 'Analysis monitor timeout'}
        controller._record('analysis', 'FAILED', details, details['error'])

def start_pipeline_v74(*args, **kwargs):
    result = as_mapping(_original_pipeline_start(*args, **kwargs))
    if result.get('job_id'):
        threading.Thread(target=_record_finished_analysis, args=(int(result['job_id']),), daemon=True, name='research-monitor-v74').start()
    return result

controller.pipeline.start = start_pipeline_v74

@app.get('/v74-health')
def v74_health():
    cfg = as_mapping(controller.settings(), {})
    job = legacy.pipeline.latest()
    latest = as_mapping_list(controller.latest(30))
    return jsonify({'version': '0.1.0-dev.74', 'runtime': 'v74_main', 'deep_scan_fail_soft': True, 'sqlite_journal_mode': 'WAL', 'sqlite_busy_timeout_ms': 30000, 'latest_research': as_mapping(job, {}) if job else None, 'recent_analysis_failures': [x for x in latest if str(x.get('subsystem')).lower() == 'analysis' and str(x.get('status')).upper() == 'FAILED'][:10], 'automation_master_enabled': str(cfg.get('automation_master_enabled', '')).lower() == 'true'})
