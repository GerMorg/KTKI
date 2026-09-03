import ast
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]/'app'

def read(name):return (ROOT/name).read_text(encoding='utf-8')

def test_v79_is_active_and_gui_has_single_navigation_model():
    run=read('v79_main.py'); sh=(ROOT.parent/'run.sh').read_text(encoding='utf-8')
    assert 'v79_main:app' in sh
    assert "legacy.NAV_ITEMS = [" in run
    assert "app.view_functions['index'] = _dashboard" in run
    assert 'render_template_string' in run

def test_research_forecast_stage_no_string_unpack_bug():
    src=read('research_pipeline.py')
    tree=ast.parse(src)
    bad=[]
    for n in ast.walk(tree):
        if isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Tuple):
            target=n.targets[0]
            if len(target.elts)==2 and isinstance(n.value,ast.Constant) and isinstance(n.value.value,str):bad.append(n.lineno)
    assert not bad
    assert "stage='FORECAST_SNAPSHOT';operation='ForecastTracker.snapshot'" in src
    assert "'DONE'" in src

def test_prefilter_has_stale_universe_and_cached_price_fallbacks():
    src=read('prefilter.py')
    assert 'if not primary:' in src
    assert 'def _cached_ticker' in src
    assert "quality='CACHED' if cached else 'VALID'" in src

def test_public_ws_subscribes_per_symbol_and_quarantines_bad_pairs():
    src=read('ws_market.py')
    assert 'self._req_symbols' in src
    assert 'self.blocked' in src
    assert 'PUBLIC_WS_SYMBOL_REJECTED' in src
    assert "'symbol':[symbol]" in src

def test_config_exposes_market_subscription_limit():
    cfg=(ROOT.parent/'config.yaml').read_text(encoding='utf-8')
    assert 'websocket_symbol_limit: 100' in cfg
    assert 'websocket_symbol_limit: int(20,250)' in cfg

def test_versions_are_consistent():
    assert "0.1.0-dev.79" in read('version.py')
    assert "0.1.0-dev.79" in (ROOT.parent.parent/'repository.yaml').read_text(encoding='utf-8')
