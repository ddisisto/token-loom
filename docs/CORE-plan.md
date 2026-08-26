# The core — transcription plan

**This file is scaffolding, not content, and it is never the product.** Headings with one line
of intent each, the disposition of every section of the current `CORE.md`, and the decisions
still open. It is untracked and not cited, and it carries its own status inline because of
that. `docs/CORE-draft.md` is the document being written; this one is deleted when that
replaces `docs/CORE.md`.

Sections are unnumbered and cited by name. Invariants get stable names, not ordinals, so a
later insertion does not renumber every inbound reference in the doc, the tests and the code.

---

## Skeleton

### The record

What a token, a node, an edge and a path are, and that bytes are derived. Nothing addresses a
byte. Establishes every noun the rest of the document uses.
*From current §1, largely intact.*

### Boundaries

A node is a boundary when the path bytes ending at it decode. **A non-boundary node is not an
act origin** — it is not a leaf. It gains children only from the act that produced it, and
once that act ends nothing can extend it, because extension requires an act and no act may
start there.
*From current §4, corrected per decision 3. The "permanent leaf" framing goes entirely, and so
does the "two things make one" enumeration, which was never exhaustive — a `create` that
tokenises a multi-byte character produces interior fragments that are neither tips nor leaves.
Current §4's "no ranked edges are ever recorded at such a node" is scoped to tips: an interior
fragment was passed through by a live generation, so the ranking for its next position was
computed and belongs on it.*

### Sources

Who produced a node. The merge key `(parent, token_id, source)`. Roots do not merge. One
vocabulary per tree, named once. Node ids are opaque and local to a store.
*From current §5, plus the id-opacity line rescued from §3. The unnamed user is `null`, so
`name` is nullable and uniqueness is on `(kind, COALESCE(name, ''))` — SQLite treats NULLs as
distinct under a plain `UNIQUE`, which would otherwise permit unlimited unnamed-user rows.*

### Rankings

The alternatives recorded at a node, keyed `(node, source, rank)`, with `token_id` unique
within a ranking.

- **A ranking belongs to the node, not to the act that found it.**
- **Rank is the order the adapter presented.** Descending logprob is expected of a backend and
  stated as such, but it is not an enforced invariant — which is what makes ties well-defined
  and extension sound.
- **A later act extends a ranking and never truncates or rewrites it.** Rows already present
  keep their values, so nothing derived from a ranking changes retroactively. A later act
  contributes only tokens not already recorded.
- **Rank means "the k-th alternative recorded here," not "the model's k-th choice."** Said out
  loud, because an analysis assuming a true top-k would otherwise be quietly wrong.
- **A node may be absent from its parent's ranking**, and a later act may supply the covering
  edge. Stated per-node rather than per-position, so it covers both an adapter that reports no
  ranking at all and one that emits EOS on a stop condition without it passing the sampler.

*From current §7, per decision 4, with §13 folded in. §13's "every such node is a fragment" is
dropped — under decision B an unranked EOS node is a boundary.*

> **Slot — open decision B′.** Is an absent ranking *recorded as declined*, or inferred from
> missing rows? Absence-as-signal cannot distinguish "never asked" from "rows lost," and the
> document's own stance is that a `generate` declines rather than guesses. Costs one column.

### Acts

`create`, `generate`, `realise` — what was done, recorded once. Fields, terminators, an act's
tokens as the path from `from` to `to`. In-flight and abandonment.

- **An act must cover a non-empty range.** Distinct from, and stated beside, *an act may
  produce no new nodes*: the covered range is reckoned before merge, so acts may overlap in
  part or in full, and that overlap is the sampling-frequency count.
- **Sampling parameters are pass-through.** Core records them and interprets none. The length
  limit is the only one core owns, because core imposes it.
- **`params` is interned after the call**, from what the adapter reports it actually used —
  `n_ctx` included — so it joins `to` and `terminator` in the null-while-in-flight set.
- **`seed` keeps its own column.** Folding it into the interned blob would mint a new params
  row per call, since seed is the one field designed to vary.
- `generate` may have a null `from`; `realise` may not, as it needs an existing edge.

*From current §6 and §8. Under decision 1 the in-flight story becomes true as stated: the lock
is held across the whole act, so acquiring it does mean no other writer is live. Under decision
C, `top_n >= top_k > 0` leaves core with the parameters and becomes an `ADAPTER.md` obligation.*

> **Slot — small.** `limit` currently does not distinguish the requested length from context
> exhaustion. Now that core owns one of the two and the adapter the other, they *could* be
> split. Default is to keep them merged.

### What the record requires of a backend

The conditions the record imposes — ids never text, no unknown-bytes case, authored bytes
round-trip, rankings are a function of the model and the path — stated as properties of the
record. The operations and obligations that satisfy them live in `docs/ADAPTER.md`, which is
also the document that may cite the llama.cpp notes.
*From current §2, split per decision A.*

### On disk

`tree.json`, `bulk.sqlite`, and the lock. The schema. The lock is held for the duration of an
act **including the model call**; writes are serialised and nothing generates concurrently. A
stale lock blocks and there is no breaking mechanism.

**`vocab` writes are insert-or-verify.** An id already present must match what `bytes_for`
returns now, or the write is a hard error. This is the one check that reaches the adapter, it
costs nothing on a path already being walked, and it catches a wrong-but-similarly-named
vocabulary on first touch. The name in `tree.json` stays advisory.

*From current §9, per decisions 1 and F. `acts.op` stays a three-value enum per decision 2, and
`nodes.deleted` stays a state column.*

> Worth stating plainly rather than letting a client discover it: a long generation now blocks
> every other write, `create` and `realise` included.

