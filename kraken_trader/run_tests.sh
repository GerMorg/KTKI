#!/bin/sh
set -eu
export PYTHONPATH="${PYTHONPATH:+$PYTHONPATH:}app"
python -m unittest discover -s tests -v
