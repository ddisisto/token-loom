# The core pass

**One pass over the substrate and the repo, before the surface is designed.** It exists because
three things were decided at once — a format change, a fault in deletion, and a boundary the core
had drawn in the wrong place — and none of them should be discovered halfway through building a
reading surface against them.

**This file is deleted when the pass is done**, and `ROADMAP-v1.0.md` is picked up after it
rather than beside it. There are never two files carrying status: this one ends where that one
begins, and that one is surface and UX only.

It carries reasoning *and* order, against the rule that keeps them apart, for one reason: the act
that absorbs the reasoning — the `FORMAT.md` split — is itself an item in the order, so both
halves die together. If this file outlives that expectation, the first half lifts out in one cut.

---

## The probes

Both were run. **`/completion` accepts a prompt as text plus token ids** — `["…", 151643, …]` —
so token replay is an adapter change and not an engine overhaul. That result is what makes the
first decision below exact rather than approximate, and it retires the assumption that the
ledger in `CLAUDE.md` was waiting on a move to transformers.

The empty-prompt probe was run too and **its answer is not written down anywhere yet.** It
belongs in `FORMAT.md`'s measurements when the split happens.

## Decision 1 — branching is a generation with a pre-filled first token

`branch_counterfactual` leaves `core/ops.py`. Taking a token the model ranked and did not sample
becomes a call in `core/session.py` beside `generate`, with the same sequence and the same
guarantees, differing in four places: the first token row is written from the recorded
counterfactual after the tree is saved, the prompt carries that token's id after the sliced text,
the budget sent to the model is one less than the length recorded, and `kind` says where the span
departed from.

**The reason is the reading surface, not the format.** A column holds everything down to the next
actualised branch point; a one-token counterfactual span is not something to read, and turning it
into one took a second act. Asking for an alternative and getting a continuation is one gesture,
which is the gesture the instrument turns on.

**`kind` is reframed as the departure decision**, not the origin of the bytes. All three values
survive unchanged and none is added: `given` — someone outside decided; `sampled` — the model's
own draw decided; `counterfactual` — a reader took a road the model ranked and did not take. The
axis had to move because such a span now holds one counterfactual token and many sampled ones,
and *what decided this span exists* is the fact worth having in one field.

**The origin's top-N is copied onto the new span at index 0.** The distribution is the same
distribution — same prefix, same position — and copying it makes the span answerable on its own
terms, so a second branch from it needs no walk back to where it came from. It is the same
argument that gave a counterfactual span a token row in the first place.

Six things have to be in the recipe. The first is the one that fails silently:

- **The response's tokens and counterfactuals shift by one before `complete`.** `add_tokens` is
  `INSERT OR REPLACE`, so an unshifted row 0 overwrites the pre-filled counterfactual, and
  `text` is then computed from the same unshifted list — the store and the text agree, check 6
  passes, and the forced token is gone without a trace. **Check 5 grows a second half to catch
  it**: row 0's `token_id` equals `origin.token_id`. It is the only thing that would.
- **`complete` sets `text` from the store rather than from its argument.** One line, and it
  carries three cases at once: identical for ordinary generation, correct with a pre-filled row,
  correct when the response is empty. It also makes `complete` say what `recover` says, which is
  check 6 stated once instead of twice.
- **The empty-prompt guard is not copied across.** Branching at token 0 of a root span leaves no
  path bytes, and the prompt is the forced token — not empty. Build the parts list without the
  text part when there is none, rather than sending an empty string.
- **The reduced budget goes to the model; the requested length is what interns.** `n_predict`
  and the `CONTEXT` derivation read the same dict, so passing the reduced copy end to end keeps
  the derivation honest. The copy must never reach `tree.intern` — the span records the length
  asked for, and holds exactly that many tokens.
- **A reduced budget of zero is arithmetic, not a mode.** At `length: 1` there is nothing to ask
  the model for: write the row, complete with no tokens and `length`, save. This avoids
  `n_predict: 0`, whose behaviour is unverified and whose failure mode is an unbounded
  generation, and it keeps the operation reachable from the suite that has no model.
- **`begin_generation` grows an `origin` argument and sets `kind` from it, and the resolution
  from `(span, index, rank)` stays in `ops.py`.** The batch id, the seed derivation and the
  `slice_start` resolution are not reimplemented in `session.py`. The resolution carries two
  refusals and both must fire before any provenance is written, for the reason the empty-prompt
  guard gives: one junk span in flight per slip is a worse answer than the error.

**Addressing stays `(span, index, rank)`.** A token index is not recoverable from a position when
the token is zero-width, so folding this into `generate`'s signature would take the end-of-text
row out of reach of every client at once.

What moves in `FORMAT.md`: decision 5 and decision 9, the worked example, the operation table,
and checks 3, 5, 6 and 7. A counterfactual span now carries params, seed, batch, index,
slice_start and a terminator, and has one or more token rows of which exactly the first is the
counterfactual. **No marker bump**: every change is a relaxation, every existing tree still
validates, and `experiments/001` cannot be rebuilt.

## Decision 2 — the anchor is canonicalised at token index 0

A branch at token 0 anchors at `(span, 0)`, which names the same point as the span's own parent.
`ops.py:address_at` already fixes the canonical name for that point — the earlier span's tip, not
the later one's byte 0 — and this is the one place that does not follow it.

