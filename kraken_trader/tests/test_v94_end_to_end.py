import unittest
from decimal import Decimal
from pathlib import Path
import tempfile
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'app'))

from decision_engine_v95 import DecisionEngineV95
from decision_matrix import DecisionMatrix

class V95EndToEndTests(unittest.TestCase):
    def setUp(self):
        self.e=DecisionEngineV95(None)
        self.cfg={'minimum_score':70,'max_position_pct':10,'cash_reserve_pct':20}

    def test_long_requires_measurable_positive_edge_after_costs(self):
        row={'symbol':'BTC/EUR','signal':'BUY','score':90,'volatility_pct':2,'momentum_pct':1,'trend_pct':1,'buy_threshold':70,'news_score':0}
        d=self.e.build(row,{'quality_score':80},1000,0,.2,'BULL',self.cfg)
        self.assertEqual(d['edge_status'],'UNKNOWN')
        self.assertFalse(d['economic_gate_passed'])
        row['expected_edge_pct']='1.0'
        d=self.e.build(row,{'quality_score':80},1000,0,.2,'BULL',self.cfg)
        self.assertTrue(d['economic_gate_passed'])
        self.assertEqual(Decimal(d['expected_edge_after_costs_pct']),Decimal('.8'))

    def test_news_score_never_becomes_an_uncalibrated_expected_edge(self):
        row={'symbol':'X','signal':'BUY','score':70,'volatility_pct':2,'momentum_pct':1,'trend_pct':1,'buy_threshold':70,'news_score':100}
        d=self.e.build(row,{'quality_score':50},1000,0,.1,'BULL',self.cfg)
        self.assertFalse(d['economic_gate_passed'])
        self.assertIsNone(d['expected_edge_gross_pct'])

    def test_avoid_means_exit_or_flat_not_implicit_short(self):
        row={'symbol':'BTC/EUR','signal':'AVOID','score':20,'volatility_pct':2,'momentum_pct':-2,'trend_pct':-1,'avoid_threshold':35}
        d=self.e.build(row,{},1000,120,.2,'BEAR',self.cfg,True,allow_short=False)
        self.assertEqual(d['direction'],'FLAT')
        self.assertEqual(d['action'],'SELL')
        self.assertEqual(Decimal(d['target_exposure_eur']),Decimal('0'))
        self.assertTrue(d['economic_gate_passed'])
        d2=self.e.build(row,{},1000,0,.2,'BEAR',self.cfg,False,allow_short=False)
        self.assertEqual(d2['action'],'HOLD')

    def test_short_sizing_uses_downside_conviction(self):
        row={'symbol':'ETH/EUR','signal':'AVOID','score':20,'volatility_pct':2,'momentum_pct':-2,'trend_pct':-1,'avoid_threshold':35}
        d=self.e.build(row,{'quality_score':80},1000,0,.2,'BEAR',self.cfg,False,allow_short=True)
        self.assertEqual(d['direction'],'SHORT')
        self.assertLess(Decimal(d['target_exposure_eur']),Decimal('0'))
        self.assertGreater(Decimal(d['signal_strength']),Decimal('0'))

    def test_holding_a_neutral_signal_keeps_target(self):
        row={'symbol':'BTC/EUR','signal':'HOLD','score':55,'volatility_pct':2,'momentum_pct':0,'trend_pct':0,'buy_threshold':70}
        d=self.e.build(row,{},1000,120,.2,'NEUTRAL',self.cfg,True)
        self.assertEqual(d['direction'],'HOLD')
        self.assertEqual(Decimal(d['target_exposure_eur']),Decimal('120'))
        self.assertEqual(d['action'],'HOLD')

    def test_decision_matrix_rejects_non_positive_economic_edge(self):
        db=None
        # This is a contract test for the context passed to DecisionMatrix.
        # Use a minimal temporary DB through the real DB class.
        from db import DB
        h=tempfile.NamedTemporaryFile(suffix='.db',delete=False); h.close()
        db=DB(h.name); db.init()
        try:
            m=DecisionMatrix(db)
            ctx={
                'canonical_id':'BTC/EUR','confirmation_count':1,'confirmation_required':1,
                'minimum_hold_ok':True,'cooldown_ok':True,'daily_limit_ok':True,
                'improvement_after_costs':'0','economic_edge_ok':False,
                'execution_confidence_ok':True,'execution_confidence':'99',
                'execution_mode':'SPOT','tax_loss_ok':True,'data_fresh':True,
                'model_health_ok':True,'route_cost_ok':True,'quote_funding_ok':True,
                'portfolio_risk_ok':True,'order_constraints_ok':True,
                'real_trading_enabled':True,'real_kill_switch_clear':True,
                'real_limits_ok':True,'real_balance_ok':True,
            }
            result=m.evaluate('BTC/EUR','BUY',ctx,'REAL')
            self.assertFalse(result['allowed'])
            self.assertFalse(next(x for x in result['checks'] if x['rule_key']=='POSITIVE_AFTER_COSTS')['passed'])
        finally:
            Path(h.name).unlink(missing_ok=True)

if __name__=='__main__':
    unittest.main()
