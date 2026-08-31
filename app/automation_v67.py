import json
import threading
from datetime import datetime, timezone, timedelta

from db import now

DEFAULTS = {
    'automation_master_enabled': 'false', 'automation_analysis_enabled': 'false',
    'automation_news_enabled': 'false', 'automation_learning_enabled': 'false',
    'automation_learning_auto_approve_enabled': 'false', 'automation_paper_enabled': 'false',
    'automation_real_enabled': 'false', 'automation_real_execute_enabled': 'false',
    'automation_tick_minutes': '5', 'automation_analysis_interval_minutes': '60',
    'automation_news_interval_minutes': '30', 'automation_learning_interval_minutes': '60',
    'automation_paper_interval_minutes': '15', 'automation_real_interval_minutes': '60',
    'analysis_top_per_category': '5', 'analysis_max_symbols': '20',
    'analysis_max_delay_seconds': '0.35', 'learning_max_evaluations': '600',
    'news_learning_max_samples': '600', 'news_local_eval_max_items': '1000',
    'forecast_due_batch_limit': '1000',
}


class AutomationControllerV67:
    """One persisted scheduler for all autonomous subsystems."""

    def __init__(self, db, pipeline, news_prefilter, controlled_learning,
                 news_learning, run_paper_cycle, real_allocator):
        self.db = db; self.pipeline = pipeline; self.news_prefilter = news_prefilter
        self.controlled_learning = controlled_learning; self.news_learning = news_learning
        self.run_paper_cycle = run_paper_cycle; self.real_allocator = real_allocator
        self.lock = threading.Lock(); self.stop_event = threading.Event(); self.ensure()

    def ensure(self):
        with self.db.con() as c:
            c.executescript("""
            CREATE TABLE IF NOT EXISTS automation_runs_v67(
              id INTEGER PRIMARY KEY AUTOINCREMENT, created_at TEXT NOT NULL,
              subsystem TEXT NOT NULL, status TEXT NOT NULL, automatic INTEGER NOT NULL,
              details_json TEXT NOT NULL, error TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_automation_runs_v67_subsystem
              ON automation_runs_v67(subsystem, id DESC);
            """)
        for key, value in DEFAULTS.items():
            if not self.db.rows('SELECT value FROM settings WHERE key=?', (key,)):
                self.db.set_setting(key, value)

    @staticmethod
    def _as_bool(value): return str(value).lower() == 'true'

    @staticmethod
    def _minutes(value, minimum=1):
        try: return max(minimum, int(float(value)))
        except (TypeError, ValueError): return minimum

    def settings(self): return {key: self.db.value(key, value) for key, value in DEFAULTS.items()}

    def enabled(self, subsystem):
        cfg = self.settings()
        return self._as_bool(cfg['automation_master_enabled']) and self._as_bool(cfg['automation_' + subsystem + '_enabled'])

    def _last_run(self, subsystem):
        rows = self.db.rows("SELECT created_at FROM automation_runs_v67 WHERE subsystem=? AND status IN ('COMPLETED','QUEUED','NOOP') ORDER BY id DESC LIMIT 1", (subsystem,))
        if not rows: return None
        try: return datetime.fromisoformat(rows[0]['created_at'].replace('Z', '+00:00'))
        except (TypeError, ValueError): return None

    def due(self, subsystem, interval_minutes):
        last = self._last_run(subsystem)
        return last is None or datetime.now(timezone.utc) - last >= timedelta(minutes=interval_minutes)

    def _record(self, subsystem, status, details=None, error=None):
        with self.db.con() as c:
            c.execute('INSERT INTO automation_runs_v67(created_at,subsystem,status,automatic,details_json,error) VALUES(?,?,?,?,?,?)',
                      (now(), subsystem, status, 1, json.dumps(details or {}, sort_keys=True, ensure_ascii=False, default=str), error))

    def _sync_legacy_flags(self, cfg):
        self.db.set('automation_enabled', 'true' if self._as_bool(cfg['automation_paper_enabled']) else 'false')
        self.db.set('real_balancing_enabled', 'true' if self._as_bool(cfg['automation_real_enabled']) else 'false')
        self.db.set('real_balancing_execute_enabled', 'true' if self._as_bool(cfg['automation_real_execute_enabled']) else 'false')
        self.db.set('real_balancing_dry_run', 'false' if self._as_bool(cfg['automation_real_execute_enabled']) else 'true')

    def _approve_pending(self):
        approved = []
        for active in self.controlled_learning.active_versions():
            family = active['family']
            for candidate in self.controlled_learning.candidates(family):
                if candidate.get('status') == 'PENDING':
                    approved.append({'kind': 'strategy', 'family': family, 'candidate_id': int(candidate['id']),
                                     'result': self.controlled_learning.decide(int(candidate['id']), 'approve')})
        for candidate in self.news_learning.candidates():
            if candidate.get('status') == 'PENDING':
                approved.append({'kind': 'news', 'candidate_id': int(candidate['id']),
                                 'result': self.news_learning.decide(int(candidate['id']), 'approve')})
        return approved

    def run_once(self, force=False):
        with self.lock:
            cfg = self.settings()
            # A manual 'run now' bypasses only the timer, never the master or
            # individual automation switches.
            if not self._as_bool(cfg['automation_master_enabled']):
                return {'status': 'DISABLED'}
            self._sync_legacy_flags(cfg); results = {}
            jobs = [('news', self._minutes(cfg['automation_news_interval_minutes'], 5)),
                    ('analysis', self._minutes(cfg['automation_analysis_interval_minutes'], 5)),
                    ('learning', self._minutes(cfg['automation_learning_interval_minutes'], 5)),
                    ('paper', self._minutes(cfg['automation_paper_interval_minutes'], 1)),
                    ('real', self._minutes(cfg['automation_real_interval_minutes'], 5))]
            for subsystem, interval in jobs:
                if not self.enabled(subsystem): continue
                if not force and not self.due(subsystem, interval): continue
                try:
                    if subsystem == 'news': result = self.news_prefilter.collect()
                    elif subsystem == 'analysis': result = self.pipeline.start()
                    elif subsystem == 'learning':
                        result = {'strategy': self.controlled_learning.propose_all(automatic=True),
                                  'news': self.news_learning.propose(automatic=True)}
                        if self._as_bool(cfg['automation_learning_auto_approve_enabled']):
                            result['auto_approved'] = self._approve_pending()
                    elif subsystem == 'paper': result = {'trades': self.run_paper_cycle()}
                    else: result = self.real_allocator.run(automatic=True)
                    results[subsystem] = result
                    status = 'QUEUED' if subsystem == 'analysis' and result.get('status') == 'QUEUED' else 'COMPLETED'
                    self._record(subsystem, status, result)
                except Exception as exc:
                    error = type(exc).__name__ + ': ' + str(exc)[:500]
                    results[subsystem] = {'status': 'FAILED', 'error': error}; self._record(subsystem, 'FAILED', results[subsystem], error)
                    self.db.audit('AUTOMATION_V67_FAILED', json.dumps({'subsystem': subsystem, 'error': error}, sort_keys=True), 'error')
            return {'status': 'COMPLETED', 'results': results, 'settings': cfg}

    def start(self):
        if self.stop_event.is_set(): return
        while not self.stop_event.wait(self._minutes(self.db.value('automation_tick_minutes', '5'), 1) * 60):
            try: self.run_once()
            except Exception as exc: self.db.audit('AUTOMATION_V67_TICK_FAILED', type(exc).__name__ + ': ' + str(exc)[:500], 'error')

    def start_background(self):
        if self.db.value('automation_v67_scheduler_disabled', 'false').lower() == 'true': return None
        thread = threading.Thread(target=self.start, daemon=True, name='automation-v67'); thread.start(); return thread

    def stop(self): self.stop_event.set()

    def latest(self, limit=30):
        return self.db.rows('SELECT * FROM automation_runs_v67 ORDER BY id DESC LIMIT ?', (max(1, min(200, int(limit))),))
