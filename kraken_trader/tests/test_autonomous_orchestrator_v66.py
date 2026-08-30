import unittest

from kraken_trader.app.autonomous_orchestrator_v66 import AutonomousOrchestratorV66, ModelInput


class TestV66(unittest.TestCase):
    def setUp(self):
        self.o = AutonomousOrchestratorV66()
        self.base = {
            "total_eur": 1000,
            "holdings": [],
            "data_fresh": True,
            "eur_balance": 1000,
        }

    @staticmethod
    def model(valid=True, status="VALID", assets=None):
        return ModelInput(
            "m", valid, 2.0, 10.0, .9, status,
            assets if assets is not None else [{
                "symbol": "BTC/EUR", "score": 90,
                "expected_return_pct": 2.0,
                "volatility_pct": 10.0,
                "currency": "EUR",
            }],
        )

    def test_invalid_models_block(self):
        r = self.o.decide([self.model(valid=False)], self.base)
        self.assertEqual(r.status, "BLOCKED")

    def test_non_validated_models_block(self):
        r = self.o.decide([self.model(status="NOT_ROBUST")], self.base)
        self.assertEqual(r.status, "BLOCKED")

    def test_no_assets_blocks(self):
        r = self.o.decide([self.model(assets=[])], self.base)
        self.assertEqual(r.status, "BLOCKED")

    def test_malformed_model_dictionary_is_ignored(self):
        r = self.o.decide([{"valid": True, "validation_status": "VALID", "confidence": "bad"}], self.base)
        self.assertEqual(r.status, "BLOCKED")

    def test_ready_path_uses_real_v65_engine(self):
        r = self.o.decide(
            [self.model()],
            self.base,
            route_options={"BTC/EUR": [{"symbol": "BTC/EUR", "quote_asset": "EUR"}]},
            tickers={"BTC/EUR": {"b": ["50000"], "a": ["50010"], "c": ["50005"]}},
        )
        self.assertEqual(r.status, "READY")
        self.assertEqual(r.twin["status"], "SIMULATED")


if __name__ == "__main__":
    unittest.main()
