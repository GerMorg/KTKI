#!/bin/sh
set -eu
export PYTHONUNBUFFERED=1
exec /opt/venv/bin/python -m autonomous_trader
