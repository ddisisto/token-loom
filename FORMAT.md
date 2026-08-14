# The format

What the on-disk shape is, and why it is that shape. `ROADMAP.md` holds direction and
phases; this holds the format and the reasoning that is expensive to reconstruct. It is
meant to outlive the phases — Phase 2 replaces the interface, not this.

**Status.** `token-loom/1` is what Phase 1 built and what `core/` currently implements.
`token-loom/2` is the amendment described here: it deletes runs and pieces from the format
and replaces them with a **parent address on each span**. Everything else — spans,
provenance, the intern table, the bulk store, the save ordering — is untouched. Until the
amendment lands, read this as the plan and `core/tree.py` as the current truth.

The amendment came out of using the thing rather than out of planning it, which is worth
noting: ten faults fell out of stress-testing the `token-loom/1` plan in prose, and this
eleventh fell out of the first honest use. Both stages were load-bearing, and neither would
have found the other's bugs.

---

## The change, in one paragraph

In `token-loom/1` a branch could only hang off a *node*, because a run's parent was a run
id. Manufacturing a node boundary at a mid-run position is what `split` existed to do, and
`split` is upstream of nearly everything awkward in the format: the piece list, the cursor
fixup, five of nine validator checks, the maintained absolute-offset chain. Let a span's
parent be an **address** — `[span, byte offset]` — and branching mid-span is just *a child
anchored at offset 9*. Nothing divides, nothing relinks, and `split` does not get simpler;
it stops existing. Runs survive as a **derived** grouping for display, computed at load,
stored nowhere.

---

## Locked decisions

### 1. A position is `(span, offset)`

A span is written once, never cut, and holds every byte it ever had. That makes
`(span, offset)` invariant under every operation there is, and it is the only address the
format uses — for a span's parent, for the cursor, for deletion, for a recorded slice start,
and on the Phase 2 wire.

> **Invariant.** No operation opens a span, so no operation invalidates an address.

It is strictly stronger than an absolute byte offset, which is what `token-loom/1` used.
An absolute offset does not identify a path — sibling branches share offsets, so resolving
one needed a run id alongside it, which smuggled the unstable thing back in through the
argument list. A span's bytes lie along exactly one root-to-leaf chain, so naming the span
names the path.

Absolute offsets remain useful and are **derived**: sum the lengths along the parent chain.
Nothing stores one. That also makes an exported subtree self-contained, which a
root-relative offset is not — span addresses travel, and that matters for the
comparison-across-trees work in `BEYOND-MVP.md`.

### 2. Nothing is editable in place

Recorded bytes are immutable. Delete cascades. There is no edit operation at any layer, and
`PATCH /api/node/{id}` does not survive into the new API.

This retires the slice hash that was once proposed as a staleness check: with bytes
immutable, recorded bounds are faithful by construction, so there is nothing to detect.

#### Provenance is write-once; the byte record is append-only

A span cannot be written whole in one go, because generation records its intent *before*
the call and its bytes after — see decision 8, and `generate` under "What the core must do".
The two halves have different rules, and keeping them apart is what makes "immutable"
precise rather than aspirational:

- **Provenance** — `kind`, `parent`, `params`, `seed`, `batch`, `index`, `slice_start`,
  `origin` — is known before the model is called, written once, and never touched again.
- **The byte record** — `text` — is empty at creation and filled in on completion. Filled
  in, never rewritten: a value that is there is final.

Nothing is ever overwritten under either rule, so the format stays semantically
append-only. The alternative — deriving a sampled span's text from its token rows, so a
span really is written in one shot — is cleaner and was rejected: it puts a bulk-store read
in front of every render and every prompt assembly, and leaves human spans holding text
while sampled ones do not.

### 3. Spans are the structure

A span is a generated or authored stretch. It holds its bytes, its provenance, and **one
address naming where it continues from**. That is the whole of the structure.

```jsonc
"s3": { "text": " calm and clear", "parent": ["s1", 11], … }  // continues after s1
"s4": { "text": " still",          "parent": ["s3",  9], … }  // branches inside s3
```

`s3` is never cut. `s4` hangs off byte 9 of it, and the fact that `s3`'s own bytes continue
past 9 is not a conflict — it is what a branch point *is*. Which of `s3`'s bytes are on the
path is determined by which child you descend into: descend to `s4` and you read `s3[0:9]`;
descend to whatever continues after `s3` and you read all of it. That was exactly what a
piece encoded, and it is now derived rather than stored.

