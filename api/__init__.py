"""The HTTP surface over `core/`. One tree per process.

Phase 2, and a clean replacement rather than a port. The old `web/` server
speaks node ids and a node-shaped compatibility view over the token core would
carry the old vocabulary into the thing built to replace it -- cheaper for a
week and a tax forever.

Three shapes are settled here and worth reading before the routes:

- **One tree per process.** The tree directory is a launch argument, the way
  `scripts/loom.sh` takes `LOOM_TREE`. There is no session registry, no
  open/new/activate, and no active-session concept for a mutation to be
  ambiguous about. Several trees means several processes.
- **The API is a separate surface over `core/`, not `loom.py --json`.** The CLI
  formats for reading -- marked cursors, elided runs, a divergence table -- and
  none of that is reusable over HTTP. A `--json` mode would be a second
  implementation in the same file, and would freeze a human-facing tool against
  a machine contract.
- **Positions, never node ids.** `(span, offset)` is the only address, per
  `FORMAT.md` decision 1. Derived run ids never appear, because a derived
  grouping renumbers.

`server.py` holds the routes and the one lock; `wire.py` holds the encoding,
which is where the rules that are easy to get wrong live and is therefore
testable without an HTTP client.
"""
