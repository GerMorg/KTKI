#!/usr/bin/with-contenv bashio
set -euo pipefail
export APP_DATA_DIR=/data APP_OPTIONS=/data/options.json
# v69/v71 remain preserved compatibility baselines; v72 is the active runtime.
exec /opt/venv/bin/gunicorn --workers 1 --threads 4 --bind 0.0.0.0:8099 v72_main:app