A span with `parent: null` is a root. Several may coexist, which is how several initial
prompts sit side by side — the empty root run `token-loom/1` needed for that is gone with
everything else.

#### Runs are derived, and still worth the word

A **run** is a maximal chain of spans with no branch point in it. Phase 2 lays out by runs
and `ROADMAP.md` reads by them; the word is accurate and stays. What changes is that it is
computed from the span tree at load, not stored — so there is exactly one representation of
any given tree, where `token-loom/1` could reach the same tree by two different paths and
had nothing to merge them back.

Do not call it a *view*: Phase 3 already has a viewport (the slice window), and it is a
different thing.

#### Text is bytes in the core, and a string only at the edges

The roadmap says every offset is a byte offset. That is a claim about the *type* a span's
text is held in, not only about the arithmetic: `len` on a Python string counts characters,
so holding text as a string would make every offset and every parent address silently wrong
the first time a non-ASCII character appeared — and correct on every ASCII test.

So a span's text is `bytes`, and everything in the core returns bytes. Decoding happens at
exactly two edges: writing the tree file, and displaying text.

The second edge is not merely a convention. A parent offset is a token boundary, and
byte-level BPE can put a token boundary inside a character — so the bytes on one side of a
branch point are not guaranteed to decode on their own even when the whole path does.
Anything that decodes a fragment has to be prepared for that; anything inside the core
avoids the question by not decoding at all.

There is also **exactly one copy of every byte**, and now exactly one representation of
where it sits. An earlier design stored the bytes twice — once as `run.text`, once implied
by span extents — and needed a rule about which won. The rule was covering for redundancy
that should not have existed. `token-loom/1` removed the second copy of the bytes;
`token-loom/2` removes the second copy of the structure.

#### Deletion is an address, and can bisect a span

`deleted` is a list of addresses. `[s3, 9]` means **nothing continues past byte 9 of `s3`**:
`s3`'s own bytes from 9 onward are unreachable, and every span anchored at offset 9 or later
is unreachable with them.

A whole span is the offset-0 case. `[s4, 0]` deletes `s4` and everything under it and
touches nothing else — which is how one fork is deleted while its sibling survives. One
address type covers both, where `token-loom/1` needed a run id for the fork case and a
split-then-delete for the truncation case.

Nothing is lost. `s3` still holds all fifteen of its bytes; the tree stops *reaching* part
of it. And the invariant `token-loom/1` had to check —

> The live pieces of a span cover a contiguous prefix from byte 0, possibly none of it.

— stops being a property to verify and becomes the literal representation. A deletion
address *is* a prefix bound.

Entries are **not** deduplicated against each other, and the list may hold one address that
another already covers. `token-loom/1` had to keep its list to maximal roots because
liveness was a walk over run ids that a nested entry would confuse; liveness here takes the
least cut per span, so it is total over any set. Pruning would actively break undo — drop
the narrower entry and restoring the wider one resurrects a subtree that was deleted
separately and never restored. Deleting something already unreachable stays a no-op, which
is what keeps the list from growing on repeated calls.

#### Soft delete is a records decision, not a structural one

It is tempting to argue that deleted spans must be retained or recorded slices stop
resolving, since a slice runs from a span back toward the root. That argument is wrong, and
the reason is worth keeping:

> **Delete cascades forward; slices point backward. The two never meet.**

A slice is entirely ancestry, and deletion cannot remove an ancestor without taking the
descendant with it. So a reachable span's slice is always resolvable — even under hard
delete. The only spans whose slices would become unresolvable are ones nothing reaches.

What soft delete actually buys is narrower and still worth having: a deleted subtree stays
inspectable, and delete stays reversible. Generated tokens cost real GPU time; that is
argument enough without inventing a structural one.

#### Where this grows

One parent address per span, in `tree.json`, which is rewritten on save. `token-loom/1`
appended one piece per span to a run's piece list and sized it at ~20 bytes; a parent
address is about the same. **This is not a size win and should not be sold as one** — a
fully single-stepped 100k-token tree is a couple of megabytes of `tree.json` either way, and
the escape hatch is the same one: the growth surface moves to the bulk store as another
record type, which the roadmap's generality constraint permits without a format change.

What it does refund is readability. `ROADMAP.md` booked "the tree file is no longer
*readable* as prose" as an accepted cost of one copy of every byte. It was not: it was the
cost of the pieces. With spans holding both their text and their attachment, following a
path by eye is following `parent` links between strings.

#### Why not overlapping runs referencing an uncut original

