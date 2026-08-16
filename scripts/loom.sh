#!/usr/bin/env bash
# token loom, from the command line. Pre-authorised wrapper around loom.py.
#
#   scripts/loom.sh new
#   scripts/loom.sh author 'The sea was'
#   scripts/loom.sh gen -n 4 --length 40
#   scripts/loom.sh show
#
# LOOM_TREE picks the tree directory; loom.py defaults to data/tree.
set -euo pipefail
cd "$(dirname "$0")/.."
exec uv run python loom.py "$@"
