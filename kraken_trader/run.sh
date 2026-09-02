#!/usr/bin/with-contenv bashio
set -euo pipefail
export APP_DATA_DIR=/data APP_OPTIONS=/data/options.json
# v69/v71/v72/v73/v74/v75/v76 remain preserved compatibility baselines; v77 is the active runtime.
exec /opt/venv/bin/gunicorn --workers 1 --threads 4 --bind 0.0.0.0:8099 v77_main:app
