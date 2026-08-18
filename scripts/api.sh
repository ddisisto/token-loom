#!/usr/bin/env bash
# Run the API over one tree, and the reading surface with it. $LOOM_TREE picks
# the tree, as it does for loom.sh; pass a path to override. One tree per
# process -- a second tree is a second process on another --port.
#
# The front end is served by this same process off the same origin: open
# http://127.0.0.1:8080/ once it is up. There is no separate web.sh and no build
# step, because web/ is served exactly as it is written.
set -euo pipefail
cd "$(dirname "$0")/.."
exec uv run --group web python -m api.server "${1:-${LOOM_TREE:-data/tree}}" "${@:2}"
