#!/usr/bin/with-contenv bashio
set -euo pipefail
export APP_DATA_DIR=/data APP_OPTIONS=/data/options.json
# Historical runtimes remain preserved for compatibility; v80_main:app is retained only as a historical baseline marker. v87 is the active runtime and adds user-facing real-trading blocker diagnostics.
exec /opt/venv/bin/gunicorn --workers 1 --threads 4 --bind 0.0.0.0:8099 v87_main:app
