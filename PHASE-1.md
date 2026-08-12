# Phase 1 — the token core

The detailed plan for the one format change, to iterate over before any code exists.
`ROADMAP.md` holds the why; this holds the shape. When Phase 1 lands this file is
superseded by the code and should be deleted rather than maintained.

**Phase 1 is additive to the repo.** Nothing here deletes the current front end — new
modules land alongside it, and the only change to existing code is `inference.py` keeping
two fields it currently discards, which is backward compatible. The old instrument keeps
working throughout, and is tagged `pre-token-core` besides. The clean break happens in
Phase 2.

---

## Locked decisions

### 1. Offsets are absolute; runs are not identity

A position is `(run, offset within run)`, and its **absolute offset** is
`run.start + offset`. Absolute offsets are assigned once, when bytes are written, and never
change.

> **Invariant.** Splitting a run changes no absolute offset and invalidates no recorded
> slice.

This is the load-bearing one. Run identity is *not* stable — splitting a run produces two
runs where there was one — so nothing durable may be keyed by it. Slices, spans and
bookmarks are keyed by absolute offsets and resolved to runs by lookup.

### 2. Nothing is editable in place

Recorded bytes are immutable. Delete cascades. There is no edit operation at any layer, and
`PATCH /api/node/{id}` does not survive into the new API.

This retires the slice hash that was proposed as a staleness check: with bytes immutable,
recorded bounds are faithful by construction, so there is nothing to detect.

### 3. Spans own the bytes; runs are structure over them

**Spans hold the text.** A span is a generated or authored stretch, and it holds its bytes,
its extent and its provenance. It is written once and never touched again — not by
splitting, not by branching, not by deletion.

**Runs hold no bytes at all.** A run is an ordered list of *pieces*, each naming a span and
a range within it, plus a parent and children. Its text is the concatenation of its pieces
resolved against their spans.

Splitting is then arithmetic on integers. Divide the piece list, relink the children, done —
no bytes move, no span is opened, and the operation cannot corrupt a record because it never
touches one.

```jsonc
"s3": { "text": " calm and clear", "extent": [11, 26], … }   // written once, never cut
"r3": { "pieces": [["s3", 0, 9]],  "children": ["r4", "r5"] } // " calm and"
"r4": { "pieces": [["s3", 9, 15]], "children": [] }           // " clear"
```

Piece offsets are span-relative and can only be span-relative, since a piece names a range
*of a span*. The run-relative position is implied by accumulation. This was ambiguous while
runs carried their own text, and it was the easiest quiet mistake in the format; it is now
unrepresentable.

There is also **exactly one copy of every byte**, so there is no authority question between
a run's text and a span's extent, and nothing to validate for agreement. The earlier design
stored the bytes twice — once as `run.text`, once implied by span extents — and needed a
rule about which won. The rule was covering for redundancy that should not have existed.

#### Why not overlapping runs referencing an uncut original

The instinct — *do not cut r3; make a new run that references its first 9 bytes* — is the
right one, and the above is where it lands. But taken literally, with `r3` left whole as a
sibling of the new run, it breaks two things.

**It stops being a trie.** `r1`'s children become several runs that all start at the same
absolute offset and overlap by construction, and the fact that two of them share their first
20 bytes is no longer visible in the structure — it has to be recovered by comparing
reference ranges. Divergence being structural is what the trie is *for*.

**Navigation inverts.** "What branches from here" is a child list in a trie. With overlapping
siblings it becomes "find every run referencing this owner whose range ends at this offset" —
a scan, on the most common read there is.

And it does not actually avoid the split. Branch `r3` at 20, then at 40, and the second
branch needs a run covering exactly `[20, 40)` — so the range gets divided anyway. The
mutation moves from the text to the range, and the structural churn is identical. What
survives from the instinct is the part that was genuinely wrong before: **the original is
never cut, because the original is the span, and runs were never the right place for bytes.**

#### Deleting can bisect a run, never a span

A span written as one stretch can later be referenced by runs on either side of a branch
point, because splitting is what creates branch points. In the worked example, `r3` and `r4`
both reference `s3`; deleting the `r4` branch while keeping `r5` removes one of them.

Nothing is lost. `s3` still holds all fifteen of its bytes, because runs were only ever
pointing at them. The tree stops *reaching* part of a span; the record of what was generated
is untouched — which is now true by construction rather than by rule.

> **Rule.** Rendering and prompt assembly walk the piece lists, never span extents. A span's
> text is what was generated; the pieces are what the tree still reaches.

#### Where this grows

Piece lists are the growth surface, and they live in `tree.json`, which is rewritten on save.
Single-token stepping presses on it: stepping does not create a run per token — a run only
splits at a branch point, so consecutive steps extend one run — but each step appends a
piece. At roughly 20 bytes a piece, a fully single-stepped 100k-token tree is ~2MB of piece
list. Tolerable, and the worst case rather than the expected one.

