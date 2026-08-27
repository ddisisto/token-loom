# The core

**What the format is.** Node, edge, source, ranking, act, the on-disk shape, the invariants and
the operations. This document is meant to be locked early and left alone.

**The test it is written against: can someone implement a reader from it alone?**

Sections are cited by name and invariants by name, never by position, so an insertion renumbers
nothing. What a backend must do to satisfy the conditions stated here is `docs/ADAPTER.md`; no
fact about a particular backend is in this document.

---

## The record

A **token** is an id in a vocabulary together with the bytes it spells.

A **node** is a state the model can be in: one token, reached from one parent node. The sequence
of tokens from a root down to a node is that state's context, and it is the only thing a node
means.

An **edge** is a token leading out of a node. Two kinds exist:

- a **taken** edge is a child node
- a **ranked** edge is an alternative recorded at that node which nothing has taken

They are the same object at different stages. **Taking a branch is realising a ranked edge into
a node**, and that is the operation this format exists to make cheap.

Bytes are derived. A node's bytes are its token's bytes; a path's bytes are its nodes' bytes in
order. Nothing addresses a byte, and no offset here is a byte offset.

One point in the tree has exactly one name, and that name is the node. Nodes are never split,
merged after the fact, or renumbered, so no name is ever invalidated and no canonicalisation is
needed. Node ids are opaque and local to a store; nothing outside a store may treat them as
stable.

## Boundaries

A token's bytes may be a fragment of a character — Qwen2.5 spells `🜁` as three tokens, none of
them valid UTF-8 alone. A control token is not such a case: `<|endoftext|>` spells the thirteen
bytes `<|endoftext|>`, which tokenise back to it, so it needs no special handling anywhere in
this format.

A node is a **boundary** when the path bytes ending at it decode.

**A non-boundary node cannot originate an act** — `INV-BOUNDARY-ORIGIN`. A context that ends
inside a character is not a state a model can be given, so this is not a policy but the only
formable position.

**A non-boundary node is not a leaf.** It gains children from the act that produced it: a
`create` whose text contains a multi-byte character passes through interior fragments and keeps
going, and so does a generation. What such a node cannot do is gain a child *afterwards*, since
adding one requires an act and no act may start there. A fragment left at the tip of an act is
therefore permanent, and a fragment inside one is ordinary.

Ranked edges at a non-boundary node arise the same way. A generation that passed through the
position computed a distribution for the next one, and it is recorded like any other. A fragment
at a tip has none, because generation stopped before that distribution existed.

## Sources

Every node records **who produced it**: a user, or a named model.

| field | meaning |
| --- | --- |
| `kind` | `user` or `model` |
| `name` | who — `alice`, `qwen2.5-7b-base`; the empty name is the unnamed user |

**Source is part of the merge key.** A node is `(parent, token_id, source)`, unique —
`INV-MERGE-KEY`. So:

- two quants of one model never factor together, and the split is visible in the tree
- authored text never collapses into a model draw that happens to match
- a draw and a deliberate branch that land on the same token from the same model **do** factor
  together, because they are the same state

**A model is always named** — `INV-SOURCE-NAMED`. Two unnamed models would be one source, and
their draws would factor together as though one had produced both. The empty name is reserved
for the unnamed user and belongs to nothing else.

Two sources speaking the same vocabulary may extend each other freely. A path may have mixed
sources along its length, and reads that do not care about provenance never look.

**Roots do not merge.** A root has no parent, so the merge key does not reach it: two roots with
the same token and source stay distinct. Each root begins its own trie, and they share a store
and a vocabulary and nothing else.

The vocabulary is named once per tree, not per source, and every id in the store is in it — that
is what makes a path replayable by concatenating ids. A tree in a second vocabulary is a new
tree, converted node by node through bytes.

## Rankings

The alternatives recorded at a node. One row per `(node, source, rank)`:

