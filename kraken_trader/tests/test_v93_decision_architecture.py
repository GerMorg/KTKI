import unittest
from decimal import Decimal
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'app'))

from execution_confidence import execution_confidence,choose_execution
from market_regime import candidate_regime
from portfolio_target import build_targets

class V93DecisionTests(unittest.TestCase):
 def test_regime_is_directional(self):
  self.assertEqual(candidate_regime(2,1),'BULL')
  self.assertEqual(candidate_regime(-2,-1),'BEAR')
  self.assertEqual(candidate_regime(2,-1),'MIXED')

 def test_health_does_not_zero_candidate_confidence(self):
  c=execution_confidence(82,{'quality_score':20},None,'BULL','UP')
  self.assertGreater(c,65)

 def test_spot_remains_available_when_margin_calibration_missing(self):
  c=execution_confidence(82,{'quality_score':20},None,'BULL','UP')
  d=choose_execution(c,True,4,65,78,86,93,97,calibration={'status':'NOT_READY'})
  self.assertEqual(d['mode'],'SPOT')
  self.assertEqual(d['leverage'],Decimal('1'))

 def test_ready_calibration_unlocks_leverage(self):
  c=execution_confidence(92,{'quality_score':80},{'status':'READY','direction':'UP','samples':30,'required_samples':20,'win_rate':.7,'net_return_pct':8},'BULL','UP')
  d=choose_execution(c,True,4,65,78,86,93,97,calibration={'status':'READY'})
  self.assertEqual(d['mode'],'MARGIN')
  self.assertIn(d['leverage'],(Decimal('2'),Decimal('3'),Decimal('4')))

 def test_target_weight_uses_quality_and_regime(self):
  rows=[{'symbol':'BULL','score':'85','volatility_pct':'2','roundtrip_cost_pct':'0.2','buy_threshold':'70','quality_score':100,'regime_factor':1},
        {'symbol':'BEAR','score':'85','volatility_pct':'2','roundtrip_cost_pct':'0.2','buy_threshold':'70','quality_score':20,'regime_factor':'.4'}]
  targets=build_targets(rows,1000,20,10,70,5)
  self.assertEqual(len(targets),2)
  weights={x['symbol']:Decimal(x['target_weight_pct']) for x in targets}
  self.assertGreater(weights['BULL'],weights['BEAR'])

if __name__=='__main__':unittest.main()