### Invariants

The checks, each with a stable name — `INV-MERGE-KEY`, `INV-RANK-DENSE`, `INV-RANK-UNIQUE`,
`INV-BOUNDARY-ORIGIN` and so on — so tests and code can cite one without depending on its
position.
*From current §10, renamed. `INV-RANK-ORDERED` relaxes from a check to a stated expectation.
`INV-RANK-UNIQUE` is new and closes a corruption the current list does not forbid. The orphan
word "grouped" does not survive.*

### Operations

Two groups, because they are different kinds of thing and lumping them is what let the
confusion in:

- **Acts** — `create`, `generate`, `realise`. Each extends the tree and each is recorded.
- **State edits** — `delete`, `undelete`. Neither is an act. They set and clear a flag;
  liveness is derived by walking the ancestry.

*From current §11, split per decision 2. "delete records an act, not a state" goes. The
derived-liveness mechanism and the idempotence that makes it work both survive unchanged.*

### Derived reads

Everything computable and nothing stored: path bytes, display text, a node's logprob, liveness,
boundary, runs, branch points, unrealised edges, sampling frequency, agreement, depth.
*From current §12, intact.*

### Conformance and extension

New. What a reader must reject, what it must ignore, and what happens when a check fails.
Connects "a new record type is a new table" to `marker`: readers ignore tables they do not know,
and the marker changes only when an existing table changes meaning. This is what makes the
first forced revision a bump rather than a break.

### What this does not specify

New. Explicit non-scope, as the standing defence against the document being reopened for a
question it was never meant to answer.

### Appendix — a worked example

New, and last so it can grow without disturbing anything. One small tree end to end: a root, a
`generate` terminating on EOS, its rankings, a second `generate` extending one of them, a
`realise`, and the exact rows.

---

## Disposition of the current document

| current | lands in | note |
| --- | --- | --- |
| §1 A node is a state | The record | intact |
| §2 The adapter contract | What the record requires + `ADAPTER.md` | split per decision A |
| §3 A position is a node | dissolved | id-opacity → Sources; "no index and no pair" dropped as an argument against a superseded design; `export` → decision G |
| §4 A boundary | Boundaries | corrected per decision 3 |
| §5 A source | Sources | intact, plus the nullable-name fix |
| §6 An act | Acts | in-flight story sound per decision 1; params reshaped per decision C |
| §7 Ranked edges | Rankings | reshaped per decisions 4 and D |
| §8 Interned parameters | Acts | folded in, and mostly emptied by decision C |
| §9 On disk | On disk | lock rewritten per decision 1; `vocab` verify per decision F |
| §10 The checks | Invariants | renamed to stable names |
| §11 Operations | Operations | split into acts and state edits per decision 2 |
| §12 Derived reads | Derived reads | intact |
| §13 Positions with no ranking | Rankings | folded in, generalised per decision B |

## Decisions recorded

So transcription does not re-litigate them.

1. **The lock broadens** to cover the whole act including the model call. Concurrent generation
   goes away. A stale lock blocks; nothing breaks it.
2. **`delete` and `undelete` are state, not acts.** Derived liveness survives; the acts table
   does not grow an op.
3. **A non-boundary node cannot originate an act but may have children.** It is not a leaf.
4. **A ranking extends and never truncates.**
5. **A — the adapter contract splits out** into `docs/ADAPTER.md`. `CORE.md` keeps the
   conditions on the record; `ADAPTER.md` states the obligations that satisfy them and is the
   document that may cite the llama.cpp notes.
6. **B — the terminating EOS becomes a node.** Gap-filling needs no new mechanism: decision 4
   already supplies a covering edge when a later act reports one.
7. **C — sampling parameters are the adapter's.** Core passes through and records only; the
   length limit is the sole exception. Effective params, `n_ctx` included, are interned after
   the call.
8. **D — no tolerance in the format.** Rank is recorded order; first value wins; rows are never
   rewritten; `token_id` is unique within a ranking. Backend self-disagreement becomes an
   adapter diagnostic, free to change as it is measured.
9. **E — an act must cover a non-empty range**, reckoned before merge.
10. **F — `vocab` writes verify rather than ignore.**
11. **Smaller** — `generate` may have a null `from`, `realise` may not; the unnamed user is the
    empty name, with a plain `UNIQUE (kind, name)` and no `COALESCE`, since the index only ever
    existed to work around NULL's distinctness; a model is always named, because source is the
    merge key; ties take the adapter's order, which generalises into decision D.

12. **G — `export` is dropped.** The id-opacity statement stands on its own: node ids are not
    to be treated as stable outside a store.

13. **C′ — parameters are the request, and there is no effective set.** An adapter meets a
    request or refuses it; nothing is substituted. `params` and `seed` are written with the act
    and never revised, and only `to` and `terminator` are null while in flight. Consequences:
    `n_ctx` leaves the format entirely, `limit` unambiguously means the requested length was
    reached, and the core supplies a seed when a caller does not so that no effective value
    re-enters by that door.

14. **B′ — an absent ranking is inferred from missing rows.** No declination column. Nothing
    records why an edge is missing, and a declination is not distinguished from a position
    nothing has generated at.

## Status

Transcription complete and every decision closed. `CORE-draft.md` holds the full document and
the worked example. Outstanding before the swap:

- ~~**Small.** `limit` and context exhaustion.~~ Dissolved by C′ — exhaustion is a refusal, not
  a terminator, so there is nothing to distinguish.
- **The appendix ids are invented.** Regenerate against the real tokeniser before locking.
- **`docs/ADAPTER.md` does not exist yet.** `CORE.md` cites it three times, and the split is
  not finished until it does.
