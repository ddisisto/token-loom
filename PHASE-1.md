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

#### Provenance is write-once; the byte record is append-only

A span cannot be written whole in one go, because generation records its intent *before* the
call and its bytes after — see decision 8, and `generate` under "What the core must do". The
two halves have different rules, and keeping them apart is what makes "immutable" precise
rather than aspirational:

- **Provenance** — `kind`, `params`, `seed`, `batch`, `index`, `slice_start`, `from`, and
  `extent[0]` — is known before the model is called, written once, and never touched again.
- **The byte record** — `text` and `extent[1]` — is empty at creation and filled in on
  completion. Filled in, never rewritten: a value that is there is final.

Nothing is ever overwritten under either rule, so the format stays semantically append-only.
The alternative — deriving a sampled span's text from its token rows, so a span really is
written in one shot — is cleaner and was rejected: it puts a bulk-store read in front of
every render and every prompt assembly, and leaves human spans holding text while sampled
ones do not.

### 3. Spans own the bytes; runs are structure over them

**Spans hold the text.** A span is a generated or authored stretch, and it holds its bytes,
its extent and its provenance. Once its bytes are written they are never touched again — not
by splitting, not by branching, not by deletion. (The one thing that happens to a span after
creation is its byte record being *filled in* when generation completes, per decision 2.
Nothing is ever overwritten.)

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

A piece is `[span, start, end)` — **half-open, and an end rather than a length**. Read
`["s3", 9, 15]` as a length and it claims 15 bytes from a 15-byte span starting at offset 9.
It is the same class of quiet mistake as the one below, and it is worth stating outright
because the two are only distinguishable by arithmetic.

Piece offsets are span-relative and can only be span-relative, since a piece names a range
*of a span*. The run-relative position is implied by accumulation. This was ambiguous while
runs carried their own text, and it was the easiest quiet mistake in the format; it is now
unrepresentable.

**Splitting, the prefix keeps the original id.** Split a run and the prefix stays under the
id it already had; the suffix is the new run. Ancestors' child lists therefore never change,
so a split is O(1) upward and touches only the run itself, its new suffix, and the children
being relinked.

This is also the concrete reason nothing durable may be keyed by a run id, which decision 1
asserts in the abstract: a stored run id keeps resolving after a split, but to *less text
than it did*. It does not dangle, which would be caught. It silently narrows, which is not.

#### Text is bytes in the core, and a string only at the edges

The roadmap says every offset is a byte offset. That is a claim about the *type* a span's
text is held in, not only about the arithmetic: `len` on a Python string counts characters,
so holding text as a string would make every extent, piece range and run start silently
wrong the first time a non-ASCII character appeared — and correct on every ASCII test.

So a span's text is `bytes`, and `run_bytes`, `path_bytes` and `piece_bytes` return bytes.
Decoding happens at exactly two edges: writing the tree file, and displaying a run.

The second edge is not merely a convention. A piece boundary is a token boundary, and
byte-level BPE can put a token boundary inside a character — so a *run's* bytes are not
guaranteed to decode on their own even when the whole path does. Anything that decodes a
fragment has to be prepared for that; anything inside the core avoids the question by not
decoding at all.

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

Because delete cascades to descendants, a span can only ever lose a *suffix*. Its byte-0
piece lives in the run that created it, and every later piece is in a descendant of that
run — so deleting the creating run takes the whole span with it. A span is therefore either
live with its head intact or entirely unreachable, never live-but-headless:

> **Invariant.** The live pieces of a span are non-overlapping and cover a contiguous prefix
> from byte 0 — possibly the whole span, possibly nothing.

#### Soft delete is a records decision, not a structural one

It is tempting to argue that deleted runs must be retained or recorded slices stop
resolving, since a slice is `[slice_start, extent[0])` along the span's ancestry and offsets
alone are not positions. That argument is wrong, and the reason is worth keeping:

> **Delete cascades forward; slices point backward. The two never meet.**

A slice runs from the span back toward the root, which is entirely ancestry, and deletion
cannot remove an ancestor without taking the descendant with it. So a reachable span's slice
is always resolvable — even under hard delete. The only spans whose slices would become
unresolvable are ones nothing reaches.