The escape hatch already exists: piece lists move to the bulk store as another record type,
which the roadmap's generality constraint permits without a format change.

One cost to note against the goal of a human-readable tree file: runs no longer read as
text, so eyeballing `tree.json` means following pieces into spans. The text is all still
there, one level of indirection away, and the headless driver's dump is the answer for
reading a tree by eye.

#### Alternatives considered

- **Runs hold text, spans hold fragments into it.** The previous version of this decision.
  Works, but stores every byte twice and needs an authority rule to arbitrate.
- **Overlapping runs over an uncut original.** Above — loses the trie and inverts navigation.
- **Spans point back at runs.** Every split invalidates the pointers of every span ending in
  the split run.
- **Spans store their *starting* run**, on the theory that a split preserves the prefix's
  identity so the start never moves. It fails on splits *before* a span's start: split a run
  at byte 5 and a span starting at byte 10 now begins in the new suffix run. Tempting and
  wrong.
- **Spans store the path as a sequence of branch choices.** Child indices shift on delete,
  and child ids are run ids, which are the unstable thing being worked around.
- **No runs at all, trie over spans directly.** Branch points would have to split spans,
  which provenance forbids.

### 4. Interned versus per-span

> **Rule.** The interned set holds what is shared across a generation call. Anything that
> varies per call lives on the span.

The trap this exists to avoid: seed varies per call by design (base seed plus call index).
Put it in the interned set and every call mints a new entry — under single-token stepping,
one table row per token, strictly worse than not interning at all.

| interned (shared)                                            | on the span (varies)                            |
| ------------------------------------------------------------ | ----------------------------------------------- |
| temperature, top_p, top_n, length, stop list, model, tokenizer, n_ctx, prompt length | seed, call index, batch id, resolved slice start, termination reason, timestamp |

**Prompt length interns; the resolved slice start does not.** Storing the slice start as an
absolute offset would make every position mint its own parameter set, defeating interning
across a session. Storing the *length* interns cleanly, and the span records the offset it
resolved to, so the exact slice is still recorded and clamping at the root is not
recomputed.

### 5. Bulk records are per token

Keyed `(span, index)`. Per-span records would be fewer but cannot grow, which is exactly
what an incomplete span needs; per-token records append naturally, make single-token
stepping structurally identical to a long run, and make the incomplete-span representation
nearly free.

### 6. sqlite for bulk, JSON for the tree

The tree file stays small, human-readable JSON. The bulk store is sqlite: random access
without loading, an index for the intern table, and somewhere for embeddings to land later.

Per the roadmap's generality constraint, **a new record type is a new table, not a new
mechanism** — the store is not shaped around tokens, they are merely its first tenant.

### 7. Tokenizer identity is explicit

A `tokenizer` field in `models.py`, defaulting to the model id. The model name is the wrong
proxy: two quants of one model share a tokenizer, and this is the exact fact that token
replay safety turns on later.

### 8. In-flight is a state, not a null

A span with no terminator record is in flight. On load, a span left in flight by a process
that is gone loads as `aborted`. Without the load-time rule, spans accumulate that are
permanently "maybe still running".

---

## On-disk shape

A tree is a directory, so its two halves cannot be separated:

    data/<name>/tree.json      # structure, spans, interned parameters
    data/<name>/bulk.sqlite    # per-token records

### Worked example

The root, one authored prompt, and a batch of two continuations — the second of which was
then branched from a counterfactual at its third token.

```jsonc
{
  "format": "token-loom/1",
  "tree_id": "…",
  "base_seed": 90210,
  "root": "r0",

  // spans hold the bytes, and are written once
  "spans": {
    "s1": { "kind": "human", "text": "The sea was", "extent": [0, 11],
            "created": "2026-08-12-10.00.00" },

    "s2": { "kind": "sampled", "text": " calm for days", "extent": [11, 25],
            "params": "p1", "seed": 90211, "batch": "b1", "index": 0,
            "slice_start": 0, "end": "length", "created": "2026-08-12-10.01.00" },

    // never cut by the branch below — r3 and r4 reference parts of it
    "s3": { "kind": "sampled", "text": " calm and clear", "extent": [11, 26],
            "params": "p1", "seed": 90212, "batch": "b1", "index": 1,
            "slice_start": 0, "end": "length", "created": "2026-08-12-10.01.00" },

    "s4": { "kind": "counterfactual", "text": " still", "extent": [20, 26],
            "from": { "span": "s3", "index": 2 },
            "created": "2026-08-12-10.02.00" }
  },

  // runs hold no bytes: pieces name a span and a range within it
  "runs": {
    "r0": { "parent": null, "start": 0,  "pieces": [],              "children": ["r1"] },
    "r1": { "parent": "r0", "start": 0,  "pieces": [["s1", 0, 11]], "children": ["r2", "r3"] },

    // batch b1, continuation 0 — never branched, so one run, one whole span
    "r2": { "parent": "r1", "start": 11, "pieces": [["s2", 0, 14]], "children": [] },

    // batch b1, continuation 1 — branched at the counterfactual point. The split
    // divided r3's piece list; s3 itself was not opened.
    "r3": { "parent": "r1", "start": 11, "pieces": [["s3", 0, 9]],  "children": ["r4", "r5"] },
    "r4": { "parent": "r3", "start": 20, "pieces": [["s3", 9, 15]], "children": [] },

    // the counterfactual branch: one token the model ranked but did not take
    "r5": { "parent": "r3", "start": 20, "pieces": [["s4", 0, 6]],  "children": [] }
  },

  "params": {
    "p1": { "temperature": 0.9, "top_p": 1, "top_n": 3, "length": 4, "stop": [],
            "model": "qwen2.5-7b-base", "tokenizer": "qwen2.5",
            "n_ctx": 16384, "prompt_length": 6000 }
  },

  "selected": { "run": "r4", "offset": 6 },
  "deleted": []
}
```

