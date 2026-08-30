import unittest
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'app'))
from portfolio_digital_twin_v64 import PortfolioDigitalTwinV64

class V64TwinTests(unittest.TestCase):
    def test_usd_path_buys_fx_before_asset(self):
        twin=PortfolioDigitalTwinV64(40,10,10)
        r=twin.simulate(1000,[{'currency':'USD','notional_eur':100}],eurusd=1.17)
        self.assertEqual(r['status'],'SIMULATED')
        self.assertEqual([x['step'] for x in r['steps']],['EUR_TO_USD','BUY_OR_SELL_ASSET'])
        self.assertAlmostEqual(r['total_cost_eur'],0.6)

    def test_missing_eurusd_blocks_usd_execution(self):
        twin=PortfolioDigitalTwinV64()
        r=twin.simulate(1000,[{'currency':'USD','notional_eur':100}],eurusd=None)
        self.assertEqual(r['status'],'MISSING_EURUSD')

    def test_eur_path_has_no_fx_step(self):
        twin=PortfolioDigitalTwinV64(40,10,10)
        r=twin.simulate(1000,[{'currency':'EUR','notional_eur':100}])
        self.assertEqual(r['status'],'SIMULATED')
        self.assertEqual([x['step'] for x in r['steps']],['BUY_OR_SELL_ASSET'])
        self.assertAlmostEqual(r['total_cost_eur'],0.5)

if __name__=='__main__':unittest.main()
