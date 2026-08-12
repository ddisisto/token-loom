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

### 3. Runs own the byte→span mapping; spans own their extent

A run holds an ordered list of span fragments covering its bytes. Splitting a run divides
that list along with the bytes; no reverse pointers exist and nothing needs re-pointing.
This is what lets spans keep the roadmap's promise of never moving while runs move freely
underneath them, and it leaves room for the co-covering case — several spans over one byte
range — without building it now.

**Spans additionally record their own `extent`**, which the fragment lists do not make
retrievable without a full scan. It is safe to store because a span's extent is genuinely
immutable: splitting does not move bytes, and deletion is soft. The two are not redundant
and neither replaces the other:

- **The span's extent is the record** — what this generation call produced, self-describing
  in the way interned parameters are meant to keep it.
- **The fragment lists are the index** — which bytes are reachable on which path. This
  cannot be derived from extents, because sibling branches occupy overlapping absolute
  ranges and only the fragment list says which path a span sits on.

> **Authority.** Where they disagree, the span is right and the index is broken. Validate
> the tiling on load.

**Fragment offsets are span-relative, not run-relative** — `["s3", 9, 15]` means *bytes 9
to 15 of span s3*, not bytes 9 to 15 of the run. The run position is implied by
accumulation, since fragments tile the run in order from its start. Two reasons it is this
way round: the run-relative half is derivable and the span-relative half is not, and bulk
records are keyed `(span, index)`, so mapping a byte in a run to its token needs the offset
*within the span*. Getting this backwards is the easiest mistake in the whole format and
it fails quietly, so the load-time validator should check both frames — fragments
contiguous within each run, and contiguous within each span.

#### Deleting can bisect a span

A span written as one stretch can later cross a branch point, because splitting is what
creates branch points. In the worked example below, `s3` covers `r3` and `r4`; deleting the
`r4` branch while keeping `r5` removes bytes from the middle of a recorded span.

This is not a violation, but it needs stating so it is not mistaken for one. A span record
says **what was generated**, not what the tree currently reaches. Deletion removes
reachability; it does not unmake the historical fact, and under soft delete the bytes are
still in the store.

> **Rule.** Rendering and prompt assembly walk the fragment lists, never span extents. Read
> a span's extent as text and you will render bytes the tree no longer reaches.

#### Where this grows

Fragment lists are the growth surface, and they live in `tree.json`, which is rewritten on
save. Single-token stepping is the case that presses on it: stepping does not create a run
per token — a run only splits at a branch point, so consecutive steps extend one run — but
each step appends a fragment. At roughly 20 bytes a fragment, a fully single-stepped 100k
token tree is ~2MB of fragment list. Tolerable, and it is the worst case rather than the
expected one.

The escape hatch already exists if it stops being tolerable: fragment lists move to the
bulk store as another record type, which the roadmap's generality constraint permits
without a format change.

#### Alternatives considered

- **Spans point back at runs.** The obvious shape, and the one this replaces. Every split
  invalidates the pointers of every span ending in the split run.
- **Spans store their *starting* run**, on the theory that a split preserves the prefix's
  identity so the start never moves. It fails on splits *before* a span's start: split a run
  at byte 5 and a span starting at byte 10 now begins in the new suffix run. Tempting and
  wrong.
- **Spans store the path as a sequence of branch choices.** Child indices shift on delete,
  and child ids are run ids, which are the unstable thing being worked around.
- **No runs at all, trie over spans directly.** Branch points would have to split spans,
  which provenance forbids — so span fragments become the nodes, which is this design with
  worse names.

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

  "runs": {
    "r0": { "parent": null, "start": 0,  "text": "",             "spans": [],
            "children": ["r1"] },
    "r1": { "parent": "r0", "start": 0,  "text": "The sea was",  "spans": [["s1", 0, 11]],
            "children": ["r2", "r3"] },

    // batch b1, continuation 0 — never split, so one run, one span
    "r2": { "parent": "r1", "start": 11, "text": " calm for days",
            "spans": [["s2", 0, 14]], "children": [] },

    // batch b1, continuation 1 — split at the counterfactual branch point.
    // r3 kept its id and shrank; r4 is the new suffix and inherited the children.
    "r3": { "parent": "r1", "start": 11, "text": " calm and",
            "spans": [["s3", 0, 9]],  "children": ["r4", "r5"] },
    "r4": { "parent": "r3", "start": 20, "text": " clear",
            "spans": [["s3", 9, 15]], "children": [] },

    // the counterfactual branch: one token the model ranked but did not take
    "r5": { "parent": "r3", "start": 20, "text": " still",
            "spans": [["s4", 0, 6]],  "children": [] }
  },

  "spans": {
    "s1": { "kind": "human", "extent": [0, 11], "created": "2026-08-12-10.00.00" },

    "s2": { "kind": "sampled", "extent": [11, 25],
            "params": "p1", "seed": 90211, "batch": "b1", "index": 0,
            "slice_start": 0, "end": "length", "created": "2026-08-12-10.01.00" },
    "s3": { "kind": "sampled", "extent": [11, 26],
            "params": "p1", "seed": 90212, "batch": "b1", "index": 1,
            "slice_start": 0, "end": "length", "created": "2026-08-12-10.01.00" },

    "s4": { "kind": "counterfactual", "extent": [20, 26],
            "from": { "span": "s3", "index": 2 },
            "created": "2026-08-12-10.02.00" }
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

- **`s3` appears in two runs**, and its `extent` still reads `[11, 26]`. It was written as
  one stretch and later split; the fragment list divided with the bytes while the span
  record did not change, which is the promise in the roadmap made concrete. The extent is
  the record of the call; the fragments are where those bytes are now reachable.
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
| `split(position)` | the primitive; idempotent at an existing boundary |
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
   validator checks run tiling, the parent/child offset chain, span extents against their
   fragments, and contiguity in both the run and span frames.
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