| column | meaning |
| --- | --- |
| `rank` | `0` is first; distinct and contiguous within a node and source |
| `token_id` | the candidate; appears at most once within a node and source |
| `logprob` | its log probability |

**A ranking belongs to the node, not to the generation that found it.** It is a function of the
model and the path, so two generations reaching a node describe one distribution and the record
does not depend on which arrived first.

**Rank is the order the source presented.** Descending logprob is expected of a model and is not
enforced. Near-ties come back in whatever order a backend produces, and imposing a global sort
would make the stored order turn on values that are not reproducible to the last bit.

**A ranking extends and is never truncated or rewritten.** A later generation contributes only
tokens not already recorded, appended at continuing ranks. Rows already present keep their
values, so anything derived from a ranking — a node's logprob above all — never changes
retroactively.

It follows that **rank means the k-th alternative recorded here, not the model's k-th choice.** A
generation recording twenty alternatives after one recorded five may contribute a token that
would outrank a stored one; it is appended below it regardless. A node's recorded depth is
whatever has accumulated there, and is not derivable from any one generation's parameters.

**A node's own logprob is not stored.** It is the ranked edge at its parent, for its source,
carrying its `token_id`. What a node was worth and what its alternatives were worth cannot drift
apart, because there is only one record of both.

**A node may be absent from its parent's ranking.** A generation that can give no ranking for a
position declines rather than guesses, and a backend may emit a token on a stop condition
without it passing through a sampler. Such a node has no derivable logprob until a later
generation supplies the covering edge — which extension then does, with no further mechanism.
`INV-RANK-COVERS` states the ordinary case and this is its exception.

**Nothing records why an edge is missing.** A declination is not distinguished from a position
nothing has generated at; in both the absence is the whole record.

Confining a draw to alternatives that are recorded is an obligation on an adapter, so in the
ordinary case a drawn token is among its parent's ranked edges and rank `0` is frequently not
the token drawn. Values are the model's own and sum to less than one, by the mass of the
vocabulary that was not recorded.

## Acts

**What was done**, recorded once. An act extends the tree from one node.

| field | on | meaning |
| --- | --- | --- |
| `op` | all | `create`, `generate` or `realise` |
| `source` | all | **who acted** — not necessarily who produced the tokens |
| `from` | all | the node it started at, or `null` if it created a root |
| `to` | all | the last node it produced; `null` only while a `generate` is in flight |
| `created` | all | timestamp, ISO 8601 |
| `params` | `generate` | index into the interned parameter table |
| `seed` | `generate` | the seed the call was made with |
| `terminator` | `generate` | why it stopped; `null` while in flight |
| `rank` | `realise` | the ranked edge that was taken |

**An act's tokens are the path from `from` (exclusive) to `to` (inclusive).** Nothing else is
stored, because each node has one parent and that path is therefore unique.

**An act must cover a non-empty range**, and one that would produce nothing is refused. This is
not the same as producing no *new* nodes: the range is reckoned before merge, so acts may
overlap in part or in full, and an act whose every node already existed is legal and records
that the path was taken again. That overlap is the sampling frequency, and it costs nothing to
keep.

**Only `generate` calls a model.** `create` tokenises text someone wrote; `realise` turns a
ranked edge that is already recorded into a node. Both are pure store operations and stay
reachable with nothing running.

**An act's source is who acted.** For `create` and `generate` that is also the source of the
nodes it produced. For `realise` it is not: a reader acts, and the node carries the source of the
model that ranked the edge.

`from` may be null for `create` and for `generate`, each of which then begins a root. It may not
be null for `realise`, which needs an existing edge to take.

| terminator | means |
| --- | --- |
| `eos` | the model emitted an end-of-text token |
| `limit` | it reached the requested length |
| `aborted` | the process generating it is gone |

**Parameters are what was asked for.** The core records the request and interprets none of it.
There is no effective parameter set and no second version to reconcile: an adapter either meets
a request or refuses it, and one that would substitute a value refuses instead. A parameter set
is therefore complete when the act is written, and nothing in it is revised when the answer comes
back.

