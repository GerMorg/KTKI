from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PACKAGE=ROOT/"autonomous_trader"

def test_new_runtime_has_no_gui_or_legacy_imports():
    forbidden=("flask","jinja","render_template","gunicorn","core_runtime","v103_main","controlled_learning.py","real_trade.py")
    for path in PACKAGE.rglob("*.py"):
        source=path.read_text(encoding="utf-8").lower()
        for token in forbidden: assert token not in source,(path,token)

def test_addon_runtime_only_copies_and_runs_new_package():
    docker=(ROOT/"Dockerfile").read_text(encoding="utf-8")
    run=(ROOT/"run.sh").read_text(encoding="utf-8")
    config=(ROOT/"config.yaml").read_text(encoding="utf-8")
    assert "COPY autonomous_trader" in docker and "COPY app" not in docker
    assert "python -m autonomous_trader" in run and "gunicorn" not in run
    assert "ingress: false" in config
    assert "real_allowed_symbols" not in config

def test_only_trading_authority_constructs_executor():
    hits=[]
    for path in PACKAGE.rglob("*.py"):
        source=path.read_text(encoding="utf-8")
        if "KrakenExecutor(" in source:hits.append(path.name)
    assert hits==["runtime.py"]
