import json

from controlled_learning import ControlledLearning
from strategy_profiles import BOUNDS, FAMILIES

FAMILY = 'xstocks'
PARAMETERS = {name: (default, *BOUNDS[FAMILY][name]) for name, default in FAMILIES[FAMILY].items()}
LABELS = {
    'base_score': 'Basiswert', 'momentum_weight': 'Momentum-Gewicht', 'trend_weight': 'Trend-Gewicht',
    'volatility_penalty': 'Volatilitätsabzug', 'spread_penalty': 'Spread-Abzug',
    'buy_threshold': 'BUY-Schwelle', 'buy_max_spread_pct': 'Maximaler BUY-Spread %',
    'avoid_threshold': 'AVOID-Schwelle', 'avoid_spread_pct': 'AVOID-Spread %',
}


class LearningApproval:
    """Compatibility facade; controlled learning is the single source of truth."""

    def __init__(self, db):
        self.db = db
        self.controlled = ControlledLearning(db)

    def ensure(self):
        self.controlled.ensure()

    def values(self):
        active = self.controlled.active(FAMILY)
        return json.loads(active['parameters_json']) if active else dict(FAMILIES[FAMILY])

    def latest(self):
        candidates = self.controlled.candidates(FAMILY)
        if not candidates:
            return None
        item = dict(candidates[0])
        item['accuracy'] = item.get('candidate_accuracy')
        item['parameters'] = json.loads(item.get('parameters_json') or '{}')
        return item

    def rows(self):
        current = self.values()
        latest = self.latest()
        proposed = latest.get('parameters', {}) if latest and latest.get('status') == 'PENDING' else {}
        return [{
            'name': f'xstocks_{name}', 'label': LABELS.get(name, name),
            'current': current[name], 'proposed': proposed.get(name),
            'minimum': bounds[0], 'maximum': bounds[1]
        } for name, bounds in BOUNDS[FAMILY].items()]

    def create_proposal(self):
        return self.controlled.propose(FAMILY, min_sample=10, min_improvement=.02)

    def approve_latest(self):
        candidate = self.latest()
        if not candidate or candidate['status'] != 'PENDING':
            return {'status': 'NOTHING_TO_APPROVE'}
        return self.controlled.decide(candidate['id'], 'approve')


# The /learning compatibility page is an actionable proposal view, not a history view.
# Once a candidate is approved it becomes the new active version and must no longer be
# shown as a "candidate" against itself. The complete version history remains available
# through ControlledLearning. This also prevents the GUI from presenting a misleading
# Active == Candidate comparison after promotion.
_original_controlled_candidates = ControlledLearning.candidates


def _actionable_candidates(self, family=None):
    rows = _original_controlled_candidates(self, family)
    return [row for row in rows if row.get('status') == 'PENDING']


ControlledLearning.candidates = _actionable_candidates
