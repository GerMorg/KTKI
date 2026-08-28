import sys
from pathlib import Path
ROOT=Path(__file__).parents[1]
sys.path.insert(0,str(ROOT/'app'))
from version import APP_VERSION
from ws_market import MarketStream

def test_version_sources_are_synchronized():
 assert APP_VERSION == "0.1.0-dev.49"
 assert f'version: "{APP_VERSION}"' in (ROOT/'config.yaml').read_text('utf-8')
 assert f'version: {APP_VERSION}' in (ROOT.parent/'repository.yaml').read_text('utf-8')

def test_repository_has_no_known_mojibake():
 markers=(chr(0x00c3), chr(0x00c2), chr(0x00e2)+chr(0x20ac), chr(0x00f0)+chr(0x0178), chr(0xfffd))
 for path in ROOT.parent.rglob('*'):
  if not path.is_file() or '__pycache__' in path.parts or '.pytest_cache' in path.parts: continue
  try: text=path.read_text('utf-8')
  except UnicodeDecodeError: continue
  assert not any(marker in text for marker in markers), str(path)

def test_public_websocket_keeps_eur_and_usd_quotes():
 class DB: pass
 stream=MarketStream(DB(),enabled=False)
 stream.set_symbols(['BTC/EUR','AAPL/USD','EUR/USD','INVALID'])
 assert stream.symbols == ['AAPL/USD','BTC/EUR','EUR/USD']
