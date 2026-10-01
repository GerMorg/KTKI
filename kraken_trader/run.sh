#!/usr/bin/with-contenv bashio
set -euo pipefail
export APP_DATA_DIR=/data APP_OPTIONS=/data/options.json
# Historical active runtime marker: v98_main:app; current runtime is v99_main:app.
# Historical runtimes remain preserved for compatibility; v90_main:app was the previous active runtime baseline; v80_main:app and earlier runtimes are retained only as historical baseline markers. v99_main:app is the active runtime.
exec /opt/venv/bin/gunicorn --workers 1 --threads 4 --bind 0.0.0.0:8099 v99_main:app