The `token-loom/1` plan rejected this at length, and the reasoning was sound — it is worth
keeping precisely because it looks like it should defeat parent addresses too, and does not.
Three arguments, each against overlapping sibling runs holding *ranges* of a shared span:

**It stops being a trie.** Siblings all start at the same absolute offset and overlap by
construction; that two of them share their first 20 bytes has to be recovered by comparing
reference ranges. — *Does not transfer.* Two spans sharing a parent address are visibly
siblings; two spans at different offsets of one parent are visibly different branch points.
Divergence stays structural, which is what the trie is for.

**Navigation inverts.** "What branches from here" becomes "find every run referencing this
owner whose range ends at this offset" — a scan, on the most common read there is. —
*Does not transfer.* That is a range query over overlapping ranges. A parent address is a
point, so it is exact match, answered by an index built at load: `span → [(offset, child)]`,
O(n) to build and O(1) to query. For comparison, `token-loom/1` scans **every run** in both
`pieces_of` and `widen`.

**It does not actually avoid the split.** Branch at 20, then at 40, and the second branch
needs a run covering exactly `[20, 40)` — the range gets divided anyway, so the churn is
identical. — *Does not transfer.* There is no range to divide. Branch `s3` at 9 and again at
12 and you have two children carrying two different parent offsets. Nothing is divided at
all, which is the point at which the two designs genuinely part company.

#### Alternatives considered

Carried forward, with the one that won added and the one that nearly stopped it corrected.

- **Runs hold text, spans hold fragments into it.** Stores every byte twice and needs an
  authority rule to arbitrate.
- **Overlapping runs over an uncut original.** Above.
- **Spans point back at runs.** Every split invalidates the pointers of every span ending
  in the split run.
- **Spans store their *starting* run**, on the theory that a split preserves the prefix's
  identity so the start never moves. It fails on splits *before* a span's start: split a run
  at byte 5 and a span starting at byte 10 now begins in the new suffix run. Tempting and
  wrong.
- **Spans store the path as a sequence of branch choices.** Child indices shift on delete,
  and child ids are run ids, which are the unstable thing being worked around.
- **Runs hold ordered pieces of spans.** What `token-loom/1` built. Correct, and larger than
  the problem.
- **No runs at all, trie over spans directly** — **chosen.** The `token-loom/1` plan
  rejected this in a single line: *"Branch points would have to split spans, which
  provenance forbids."* That holds only if a trie edge must point at a whole node. Let the
  edge carry a byte offset into its parent and a mid-span branch point needs no cut.

> **The lesson, which is the expensive part to re-learn.** Three of those six rejections
> turn on run ids being unstable. The design worked around the instability rather than
> removing its cause, and the one option that removed the cause was dismissed in a sentence
> aimed at a variant nobody had written down. A rejection that short, against an option that
> structural, deserved a worked counterexample. It cost a format version — cheaply, because
> the code was a day old and there was no data to migrate, but it would not always be cheap.

#### What this deletes

| gone | what it was for |
| --- | --- |
| `runs`, `pieces` | somewhere to put branch structure, when an edge could only name a node |
| `split` | manufacturing a node boundary at a mid-run position |
| the zero-length piece | the only link between an in-flight span and its run |
| `run.start`, `span.extent` | absolute offsets, maintained as stored state |
| `at`, `absolute`, `locate`, `widen`, `_attach` | conversions between two coordinate systems |
| the `selected` fixups in `split` and `delete` | reseating a cursor whose address had narrowed |
| validator checks 1, 2, 4, 5, 7 | a redundant representation agreeing with itself |
| the extend-vs-branch rule in `_attach` | a storage shape with no semantic content |

Nothing in the bulk store changes. It is keyed by span id throughout and never mentions a
run, which is the clearest signal that this change is in the right layer.

### 4. Interned versus per-span

> **Rule.** The interned set holds what is shared across a generation call. Anything that
> varies per call lives on the span.

The trap this exists to avoid: seed varies per call by design (base seed plus call index).
Put it in the interned set and every call mints a new entry — under single-token stepping,
one table row per token, strictly worse than not interning at all.

| interned (shared) | on the span (varies) |
| --- | --- |
| temperature, top_p, top_n, length, stop list, model, tokenizer, n_ctx, prompt length | seed, call index, batch id, resolved slice start, timestamp |

Termination reason is on neither: it belongs to the bulk store, per decision 8.

**Prompt length interns; the resolved slice start does not.** Storing the slice start as a
parameter would make every position mint its own parameter set, defeating interning across a
session. Storing the *length* interns cleanly, and the span records the address it resolved
to — so the exact slice is still recorded, and clamping at the root is not recomputed.

