#!/usr/bin/with-contenv bashio
set -euo pipefail
export APP_DATA_DIR=/data APP_OPTIONS=/data/options.json
# Historical runtimes remain preserved for compatibility; v90_main:app was the immediately previous active runtime baseline; v80_main:app is retained only as a historical baseline marker. v96 is the active runtime: market regime, directional model quality, risk-aware target sizing and confidence/calibration select Spot versus Margin/Short execution.
exec /opt/venv/bin/gunicorn --workers 1 --threads 4 --bind 0.0.0.0:8099 v96_main:app
