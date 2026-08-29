"""Model-health checks used before an autonomous real decision.

A score is not a probability.  This module therefore refuses to turn a raw
0..100 scanner score into an execution permission.  It requires evidence from
real historical forecasts and compares against simple benchmarks.
"""
import json
import math
from decimal import Decimal

D = lambda x: Decimal(str(x or 0))


class ModelHealth:
    REQUIRED_HORIZONS = (24, 168)

    def __init__(self, db):
        self.db = db
        self.ensure()

    def ensure(self):
        with self.db.con() as c:
            c.execute("""CREATE TABLE IF NOT EXISTS model_health_snapshots(
                id INTEGER PRIMARY KEY AUTOINCREMENT, created_at TEXT NOT NULL,
                family TEXT NOT NULL, status TEXT NOT NULL, score TEXT NOT NULL,
                details_json TEXT NOT NULL)""")

    @staticmethod
    def _drawdown(values):
        equity = peak = 1.0
        worst = 0.0
        for value in values:
            equity *= max(1e-9, 1 + float(value) / 100)
            peak = max(peak, equity)
            worst = min(worst, equity / peak - 1)
        return worst * 100

    def evaluate(self, family, min_samples=20, min_net_return_pct=0.0, max_drawdown_pct=-25.0):
        rows = self.db.rows("""SELECT f.horizon_hours,f.direction,f.scanner_score,f.features_json,
                                     e.actual_return_pct,e.direction_correct
                              FROM research_forecasts f
                              JOIN forecast_evaluations e ON e.forecast_id=f.id
                              WHERE f.family=? ORDER BY f.id""", (family,))
        details = {'family': family, 'samples': len(rows), 'horizons': {}, 'benchmarks': {}, 'gates': []}
        for horizon in self.REQUIRED_HORIZONS:
            subset = [r for r in rows if int(r['horizon_hours']) == horizon]
            returns = [float(r['actual_return_pct'] or 0) for r in subset]
            cost_adjusted = []
            for r in subset:
                try: features = json.loads(r.get('features_json') or '{}')
                except Exception: features = {}
                cost = float(features.get('estimated_roundtrip_cost_pct') or 0)
                direction = str(r.get('direction') or 'FLAT')
                actual = float(r.get('actual_return_pct') or 0)
                strategy = actual - cost if direction == 'UP' else (-actual - cost if direction == 'DOWN' else 0.0)
                cost_adjusted.append(strategy)
            hit = sum(int(r['direction_correct']) for r in subset)
            n = len(subset)
            model_net = sum(cost_adjusted)
            buy_hold = sum(returns)
            details['horizons'][str(horizon)] = {
                'samples': n, 'hit_rate': hit / n if n else None,
                'model_net_return_pct': model_net, 'buy_hold_sum_pct': buy_hold,
                'excess_return_pct': model_net - buy_hold,
                'max_drawdown_pct': self._drawdown(cost_adjusted) if cost_adjusted else None,
            }
            details['gates'].append({'name': f'H{horizon}_SAMPLES', 'passed': n >= min_samples, 'actual': n, 'required': min_samples})
            details['gates'].append({'name': f'H{horizon}_NET_RETURN', 'passed': model_net >= min_net_return_pct, 'actual': model_net, 'required': min_net_return_pct})
            details['gates'].append({'name': f'H{horizon}_DRAWDOWN', 'passed': not cost_adjusted or self._drawdown(cost_adjusted) >= max_drawdown_pct,
                                     'actual': self._drawdown(cost_adjusted) if cost_adjusted else None, 'required': max_drawdown_pct})
        # A model must beat a passive/no-action baseline after costs on at least
        # one horizon and never fail the hard drawdown/sample gates.
        hard = all(g['passed'] for g in details['gates'])
        excess = [v['excess_return_pct'] for v in details['horizons'].values() if v['samples']]
        benchmark_ok = bool(excess) and max(excess) > 0
        details['gates'].append({'name': 'BENCHMARK_EXCESS', 'passed': benchmark_ok, 'actual': max(excess) if excess else None, 'required': '> 0'})
        status = 'READY' if hard and benchmark_ok else 'NOT_READY'
        score = 100.0 if status == 'READY' else max(0.0, min(100.0, sum(1 for g in details['gates'] if g['passed']) / max(1, len(details['gates'])) * 100))
        with self.db.con() as c:
            c.execute('INSERT INTO model_health_snapshots(created_at,family,status,score,details_json) VALUES(?,?,?,?,?)',
                      (self.db.now() if hasattr(self.db, 'now') else __import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat(), family, status, str(score), json.dumps(details, sort_keys=True)))
        return {'status': status, 'score': score, **details}

    def all_ready(self, families):
        result = {family: self.evaluate(family) for family in families}
        return bool(result) and all(x['status'] == 'READY' for x in result.values()), result
