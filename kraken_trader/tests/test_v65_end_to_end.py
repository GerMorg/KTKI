import sys, unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'app'))
from autonomous_decision_v65 import build_plan, simulate_end_to_end
from autonomous_portfolio_v65 import DecisionPolicy

class V65EndToEndTests(unittest.TestCase):
    def policy(self):
        return DecisionPolicy(cash_reserve_pct=0,max_position_pct=100,no_trade_band_pct=0,min_trade_eur=1,max_trade_eur=1000,max_actions=5,minimum_score=70,fx_fee_bps=10,trading_fee_bps=40,slippage_bps=10)
    def outputs(self,currency='EUR'):
        return [{'symbol':'BTC','score':90,'expected_return_pct':10,'volatility_pct':5,'currency':currency,'model_valid':True}]
    def test_unvalidated_model_output_never_enters_plan(self):
        plan=build_plan([{'symbol':'BTC','score':99,'expected_return_pct':20,'volatility_pct':5,'model_valid':False}],1000,[],self.policy())
        self.assertEqual(plan['actions'],[])
    def test_model_to_eur_twin_is_complete(self):
        r=simulate_end_to_end(self.outputs(),1000,[],1100,policy=self.policy())
        self.assertEqual(r['status'],'SIMULATED')
        self.assertTrue(r['plan']['actions'])
        self.assertGreater(r['simulation']['total_cost_eur'],0)
    def test_model_to_usd_requires_fx(self):
        r=simulate_end_to_end(self.outputs('USD'),1000,[],1000,policy=self.policy())
        self.assertEqual(r['status'],'BLOCKED_FX_RATE_MISSING')
    def test_model_to_usd_tracks_fx_and_trade_cost(self):
        r=simulate_end_to_end(self.outputs('USD'),1000,[],1100,fx_rate_eur_per_usd=.85,policy=self.policy())
        self.assertEqual(r['status'],'SIMULATED')
        self.assertGreater(r['simulation']['fx_cost_eur'],0)
        self.assertGreater(r['simulation']['trade_cost_eur'],0)
    def test_cheapest_route_is_selected(self):
        routes={'BTC':[{'symbol':'BTC/EUR','quote_asset':'EUR'},{'symbol':'BTC/USD','quote_asset':'USD'}]}
        tickers={'BTC/EUR':{'b':['99'],'a':['100'],'c':['99.5']},'BTC/USD':{'b':['110'],'a':['110.1'],'c':['110.05']},'EUR/USD':{'b':['1.20'],'a':['1.2001'],'c':['1.20005']}}
        plan=build_plan(self.outputs(),1000,[],self.policy(),routes,tickers)
        self.assertEqual(plan['actions'][0]['currency'],'USD')
        self.assertEqual(plan['actions'][0]['selected_route'],'BTC/USD')
    def test_invalid_plan_input_is_rejected(self):
        from autonomous_portfolio_v65 import DigitalTwin
        with self.assertRaises(TypeError): DigitalTwin().execute([],1000)

if __name__=='__main__': unittest.main()
