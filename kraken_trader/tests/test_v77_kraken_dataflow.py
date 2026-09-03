import ast
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1];APP=ROOT/'app'
class V77KrakenDataflowTests(unittest.TestCase):
 def test_active_runtime_and_version(self):
  run=(ROOT/'run.sh').read_text(encoding='utf-8');version=(APP/'version.py').read_text(encoding='utf-8');config=(ROOT/'config.yaml').read_text(encoding='utf-8')
  self.assertIn('v79_main:app',run);self.assertIn("APP_VERSION='0.1.0-dev.79'",version);self.assertIn('version: 0.1.0-dev.79',config)
 def test_readonly_private_websocket_is_enabled_by_v77(self):
  source=(APP/'main.py').read_text(encoding='utf-8');runtime=(APP/'v77_main.py').read_text(encoding='utf-8');config=(ROOT/'config.yaml').read_text(encoding='utf-8')
  self.assertIn("private_websocket_readonly_enabled',False",source);self.assertIn('legacy.private_stream.enabled = True',runtime);self.assertIn('private_websocket_readonly_enabled: true',config);self.assertIn('wss://ws-auth.kraken.com/v2',(APP/'ws_private.py').read_text(encoding='utf-8'))
 def test_bootstrap_is_non_blocking_and_has_rest_fallback(self):
  runtime=(APP/'v77_main.py').read_text(encoding='utf-8');self.assertIn('threading.Thread(target=_startup_dataflow',runtime);self.assertIn('def _light_rest_portfolio_sync()',runtime);self.assertIn('def _sync_private_balances()',runtime);self.assertIn("_audit('V77_PORTFOLIO_SNAPSHOT'",runtime);self.assertIn("_audit('V77_PRIVATE_BALANCE_APPLIED'",runtime);self.assertIn("_audit('V77_REST_FALLBACK_FAILED'",runtime);self.assertIn('APP_DISABLE_WEBSOCKETS',runtime)
 def test_runtime_sources_compile(self):
  for path in (APP/'v77_main.py',APP/'v79_main.py',APP/'main.py',APP/'ws_private.py',APP/'portfolio_sync.py'):ast.parse(path.read_text(encoding='utf-8'),filename=str(path))
 def test_portfolio_builder_values_eur_balance_and_asset(self):
  from portfolio_sync import build_rows
  balances={'EUR':'1250.50','BTC':'0.1'};assets={'EUR':{'altname':'EUR'},'BTC':{'altname':'XBT'}};pairs={'XXBTZEUR':{'base':'BTC','quote':'EUR','altname':'BTCEUR'}};tickers={'BTCEUR':{'c':['60000']}}
  rows,total,quality=build_rows(balances,set(),assets,pairs,tickers);self.assertEqual(total,'7250.50');self.assertEqual(quality,'VALID');by_name={row['display_name']:row for row in rows};self.assertEqual(by_name['EUR']['eur_value'],'1250.50');self.assertEqual(by_name['BT']['eur_value'],'6000.0')
if __name__=='__main__':unittest.main()
