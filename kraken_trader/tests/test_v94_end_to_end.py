import unittest
from decimal import Decimal
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'app'))
from decision_engine_v94 import DecisionEngineV94

class V94EndToEndTests(unittest.TestCase):
    def setUp(self):
        self.e=DecisionEngineV94(None)
        self.cfg={'minimum_score':70,'max_position_pct':10,'cash_reserve_pct':20}
    def test_long_requires_positive_edge_after_costs(self):
        row={'symbol':'BTC/EUR','signal':'BUY','score':90,'volatility_pct':2,'buy_threshold':70,'news_score':0}
        d=self.e.build(row,{'quality_score':80,'expected_edge_after_costs_pct':.5},1,0,.2,'BULL',self.cfg)
        self.assertTrue(d['economic_gate_passed'])
        d2=self.e.build(row,{'quality_score':80,'expected_edge_after_costs_pct':.1},1,0,.2,'BULL',self.cfg)
        self.assertFalse(d2['economic_gate_passed'])
    def test_same_decision_inputs_are_deterministic(self):
        row={'symbol':'BTC/EUR','signal':'BUY','score':88,'volatility_pct':2,'buy_threshold':70,'news_score':10}
        h={'quality_score':75,'expected_edge_after_costs_pct':1}
        a=self.e.build(row,h,1000,50,.2,'BULL',self.cfg)
        b=self.e.build(row,h,1000,50,.2,'BULL',self.cfg)
        self.assertEqual(a,b)
    def test_hold_is_not_zero_target(self):
        row={'symbol':'BTC/EUR','signal':'BUY','score':80,'volatility_pct':2,'buy_threshold':70}
        d=self.e.build(row,{'quality_score':80,'expected_edge_after_costs_pct':1},1000,30,.1,'BULL',self.cfg,True)
        self.assertEqual(d['action'],'BUY')
    def test_short_is_directionally_symmetric(self):
        row={'symbol':'ETH/EUR','signal':'AVOID','score':85,'volatility_pct':2,'buy_threshold':70}
        d=self.e.build(row,{'quality_score':80,'directions':{'DOWN':{'net_return_pct':2}}},1000,0,.2,'BEAR',self.cfg)
        self.assertEqual(d['direction'],'SHORT')
        self.assertLess(Decimal(d['target_exposure_eur']),Decimal('0'))
    def test_target_zero_is_an_explicit_exit(self):
        row={'symbol':'BTC/EUR','signal':'AVOID','score':20,'volatility_pct':2,'buy_threshold':70}
        d=self.e.build(row,{'quality_score':20},1000,120,.5,'BEAR',self.cfg,True)
        self.assertEqual(d['action'],'SELL')
        self.assertEqual(Decimal(d['target_exposure_eur']),Decimal('0'))
        self.assertTrue(d['economic_gate_passed'])

    def test_news_is_an_input_not_a_standalone_trigger(self):
        row={'symbol':'X','signal':'BUY','score':60,'volatility_pct':2,'buy_threshold':70,'news_score':100}
        d=self.e.build(row,{'quality_score':50,'expected_edge_after_costs_pct':0},1000,0,.1,'BULL',self.cfg)
        self.assertFalse(d['economic_gate_passed'])

if __name__=='__main__': unittest.main()
