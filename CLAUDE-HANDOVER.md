# Handover

Working notes too ephemeral for `CLAUDE.md`, `ROADMAP.md` or `FORMAT.md`, carried across a
compaction.

**Delete each item as it closes, and the file when it empties.** It is a message between
sessions, not documentation. Anything here that turns out to be durable belongs in one of
the three files above instead.

---

## Where things stand

Three suites: `core_test.py` 198 and `api_test.py` 62 with no model, `llama_test.py` 42
against the server on 8081. `api_test.py` needs the `web` group — `uv run --group web python
api_test.py`, or the venv directly.

**Phase 2's server half has landed and the old stack is gone.** `api/` speaks positions over
HTTP, one tree per process; `inference.py`, `models.py`, `params.py`, `util/`, `web/` and
`smoke_test.py` were deleted whole. One substrate, two clients, and neither sits on the other.

**The next work is the front end, and it is the half that needs interaction.** Nothing about
it is designed yet, deliberately — the shape wanted is a wireframe first, then components
built and refined one at a time, then integration, with Daniel driving rather than reviewing
a finished thing. Prior work is to be absorbed in intent only; the old browser UI was a few
simple panels and was retired without being kept as a visual reference, on purpose.

**The research thread is still deliberately paused**, one full cycle in. `RESEARCH.md` is the
landing page and `experiments/001-temperature.md` is the record. The next research move is
choosing an axis to sample prompts along, which wants fresh eyes.

Nothing is open at the format level.

## Threads to pick up, in the order they will bite

**1. Two writers on one tree directory are unguarded, and the failure is partly silent.**
Found while settling that the CLI should *not* consume the API — both are clients of `core/`,
which is right, and which means nothing stops `loom.py author` running against a tree an API
server has open. `Tree.save` rewrites the file whole via rename, so the loser's spans simply
vanish. Then ids are minted one past the highest **in the tree**, so a re-minted `s7` inherits
the dead `s7`'s bulk rows. Check 6 catches most of that — text against what its tokens spell —
but stale counterfactual *ranks*, at indices the new span also has, survive it: a branch onto a
token the model never ranked. Two cheap fixes, both in `core/`, neither built: an exclusive
lock on the tree directory taken by whoever opens it for writing, with `loom.py` refusing
while the server holds it; and a tenth validator check that no bulk row names a span the tree
does not have, for which `store.spans_with_tokens()` already exists. Deferred deliberately to
keep the API moving, not because it is small. **This gets sharper the moment a browser is
open**, since the natural way to work is a UI in one window and the CLI in a terminal.

**2. `PLAYBOOKS.md` may be dropped, and Daniel is carrying that thread.** The argument is that
`demo.py` is the construction and `README.md` can carry the idea without leaking one
generation's specifics as though they were findings. Do not act on it from this side. One
consequence worth knowing if it lands: `PLAYBOOKS.md` quoting the demo tree line by line is
the *only* reason `data/demo/` cannot be rebuilt, so dropping it releases that constraint and
the note in `CLAUDE.md` about the sanctioned text substitution would want rewriting.

**3. `data/sweep-1/` predates the alignment fix.** About 40 of its ~10,070 token rows carry
the pre-`d31a3d2` shape, where a merged entry stored a byte fragment's id as though it
described a whole character. It was generated with `cache_prompt` on, so it is faithful but
not reproducible from what each span carries. `lock(3)` and `lock(10)` are unaffected and
nothing was re-run. Do not treat it as a clean reference tree; `data/demo/` is the clean one.

## For the front end specifically

**The wire is settled and `api/wire.py` is where its rules live**, not the route handlers.
Four that a client has to know:

- a **position** is `{"span", "offset"}` in a body and `s3+9` in a query parameter, `null`
  and `.` respectively for the root
- **text may be `{"b64": …}`** instead of a string, for bytes that do not decode. Reachable
  from a counterfactual branch onto a byte-fallback token, never from generation
- **runs carry no ids** at any depth, and cannot be given any — they renumber
- **every mutation returns the whole tree**, so there is nothing to patch client-side

**Generation blocks the request**, tens of seconds for a batch. Streaming is deferred entire,
so the front end needs to cope rather than wait for it — and a read *during* generation sees
in-flight spans, which is the honest thing to show and exactly what streaming's placeholder
forks will render later.

**`GET /api/settings` is the only route that needs the model server**, and it 503s without
one. Everything else, including authoring, works with nothing on 8081 — composing a prompt
with no model running is a property of the format, and `api_test.py` asserts it.

**The CLI is still the specification.** Anything the front end wants that `loom.py` cannot do
is worth checking against `core/` first: three times now the honest answer was that the read
was missing from both, and it belonged in `core/ops.py` rather than in either client.

## Facts that will save an hour

**`experiments/` files are written in two commits and not tidied between them** — the
pre-registration before the run, the results after. `CLAUDE.md` has the reasoning. Corrections
append; editing an experiment file after its results land spends the only thing
pre-registration buys.

**`cache_prompt` is off and generation is therefore slower**, by the cost of reprocessing the
prompt on every call. This is deliberate and `BEYOND-MVP.md` holds the two routes back to the
speed. If a sweep feels slow, that is why, and it is not a regression.

**`scripts/` is committed.** `sweep.sh` is a temperature sweep in executable form — copy it
rather than editing it for a different experiment. `api.sh` serves one tree on 8080.

**The archive is `../archive/`**, a sibling of the repo and outside it. It holds the
old-format trees including `data/local.json`, the dead `run.sh` and `screenshot.sh`, and
upstream's README screenshots. Nothing there is needed to run anything, and git history still
has everything that was ever tracked — including everything Phase 2 deleted.

**`llama_test.py:context_limit` needs a second server** and skips rather than fails without
one:

    CTX=512 PORT=8082 scripts/llama-server.sh --n-gpu-layers 0

CPU-only, because a second GPU instance does not fit in 8GB beside the first.

**`data/tree/` is disposable scratch** and may hold a stale-format tree; `loom.py new`
refuses it cleanly rather than tracebacking. Delete it when convenient. `data/demo/` is
committed and is the one to leave alone.