What soft delete actually buys is narrower and still worth having: a deleted subtree stays
inspectable, and delete stays reversible. Generated tokens cost real GPU time; that is
argument enough without inventing a structural one.

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
| temperature, top_p, top_n, length, stop list, model, tokenizer, n_ctx, prompt length | seed, call index, batch id, resolved slice start, timestamp |

Termination reason is on neither: it belongs to the bulk store, per decision 8.

**Prompt length interns; the resolved slice start does not.** Storing the slice start as an
absolute offset would make every position mint its own parameter set, defeating interning
across a session. Storing the *length* interns cleanly, and the span records the offset it
resolved to, so the exact slice is still recorded and clamping at the root is not
recomputed.

#### Units are mixed, so they are labelled

Three numeric parameters, two unit systems, and nothing in the names to tell them apart:

| field           | unit   | why                                              |
| --------------- | ------ | ------------------------------------------------ |
| `prompt_length` | bytes  | it is a slice length, and slices are byte ranges  |
| `length`        | tokens | it is `max_tokens` on the request                 |
| `n_ctx`         | tokens | it is the server's `--ctx-size`                   |

The mix is not an accident to be tidied away. The slice is chosen against the tree, which is
bytes; the limits are imposed by the model, which is tokens. Deriving one from the other
needs a tokenizer, which is exactly what the byte anchor exists to avoid depending on.

### 5. Bulk records are per token

Keyed `(span, index)`. Per-span records would be fewer but cannot grow, which is exactly
what an incomplete span needs; per-token records append naturally, make single-token
stepping structurally identical to a long run, and make the incomplete-span representation
nearly free.

**A counterfactual span gets a token row too**, for its single token. It costs one row and
buys uniformity: "walk the tokens of a span" then has no special case, and the branch is
described by the same records as the path it diverged from.

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

**The terminator record is the only place termination is written.** An `end` field on the
span would record the same fact twice, with a crash window between them and no rule saying
which wins. Two things settle it in favour of the bulk store:

- A span in `tree.json` would otherwise have to be *updated* when generation finishes, for a
  fact that is not part of its byte record — so decision 2's split between write-once
  provenance and append-only bytes would need a third category for it.
- Streaming appends tokens and then a terminator without touching the tree file at all. The
  terminator landing in sqlite is the atomic "done" signal, which is precisely what a
  separate `end` field would undermine.