A generation that would not fit the room a backend has is refused before anything is written, so
running out of context is not a way for a generation to end. That is why `limit` means one thing.

Every distinct parameter set is written once and referenced by index. The seed keeps a column of
its own, because it is designed to vary per call and interning it would mint a row each time; the
core supplies one when a caller does not, so that it too is part of the request.

**A `generate` act whose `to` and `terminator` are null is in flight.** Only `generate` can be;
the other two are one write each. The lock makes it decidable: a writer holds the lock for the
whole of an act, so acquiring it means no other writer is live, and every such act is abandoned
and is recorded `aborted`.

## What the record requires of a backend

**The core names no backend.** It requires these conditions of anything that produces a record,
and `docs/ADAPTER.md` states the operations and obligations that satisfy them.

1. **Generations contribute ids, never text.** No node and no ranked edge stores bytes, and none
   is derived from a generation.
2. **Every id stored can be spelled.** Bytes come from the vocabulary, for every id — including
   ids that are a fragment of a character and ids that are control tokens. What the vocabulary
   says, not what a generation said about an occurrence. There is no unknown-bytes case anywhere
   in this format.
3. **Authored bytes round-trip.** Tokenising text and reassembling the result returns the input
   unchanged, and `create` checks it on the text at hand rather than assuming it.
4. **A token sequence is evaluated verbatim.** A path re-tokenised before evaluation is not the
   path that was recorded, and replay is the property the whole format exists to hold.
5. **A ranking is the model's own distribution, not a sampler's.** Its ids, their order and their
   values depend on the model and the path and on nothing in the parameters. A ranking already
   shaped by temperature or truncation could not be keyed on the node, and so could not merge.
6. **A request is met or refused, never adjusted.** No parameter is substituted, softened or
   silently clamped, so what an act records is both what was asked for and what was done.

**What cannot be delivered is declined, never guessed.** A ranking that could not be recorded is
an absent ranked edge, not an estimate; a request that cannot be met is refused before any act is
written, rather than met approximately.

An adapter absorbs its backend's faults rather than passing them through, so what the core sees
is a repaired stream. Where it gets an answer, and from how many sources, is not the core's
concern.

## On disk

Two files and a lock, in a directory.

**`tree.json`** — provenance only. The structure is far too large to read by eye and lives
entirely in SQL.

```json
{
  "marker": "token-loom/nodes-1",
  "created": "2026-08-25T11:56:00Z",
  "vocabulary": "qwen2.5-7b-base"
}
```

A reader that does not recognise `marker` stops. The vocabulary name is advisory; what enforces
it is the `vocab` table.

**`bulk.sqlite`** — everything else. A new record type is a new table, not a new mechanism.

```sql
CREATE TABLE vocab (                       -- one row per id ever stored
  token_id INTEGER PRIMARY KEY,
  bytes    BLOB NOT NULL);                 -- may be a fragment of a character

CREATE TABLE sources (
  id   INTEGER PRIMARY KEY,
  kind TEXT NOT NULL,                      -- 'user' | 'model'
  name TEXT NOT NULL,                      -- '' is the unnamed user, and nothing else
  UNIQUE (kind, name));

CREATE TABLE nodes (
  id       INTEGER PRIMARY KEY,
  parent   INTEGER,                        -- NULL for a root
  token_id INTEGER NOT NULL,
  source   INTEGER NOT NULL,
  deleted  INTEGER,                        -- 1 if this node is deleted, else NULL
  UNIQUE (parent, token_id, source));      -- roots are exempt: NULL parents never collide,
                                           -- which is Sources' rule, not an artefact

CREATE TABLE edges (                       -- ranked, not taken
  node     INTEGER NOT NULL,
  source   INTEGER NOT NULL,
  rank     INTEGER NOT NULL,
  token_id INTEGER NOT NULL,
  logprob  REAL NOT NULL,
  PRIMARY KEY (node, source, rank),
  UNIQUE (node, source, token_id));

CREATE TABLE params (id INTEGER PRIMARY KEY, json TEXT NOT NULL);

CREATE TABLE acts (
  id      INTEGER PRIMARY KEY,
  op      TEXT NOT NULL,                   -- 'create' | 'generate' | 'realise'
  source  INTEGER NOT NULL,
  "from"  INTEGER, "to" INTEGER,
  created TEXT NOT NULL,
  params  INTEGER, seed INTEGER, terminator TEXT,   -- 'generate' only
  rank    INTEGER);                                 -- 'realise' only
```