Four things to read off it:

- **`s3` still holds all fifteen of its bytes**, and is referenced in two pieces by two
  runs. The branch divided a piece list; the span was never opened. This is the roadmap's
  promise that spans never move, made true by construction rather than by discipline.
- **`r3` and `r5` both start at absolute offset 20.** Sibling branches share offsets, which
  is why an offset alone is not a position — the path is the other half.
- **`s4` has no parameters and no seed.** A counterfactual selection is not a generation
  call; it points at the span whose top-N it came from and carries nothing it never had.
- **`slice_start: 0` is on the span, `prompt_length: 6000` in the interned set.** Both
  continuations of batch `b1` share `p1`; a batch at a different position shares it too.

### Bulk store

```sql
CREATE TABLE tokens (
  span TEXT, idx INTEGER, token_id INTEGER, bytes BLOB, logprob REAL,
  PRIMARY KEY (span, idx)
);
CREATE TABLE counterfactuals (
  span TEXT, idx INTEGER, rank INTEGER, token_id INTEGER, bytes BLOB, logprob REAL,
  PRIMARY KEY (span, idx, rank)
);
CREATE TABLE terminators (          -- a span is complete when its row lands
  span TEXT PRIMARY KEY, reason TEXT, written TEXT
);
```

`bytes` is stored rather than derived. It is what the server returns, and encoding the
token string instead is lossy for exactly the byte-fallback tokens that split a UTF-8
character — the case byte anchoring exists to handle.

---

## What the core must do

Six operations. Everything in Phase 2 and 3 is built from these.

| operation | notes |
| --------- | ----- |
| `author(position, text)` | appends a human span; no tokens |
| `generate(position, params, n)` | one batch id, n spans, n seeds derived from the base |
| `split(position)` | the primitive; divides a piece list and relinks. Idempotent at an existing boundary, and touches no span |
| `delete(run)` | cascades; soft, and the bulk store is untouched |
| `slice(position, length)` | resolves to `(start_abs, end_abs)` and the text to send |
| `branch_counterfactual(span, index, rank)` | splits, then appends a counterfactual span |

`split` is the one to get right first: generating from a mid-run position, branching to a
counterfactual, and moving a slice end all reduce to it.

---

## Build order

Each step is verifiable on its own, which is what keeps the big-bang confined to Phase 2.

1. **Format module** — read and write `tree.json` and `bulk.sqlite`, with the load-time
   validator. No generation. Verify by round-tripping the worked example above; the
   validator checks piece ranges against span lengths, the parent/child offset chain, each
   span's extent against its own text, and that every span's bytes are covered by pieces
   exactly once and contiguously.
2. **Core operations** — the six, over the format module. Verify with the headless driver
   on a tree built entirely by hand, no model involved.
3. **`inference.py`** — keep the token `id` and `bytes` array, key counterfactuals by id.
   Additive; the current front end is unaffected.
4. **Generation into the core** — wire `generate` to `inference.gen`, writing spans and
   bulk records. First point at which a real model is needed.
5. **Headless driver** — author, generate, branch, split, dump. This is the deliverable
   that makes Phase 1 *usable*, not merely complete.

Phase 1 is done when a tree can be built, branched, split, saved, reloaded and dumped from
the command line, with per-token logprobs and counterfactuals intact across the round trip.

---

## Not in Phase 1

- Any UI, any HTTP surface. Phase 2.
- Migration. `data/local.json` becomes archive JSON.
- Vacuum. Soft delete only; the append-only store makes it nearly free to defer.
- Streaming, though the incomplete-span state it needs is here.
- Editing, at any layer, ever.
- Co-covering spans, prefix merging, embeddings. See `BEYOND-MVP.md` — the shapes above
  leave room for them; nothing builds them.
