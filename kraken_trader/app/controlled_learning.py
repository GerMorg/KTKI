import hashlib
import json
import math
from db import now
from strategy_profiles import FAMILIES, BOUNDS, score_features

GATE_DEFAULTS = {
    'required_horizons': [24, 168],
    'minimum_horizon_samples': 5,
    'minimum_candidate_coverage': 0.50,
    'minimum_net_return_improvement': 0.01,
    'maximum_candidate_drawdown_pct': -25.0,
    'maximum_drawdown_degradation_pct': 2.0,
}


class ControlledLearning:
    def __init__(self, db):
        self.db = db
        self.ensure()

    def ensure(self):
        with self.db.con() as c:
            c.executescript("""
            CREATE TABLE IF NOT EXISTS parameter_family_versions(
                id INTEGER PRIMARY KEY AUTOINCREMENT, created_at TEXT NOT NULL,
                family TEXT NOT NULL, version INTEGER NOT NULL, status TEXT NOT NULL,
                parameters_json TEXT NOT NULL, parent_version INTEGER,
                source TEXT NOT NULL, reason TEXT NOT NULL, UNIQUE(family,version));
            CREATE TABLE IF NOT EXISTS learning_candidates(
                id INTEGER PRIMARY KEY AUTOINCREMENT, created_at TEXT NOT NULL,
                family TEXT NOT NULL, status TEXT NOT NULL, base_version INTEGER NOT NULL,
                sample_count INTEGER NOT NULL, active_accuracy TEXT NOT NULL,
                candidate_accuracy TEXT NOT NULL, improvement TEXT NOT NULL,
                ci_low TEXT NOT NULL, ci_high TEXT NOT NULL, parameters_json TEXT NOT NULL,
                reason TEXT NOT NULL, decided_at TEXT);
            CREATE TABLE IF NOT EXISTS learning_shadow_results(
                id INTEGER PRIMARY KEY AUTOINCREMENT, created_at TEXT NOT NULL,
                candidate_id INTEGER NOT NULL, forecast_id INTEGER NOT NULL,
                active_correct INTEGER NOT NULL, candidate_correct INTEGER NOT NULL,
                details_json TEXT NOT NULL, UNIQUE(candidate_id,forecast_id));
            CREATE TABLE IF NOT EXISTS learning_candidate_metrics(
                candidate_id INTEGER NOT NULL, horizon_hours INTEGER NOT NULL,
                sample_count INTEGER NOT NULL, active_decisions INTEGER NOT NULL,
                candidate_decisions INTEGER NOT NULL, active_coverage TEXT NOT NULL,
                candidate_coverage TEXT NOT NULL, active_net_return TEXT NOT NULL,
                candidate_net_return TEXT NOT NULL, net_return_improvement TEXT NOT NULL,
                active_max_drawdown TEXT NOT NULL, candidate_max_drawdown TEXT NOT NULL,
                details_json TEXT NOT NULL, PRIMARY KEY(candidate_id,horizon_hours));
            """)
            cols = {x['name'] for x in self.db.rows('PRAGMA table_info(learning_candidates)')}
            for name, definition in (
                ('gate_policy_json', "TEXT NOT NULL DEFAULT '{}'"),
                ('gate_results_json', "TEXT NOT NULL DEFAULT '[]'"),
                ('validation_fingerprint', "TEXT NOT NULL DEFAULT ''"),
            ):
                if name not in cols:
                    c.execute(f'ALTER TABLE learning_candidates ADD COLUMN {name} {definition}')
            for family, params in FAMILIES.items():
                c.execute(
                    'INSERT OR IGNORE INTO parameter_family_versions(created_at,family,version,status,parameters_json,parent_version,source,reason) VALUES(?,?,1,?,?,NULL,?,?)',
                    (now(), family, 'ACTIVE', json.dumps(params, sort_keys=True), 'DEFAULT', 'Deterministische Ausgangsversion'))
        self._migrate_legacy_xstocks()

    def _migrate_legacy_xstocks(self):
        try:
            rows = self.db.rows("SELECT name,value,version FROM strategy_parameters WHERE name LIKE 'xstocks_%'")
        except Exception:
            return
        if not rows:
            return
        current = self.active('xstocks')
        params = json.loads(current['parameters_json'])
        mapping = {x['name'].removeprefix('xstocks_'): float(x['value']) for x in rows}
        params.update({k: v for k, v in mapping.items() if k in params})
        if params == json.loads(current['parameters_json']):
            return
        with self.db.con() as c:
            c.execute('UPDATE parameter_family_versions SET parameters_json=?,source=?,reason=? WHERE id=?',
                      (json.dumps(params, sort_keys=True), 'LEGACY_MIGRATION',
                       'Übernahme der vorhandenen xStock-Parameter', current['id']))

    @staticmethod
    def _wilson(successes, n, z=1.96):
        if not n:
            return 0.0, 1.0
        p = successes / n
        d = 1 + z * z / n
        center = (p + z * z / (2 * n)) / d
        margin = z * math.sqrt((p * (1 - p) + z * z / (4 * n)) / n) / d
        return max(0, center - margin), min(1, center + margin)

    def active(self, family):
        rows = self.db.rows(
            "SELECT * FROM parameter_family_versions WHERE family=? AND status='ACTIVE' ORDER BY version DESC LIMIT 1",
            (family,))
        return rows[0] if rows else None

    def active_versions(self):
        return [active for family in FAMILIES if (active := self.active(family))]

    def family_overview(self):
        result = []
        for family in FAMILIES:
            active = self.active(family)
            counts = {row['status']: row['n'] for row in self.db.rows(
                'SELECT status,COUNT(*) AS n FROM learning_candidates WHERE family=? GROUP BY status', (family,))}
            latest = self.db.rows(
                'SELECT id,status,created_at,decided_at FROM learning_candidates WHERE family=? ORDER BY id DESC LIMIT 1', (family,))
            result.append({
                'family': family,
                'active_version': active['version'] if active else None,
                'pending_count': int(counts.get('PENDING', 0)),
                'approved_count': int(counts.get('APPROVED', 0)),
                'rejected_count': int(counts.get('REJECTED', 0)),
                'latest_candidate_id': latest[0]['id'] if latest else None,
                'latest_status': latest[0]['status'] if latest else 'NONE',
                'latest_created_at': latest[0]['created_at'] if latest else None,
                'latest_decided_at': latest[0]['decided_at'] if latest else None,
            })
        return result

    def _required_horizons(self):
        raw = self.db.value('learning_required_horizons', '24,168')
        try:
            values = sorted({int(x.strip()) for x in str(raw).split(',') if x.strip()})
        except ValueError:
            values = list(GATE_DEFAULTS['required_horizons'])
        return values or list(GATE_DEFAULTS['required_horizons'])

    def gate_policy(self):
        def number(key, default, cast=float):
            try:
                return cast(float(self.db.value(key, str(default))))
            except (TypeError, ValueError):
                return cast(default)
        return {
            'required_horizons': self._required_horizons(),
            'minimum_horizon_samples': max(1, number('learning_min_horizon_samples', GATE_DEFAULTS['minimum_horizon_samples'], int)),
            'minimum_candidate_coverage': min(1.0, max(0.0, number('learning_min_candidate_coverage', GATE_DEFAULTS['minimum_candidate_coverage']))),
            'minimum_net_return_improvement': number('learning_min_net_return_improvement', GATE_DEFAULTS['minimum_net_return_improvement']),
            'maximum_candidate_drawdown_pct': min(0.0, number('learning_max_candidate_drawdown_pct', GATE_DEFAULTS['maximum_candidate_drawdown_pct'])),
            'maximum_drawdown_degradation_pct': max(0.0, number('learning_max_drawdown_degradation_pct', GATE_DEFAULTS['maximum_drawdown_degradation_pct'])),
        }

    def _gate_results(self, metrics, accuracy_improvement, minimum_accuracy_improvement, policy=None):
        policy = policy or self.gate_policy()
        by_horizon = {int(x['horizon_hours']): x for x in metrics}
        results = [{
            'gate': 'ACCURACY_IMPROVEMENT', 'horizon_hours': None,
            'passed': accuracy_improvement >= minimum_accuracy_improvement,
            'actual': accuracy_improvement, 'required': minimum_accuracy_improvement,
        }]
        for horizon in policy['required_horizons']:
            metric = by_horizon.get(int(horizon))
            results.append({'gate': 'HORIZON_PRESENT', 'horizon_hours': horizon,
                            'passed': metric is not None, 'actual': metric is not None, 'required': True})
            if metric is None:
                continue
            sample_count = int(metric['sample_count'])
            coverage = float(metric['candidate_coverage'])
            net_improvement = float(metric['net_return_improvement'])
            candidate_dd = float(metric['candidate_max_drawdown'])
            active_dd = float(metric['active_max_drawdown'])
            checks = (
                ('MINIMUM_HORIZON_SAMPLE', sample_count >= policy['minimum_horizon_samples'], sample_count, policy['minimum_horizon_samples']),
                ('MINIMUM_CANDIDATE_COVERAGE', coverage >= policy['minimum_candidate_coverage'], coverage, policy['minimum_candidate_coverage']),
                ('POSITIVE_NET_RETURN_IMPROVEMENT', net_improvement >= policy['minimum_net_return_improvement'], net_improvement, policy['minimum_net_return_improvement']),
                ('MAXIMUM_CANDIDATE_DRAWDOWN', candidate_dd >= policy['maximum_candidate_drawdown_pct'], candidate_dd, policy['maximum_candidate_drawdown_pct']),
                ('MAXIMUM_DRAWDOWN_DEGRADATION', candidate_dd >= active_dd - policy['maximum_drawdown_degradation_pct'], candidate_dd - active_dd, -policy['maximum_drawdown_degradation_pct']),
            )
            for gate, passed, actual, required in checks:
                results.append({'gate': gate, 'horizon_hours': horizon, 'passed': bool(passed), 'actual': actual, 'required': required})
        return results

    @staticmethod
    def _gates_pass(results):
        return bool(results) and all(x['passed'] for x in results)

    def _evaluations(self, family):
        cols = {x['name'] for x in self.db.rows('PRAGMA table_info(research_forecasts)')}
        features = 'f.features_json' if 'features_json' in cols else "'{}' AS features_json"
        horizon = 'f.horizon_hours' if 'horizon_hours' in cols else '0 AS horizon_hours'
        return self.db.rows(
            f"SELECT f.id,f.direction,f.scanner_score,{features},{horizon},e.direction_correct,e.actual_return_pct "
            f"FROM forecast_evaluations e JOIN research_forecasts f ON f.id=e.forecast_id "
            f"JOIN market_universe u ON u.symbol=f.symbol WHERE u.category=? ORDER BY f.id", (family,))

    def _rows_for_ids(self, ids, family):
        if not ids:
            return []
        rows = self._evaluations(family)
        wanted = set(int(x) for x in ids)
        by_id = {int(row['id']): row for row in rows}
        return [by_id[x] for x in ids if int(x) in wanted and int(x) in by_id]

    @staticmethod
    def _sample_fingerprint(rows):
        payload = []
        for row in rows:
            payload.append((
                int(row['id']), str(row.get('direction') or ''), int(row.get('horizon_hours') or 0),
                str(row.get('actual_return_pct') if row.get('actual_return_pct') is not None else ''),
                str(row.get('features_json') or '{}'),
            ))
        return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()).hexdigest()

    @staticmethod
    def _strategy_return(signal, actual, cost_rate):
        if signal == 'BUY':
            return actual - cost_rate
        if signal == 'AVOID':
            return -actual - cost_rate
        return 0.0

    def _shadow(self, rows, active_params, candidate_params):
        shadow = []
        for row in rows:
            try:
                features = json.loads(row.get('features_json') or '{}')
            except Exception:
                features = {}
            if not isinstance(features, dict):
                features = {}
            if not {'momentum_pct', 'trend_pct', 'volatility_pct', 'spread_pct'}.issubset(features):
                up = row.get('direction') == 'UP'
                features = {'momentum_pct': 1 if up else -1, 'trend_pct': 1 if up else -1,
                            'volatility_pct': 0, 'spread_pct': 0}
            _, active_signal = score_features(features, active_params)
            _, candidate_signal = score_features(features, candidate_params)
            actual = float(row.get('actual_return_pct') or 0)
            cost_rate = float(features.get('estimated_roundtrip_cost_pct') or features.get('estimated_cost_pct') or 0)
            def correct(signal):
                return int((signal == 'BUY' and actual > 0) or (signal == 'AVOID' and actual < 0) or
                           (signal == 'HOLD' and abs(actual) < 1))
            a, c = correct(active_signal), correct(candidate_signal)
            shadow.append((row['id'], a, c, {
                'active_signal': active_signal, 'candidate_signal': candidate_signal,
                'actual_return_pct': actual, 'horizon_hours': int(row.get('horizon_hours') or 0),
                'estimated_cost_pct': cost_rate,
                'active_return_after_costs_pct': self._strategy_return(active_signal, actual, cost_rate),
                'candidate_return_after_costs_pct': self._strategy_return(candidate_signal, actual, cost_rate),
            }))
        return shadow

    def _metrics(self, shadow):
        grouped = {}
        for item in shadow:
            grouped.setdefault(int(item[3].get('horizon_hours') or 0), []).append(item)
        out = []
        for horizon, items in sorted(grouped.items()):
            n = len(items)
            active_returns = [x[3]['active_return_after_costs_pct'] for x in items]
            candidate_returns = [x[3]['candidate_return_after_costs_pct'] for x in items]
            def drawdown(values):
                equity = peak = 1.0
                worst = 0.0
                for value in values:
                    equity *= max(.000001, 1 + value / 100)
                    peak = max(peak, equity)
                    worst = min(worst, equity / peak - 1)
                return worst * 100
            active_decisions = sum(x[3]['active_signal'] != 'HOLD' for x in items)
            candidate_decisions = sum(x[3]['candidate_signal'] != 'HOLD' for x in items)
            active_hits = sum(x[1] for x in items if x[3]['active_signal'] != 'HOLD')
            candidate_hits = sum(x[2] for x in items if x[3]['candidate_signal'] != 'HOLD')
            active_low, active_high = self._wilson(active_hits, active_decisions)
            candidate_low, candidate_high = self._wilson(candidate_hits, candidate_decisions)
            active_net = sum(active_returns)
            candidate_net = sum(candidate_returns)
            out.append({
                'horizon_hours': horizon, 'sample_count': n,
                'active_decisions': active_decisions, 'candidate_decisions': candidate_decisions,
                'active_hits': active_hits, 'candidate_hits': candidate_hits,
                'active_coverage': active_decisions / n, 'candidate_coverage': candidate_decisions / n,
                'active_accuracy_raw': active_hits / active_decisions if active_decisions else None,
                'candidate_accuracy_raw': candidate_hits / candidate_decisions if candidate_decisions else None,
                'active_accuracy_robust_low': active_low, 'candidate_accuracy_robust_low': candidate_low,
                'candidate_accuracy_robust_high': candidate_high,
                'accuracy_improvement': candidate_low - active_low,
                'active_net_return': active_net, 'candidate_net_return': candidate_net,
                'net_return_improvement': candidate_net - active_net,
                'active_max_drawdown': drawdown(active_returns),
                'candidate_max_drawdown': drawdown(candidate_returns),
            })
        return out

    def _score_parameter_set(self, params, rows):
        returns = []
        decided = hits = 0
        for row in rows:
            try:
                features = json.loads(row.get('features_json') or '{}')
            except Exception:
                features = {}
            if not isinstance(features, dict):
                features = {}
            if not {'momentum_pct', 'trend_pct', 'volatility_pct', 'spread_pct'}.issubset(features):
                up = row.get('direction') == 'UP'
                features = {'momentum_pct': 1 if up else -1, 'trend_pct': 1 if up else -1,
                            'volatility_pct': 0, 'spread_pct': 0}
            _, signal = score_features(features, params)
            actual = float(row.get('actual_return_pct') or 0)
            cost = float(features.get('estimated_roundtrip_cost_pct') or features.get('estimated_cost_pct') or 0)
            returns.append(self._strategy_return(signal, actual, cost))
            if signal != 'HOLD':
                decided += 1
                hits += int((signal == 'BUY' and actual > 0) or (signal == 'AVOID' and actual < 0))
        coverage = decided / max(1, len(rows))
        low = self._wilson(hits, decided)[0] if decided else 0.0
        return {'objective': sum(returns) + 5 * low + min(1.0, coverage), 'net_return': sum(returns),
                'decisions': decided, 'hits': hits, 'coverage': coverage,
                'hit_rate_raw': hits / decided if decided else None, 'hit_rate_robust': low}

    def _candidate(self, family, params, rows):
        """Deterministic coordinate search over the provided training rows only."""
        steps = {'base_score': .5, 'momentum_weight': .2, 'trend_weight': .5,
                 'volatility_penalty': .1, 'spread_penalty': 1.0, 'buy_threshold': 1.0,
                 'buy_max_spread_pct': .05, 'avoid_threshold': .5, 'avoid_spread_pct': .1}
        best = dict(params)
        best_eval = self._score_parameter_set(best, rows)
        evaluated = 1
        for _ in range(8):
            improved = False
            for name, step in steps.items():
                for direction in (-1, 1):
                    trial = dict(best)
                    lo, hi = BOUNDS[family][name]
                    trial[name] = round(max(lo, min(hi, float(best[name]) + step * direction)), 4)
                    ev = self._score_parameter_set(trial, rows)
                    evaluated += 1
                    if ev['objective'] > best_eval['objective'] + 1e-12:
                        best, best_eval, improved = trial, ev, True
            if not improved:
                break
        self._last_search_details = {'algorithm': 'coordinate_search_v58', 'evaluated': evaluated,
                                     'training_count': len(rows), 'best': best_eval}
        return best

    def propose(self, family, min_sample=10, min_improvement=.02):
        if family not in FAMILIES:
            return {'status': 'UNKNOWN_FAMILY'}
        rows = self._evaluations(family)
        total = len(rows)
        if total < min_sample:
            return {'status': 'INSUFFICIENT_DATA', 'sample_count': total, 'required': min_sample}
        active = self.active(family)
        if not active:
            return {'status': 'NO_ACTIVE_VERSION'}
        active_params = json.loads(active['parameters_json'])
        policy = self.gate_policy()
        minimum_validation = max(3, int(self.db.value('learning_min_validation_samples', '5')),
                                 len(policy['required_horizons']) * int(policy['minimum_horizon_samples']))
        validation_count = max(minimum_validation, int(math.ceil(total * .30)))
        if validation_count >= total:
            return {'status': 'INSUFFICIENT_TRAINING', 'sample_count': total,
                    'required_validation': minimum_validation, 'training_count': max(0, total - validation_count),
                    'validation_count': validation_count}
        ordered = list(rows)
        training_rows = ordered[:-validation_count]
        validation_rows = ordered[-validation_count:]
        candidate = self._candidate(family, active_params, training_rows)
        if candidate == active_params:
            return {'status': 'NO_PARAMETER_CHANGE', 'sample_count': total, 'training_count': len(training_rows),
                    'validation_count': len(validation_rows), 'base_version': active['version']}
        shadow = self._shadow(validation_rows, active_params, candidate)
        metrics = self._metrics(shadow)
        active_decisions = sum(x[3]['active_signal'] != 'HOLD' for x in shadow)
        candidate_decisions = sum(x[3]['candidate_signal'] != 'HOLD' for x in shadow)
        active_correct = sum(x[1] for x in shadow if x[3]['active_signal'] != 'HOLD')
        candidate_correct = sum(x[2] for x in shadow if x[3]['candidate_signal'] != 'HOLD')
        active_accuracy = self._wilson(active_correct, active_decisions)[0] if active_decisions else 0.0
        candidate_accuracy = self._wilson(candidate_correct, candidate_decisions)[0] if candidate_decisions else 0.0
        improvement = candidate_accuracy - active_accuracy
        gates = self._gate_results(metrics, improvement, min_improvement, policy)
        status = 'PENDING' if self._gates_pass(gates) else 'REJECTED_GATE'
        reason = 'Alle Freigabe-Gates erfüllt; ausdrückliche Freigabe erforderlich' if status == 'PENDING' else 'Mindestens ein Freigabe-Gate wurde nicht erfüllt'
        validation_fingerprint = self._sample_fingerprint(validation_rows)
        with self.db.con() as c:
            cur = c.execute(
                'INSERT INTO learning_candidates(created_at,family,status,base_version,sample_count,active_accuracy,candidate_accuracy,improvement,ci_low,ci_high,parameters_json,reason,decided_at,gate_policy_json,gate_results_json,validation_fingerprint) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                (now(), family, status, active['version'], len(validation_rows), str(active_accuracy), str(candidate_accuracy),
                 str(improvement), str(self._wilson(candidate_correct, candidate_decisions)[0]),
                 str(self._wilson(candidate_correct, candidate_decisions)[1] if candidate_decisions else 0.0),
                 json.dumps(candidate, sort_keys=True), reason, None if status == 'PENDING' else now(),
                 json.dumps(policy, sort_keys=True), json.dumps(gates, sort_keys=True), validation_fingerprint))
            candidate_id = cur.lastrowid
            c.executemany(
                'INSERT INTO learning_shadow_results(created_at,candidate_id,forecast_id,active_correct,candidate_correct,details_json) VALUES(?,?,?,?,?,?)',
                [(now(), candidate_id, fid, a, cc, json.dumps(details, sort_keys=True)) for fid, a, cc, details in shadow])
            c.executemany(
                'INSERT INTO learning_candidate_metrics(candidate_id,horizon_hours,sample_count,active_decisions,candidate_decisions,active_coverage,candidate_coverage,active_net_return,candidate_net_return,net_return_improvement,active_max_drawdown,candidate_max_drawdown,details_json) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)',
                [(candidate_id, m['horizon_hours'], m['sample_count'], m['active_decisions'], m['candidate_decisions'],
                  str(m['active_coverage']), str(m['candidate_coverage']), str(m['active_net_return']),
                  str(m['candidate_net_return']), str(m['net_return_improvement']), str(m['active_max_drawdown']),
                  str(m['candidate_max_drawdown']), json.dumps(m, sort_keys=True)) for m in metrics])
        self.db.audit('CONTROLLED_LEARNING_CANDIDATE', json.dumps({
            'candidate_id': candidate_id, 'family': family, 'status': status,
            'training_count': len(training_rows), 'validation_count': len(validation_rows),
            'improvement': improvement, 'validation_fingerprint': validation_fingerprint,
            'gates': gates}, sort_keys=True))
        return {'status': status, 'candidate_id': candidate_id, 'sample_count': len(validation_rows),
                'total_sample_count': total, 'training_count': len(training_rows), 'validation_count': len(validation_rows),
                'improvement': improvement, 'ci': [self._wilson(candidate_correct, candidate_decisions)[0],
                                                     self._wilson(candidate_correct, candidate_decisions)[1] if candidate_decisions else 0.0],
                'metrics': metrics, 'gate_policy': policy, 'gate_results': gates,
                'validation_fingerprint': validation_fingerprint}

    def propose_all(self, automatic=True, min_sample=10, min_improvement=.02):
        return {'status': 'COMPLETED', 'automatic': bool(automatic),
                'families': {family: self.propose(family, min_sample, min_improvement) for family in FAMILIES}}

    def decide(self, candidate_id, action):
        rows = self.db.rows('SELECT * FROM learning_candidates WHERE id=?', (candidate_id,))
        if not rows:
            return {'status': 'NOT_FOUND'}
        proposal = rows[0]
        if proposal['status'] != 'PENDING':
            return {'status': 'NOT_PENDING'}
        current = self.active(proposal['family'])
        if not current or int(current['version']) != int(proposal['base_version']):
            with self.db.con() as c:
                c.execute("UPDATE learning_candidates SET status='STALE',decided_at=? WHERE id=?", (now(), candidate_id))
            return {'status': 'STALE'}
        if action == 'reject':
            with self.db.con() as c:
                c.execute("UPDATE learning_candidates SET status='REJECTED',decided_at=? WHERE id=?", (now(), candidate_id))
            self.db.audit('CONTROLLED_LEARNING_REJECTED', str(candidate_id))
            return {'status': 'REJECTED'}
        if action != 'approve':
            return {'status': 'INVALID_ACTION'}
        try:
            params = json.loads(proposal['parameters_json'])
        except Exception:
            return {'status': 'INVALID_PARAMETER_SET'}
        if set(params) != set(FAMILIES[proposal['family']]):
            return {'status': 'INVALID_PARAMETER_SET'}
        for name, value in params.items():
            lo, hi = BOUNDS[proposal['family']][name]
            if not lo <= float(value) <= hi:
                return {'status': 'OUT_OF_BOUNDS', 'parameter': name}
        stored_ids = [int(x['forecast_id']) for x in self.db.rows(
            'SELECT forecast_id FROM learning_shadow_results WHERE candidate_id=? ORDER BY id', (candidate_id,))]
        validation_rows = self._rows_for_ids(stored_ids, proposal['family'])
        if len(validation_rows) != len(stored_ids):
            return self._block_recheck(candidate_id, 'VALIDATION_SAMPLE_MISSING')
        fingerprint = self._sample_fingerprint(validation_rows)
        if not proposal.get('validation_fingerprint') or fingerprint != proposal['validation_fingerprint']:
            return self._block_recheck(candidate_id, 'VALIDATION_SAMPLE_CHANGED', {'sample_unchanged': False})
        policy = self.gate_policy()
        active_params = json.loads(current['parameters_json'])
        shadow = self._shadow(validation_rows, active_params, params)
        metrics = self._metrics(shadow)
        stored_gates = json.loads(proposal.get('gate_results_json') or '[]')
        required_accuracy = float(next((x.get('required') for x in stored_gates if x.get('gate') == 'ACCURACY_IMPROVEMENT'), .02))
        gate_results = self._gate_results(metrics, float(proposal['improvement']), required_accuracy, policy)
        if not self._gates_pass(gate_results):
            return self._block_recheck(candidate_id, 'GATE_RECHECK_FAILED', {'gate_results': gate_results})
        new_version = int(current['version']) + 1
        with self.db.con() as c:
            c.execute("UPDATE parameter_family_versions SET status='SUPERSEDED' WHERE family=? AND status='ACTIVE'", (proposal['family'],))
            c.execute(
                'INSERT INTO parameter_family_versions(created_at,family,version,status,parameters_json,parent_version,source,reason) VALUES(?,?,?,?,?,?,?,?)',
                (now(), proposal['family'], new_version, 'ACTIVE', proposal['parameters_json'], current['version'],
                 f'APPROVED_CANDIDATE_{candidate_id}', 'Explizite Benutzerfreigabe nach erneuter identischer Schattenprüfung'))
            c.execute("UPDATE learning_candidates SET status='APPROVED',decided_at=?,gate_policy_json=?,gate_results_json=? WHERE id=?",
                      (now(), json.dumps(policy, sort_keys=True), json.dumps(gate_results, sort_keys=True), candidate_id))
        self.db.audit('CONTROLLED_LEARNING_APPROVED', json.dumps({'candidate_id': candidate_id,
                      'family': proposal['family'], 'version': new_version, 'validation_fingerprint': fingerprint,
                      'gates': gate_results}, sort_keys=True))
        return {'status': 'APPROVED', 'version': new_version, 'gate_results': gate_results}

    def _block_recheck(self, candidate_id, reason, extra=None):
        payload = {'candidate_id': candidate_id, 'reason': reason}
        if extra:
            payload.update(extra)
        with self.db.con() as c:
            c.execute("UPDATE learning_candidates SET status='REJECTED_RECHECK',decided_at=?,reason=? WHERE id=?",
                      (now(), 'Freigabe bei erneuter Prüfung blockiert: ' + reason, candidate_id))
        self.db.audit('CONTROLLED_LEARNING_APPROVAL_BLOCKED', json.dumps(payload, sort_keys=True), 'warning')
        return {'status': 'REJECTED_RECHECK', 'reason': reason, **(extra or {})}

    def rollback(self, family, target_version):
        target = self.db.rows('SELECT * FROM parameter_family_versions WHERE family=? AND version=?', (family, target_version))
        current = self.active(family)
        if not target or not current:
            return {'status': 'NOT_FOUND'}
        next_version = int(current['version']) + 1
        with self.db.con() as c:
            c.execute("UPDATE parameter_family_versions SET status='SUPERSEDED' WHERE family=? AND status='ACTIVE'", (family,))
            c.execute('INSERT INTO parameter_family_versions(created_at,family,version,status,parameters_json,parent_version,source,reason) VALUES(?,?,?,?,?,?,?,?)',
                      (now(), family, next_version, 'ACTIVE', target[0]['parameters_json'], current['version'],
                       f'ROLLBACK_TO_{target_version}', 'Vollständiger kontrollierter Rollback'))
        self.db.audit('CONTROLLED_LEARNING_ROLLBACK', json.dumps({'family': family,
                      'target_version': target_version, 'new_version': next_version}))
        return {'status': 'ROLLED_BACK', 'version': next_version}

    def candidates(self, family=None):
        if family is None:
            return self.db.rows('SELECT * FROM learning_candidates ORDER BY id DESC LIMIT 100')
        return self.db.rows('SELECT * FROM learning_candidates WHERE family=? ORDER BY id DESC LIMIT 100', (family,))

    def metrics(self, candidate_id=None, family=None):
        if candidate_id is not None:
            return self.db.rows('SELECT * FROM learning_candidate_metrics WHERE candidate_id=? ORDER BY candidate_id DESC,horizon_hours', (candidate_id,))
        if family is not None:
            return self.db.rows('SELECT m.* FROM learning_candidate_metrics m JOIN learning_candidates c ON c.id=m.candidate_id WHERE c.family=? ORDER BY m.candidate_id DESC,m.horizon_hours', (family,))
        return self.db.rows('SELECT * FROM learning_candidate_metrics ORDER BY candidate_id DESC,horizon_hours')

    def versions(self, family=None):
        if family is None:
            return self.db.rows('SELECT * FROM parameter_family_versions ORDER BY family,version DESC')
        return self.db.rows('SELECT * FROM parameter_family_versions WHERE family=? ORDER BY version DESC', (family,))