`bytes` is a BLOB, so no escape is needed anywhere in the store. It lives in `vocab` rather than
on a node because it is a property of the id, not of the occurrence.

**`vocab` writes verify.** An id already present must spell what the vocabulary says now, or the
write fails. This is the only check that reaches outside the store; it costs nothing on a path
already being walked, and it catches a store opened against the wrong vocabulary at the first id
the two disagree on.

`vocab` is filled from the vocabulary and never from a generation, and holds only the ids a tree
actually stores, so the directory stays self-contained and small. Whether an adapter answers per
call or from a vocabulary it inflated once is its own business — the store looks the same either
way.

**`lock`** — held with `flock` for the whole of an act, **the model call included**. Writes are
serialised and nothing generates concurrently, so a long generation blocks every other write,
`create` and `realise` among them. A stale lock blocks and nothing breaks it. Recording abandoned
acts is the first write after acquisition, so **opening a tree for writing can modify it.** A
reader takes no lock.

## The invariants

- **`INV-TREE-PARENT`** — every non-null `parent` names a node that exists.
- **`INV-TREE-ROOTED`** — following `parent` from any node reaches a root; there are no cycles.
- **`INV-MERGE-KEY`** — `(parent, token_id, source)` is unique.
- **`INV-VOCAB-CLOSED`** — every `token_id` in `nodes` and `edges` is in `vocab`.
- **`INV-SOURCE-CLOSED`** — every `source` in `nodes`, `edges` and `acts` is in `sources`.
- **`INV-SOURCE-NAMED`** — a source of kind `model` has a non-empty `name`. The empty name is
  the unnamed user and belongs to nothing else.
- **`INV-RANK-ANCHORED`** — no `edges` row names a node that does not exist. A deleted node is
  still held, so its rows are not orphans.
- **`INV-RANK-DENSE`** — ranks within a `(node, source)` are distinct and contiguous from `0`.
- **`INV-RANK-UNIQUE`** — a `token_id` appears at most once within a `(node, source)`.
- **`INV-RANK-COVERS`** — a node whose source is a model appears among its parent's ranked edges
  for that source, unless no covering edge was recorded; see Rankings.
- **`INV-ACT-PATH`** — for an act not in flight, `from` and `to` exist, `to` descends from
  `from`, and the range between them is non-empty.
- **`INV-ACT-SOURCE`** — for `create` and `generate`, every node on that path carries the act's
  source; for `realise`, the one node carries the source of the edge it took.
- **`INV-ACT-CREATE`** — a `create` act has no `params`, `seed`, `terminator` or `rank`.
- **`INV-ACT-GENERATE`** — a `generate` act has `params` and `seed` and no `rank`, and its `to`
  and `terminator` are null together or non-null together.
- **`INV-ACT-REALISE`** — a `realise` act has `rank` and a non-null `from`, and no `params`,
  `seed` or `terminator`; `to` is a child of `from`; and the edge `(from, to.source, rank)`
  exists and carries `to.token_id`.
- **`INV-BOUNDARY-ORIGIN`** — an act's `from` is a boundary node, or null.

Descending logprob within a ranking is **not** an invariant. Rankings says why.

## Operations

### Acts

Each extends the tree, and each is recorded in `acts`.

