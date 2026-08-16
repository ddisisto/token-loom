#!/usr/bin/env bash
# Run the API over one tree. $LOOM_TREE picks it, as it does for loom.sh;
# pass a path to override. One tree per process -- a second tree is a second
# process on another --port.
set -euo pipefail
cd "$(dirname "$0")/.."
exec uv run --group web python -m api.server "${1:-${LOOM_TREE:-data/tree}}" "${@:2}"
