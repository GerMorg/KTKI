import math,sys
sys.path.insert(0,'kraken_trader/app')
from model_validation_v63 import StrategyValidationEngine

def test_validation_rejects_length_mismatch():
    r=StrategyValidationEngine().validate([1,2,3],['HOLD']*2)
    assert r['status']=='INVALID_INPUT'

def test_validation_produces_all_benchmarks():
    prices=[100+i*0.1 for i in range(160)]
    signals=['BUY']*len(prices)
    r=StrategyValidationEngine({'roundtrip_cost_rate':0.001}).validate(prices,signals,folds=4,embargo=3)
    assert r['status'] in ('VALID','NOT_ROBUST')
    assert all(set(('strategy','buy_hold','cash')).issubset(f) for f in r['folds'])
    assert len(r['gates'])==5

def test_costs_reduce_strategy_result():
    prices=[100+i*0.1 for i in range(160)]
    signals=['BUY' if i<80 else 'AVOID' for i in range(len(prices))]
    free=StrategyValidationEngine({'roundtrip_cost_rate':0}).validate(prices,signals,folds=3)
    costly=StrategyValidationEngine({'roundtrip_cost_rate':0.02}).validate(prices,signals,folds=3)
    assert costly['aggregate']['mean_net_return'] <= free['aggregate']['mean_net_return']