| operation | writes | leaves |
| --- | --- | --- |
| `create(at, bytes)` | one act, and nodes for the tokens | tokenised against the tree's vocabulary; refuses if the round trip does not hold |
| `generate(at, params)` | one act, and nodes for what was drawn | provenance first, then the nodes |
| `realise(node, rank)` | one act and one node | the ranked edge, taken; no model call |

**Creating is bytes in, tokens out.** Authored bytes must be valid UTF-8. The text is tokenised,
the resulting nodes are reassembled exactly as Derived reads will reassemble them, and the result
is compared against what was authored; a mismatch refuses the act. The comparison is against the
reassembly and never against a backend's own way of turning ids back into text, because the
reassembly is what a reader will do and is therefore the thing that has to hold.

This also settles what the bytes cannot: a special-token literal may be read as one token or as
its characters, the two spell the same bytes either way, and the stored ids tell them apart with
no field to record it.

**Generation is two writes.** The act, its parameters and its seed are written and committed
*before* the model is called; the nodes, the ranked edges and the terminator when it answers. An
act with no `to` and no terminator is therefore a generation in flight, and no node can ever
belong to an act the store has not heard of.

**`realise` is one write and no call.** The ranked edge at `(node, source, rank)` is already
recorded, so taking it is a lookup and a node — and if that node already exists, the merge key
finds it and only the act is written. Nothing is in flight and nothing can abort.

**Branching is `realise` then `generate`.** Realising gives the node; generating from it
continues. The two are separate acts, so an alternative can be taken and left unexplored, or
several taken at one node before any is continued, and neither needs an adapter that can
generate.

**Merging is checked, not assumed.** Every node an act produces is looked up by
`(parent, token_id, source)` first and reused if it exists.

**Nothing is created below a node that is not live**, and every act starts at a boundary.

### State edits

Neither is an act, and neither is recorded in `acts`.

| operation | writes | leaves |
| --- | --- | --- |
| `delete(node)` | `deleted` on that node alone | descendants untouched |
| `undelete(node)` | clears it | live again only if its ancestry is |

**A delete names one node.** Whether a node is live is derived by walking its ancestry: it is
live when neither it nor any ancestor is deleted. So a delete is one write, undoing it is one
write, and a descendant deleted on its own account stays deleted when its ancestor comes back.
Deleting what is already effectively deleted is legal, and is what makes that work. Because a
node is one token, a delete lands anywhere — there is no such thing as deleting mid-run.

## Derived reads

Nothing here is stored.

- **A node's bytes** — its `vocab` entry.
- **A path's bytes** — the bytes of each node from the root down, in order.
- **Display text** — a path's bytes, decoded. At a boundary node that is the whole path; at a
  fragment tip the trailing fragment has no string form and is shown as its ids.
- **A node's logprob** — the ranked edge at its parent, for its source, with its `token_id`.
- **An act's tokens** — the path from `from` to `to`.
- **Whether a node is live** — neither it nor any ancestor carries `deleted`. A descent from the
  root carries the answer down and costs nothing.
- **Whether a node is a boundary** — its path bytes decode.
- **Runs** — maximal chains where each node has exactly one live child. Runs have no ids.
- **Branch points** — nodes with more than one child.
- **Unrealised edges** — ranked edges at a node with no matching child. This is the branchable
  set, and it is a `LEFT JOIN`.
- **Sampling frequency** — how many acts' paths pass through a node.
- **Agreement** — nodes reached by more than one source, or by more than one act.
- **Depth** — a node's distance from the root, in tokens.

## Conformance and extension

- A reader that does not recognise `marker` stops.
- **A reader ignores tables and columns it does not know**, and adding a record type does not
  change `marker`. This is what allows the format to grow without invalidating a reader.
- **`marker` changes only when an existing table changes meaning** — the one circumstance that
  makes an older reader wrong rather than merely incomplete.
- A store that fails an invariant is not repaired silently. A reader reports it; a writer refuses
  to write.

