#!/usr/bin/env bash
# Run the web backend. Defaults to the lighthouse tree; pass another path to override.
set -euo pipefail
cd "$(dirname "$0")/.."
exec uv run --group web python -m web.server "${1:-data/local.json}" "${@:2}"
