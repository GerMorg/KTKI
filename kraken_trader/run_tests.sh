#!/bin/sh
set -eu
PYTHONPATH=app python -m unittest discover -s tests -v
