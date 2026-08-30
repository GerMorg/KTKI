import unittest
from kraken_trader.app.autonomous_orchestrator_v66 import AutonomousOrchestratorV66, ModelInput

class Optimizer:
    def optimize(self, assets, portfolio):
        return assets

class Twin:
    def simulate(self, actions, portfolio):
        return {"status": "OK", "actions": actions}

class Matrix:
    def evaluate(self, *args):
        return {"allowed": True, "blocker": "Alle Regeln erfüllt", "checks": []}

class TestV66(unittest.TestCase):
    def setUp(self):
        self.o = AutonomousOrchestratorV66(Optimizer(), object(), Twin(), Matrix())
        self.base = {"positions": {}, "data_fresh": True, "portfolio_risk_ok": True}

    def test_invalid_models_block(self):
        r = self.o.decide([ModelInput("m", False, .2, .1, .9, {"BTC/EUR": 1})], self.base)
        self.assertEqual(r.status, "BLOCKED")

    def test_positive_valid_model_reaches_twin(self):
        r = self.o.decide([ModelInput("m", True, .2, .1, .9, {"BTC/EUR": 1})], self.base)
        self.assertEqual(r.status, "READY")
        self.assertIsNotNone(r.twin)

    def test_no_assets_blocks(self):
        r = self.o.decide([ModelInput("m", True, .2, .1, .9, {})], self.base)
        self.assertEqual(r.status, "BLOCKED")

if __name__ == "__main__":
    unittest.main()