In flight is legible from either half on its own: no terminator row, and `extent[1]` still
null. That redundancy is fine because both are *absences* — there is no pair of written
values that can disagree.

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
            "slice_start": 0, "created": "2026-08-12-10.01.00" },

    // never cut by the branch below — r3 and r4 reference parts of it
    "s3": { "kind": "sampled", "text": " calm and clear", "extent": [11, 26],
            "params": "p1", "seed": 90212, "batch": "b1", "index": 1,
            "slice_start": 0, "created": "2026-08-12-10.01.00" },

    // token_id, not rank: rank is only meaningful against the N that was requested
    "s4": { "kind": "counterfactual", "text": " still", "extent": [20, 26],
            "origin": { "span": "s3", "index": 2, "token_id": 2058 },
            "created": "2026-08-12-10.02.00" },

    // in flight: provenance written, byte record still empty
    "s5": { "kind": "sampled", "text": null, "extent": [26, null],
            "params": "p1", "seed": 90213, "batch": "b2", "index": 0,
            "slice_start": 0, "created": "2026-08-12-10.03.00" }
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
    "r4": { "parent": "r3", "start": 20, "pieces": [["s3", 9, 15]], "children": ["r6"] },

    // the counterfactual branch: one token the model ranked but did not take
    "r5": { "parent": "r3", "start": 20, "pieces": [["s4", 0, 6]],  "children": [] },

    // batch b2, in flight: an empty piece, widened when the bytes land
    "r6": { "parent": "r4", "start": 26, "pieces": [["s5", 0, 0]],  "children": [] }
  },

  "params": {
    "p1": { "temperature": 0.9, "top_p": 1, "top_n": 3,
            "length": 3,            // tokens
            "stop": [],
            "model": "qwen2.5-7b-base", "tokenizer": "qwen2.5",
            "n_ctx": 16384,         // tokens
            "prompt_length": 6000 } // bytes
  },

  "selected": { "run": "r4", "offset": 6 },
  "deleted": []
}
```

Six things to read off it:

- **`s3` still holds all fifteen of its bytes**, and is referenced in two pieces by two
  runs. The branch divided a piece list; the span was never opened. This is the roadmap's
  promise that spans never move, made true by construction rather than by discipline.
- **`r3` and `r5` both start at absolute offset 20.** Sibling branches share offsets, which
  is why an offset alone is not a position — the path is the other half.
- **`s4` has no parameters and no seed.** A counterfactual selection is not a generation
  call; it points at the span whose top-N it came from and carries nothing it never had.
  The field is `origin` rather than the more natural `from`, which is a Python keyword —
  a small ugliness in the format beats `from_` at every use site in the code.
- **`slice_start: 0` is on the span, `prompt_length: 6000` in the interned set.** Both
  continuations of batch `b1` share `p1`; a batch at a different position shares it too.
- **`s5` and `r6` are one generation call in flight**, joined by a **zero-length piece**.
  The span has provenance and no bytes; neither record becomes false if the process dies,
  and it loads as aborted. `r6` is also, exactly, the placeholder fork streaming will need.

  The empty piece is what links the two. An in-flight span has no bytes, so without it
  nothing connects `s5` to `r6` — and with two calls in flight at once, a crash would leave
  no way to tell which span belonged to which run. The alternative was a `run` field on the
  span, which would have introduced the one thing decision 1 forbids: a durable reference
  keyed by run id. Instead the link rides the existing mechanism, and completion *widens*
  the piece from `[0, 0]` to `[0, len]` rather than adding a second one. It also makes
  check 7 total, since even an in-flight span now has a piece to be positioned against.
- **`deleted` is a list of run ids**, and deleted runs stay in `runs` with their pieces
  intact. Soft delete removes reachability, not records.

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
-- reason: length | stop | eos | context | aborted
```

`bytes` is stored rather than derived. It is what the server returns, and encoding the
token string instead is lossy for exactly the byte-fallback tokens that split a UTF-8
character — the case byte anchoring exists to handle.

### What the validator checks

Two of these have a scope that matters, and getting the scope wrong makes the check fire on
correct trees or stay silent on broken ones.

Over **all runs**, live and deleted:

1. Every piece range is within its span: `0 <= start <= end <= len(span.text)`. An empty
   piece is legal only for a span with no bytes — one in flight, or one aborted before its
   first token arrived — and must be the last piece in its run, since the run cannot have
   grown past a span that never produced anything.
2. The offset chain holds: `run.start == parent.start + total length of parent's pieces`,
   and the root starts at 0.
3. Parent and child agree — every child names its parent, every parent lists its child.
4. **Strong coverage.** Every byte of every complete span is covered by exactly one piece,
   contiguously from 0. This is what the operations preserve; nothing may lose or duplicate
   a piece.

Over **live runs only**:

5. **Prefix coverage.** The live pieces of a span are non-overlapping and cover a contiguous
   prefix from byte 0 — possibly all of it, possibly none. This is the form that survives
   delete, per decision 3.

Per span:

6. `extent[1] - extent[0] == len(text)` for a complete span; `extent[1] is null` exactly
   when `text` is null.
7. `extent[0]` is where the span actually sits — the absolute offset of its byte-0 piece,
   computed from the run chain. Without this the one absolute number on a span can drift
   with nothing to catch it.
8. A complete span's `text` equals the concatenation of its token rows' `bytes`, with
   indices contiguous from 0. Human spans have no token rows at all; a counterfactual span
   has exactly one.
9. A complete **sampled** span has a terminator row. Only a sampled span was ever in flight —
   human and counterfactual spans are complete the moment they are created — so only they
   have anything to terminate.

Check 8 earns its keep three times over: it is the only thing that would catch byte-fallback
tokens being mishandled, it is what makes a `text` field and a `bytes` blob safe to hold the
same information, and it is the check a future vacuum has to pass — reclaim a token row
belonging to a live span and it fails immediately.

