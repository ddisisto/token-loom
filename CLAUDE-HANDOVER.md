# Handover

A one-shot load for the session that starts Phase 2. Written at the close of the session
that built Phase 1, and holding only what `CLAUDE.md`, `ROADMAP.md` and `BEYOND-MVP.md` do
not — mostly one design realisation that arrived *after* the code was done, and that should
land before Phase 2 planning gets far.

**Delete or rewrite this file once it has been read.** It is a message between sessions, not
documentation.

---

## Read first, in this order

1. `CLAUDE.md` — loads automatically; current as of the last commit
2. This file
3. `ROADMAP.md` — Phase 2 section, plus "The model" for the vocabulary
4. `PHASE-1.md` — **only** if you need a closed decision's reasoning. It is superseded by the
   code and due for deletion in the first Phase 2 commit. Do not maintain it.

Then, before touching anything: `uv run python core_test.py` (101 checks, no model needed)
and, with `scripts/llama-server.sh` running, `uv run python llama_test.py` (27 checks).
Both were green at `0c1c254`.

---

## The thing that changed after Phase 1 closed

Phase 1 settled that durable references hold **absolute byte offsets**, resolved to runs by
lookup, because run ids narrow silently under splits. That is true but incomplete, and Daniel
spotted the gap in conversation after the code was pushed:

> **An absolute offset does not identify a path.** Sibling branches share offsets — `r3` and
> `r5` both start at 20 — so `at()` needs a run id to say *which* path, which smuggles the
> unstable thing back in through the argument list.

`ROADMAP.md` already shows the strain: Phase 3 proposes bookmarks "anchored to byte offsets
**and node ids**". That "and" is the bug.

### The answer already exists, and it is the span

A span is written once, never cut, and holds every byte it ever had — `s3` still holds all
fifteen bytes after the split that left `r3` reaching nine. "The longest extent it ever had,
from generation completion" is the definition of a span. Phase 1 used it as a *storage* unit
and never as an *addressing* unit, which was the oversight.

**`(span, offset)` is invariant under every operation.** `split` divides piece lists and never
opens a span. `delete` marks runs. `author`, `generate` and `branch` only add spans. A future
vacuum is already forbidden from removing them. And because a span's pieces lie along one
root-to-leaf chain, naming the span names the path — so it is strictly stronger than an
absolute offset, not merely different.

`core/ops.py:locate()` already resolves `(span, offset)` to a current `Position`. It was
written for `branch_counterfactual` and is the general answer; nothing new is needed.

### What to change

**No stored bytes change.** Spans, pieces, extents, the bulk store, the validator's nine
checks — all identical. This is why it costs nothing to do now, and why it was not a Phase 1
failure to have missed it.

- `Tree.selected` becomes `{span, offset}`, with `span: null` meaning the root of a tree that
  has no spans yet. That is the only special case.
- **The cursor fixup in `ops.split` disappears entirely** — there is nothing to reseat. The
  fixup in `ops.delete` reduces to a display concern: the address still resolves, it just
  points into an unreachable branch, and the UI decides where to put the user instead.
- `core_test.py`'s "selected is the one thing in the file keyed by a run id" section should
  be rewritten to assert the opposite — that a split leaves the cursor *untouched*. It is
  currently the standing demonstration of the hazard; it should become the demonstration that
  the hazard is gone.
- `validate.py` does not check `selected` at all. It should, once the shape is stable.

**The CLI, with a distinction worth keeping.** Run forms are good *input* — typing `r4` for
that run's tip is natural and stable enough for a command you are typing right now. It is the
**stored** cursor that must be span-addressed. So:

- keep `r4`, `r4:9`, `r4@100` as input syntax
- add `s1+12` as an input form, span-relative
- resolve to `(span, offset)` before writing `selected`
- `show` should probably print the cursor as `s1+12`, since it says what it is relative to
  where a bare `40` does not

**Phase 2's API then falls out.** Positions on the wire are `(span, offset)`; run ids never
reach it. That was the one Phase 2 decision flagged as needing to be made early, and this
makes it. A run id in a URL would resolve after a split and mean less than it did — the same
hazard `selected` currently demonstrates, promoted to the network.

Bonus worth knowing: absolute offsets are root-relative and meaningless in an exported
subtree. Span addresses travel. That matters for the comparison-across-trees work in
`BEYOND-MVP.md`.

### Suggested order

Land the span-addressing change as a small Phase 1 amendment *before* planning Phase 2 in
detail. It is maybe an hour, it deletes more code than it adds, and it turns an open API
question into a settled one.

---

## The plan, briefly

