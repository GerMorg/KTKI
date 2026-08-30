import unittest
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'app'))
from portfolio_optimization_v64 import PortfolioOptimizerV64

class V64PortfolioTests(unittest.TestCase):
    def test_targets_respect_cash_reserve_and_position_cap(self):
        o=PortfolioOptimizerV64(cash_reserve_pct=20,max_position_pct=40)
        w=o.target_weights({'BTC':10,'ETH':5,'SOL':1})
        self.assertGreaterEqual(w['EUR'],20)
        self.assertLessEqual(w['BTC'],40)
        self.assertLessEqual(w['ETH'],40)
        self.assertAlmostEqual(sum(w.values()),100,places=6)

    def test_risk_adjustment_penalizes_high_variance_asset(self):
        o=PortfolioOptimizerV64(cash_reserve_pct=0,max_position_pct=100)
        w=o.target_weights({'A':1,'B':1},{'A':{'A':1},'B':{'B':4}},risk_aversion=1)
        self.assertGreater(w['A'],w['B'])

    def test_rebalance_band_and_min_trade_are_real_gates(self):
        o=PortfolioOptimizerV64(no_trade_band_pct=2,min_trade_eur=20,max_trade_eur=100)
        plan=o.rebalance_plan({'BTC':10,'ETH':10},{'BTC':11,'ETH':15},1000)
        self.assertEqual(len(plan),1)
        self.assertEqual(plan[0]['symbol'],'ETH')
        self.assertEqual(plan[0]['notional_eur'],50)

    def test_max_trade_limits_single_action(self):
        o=PortfolioOptimizerV64(no_trade_band_pct=0,min_trade_eur=1,max_trade_eur=100)
        plan=o.rebalance_plan({'BTC':0},{'BTC':50},1000)
        self.assertEqual(plan[0]['notional_eur'],100)

    def test_usd_route_includes_fx_cost(self):
        o=PortfolioOptimizerV64(fee_bps=40,fx_fee_bps=10,slippage_bps=10)
        r=o.route('USD',['EUR'])
        self.assertTrue(r.fx_required)
        self.assertAlmostEqual(r.total_cost_pct,.6)

    def test_eur_route_does_not_buy_fx(self):
        o=PortfolioOptimizerV64(fee_bps=40,fx_fee_bps=10,slippage_bps=10)
        r=o.route('EUR',['EUR'])
        self.assertFalse(r.fx_required)
        self.assertAlmostEqual(r.total_cost_pct,.5)

    def test_turnover_is_computed_from_executable_plan(self):
        o=PortfolioOptimizerV64(no_trade_band_pct=0,min_trade_eur=1,max_trade_eur=1000)
        plan=o.rebalance_plan({'BTC':0},{'BTC':10},1000)
        self.assertAlmostEqual(o.turnover(plan,1000),.1)

if __name__=='__main__':unittest.main()
