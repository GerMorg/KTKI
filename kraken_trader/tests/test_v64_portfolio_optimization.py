import unittest
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'app'))
from portfolio_optimization_v64 import PortfolioOptimizerV64
class V64PortfolioTests(unittest.TestCase):
 def test_constraints_and_normalization(self):
  w=PortfolioOptimizerV64(20,40).target_weights({'BTC':10,'ETH':5,'SOL':1});self.assertGreaterEqual(w['EUR'],20);self.assertLessEqual(max(w[k] for k in w if k!='EUR'),40);self.assertAlmostEqual(sum(w.values()),100,places=6)
 def test_risk_adjustment(self):
  w=PortfolioOptimizerV64(0,100).target_weights({'A':1,'B':1},{'A':{'A':1},'B':{'B':4}},1);self.assertGreater(w['A'],w['B'])
 def test_rebalance_band_and_min_trade(self):
  p=PortfolioOptimizerV64(no_trade_band_pct=2,min_trade_eur=20,max_trade_eur=100).rebalance_plan({'BTC':10,'ETH':10},{'BTC':11,'ETH':15},1000);self.assertEqual([x['symbol'] for x in p],['ETH']);self.assertEqual(p[0]['notional_eur'],50)
 def test_max_trade(self):
  p=PortfolioOptimizerV64(no_trade_band_pct=0,min_trade_eur=1,max_trade_eur=100).rebalance_plan({'BTC':0},{'BTC':50},1000);self.assertEqual(p[0]['notional_eur'],100)
 def test_fx_cost(self):
  r=PortfolioOptimizerV64(20,25,2,20,250,40,10,10).route('USD',['EUR']);self.assertTrue(r.fx_required);self.assertAlmostEqual(r.total_cost_pct,.6)
 def test_eur_no_fx(self):
  r=PortfolioOptimizerV64().route('EUR',['EUR']);self.assertFalse(r.fx_required);self.assertAlmostEqual(r.total_cost_pct,.5)
 def test_turnover(self):
  o=PortfolioOptimizerV64(no_trade_band_pct=0,min_trade_eur=1,max_trade_eur=1000);p=o.rebalance_plan({'BTC':0},{'BTC':10},1000);self.assertAlmostEqual(o.turnover(p,1000),.1)
if __name__=='__main__':unittest.main()
