#!/bin/sh
set -eu
export PYTHONPATH="."
python -m pytest -q tests/test_autonomous_core.py tests/test_autonomous_flow.py tests/test_autonomous_static.py tests/test_autonomous_resilience.py tests/test_autonomous_sensor.py