**A vacuum would retire check 4, not satisfy it.** As scoped in `ROADMAP.md`, vacuum is a
bulk-store operation and never touches `runs`, so check 4 is untouched by it. If it ever
grows a second job and purges soft-deleted runs from the tree, check 4 is exactly what
breaks — the span keeps all its bytes while the pieces covering its tail disappear, and
truncating the span to compensate is forbidden. Keep it as the alarm on that scope creep.

---

## What the core must do

Six operations. Everything in Phase 2 and 3 is built from these.

| operation | notes |
| --------- | ----- |
| `author(position, text)` | appends a human span; no tokens |
| `generate(position, params, n)` | one batch id, n spans, n seeds derived from the base |
| `split(position)` | the primitive; divides a piece list and relinks. The prefix keeps the run id. Idempotent at an existing boundary, and touches no span |
| `delete(run)` | cascades; soft, and the bulk store is untouched |
| `slice(position, length)` | resolves to `(start_abs, end_abs)` and the text to send |
| `branch_counterfactual(span, index, rank)` | splits, then appends a counterfactual span carrying the chosen `token_id` |

`split` is the one to get right first: generating from a mid-run position, branching to a
counterfactual, and moving a slice end all reduce to it.

`generate` is the one with an order that matters, because it straddles the model call and
decision 2 splits a span across it:

1. split if the position needs it, then create `n` child runs with empty piece lists
2. write `n` in-flight spans — provenance only — and **save the tree**. This is the intent
   record, and it is what makes a crash mid-generation legible rather than invisible
3. token rows append to the bulk store as they arrive
4. on completion, per span: fill `text` and `extent[1]`, append one piece to its run, write
   the terminator row

Every step after 1 is an append or a fill. Nothing is rewritten, and a crash at any point
leaves a tree that loads — with an aborted span holding however many tokens made it.

Saving the tree at step 2 rather than step 4 is also what keeps the bulk store free of
orphans in the crash case, not just the reachability one: because the span is written before
its first token, no bulk row can ever name a span the tree has not heard of. The ordering is
doing two jobs, and the second is the reason to resist reversing it for a saved write.

---

## Build order

Each step is verifiable on its own, which is what keeps the big-bang confined to Phase 2.

1. **Format module** — read and write `tree.json` and `bulk.sqlite`, with the load-time
   validator described under "What the validator checks". No generation. Verify by
   round-tripping the worked example above, and by confirming each check fires on a tree
   deliberately broken in that one way — a validator that has never rejected anything is an
   untested one.
2. **Core operations** — the six, over the format module. Verify with the headless driver
   on a tree built entirely by hand, no model involved.
3. **A native `llama-server` adapter**, not a patch to `inference.py` — see below.
4. **Generation into the core** — a session owning the tree, the store and the server, and
   with them the save ordering. First point at which a real model is needed.
5. **Headless driver** — author, generate, branch, split, dump. This is the deliverable
   that makes Phase 1 *usable*, not merely complete.

Phase 1 is done when a tree can be built, branched, split, saved, reloaded and dumped from
the command line, with per-token logprobs and counterfactuals intact across the round trip.

### Why the adapter is new code, not a patched `inference.py`

The original plan was to keep two fields `inference.py` discards. Reading it against what the
core actually needs, that was bolting onto the wrong thing.

**Most of it is unreachable.** `search` calls `client.Engine`, removed in the OpenAI SDK v1,
so it would raise rather than work. The AI21 chain — six functions — serves `j1-large` and
`j1-jumbo`, and Jurassic-1 is discontinued. `completions_text`, `save_response_json` and
`fix_openAI_token` are never called, the last carrying its own `TODO this doesn't work`.
`format_openAI_prompt` only runs when `echo=True`, which `llama-server` never is. About 120
of 373 lines are live, and most of that is provider-quirk plumbing — `drop_params`, echo,
the placeholder API key, OpenRouter's `extra_body` — that one local server needs none of.

**And `seed` is not in the request path at all.** Neither `openAI_generate` nor
`DEFAULT_GENERATION_SETTINGS` carries it. Per-span seeds derived from a base are how N
continuations differ and how a tree replays; so the work was never "keep two fields", it was
"add the parameter the design rests on, to a request builder shaped for a different data
model, whose output shape the core then has to unpick".