`slice_start` is an address like everything else, which is a change from `token-loom/1`
where it was an absolute offset. It was the last root-relative number in the record, and the
only one that could not be mechanically rebased on export.

#### Units are mixed, so they are labelled

Three numeric parameters, two unit systems, and nothing in the names to tell them apart:

| field | unit | why |
| --- | --- | --- |
| `prompt_length` | bytes | it is a slice length, and slices are byte ranges |
| `length` | tokens | it is `max_tokens` on the request |
| `n_ctx` | tokens | it is the server's `--ctx-size` |

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

A `tokenizer` field, defaulting to the model id. The model name is the wrong proxy: two
quants of one model share a tokenizer, and this is the exact fact that token replay safety
turns on later.

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

In flight is legible from either half on its own: no terminator row, and `text` still null.
That redundancy is fine because both are *absences* — there is no pair of written values
that can disagree.

An in-flight span needs no special link to the structure any more. It carries its own
parent address from the moment it is created, which is what the zero-length piece was
standing in for, and it is exactly the placeholder fork streaming will need.

---

## On-disk shape

A tree is a directory, so its two halves cannot be separated:

    data/<name>/tree.json      # spans and interned parameters
    data/<name>/bulk.sqlite    # per-token records

### Worked example

The root, one authored prompt, and a batch of two continuations — the second of which was
then branched from a counterfactual at its third token. The same tree `token-loom/1`
represented in five spans and seven runs.

```jsonc
{
  "format": "token-loom/2",
  "tree_id": "…",
  "base_seed": 90210,

  "spans": {
    // a root: nothing precedes it
    "s1": { "kind": "human", "text": "The sea was", "parent": null,
            "created": "2026-08-12-10.00.00" },

    // batch b1, both continuations anchored at the same point — that is what
    // "two continuations from one position" means, and it is visible as such
    "s2": { "kind": "sampled", "text": " calm for days", "parent": ["s1", 11],
            "params": "p1", "seed": 90211, "batch": "b1", "index": 0,
            "slice_start": ["s1", 0], "created": "2026-08-12-10.01.00" },

    "s3": { "kind": "sampled", "text": " calm and clear", "parent": ["s1", 11],
            "params": "p1", "seed": 90212, "batch": "b1", "index": 1,
            "slice_start": ["s1", 0], "created": "2026-08-12-10.01.00" },

    // branches inside s3, which is not cut. token_id, not rank: rank is only
    // meaningful against the N that was requested
    "s4": { "kind": "counterfactual", "text": " still", "parent": ["s3", 9],
            "origin": { "span": "s3", "index": 2, "token_id": 2058 },
            "created": "2026-08-12-10.02.00" },

    // in flight: provenance written, byte record still empty
    "s5": { "kind": "sampled", "text": null, "parent": ["s3", 15],
            "params": "p1", "seed": 90213, "batch": "b2", "index": 0,
            "slice_start": ["s1", 0], "created": "2026-08-12-10.03.00" }
  },

  "params": {
    "p1": { "temperature": 0.9, "top_p": 1, "top_n": 3,
            "length": 3,            // tokens
            "stop": [],
            "model": "qwen2.5-7b-base", "tokenizer": "qwen2.5",
            "n_ctx": 16384,         // tokens
            "prompt_length": 6000 } // bytes
  },

  "selected": ["s3", 15],
  "deleted": []
}
```

Six things to read off it:

- **The file reads as prose again.** Follow `s1` → `s3` → `s4` and the text is right there.
  This is what the pieces cost.
- **`s3` still holds all fifteen of its bytes**, and nothing references a range of it. The
  branch at byte 9 is recorded on `s4`, where it belongs — a fact about the child, not a
  division of the parent.
- **`s2` and `s3` share a parent address.** Sibling branches are structurally visible, and
  no absolute offset appears anywhere, so nothing has to be maintained in agreement with
  anything else.
- **`s4` has no parameters and no seed.** A counterfactual selection is not a generation
  call; it points at the span whose top-N it came from and carries nothing it never had. The
  field is `origin` rather than the more natural `from`, which is a Python keyword — a small
  ugliness in the format beats `from_` at every use site in the code.

  Note `parent` and `origin` overlap by design: `origin` records *which* counterfactual,
  `parent` records *where it attaches*. They must agree, and check 5 says so.
- **`slice_start` is on the span, `prompt_length` in the interned set.** Both continuations
  of batch `b1` share `p1`; a batch at a different position shares it too.
