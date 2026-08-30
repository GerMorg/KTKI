"""Backward-compatible backtest facade using the v62 validation engine."""
from model_validation import ModelValidationEngine

class BacktestEngine:
    def __init__(self, db): self.db=db; self.validator=ModelValidationEngine(db)
    def run(self,symbol,interval_min=60,cost_rate=.006):
        result=self.validator.run(symbol,interval_min,cost_rate,folds=4,embargo_points=1)
        if result.get('status') not in ('VALID','NOT_ROBUST'): return result
        folds=result['folds'];strategy=[x['strategy']['total_return'] for x in folds];hold=[x['buy_hold']['total_return'] for x in folds]
        saved=self.db.rows('SELECT id FROM model_validation_runs ORDER BY id DESC LIMIT 1')
        return {'status':result['status'],'run_id':saved[0]['id'] if saved else None,'symbol':symbol,'no_position_return':0.0,
                'buy_hold_return':sum(hold)/len(hold),'trend_return':sum(strategy)/len(strategy),
                'trend_max_drawdown':min(x['strategy']['max_drawdown'] for x in folds),'turnovers':sum(x['trades'] for x in folds),
                'estimated_cost_rate':cost_rate,'validation_method':result['method'],'validation_gates':result['gates'],'folds':folds}
    def recent(self): return self.validator.recent()