## What this does not specify

- How a backend produces any of this. That is `docs/ADAPTER.md`.
- Sampling parameters and what they mean, beyond the length limit the core imposes.
- Any reading surface — layout, navigation, selection, or what a client chooses to show.
- Concurrency beyond the lock: no protocol across machines, and no lock breaking.
- Import, export, and conversion between vocabularies, beyond the statement that a tree in a
  second vocabulary is a second tree.
- Performance, indexing beyond the keys stated here, and reclaiming space.
- Any interpretation of logprobs — comparison, aggregation, or what a distribution means.

---

## Appendix — a worked example

One tree, built in six stages. Every construct in this document appears in it, and the rows are
exact.

**The ids and logprobs below are real**, taken from `qwen2.5-7b-base` — `Qwen2.5-7B.i1-Q4_K_M`
served by llama.cpp over Vulkan, 16k context. Logprobs are shown to four places; nothing else is
rounded or invented.

### Sources

| `id` | `kind` | `name` |
| --- | --- | --- |
| 1 | `user` | *empty* |
| 2 | `model` | `qwen2.5-7b-base` |

### Stage 1 — `create(null, "The sky")`

Authored by the unnamed user. Tokenises to two ids, and begins a root because `from` is null.

| node | `parent` | `token_id` | bytes | `source` |
| --- | --- | --- | --- | --- |
| 1 | *null* | 785 | `The` | 1 |
| 2 | 1 | 12884 | ` sky` | 1 |

Act 1: `create`, source 1, `from` *null*, `to` 2.

### Stage 2 — `generate(at=2)`, `top_k` 5, `top_n` 5, `length` 3, seed 42

| node | `parent` | `token_id` | bytes | `source` |
| --- | --- | --- | --- | --- |
| 3 | 2 | 5023 | ` currently` | 2 |
| 4 | 3 | 702 | ` has` | 2 |
| 5 | 4 | 220 | ` ` | 2 |

Act 2: `generate`, source 2, `from` 2, `to` 5, `params` 1, `seed` 42, `terminator` `limit`.

The ranking recorded at node 2 — the alternatives for the position that produced node 3:

| `rank` | `token_id` | bytes | `logprob` |
| --- | --- | --- | --- |
| 0 | 374 | ` is` | −1.3218 |
| 1 | 702 | ` has` | −1.6666 |
| 2 | 5023 | ` currently` | −2.0363 |
| 3 | 572 | ` was` | −2.7138 |
| 4 | 594 | `'s` | −3.7901 |

**Rank 0 is not the token drawn.** ` currently` was, at rank 2. Rankings are recorded at nodes 3
and 4 the same way. **Node 5 has no ranking**: generation stopped there, so no distribution for a
following position was ever computed. That is a tip with no ranking, not a declination.

### Stage 3 — `generate(at=2)`, `top_k` 5, `top_n` 20, `length` 2, seed 99

| node | `parent` | `token_id` | bytes | `source` |
| --- | --- | --- | --- | --- |
| 6 | 2 | 702 | ` has` | 2 |
| 7 | 6 | 6519 | ` turned` | 2 |

Act 3: `generate`, source 2, `from` 2, `to` 7, `params` 2, `seed` 99, `terminator` `limit`.

**The ranking at node 2 extends from five rows to twenty.** The five already stored keep their
values — this generation reported them bit-identically, which is what obligation 5 in
`docs/ADAPTER.md` asks of a backend — and the fifteen it reported below them are appended:

| `rank` | `token_id` | bytes | `logprob` | | `rank` | `token_id` | bytes | `logprob` |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 5 | 1030 | ` had` | −4.3049 | | 13 | 748 | `’s` | −5.1507 |
| 6 | 518 | ` at` | −4.3088 | | 14 | 646 | ` can` | −5.7753 |
| 7 | 3685 | ` below` | −4.3841 | | 15 | 17167 | ` consists` | −5.8098 |
| 8 | 3403 | ` above` | −4.3868 | | 16 | 5868 | ` looks` | −5.8294 |
| 9 | 1431 | ` now` | −4.8847 | | 17 | 2669 | ` already` | −5.9023 |
| 10 | 304 | ` in` | −4.9828 | | 18 | 4041 | ` comes` | −5.9496 |
| 11 | 323 | ` and` | −5.0173 | | 19 | 1083 | ` also` | −5.9643 |
| 12 | 686 | ` will` | −5.1101 | | | | | |

Node 3's logprob is −2.0363 before the extension and −2.0363 after it.

**Node 4 and node 6 are both ` has`, and they are different nodes.** One is a child of node 3 and
one of node 2, so the merge key never brings them together. Node 2 now has two children and is a
branch point.

### Stage 4 — `generate(at=2)` again, identical to stage 2

Same parameters and the same seed. The model reproduces the path exactly, so every node merges
and nothing new is written but the act.

Act 4: `generate`, source 2, `from` 2, `to` 5, `params` 1, `seed` 42, `terminator` `limit` —
every field but the id identical to act 2.

**An act that produces no new nodes still covers a non-empty range.** The range is reckoned before
merge, so this act covers nodes 3, 4 and 5, and node 3's sampling frequency becomes 2. The
rankings it reported were already recorded, so extension appends nothing.

### Stage 5 — `realise(node 2, rank 0)`

The unnamed user takes ` is` — the alternative the model ranked highest at node 2 and that neither
generation drew. No model is called.

| node | `parent` | `token_id` | bytes | `source` |
| --- | --- | --- | --- | --- |
| 8 | 2 | 374 | ` is` | 2 |

Act 5: `realise`, source **1**, `from` 2, `to` 8, `rank` 0.

**The act's source and the node's source differ.** A reader acted; the model is what ranked the
edge, and the node carries the model. Node 8 has no ranking, because nothing has generated from
it.

### Stage 6 — `create(node 8, "<|endoftext|>🜁")`

Authored bytes: the thirteen characters `<|endoftext|>`, then `F0 9F 9C 81`.

| node | `parent` | `token_id` | bytes | `source` | boundary |
| --- | --- | --- | --- | --- | --- |
| 9 | 8 | 151643 | `<\|endoftext\|>` | 1 | yes |
| 10 | 9 | 9284 | `F0 9F` | 1 | no |
| 11 | 10 | 250 | `9C` | 1 | no |
| 12 | 11 | 223 | `81` | 1 | yes |

Act 6: `create`, source 1, `from` 8, `to` 12.

**The special-token literal read as one token.** The tokeniser returned id 151643 for those
thirteen characters, not thirteen characters' worth of ids. Either reading would have spelled the
same bytes, and the stored id is what tells them apart — no field records which was meant.
End-of-text is otherwise a node like any other: its path bytes decode, so it is a boundary and an
act may start there.

**Nodes 10 and 11 are not boundaries and are not leaves.** They have children, produced by the
same act that produced them. What a non-boundary node cannot do is originate an act — and since
only an act adds children, nodes 10 and 11 can never gain another one. Node 12 is a boundary and
can be extended normally.

### Reading the finished tree

- **Path bytes to node 5** — `The sky currently has `.
- **Path bytes to node 12** — `The sky is<|endoftext|>🜁`. Display shows the terminator literally.
- **Node 3's logprob** — −2.0363, the edge at node 2 for source 2 carrying token 5023. Stored
  once, derived rather than duplicated.
- **Unrealised edges at node 2** — ranks 3 through 19. Ranks 0, 1 and 2 have children: nodes 8, 6
  and 3. This is the branchable set.
- **Sampling frequency at node 3** — 2. Acts 2 and 4 both pass through it.
- **Depth of node 12** — 6.
- **Branch points** — node 2 alone, with children 3, 6 and 8.
- **Agreement** — node 2 is reached by five acts and node 3 by two.
