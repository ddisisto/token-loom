# Handover

Working notes too ephemeral for `CLAUDE.md`, `ROADMAP.md` or `FORMAT.md`, carried across a
compaction. Written at the close of the session that built `token-loom/2`.

**Delete each item as it closes, and the file when it empties.** It is a message between
sessions, not documentation. Anything here that turns out to be durable belongs in one of
the three files above instead.

---

## Where things stand

`token-loom/2` is built, tested and exercised: `core_test.py` 121 green with no model,
`llama_test.py` 27 green against `scripts/llama-server.sh`, and driven end to end through
`loom.py` against the live model including the awkward offset-0 counterfactual branch.

It lives on the branch **`token-loom-2`**, six commits, not merged. `main` is at `eab0458`
and is *internally inconsistent* — it carries the `token-loom/2` docs over `token-loom/1`
code, because the docs landed before the branch was cut. That is the main argument for
merging promptly rather than polishing on the branch.

The tag **`token-loom-1`** marks `57db927`, the last commit where code and docs agreed on the
old format. It exists so the doc trim below can delete every reference without losing the
reachable state.

## Open threads, in the order they want doing

### 1. Merge the branch

Not yet agreed explicitly — the ordering question was left open and then overtaken. Nothing
competes with it, the branch has been exercised by hand, and `main` is in a worse resting
state than either side. **Ask, then merge.**

### 2. Renumber the format marker to `token-loom/1`

Decided, with one condition that must land in the same commit.

The concern was that a genuine old `token-loom/1` tree would pass the marker check and load
silently wrong — `Span.from_json` reads `parent` with `.get()`, so every span would become a
root. Daniel confirms exactly one such tree exists and it is in his trash. The fix removes
the hazard regardless: **make `parent` a required key** (`d['parent']`, not `d.get('parent')`).
New files always carry it — roots have it as `null` — and old ones fail loudly.

Renumber and require-the-key together, or do neither.

### 3. Trim the `token-loom/1` references

It never went live and a new reader only needs current state. Three categories, and they are
not equal:

- **Comparative asides** — "where `token-loom/1` needed a run id...", scattered through
  docstrings in `core/ops.py`, `core/tree.py`, `core/validate.py`, `core/session.py` and
  `loom.py`. Trim freely.
- **`FORMAT.md`'s alternatives list** — *keep*, this is the expensive lesson: a one-line
  rejection of the right answer nearly held. But rewrite it so it reads as shapes considered
  and rejected, one of which happened to get built, rather than requiring the reader to know
  a `/1` existed.
- **`FORMAT.md`'s "What the amendment cost"** — the measured numbers and the two build
  findings (the zero-width run, why `deleted` must not be pruned). The findings are durable
  and should survive in some form; the before/after line counts are archaeology and can go.

### 4. Functional testing, before calling core + CLI done

Four gaps, the first two being things the code has never done:

- **Stop strings.** `STOP` is a distinct termination reason and nothing exercises it —
  `llama_test.py` only ever asserts `LENGTH` or `EOS`. Test with `--stop '.'` and
  `--stop $'\n'`. Daniel's `daniel-notes.md` treats stop-token handling as central, so the
  format-level half should be proven now even though the UI defers to `BEYOND-MVP.md`.
- **The context-limit derivation.** `CONTEXT` is the only *derived* terminator — "nothing
  stopped it and it produced fewer tokens than were asked for" — which makes it the easiest
  to get silently wrong. Forcing it needs `llama-server` restarted with a small `--ctx-size`;
  `scripts/llama-server.sh` takes `CTX` from the environment.
- **Multiple root prompts, once.** The format permits several spans with `parent: null` and
  `show` should splice the zero-width root. That is a claim from reading the code, not from
  running it. Not a flow to build on — `ROADMAP.md`'s MVP step 1 is one prompt composed with
  separators, not siblings — just a claim to check.
- **A deep single-token chain, for correctness not speed.** Spans-as-numerous-as-tokens was
  the sizing assumption behind the whole design and `ancestry` now walks span by span.
  Explicitly *not* an optimisation task.

### 5. CLI polish

The reframe worth holding while doing it: the CLI is the **reference client**, not a scratch
tool. Whatever it can do sets the floor for the Phase 2 API, so this is partly specification.

- **`tokens` does not print rank numbers**, but `branch <span> <index> <rank>` takes one — so
  today you count columns to use the command. Sharpest usability edge.
- **The cursor should mark its position inline** in the rendered text, not just with ` ←` at
  the end of the run line. Wrinkle: that line truncates at 68 characters, so the mark has to
  survive truncation — probably by windowing the shown text around the cursor rather than
  always from the start.
- **Batches are recorded and nothing reads them.** Every span carries `batch b0[2]`; no
  command groups or filters by it. The batch id was pulled forward into Phase 1 precisely so
  a batch could be read back as the experiment it was, and that payoff is uncollected.
- **No way to list parameter sets.** The intern table is invisible except one span at a time.
- More will surface in use — Daniel expects this and it is the point of doing the pass.

### 6. Close the throughput question

`ROADMAP.md` under "Open questions" still carries **throughput under broad sampling**.
Dropped: any optimisation question comes much later. Delete the section rather than answering
it, and with it the last open item before Phase 2.

---

## Two things about the code that are not yet written down anywhere durable

Both should end up in `FORMAT.md` or `CLAUDE.md` if they survive the trim.

**The zero-width run.** `branch <span> 0 <rank>` anchors a counterfactual at byte 0 of a span
that also continues, which makes a derived run with no bytes in it. That is a fork point, not
a run, so `loom.py:build` splices its branches into its parent's and the counterfactual
renders as a sibling of the span whose first token it replaces. The `resuming` flag in
`outline()` is what makes this terminate — without it the case either loses the branch or
forks into itself forever.

**Why `deleted` is not pruned.** The first implementation dropped entries another already
covered, out of `token-loom/1` habit. Two faults: an entry is always unreachable under its own
cut, so testing it against the full list drops everything and resurrects what it deleted; and
pruning at all breaks undo, since restoring a wide cut then resurrects a subtree that was
deleted separately by a narrower one. `Tree.live` takes the least cut per span and is total
over any set, so maximality bought nothing.

---

## Method notes worth carrying

`CLAUDE.md`'s **Method** section holds the durable version. Two things from this session that
are not in it:

**The failure ratio held again.** Three failures in the rewritten test suite: two were
miscounted byte lengths in assertions, one was a real bug. Both test errors were eyeballed
rather than computed. `'The sea was'[:8]` is `'The sea '` *with* the trailing space, and
`strip()` eats the trailing space a slice output ends with.

**Twice, "is the test wrong or the code wrong?" had a third answer: the test asks for
something that cannot hold.** `back.to_json() == tree.to_json()` after a round trip cannot be
true when the tree has spans in flight, because `open_tree` recovers them to aborted — and
asserting sameness was hiding the one thing worth checking there. Likewise the `token-loom/1`
check that `text` and `extent[1]` agreed about in-flight went tautological, not redundant,
once there was one field. Both are findings, not nuisances, and both belong in a docstring.

**On the process itself.** The `token-loom/2` realisation came from *using* the finished
`token-loom/1` core, not from planning it — ten faults fell out of prose, the eleventh only
out of use. Neither stage finds the other's bugs. This is in `CLAUDE.md` now; it is repeated
here because the CLI pass above is the same bet being placed again.
