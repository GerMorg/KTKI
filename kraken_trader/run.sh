#!/usr/bin/with-contenv bashio
set -euo pipefail
export APP_DATA_DIR=/data APP_OPTIONS=/data/options.json
# Historical runtimes remain preserved for compatibility; v86 is the active runtime and diagnostics are isolated from application startup.
exec /opt/venv/bin/gunicorn --workers 1 --threads 4 --bind 0.0.0.0:8099 v86_main:app
