import unittest
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'app'))

from execution_confidence import execution_confidence,choose_execution,short_execution

class ExecutionConfidenceTests(unittest.TestCase):
 def test_good_but_not_exceptional_stays_spot(self):
  c=execution_confidence(82,{'score':50,'horizons':{'24':{'samples':137}}},{'direction':'UP','samples':0,'required_samples':20,'win_rate':0,'net_return_pct':0})
  d=choose_execution(c,True,4,70,80,88,94,97,calibration={'status':'NOT_READY'})
  self.assertEqual(d['mode'],'SPOT')
  self.assertEqual(d['leverage'],1)

 def test_higher_confidence_unlocks_higher_leverage(self):
  self.assertEqual(choose_execution(81,True,4,70,80,88,94,97,calibration={'status':'READY'})['leverage'],2)
  self.assertEqual(choose_execution(89,True,4,70,80,88,94,97,calibration={'status':'READY'})['leverage'],3)
  self.assertEqual(choose_execution(95,True,4,70,80,88,94,97,calibration={'status':'READY'})['leverage'],4)

 def test_max_leverage_caps_the_tier(self):
  self.assertEqual(choose_execution(99,True,3,70,80,88,94,97,calibration={'status':'READY'})['leverage'],3)

 def test_short_requires_down_calibration_and_confidence(self):
  bad=short_execution(90,{'status':'NOT_READY'},4,75,78,86,93,97)
  self.assertEqual(bad['mode'],'BLOCKED')
  good=short_execution(90,{'status':'READY','direction':'DOWN','samples':20,'required_samples':20,'win_rate':.7,'net_return_pct':5},4,75,78,86,93,97)
  self.assertEqual(good['mode'],'MARGIN')
  self.assertEqual(good['leverage'],3)

if __name__=='__main__':
 unittest.main()