**Phase 0 ✅** cleared the ground — tkinter gone, renamed, dependencies 16 → 3.
**Phase 1 ✅** the token core: bytes anchor, tokens overlay, spans own the bytes, runs are
structure, sqlite bulk store, six operations, native llama-server, a headless driver.
**Phase 2** the API and front end rebuilt against it. A clean replacement, not a port. This
is where `inference.py`, `models.py`, `params.py`, `util/` and `web/` all retire *together* —
piecemeal migration is explicitly the wrong move, and `CLAUDE.md` says so.
**Phase 3** reads and annotation: slice-selectable viewport, bookmarks, branch-to-counterfactual
in the UI, sibling divergence as a read. Then the MVP is done.

**Beyond** (`BEYOND-MVP.md`, nothing built): generation control and streaming, both deferred
whole; embeddings and distances; a generation controller; token replay instead of
re-tokenisation.

One measurement still open, in `ROADMAP.md`: throughput under broad sampling. Now cheap to
take — `session.generate` already issues N sequential calls with `cache_prompt` on.

---

## How this project runs

**Plan in prose, then build.** Phase 1 went: lock decisions in `PHASE-1.md`, stress-test it,
*then* write code. Ten real faults were caught in prose that would have been expensive in
code — including one where the validator invariant contradicted soft delete, which would have
fired on every tree after the first delete. Keep doing this.

**Probe rather than reason, when the question is decidable.** Several confident assumptions
turned out wrong, and each was settled in minutes with a throwaway script:

| assumed | actual |
| --- | --- |
| the native and OpenAI endpoints differ in token payload | identical — `{id, token, bytes, logprob, top_logprobs}` |
| the sampled token is always in its own top-N | absent ~⅓ of the time at temperature 0.9 |
| `n_probs: 0` merely drops counterfactuals | drops per-token **bytes** too; there is no overlay without it |
| a token can only be a fragment of a character in theory | `🜁` is three tokens, none valid UTF-8 alone |

Daniel's framing on the last one is the one to generalise: **absence of observation cannot
settle a question about what is possible.** Ask the vocabulary, not the samples.

**Test the invariant, not the value.** The test that earned its keep most was asserting that
a split leaves the *absolute offset* a cursor named unchanged — not that the cursor equals
some particular pair. Value-equality tests would have passed on a wrong implementation.

**Scratchpad, not `/tmp`.** Multi-line `python -c` gets blocked by the command classifier;
write a script to the scratchpad and run it. Bash is zsh — quote globs (`--include='*.py'`)
or they get eaten. Commands run serially and un-bundled, no `&&`, no redirects.

---

## Meta

**On Daniel.** He plans before building and it visibly pays. He reads the code himself and
notices things — the `inference.py` reassessment came from him looking at it, not from me
raising it, and he was right: two thirds unreachable, and `seed` never in the request path at
all. When he says "should we step back and reassess", treat it as a prompt to gather evidence,
not to defend the plan. He is decisive once evidence is in ("I'll take the cost"), explicit
about scoping things out, and values maintainability enough to accept a big-bang rewrite for
it. He does not need hedging or flattery; he needs the actual trade-off named.

**On me, from this session.** The production code held up under review; my **test assertions**
were where the sloppiness went. I miscounted bytes twice (`'café — '` is 7 characters and 10
bytes, not 6 and 9), asserted a tautology that could never fail, and left a dynamic-import
line guarding against a circular import that did not exist. All three were caught by running
things rather than by reading them. The lesson is narrow and worth carrying: **arithmetic in
a test is code too, and it is not checked by anything.** Compute it, do not eyeball it.

The other pattern worth repeating: when a check failed, the first question was "is the test
wrong or is the code wrong?", and twice the honest answer was "the test asks for something
the design makes unreachable" — prefix coverage could not be made to fail, because delete
cascades. That is a finding, not a nuisance, and it belongs in the docstring.

**On the systems.** `CLAUDE.md` is loaded every session and is worth keeping honest; it had
drifted badly by the end of Phase 1 (wrong remote, missing `core/`, a Phase 4 that no longer
exists) and was corrected in `0c1c254`. Memory at
`~/.claude/projects/-home-daniel-prj-loom-loom/memory/` holds three notes; the project one
now points at the repo rather than duplicating it, because the repo docs are better
maintained than any memory will be.

---

## Loose

The first real generation through the finished CLI produced four continuations of "the sea
was", and **all four chose `' calm'`**. The instrument answered its own motivating question —
attractors in the prior — on its first honest use, without being asked to. That is either a
good omen or a very on-the-nose one.

The span-as-address realisation is itself an argument for the method. Ten faults fell out of
planning in prose; this eleventh only fell out of *using the thing*. Both stages were
load-bearing, and neither would have found the other's bugs. Worth remembering when the
temptation arrives to skip one of them.

The counterfactual display in `loom.py tokens` turned out better than expected as a read: the
`*` marking the sampled token is missing about a third of the time at temperature 0.9, so the
gap between "what the model ranked" and "what it did" is visible at a glance rather than
inferable. That was not designed in — it fell out of storing the two as independent records.
Phase 3's sibling-divergence read should probably be built the same way: store the honest
thing, and let the display find the question.