**The endpoint choice follows from something upstream of it.** No hosted provider can feed
the token core: it needs per-token ids, bytes and logprobs on a *raw continuation*, and no
OpenRouter provider returns logprobs on its completions endpoint. Keeping an
OpenAI-compatible shape to preserve hosted reach would preserve nothing usable. Measured
against the running server, both endpoints return an identical token payload — `{id, token,
bytes, logprob, top_logprobs}` — so the native one is chosen for what it adds around that:

- **`stop_type`** separates `eos` from `word` from `limit`. The compatible layer flattens the
  first two into `finish_reason: stop`, losing exactly the distinction worth recording —
  whether the model chose to stop or an operator's stop string matched.
- **`tokens_evaluated`** comes back without asking, which is what the context-limit
  derivation needs.

`inference.py`, `models.py` and `params.py` are left untouched and die together in Phase 2,
rather than leaving a half-migrated registry behind. The cost, accepted deliberately: the
capability table stops being the extension point, so a hosted provider later means a second
adapter rather than one dict entry.

### Two things the server settled that the plan had guessed at

**`n_probs` is not optional.** Requesting zero counterfactuals returns no
`completion_probabilities` at all — and with it go the per-token *bytes*, not just the
alternatives. There is no token overlay to store without them, so `top_n >= 1` is a hard
requirement rather than a default worth quietly applying.

**Rank 0 is not always the token that was sampled.** At temperature 1.0, three of twelve
sampled tokens were absent from their own top-3. The worked example above happens to show
the sampled token at rank 0 and should not be read as a rule: the `tokens` and
`counterfactuals` tables are independent records, which is why they are separate tables.

---

## Settled: a token can be a fragment of a character

This was carried as an open question, on the grounds that waiting to observe one could never
close it — absence only ever means the case has not come up yet. The decidable form is the
vocabulary, and it turned out cheap to ask: tokenise text the merges will not have covered,
and look at whether any single token's bytes are valid UTF-8 alone.

Against Qwen2.5 they are not. A single alchemical symbol `🜁` — four UTF-8 bytes — comes back
as **three tokens, none of them valid alone**. Rare scripts, historic scripts and emoji all
behave the same way; ordinary English does not. So this is reachable in ordinary use rather
than a corner case, and two things follow.

**A span can end mid-character**, when a length limit falls inside one. Its bytes then have
no string form, and `tree.json` is JSON. Of the three candidates — an escape, dropping the
trailing partial token, or refusing to stop mid-character at the generation layer — **the
escape wins**, as `{"b64": …}` in place of the usual string:

> Dropping the token would make the tree disagree with what the model emitted, which is the
> one thing every other decision here is arranged to prevent. Being unreadable by eye costs
> nothing in exchange, given the bytes in question are half a character.

`null` keeps meaning *in flight* and nothing else; a string and an object are the two
complete forms.

**A slice start can land mid-character**, which is the more disruptive half and was not on
the list at all. `prompt_length` is in bytes, so subtracting it lands wherever it lands — and
the prompt has to be decoded to be sent. `slice_at` therefore nudges the start forward to the
next character boundary *before* the span records it, so `slice_start` describes the slice
that was used rather than the one that was asked for.

What remains, deliberately unhandled: a generation point placed inside a character. The
prompt then genuinely has no string form, and the adapter raises rather than guessing.
Fixing it properly means sending token ids instead of text — the token-replay path in
`BEYOND-MVP.md` — which needs mixed-mode assembly, since human spans have no tokens. Not
worth pulling forward for a case that requires branching inside an emoji on purpose.

## Not in Phase 1

- Any UI, any HTTP surface. Phase 2.
- Migration. `data/local.json` becomes archive JSON.
- Vacuum. Soft delete only; the append-only store makes it nearly free to defer.
- Streaming, though the incomplete-span state it needs is here.
- Editing, at any layer, ever.
- Co-covering spans, prefix merging, embeddings. See `BEYOND-MVP.md` — the shapes above
  leave room for them; nothing builds them.