**It is a live fault, not a tidy-up.** `Tree.live` cuts `(s3, 0)` by making `s3` unreachable, and
every child anchored there goes with it. So deleting a span today also deletes the branch that
replaces its first token, which shares none of its bytes and which the reader was reading as the
alternative to it. Decision 1 makes it worse: what is lost stops being a one-token stub and
becomes a whole continuation.

The fix is the address. Attach at the origin span's own parent, and check 5 canonicalises both
sides. Two consequences: an index-0 branch off a root becomes a second root, which is already
legal; and the zero-width splice rule in `runs` stays, because an empty aborted span with two
children still reaches it.

## Decision 3 — `divergence` leaves the core

Out of `core/ops.py` and out of the API, into `loom.py`. **Analysis over stored rows is not an
operation on the trie.** `runs` stays where it is — it produces the structure the wire sends, and
implementing it twice is getting it wrong twice — and that is the line: `ops.py` owns what makes
or reads the structure, and a client owns what it computes over the record.

This reverses a position stated in `CLAUDE.md`, and the reversal is the point. The original
argument was that a client which cannot do it is short of the floor; that conflated *the CLI can
do this* with *the core must own it*, and the second does not follow. `ROADMAP-v1.0.md` already
records that `GET /api/divergence` has nothing to say about a tree the surface makes.

## Still to settle — the constituent tokens of a merged entry

**Offering a choice between the tokens that spell one character needs records the adapter throws
away today.** `_align` recovers each group from `return_tokens`, then stores the group as one row
with a null id and drops its alternatives, because a merged row must not claim the last
fragment's id for the whole group's bytes. So the breakdown is not a flyout change: it is a
question about what is recorded.

Three things stand in the way and only the first is bookkeeping. The constituent ids are known
but their individual bytes are not — the response carries the group's bytes, not each fragment's.
Only the group's *final* fragment has ranked alternatives at all, since `n_probs` is per entry
and entries are regrouped. And a per-fragment row would end the rule that a span's rows spell its
text in order, unless the fragments spell it between them, which needs those bytes.

The token-id prompt makes a second route available: ask the model at that exact position, with
`n_predict: 1`, and read the alternatives directly. That is a call per inspection rather than a
record, and it is the *ask the vocabulary, not the samples* move. **Decide which before building
either.** Nothing else in this pass is blocked on it.

---

## The order

Nothing here holds reasoning of its own. Each item points at what does.

### Stage A — the core changes

- [ ] Decision 2, first and alone. It is a fault in what is on disk now, it is small, and
      decision 1 makes its blast radius larger.
- [ ] Decision 1 in `core/`, with the six recipe items above and the new half of check 5.
- [ ] `core_test.py` reaches, on purpose: the pre-filled row surviving an abort as an ordinary
      counterfactual span; the shift, via check 5's new half; the reduced budget hitting zero;
      a branch at token 0 landing on the canonical anchor; a branch onto a byte-fallback token
      producing a span that now decodes.
- [ ] Decision 3. `divergence` and its route out; `loom.py` keeps the read.
- [ ] `POST /api/branch` takes `settings` and `n` and answers like `generate`; `web/api.mjs` and
      `loom.py branch` follow. This is the Stage 4 item *"they become one request shape"*,
      arriving early because the merge is what unifies them.

### Stage B — the repo

- [ ] The Python suites move to `tests/`: `core_test.py`, `api_test.py`, `llama_test.py`, and
      the new `cli_test.py`. `web/web_test.mjs` stays where it is — different runtime, different
      runner, already beside what it tests.
- [ ] `cli_test.py` takes `driver`, `cli_reads` and `capping_the_render` out of `core_test.py`.
      All three `import loom` and test the reference client rather than the substrate; the split
      line already exists and matches the shape the code has.
- [ ] The suites are still four scripts that print what they assert and why. **The pytest
      question is not reopened here**, but it has now been read once as a one-line rejection of a
      structural option — which is a warning sign this project takes seriously. If splitting does
      not relieve the pressure, it earns a worked comparison rather than another one-liner.

### Stage C — the documents

- [ ] `FORMAT.md` splits. What the format *is* — position, span, kinds, on-disk shape, worked
      example, bulk schema, the eight checks, the operation table — stands alone and reads in one
      pass with no arguments in it. The locked-decision prose, *Settled by measurement*, *What
      the build found* and the adapter rationale become the ledger beside it. Roughly 210 lines
      descriptive against 640 argumentative today.
      **The test: can someone implement a reader from the descriptive half alone?**
- [ ] Decisions 1, 2 and 3 are absorbed into the descriptive half as they now stand. Nothing in
      it says what it used to be.
- [ ] The empty-prompt probe's answer joins the measurements.
- [ ] `n_probs` and *rank 0 is not always the sampled token* are stated once. They are currently
      in both `CLAUDE.md` and `FORMAT.md`, which is the same missing seam seen from the other
      side.
- [ ] `CLAUDE.md` loses what stops being true: the *zero-width token cannot be clicked* passage
      becomes a `DIRECTION.md` pointer, the `divergence` justification goes, and the branch
      operation is described as it is.
- [ ] Delete this file.

Then `ROADMAP-v1.0.md`, which is surface and UX from its first line.