- **`s5` is one generation call in flight.** It has provenance, a parent address and no
  bytes; neither record becomes false if the process dies, and it loads as aborted.

`selected` is `["s3", 15]` — the tip of `s3`, where `s5` is growing. `null` means a tree
with no spans yet, and is the only special case.

### Bulk store

Unchanged from `token-loom/1`.

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

`bytes` is stored rather than derived. It is what the server returns, and encoding the token
string instead is lossy for exactly the byte-fallback tokens that split a UTF-8 character —
the case byte anchoring exists to handle.

### What the validator checks

Seven, of which four are structural and three need the bulk store. `token-loom/1` had nine,
six of them structural; the three that went were checking that runs and pieces agreed with
spans, which is not a question that can be asked any more.

Structural:

1. **Every parent resolves and is in range.** `parent` is null, or `[p, k]` where `p` is a
   span and `0 <= k <= len(p.text)`. A span still in flight has no bytes, so only `k == 0`
   is legal against it — see the note under "Open" below.
2. **The parent chain terminates.** No cycles. Reachability needs no separate check: a span
   whose chain reaches null is reachable by construction, which is a class of orphan
   `token-loom/1` had to look for.
3. **A span's own record is consistent.** `kind` is one of the three, a counterfactual
   carries an `origin`, and a `slice_start` lies on the span's own ancestry — naming a span
   on some other branch, or an offset past what that span contributes to this path, is a
   bug. `token-loom/1` could not express that check, let alone catch it: an absolute offset
   can only be held to arithmetic, where an address can be held to a path.
4. **Every `deleted` entry resolves** to an existing span with an offset in range.

With the store:

5. **A counterfactual span attaches where its origin says.** `parent == [origin.span, byte
   offset of token origin.index]`. The two records are written together and must not drift.
6. **A complete span's `text` is what its tokens spell**, with indices contiguous from 0.
   Human spans have no token rows at all; a counterfactual span has exactly one.
7. **A complete sampled span has a terminator row.** Only a sampled span was ever in flight —
   human and counterfactual spans are complete the moment they are created — so only they
   have anything to terminate.

Check 6 earns its keep three times over: it is the only thing that would catch byte-fallback
tokens being mishandled, it is what makes a `text` field and a `bytes` blob safe to hold the
same information, and it is the check a future vacuum has to pass — reclaim a token row
belonging to a live span and it fails immediately.

One `token-loom/1` check went **tautological** rather than redundant, which is worth naming
because it looks like a gap in the list above: it verified that `text` and `extent[1]` agreed
about whether a span was in flight. There is one field now, and `complete` reads it, so
nothing is left that could disagree. That is the same finding as "the test asks for something
the design makes unreachable" — a result, not a hole.

A validator that has never rejected anything is an untested one. Each check gets a tree
deliberately broken in that one way.

---

## What the core must do

**Five operations**, where `token-loom/1` had six. Everything in Phase 2 and 3 is built from
these.

| operation | notes |
| --- | --- |
| `author(position, text)` | one human span with `parent = position`; no tokens |
| `generate(position, params, n)` | one batch id, `n` spans all with `parent = position`, `n` seeds derived from the base |
| `delete(position)` | soft, cascades, and the bulk store is untouched. A span id is the offset-0 case |
| `slice(position, length)` | resolves to `(start address, end address)` and the text to send |
| `branch_counterfactual(span, index, rank)` | one counterfactual span with `parent = [span, byte offset of token index]` |

`split` is not among them. It had exactly one job — produce a node to hang something off —
and every caller now uses the position it already had. `restore` is the inverse of `delete`
and is a list operation, which is what soft delete buys.

`generate` is the one with an order that matters, because it straddles the model call and
decision 2 splits a span across it:

1. write `n` in-flight spans — provenance and parent address only — and **save the tree**.
   This is the intent record, and it is what makes a crash mid-generation legible rather
   than invisible
2. token rows append to the bulk store as they arrive
3. on completion, per span: fill `text`, write the terminator row

Every step is an append or a fill. Nothing is rewritten, and a crash at any point leaves a
tree that loads — with an aborted span holding however many tokens made it.

Saving the tree at step 1 rather than step 3 is also what keeps the bulk store free of
orphans in the crash case, not just the reachability one: because the span is written before
its first token, no bulk row can ever name a span the tree has not heard of. The ordering is
doing two jobs, and the second is the reason to resist reversing it for a saved write.

