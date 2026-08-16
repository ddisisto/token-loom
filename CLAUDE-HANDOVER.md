# Handover

Working notes too ephemeral for `CLAUDE.md`, `ROADMAP.md` or `FORMAT.md`, carried across a
compaction.

**Delete each item as it closes, and the file when it empties.** It is a message between
sessions, not documentation. Anything here that turns out to be durable belongs in one of
the three files above instead.

---

## Where things stand

`core_test.py` 198 green with no model, `llama_test.py` 42 green against the server on 8081.

**The research thread has completed one full cycle and is deliberately paused.** Experiment
001 was pre-registered, run blind, and answered — see `RESEARCH.md`, which is now a landing
page, and `experiments/001-temperature.md`, which is the record. The pause is intentional:
the next research move is choosing an axis to sample prompts along, and that is better done
with fresh eyes than immediately.

**The build thread is the current work.** `ROADMAP.md` Phase 2, and specifically the parts
that do not need interaction — that is what this session's break from research is for.

Nothing is open at the format level. Everything below is either a thread to pick up or a
fact that is easy to get wrong and does not belong anywhere permanent yet.

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
keep the API moving, not because it is small.

**2. `data/sweep-1/` predates the alignment fix.** About 40 of its ~10,070 token rows carry
the pre-`d31a3d2` shape, where a merged entry stored a byte fragment's id as though it
described a whole character. It was generated with `cache_prompt` on, so it is faithful but
not reproducible from what each span carries. `lock(3)` and `lock(10)` are unaffected and
nothing was re-run. Do not treat it as a clean reference tree; `data/demo/` is the clean one.

## Facts that will save an hour

**`experiments/` files are written in two commits and not tidied between them** — the
pre-registration before the run, the results after. `CLAUDE.md` has the reasoning. Corrections
append; editing an experiment file after its results land spends the only thing
pre-registration buys.

**`cache_prompt` is off and generation is therefore slower**, by the cost of reprocessing the
prompt on every call. This is deliberate and `BEYOND-MVP.md` holds the two routes back to the
speed. If a sweep feels slow, that is why, and it is not a regression.

**`scripts/` is committed now.** It used to be swallowed by a `[Ss]cripts` rule inherited from
a virtualenv gitignore template, which `CLAUDE.md` had rationalised as deliberate. `sweep.sh`
is there and is a temperature sweep in executable form — copy it rather than editing it for a
different experiment.

**The archive is `../archive/`**, a sibling of the repo and outside it. It holds the
old-format trees including `data/local.json`, the dead `run.sh` and `screenshot.sh`, and
upstream's README screenshots. Nothing there is needed to run anything, and git history still
has everything that was ever tracked.

**`llama_test.py:context_limit` needs a second server** and skips rather than fails without
one:

    CTX=512 PORT=8082 scripts/llama-server.sh --n-gpu-layers 0

CPU-only, because a second GPU instance does not fit in 8GB beside the first.

## For the build thread specifically

**The CLI is the specification, and it grew this session.** `loom.py` now also has
`diverge` (sibling agreement as a number), `show <position> --depth n`, `batches --params
<key>` and `gen --stay`. All four are reads or flags the API will want, and `divergence` lives
in `core/ops.py` rather than in `loom.py` precisely so the API can reach it.

**Nothing in the CLI emits machine-readable output.** Every command prints for a human. Still
worth deciding early whether the API is a separate surface over `core/` (probably) or whether
`loom.py` grows a `--json` mode (probably not).

**`data/tree/` is disposable scratch** and may hold a stale-format tree; `loom.py new` refuses
it cleanly rather than tracebacking. Delete it when convenient. `data/demo/` is committed and
is the one to leave alone — `demo.py --force` is the only thing that should rewrite it.
