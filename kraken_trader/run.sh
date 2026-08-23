#!/usr/bin/with-contenv bashio
set -euo pipefail
export APP_DATA_DIR=/data
export APP_OPTIONS=/data/options.json
exec /opt/venv/bin/gunicorn --workers 1 --threads 4 --bind 0.0.0.0:8099 --access-logfile - --error-logfile - main:app