The step `token-loom/1` had before all of these — *split if the position needs it, then
create n child runs with empty piece lists* — is gone entirely.

---

## Settled by measurement

Three assumptions that a throwaway script overturned in minutes. The general rule is worth
more than any of them: **absence of observation cannot settle a question about what is
possible.** Ask the vocabulary, not the samples.

### `n_probs` is not optional

Requesting zero counterfactuals returns no `completion_probabilities` at all — and with it
go the per-token *bytes*, not just the alternatives. There is no token overlay to store
without them, so `top_n >= 1` is a hard requirement rather than a default worth quietly
applying.

### Rank 0 is not always the token that was sampled

At temperature 0.9 the sampled token is absent from its own top-3 roughly a third of the
time. The `tokens` and `counterfactuals` tables are independent records, which is why they
are separate tables — and the worked example above happens to show the sampled token at rank
0, which should not be read as a rule.

This turned out to be a good read rather than merely a fact: the `*` marking the sampled
token in `loom.py tokens` is missing about a third of the time, so the gap between what the
model ranked and what it did is visible at a glance rather than inferable. It was not
designed in. It fell out of storing the two as independent records, which is the argument
for Phase 3's sibling-divergence read being built the same way: store the honest thing, and
let the display find the question.

### A token can be a fragment of a character

Carried as an open question on the grounds that waiting to observe one could never close it.
The decidable form is the vocabulary, and it was cheap to ask: tokenise text the merges will
not have covered, and look at whether any single token's bytes are valid UTF-8 alone.

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
the prompt has to be decoded to be sent. `slice` therefore nudges the start forward to the
next character boundary *before* the span records it, so `slice_start` describes the slice
that was used rather than the one that was asked for.

What remains deliberately unhandled: a generation point placed inside a character. The
prompt then genuinely has no string form, and the adapter raises rather than guessing.
Fixing it properly means sending token ids instead of text — the token-replay path in
`BEYOND-MVP.md` — which needs mixed-mode assembly, since human spans have no tokens. Not
worth pulling forward for a case that requires branching inside an emoji on purpose.

---

## Why the adapter is new code, not a patched `inference.py`

Kept because the reasoning is the kind that gets re-opened. The original plan was to keep
two fields `inference.py` discards; reading it against what the core actually needs, that
was bolting onto the wrong thing.

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

---

## Landing the amendment

No migration: `data/tree/` is disposable scratch and no-migration is already policy. The
format marker goes to `token-loom/2` and `token-loom/1` trees are refused on load rather
than converted.

1. **`core/tree.py`** — `Span` gains `parent`, loses `start`/`end`. `Run` and `Piece` go,
   with `pieces_of`, `run_bytes`, `piece_bytes` and the run half of `ancestry`. A child index
   built at load answers "what branches from here".
2. **`core/validate.py`** — the seven checks above, replacing nine.
3. **`core/ops.py`** — `split`, `at`, `absolute`, `locate`, `widen` and `_attach` are
   deleted. `author`, `generate` and `branch_counterfactual` each collapse to constructing
   one span. `delete` takes a position.
4. **`core/session.py`** — the save ordering is unchanged; only the call it wraps changes.
5. **`loom.py`** — the `split` command goes. Positions are `s3+9`; `show` prints span
   addresses, and derived run ids are display-only and must not be accepted as input, since
   a derived grouping renumbers.
6. **`core_test.py`** — the section asserting that a split reseats the cursor becomes the
   demonstration that there is nothing to reseat. Fixtures shrink to spans.

It should delete substantially more than it adds. If it does not, something has been
misunderstood.

**Arithmetic in a test is code too, and nothing checks it.** The `token-loom/1` build's
sloppiness went almost entirely into test assertions — miscounted byte lengths twice, and a
tautology that could never fail. Compute the expected values; do not eyeball them.

## Open

**Can a child anchor on an in-flight parent at an offset it has not reached?** Under
blocking generation, no — a span cannot be branched from before it returns, so check 1's
`k == 0` restriction costs nothing. Streaming makes it reachable, and the answer is probably
that the check becomes "against the bytes that have arrived". Not worth deciding before
streaming is.

## Not in the MVP

- Migration. `data/local.json` becomes archive JSON.
- Vacuum. Soft delete only; the append-only store makes it nearly free to defer.
- Streaming, though the incomplete-span state it needs is here.
- Editing, at any layer, ever.
- Co-covering spans, prefix merging, embeddings. See `BEYOND-MVP.md` — the shapes above
  leave room for them; nothing builds them.
