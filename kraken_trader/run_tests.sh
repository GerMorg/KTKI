#!/bin/sh
set -eu
# Keep repository-root imports available for package-qualified v66 tests,
# while retaining app/ imports used by the legacy test suite.
export PYTHONPATH="${PYTHONPATH:+$PYTHONPATH:}app"
python -m unittest discover -s tests -v
