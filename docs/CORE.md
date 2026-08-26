# The core

**What the format is.** Node, edge, source, act, the adapter contract, the on-disk shape, the
checks, and the operations. No arguments: nothing here has to be defended to be read, and this
document is meant to be locked early and left alone.

**The test this document is written against: can someone implement a reader from it alone?**

---

## 1. A node is a state, an edge is a token

A **token** is an id in a vocabulary together with the bytes it spells.

A **node** is a state the model can be in: one token, reached from one parent node. The
sequence of tokens from a root down to a node is that state's context, and it is the only
thing a node means.

An **edge** is a token leading out of a node. Two kinds exist:

- a **taken** edge is a child node
- a **ranked** edge is an alternative the model scored at that node and nothing has taken

They are the same object at different stages. **Taking a branch is realising a ranked edge
into a node**, and that is the whole operation this format exists to make cheap.

Bytes are derived. A node's bytes are its token's bytes; a path's bytes are its nodes' bytes
in order. Nothing addresses a byte, and no offset here is a byte offset.

## 2. The adapter contract

**The core names no backend.** It requires three operations, and an **adapter** is anything
that provides them for one vocabulary.

| operation | returns |
| --- | --- |
| `tokenize(bytes)` | the ids that spell those bytes, in order, each with its own bytes |
| `bytes_for(id)` | what that id spells, exactly, for every id the adapter can emit |
| `generate(ids, params)` | per position: the id drawn, its logprob, and the top `top_n` ranked ids with theirs — and a terminator |

Five guarantees, and each one exists because a real backend broke it:

1. **`generate` returns ids, never text.** The core stores no bytes from a generation and
   derives none from one. An adapter that can only report what it produced as text is not an
   adapter.
2. **`bytes_for` answers for every id, including ids that are a fragment of a character and
   ids that are control tokens.** It reports what the vocabulary says, not what a generation
   said about an occurrence.
3. **`tokenize` round-trips.** Reassembling its ids' bytes returns the input unchanged.
4. **The token sequence is evaluated verbatim.** An adapter that re-tokenises a prompt cannot
   replay a path, which is the property section 1 exists to hold.
5. **A ranking is the model's own distribution, not the sampler's.** The ids, their order and
   their values depend on the model and the path and on nothing in `params`. An adapter that
   can only report a ranking already shaped by temperature or truncation cannot satisfy this,
   and section 7 would have to key rankings on the act instead of on the node — which is to
   say, could not merge at all.

An adapter may satisfy these however it likes, from as many sources as it likes: reading a
model file, calling one endpoint, calling several. **Where it gets an answer is not the core's
concern**, and no fact about a particular backend belongs in this document.

An adapter also absorbs its backend's faults rather than passing them through. Some are
lossy in ways that produce a record which is quietly wrong rather than an error, so what the
core sees is a repaired stream, not a raw one. `docs/SERVER.md` is the notes for the llama.cpp
adapter and is the only place such behaviour is written down.

Two consequences the core does state, because they are conditions on the record and not on
any backend:

- **What a `generate` cannot deliver, it declines.** A ranking that could not be recorded is
  a missing ranked edge — section 13 — not a guess.
- **An id whose bytes no adapter can answer for cannot be stored.** There is no unknown-bytes
  case anywhere in this format.

## 3. A position is a node

There is no index and no pair. One point in the tree has exactly one name, so no
canonicalisation rule is needed and no position is ever invalidated: nodes are never split,
merged after the fact, or renumbered.

Node ids are opaque and local to a store. Export remaps them.

## 4. A boundary

A token's bytes may be a fragment of a character — Qwen2.5 spells `🜁` as three tokens, none
of them valid UTF-8 alone. A control token is not such a case: `<|endoftext|>` spells the
thirteen bytes `<|endoftext|>`, which tokenise back to it, so it needs no special handling
anywhere in this format.

A node is a **boundary** when the path bytes ending at it decode. Interior fragments are
real and reachable; they are simply not places anything can start from.

**Every act begins at a boundary node** — check 10. A context that ends inside a character is
not a state a model can be given, so this is not a policy but the only formable position.

**A node that is not a boundary is a permanent leaf.** Two things make one: a `generate`
stopped by `limit` on a fragment, and a `realise` of a ranked edge whose token is a fragment.
Both are recorded as they happened. No act may start there, and no ranked edges are ever
recorded at such a node, so it can never be extended and nothing needs to say so twice —
`generate` refuses it exactly as it refuses any non-boundary node. The record keeps what the
model emitted or ranked, and nothing is dropped to make a tip usable.

## 5. A source

Every node records **who produced it**: a user, or a named model.

| field | meaning |
| --- | --- |
| `kind` | `user` or `model` |
| `name` | who — `alice`, `qwen2.5-7b-base`; a default exists for the unnamed user |

**Source is part of the merge key.** A node is `(parent, token_id, source)`, unique. So:

- two quants of one model never factor together, and the split is visible in the tree
- authored text never collapses into a model draw that happens to match
- a draw and a deliberate branch that land on the same token from the same model **do**
  factor together, because they are the same state

Two sources speaking the same vocabulary may extend each other freely. A path may have mixed
sources along its length, and reads that do not care about provenance never look.

**Roots do not merge.** A root has no parent, so the merge key does not reach it: two roots
with the same token and source stay distinct. Each root begins its own trie, and they share a
store and a vocabulary and nothing else.

The vocabulary is named once per tree, not per source, and every id in the store is in it —
that is what makes a path replayable by concatenating ids. A tree in a second vocabulary is a
new tree, converted node by node through bytes.

## 6. An act

**What was done**, recorded once. An act extends the tree from one node.

| field | on | meaning |
| --- | --- | --- |
| `op` | all | `create`, `generate` or `realise` |
| `source` | all | **who acted** — not necessarily who produced the tokens |
| `from` | all | the node it started at, or `null` if it created a root |
| `to` | all | the last node it produced; `null` while in flight |
| `created` | all | timestamp, ISO 8601 |
| `params` | `generate` | index into the interned parameter table |
| `seed` | `generate` | the seed this call was made with |
| `terminator` | `generate` | why it stopped; `null` while in flight |
| `rank` | `realise` | the ranked edge that was taken |

**An act's tokens are the path from `from` (exclusive) to `to` (inclusive).** Nothing else is
stored, because each node has one parent and that path is therefore unique.

**Only `generate` calls a model.** `create` tokenises text someone wrote; `realise` turns a
ranked edge that is already recorded into a node. Both are pure store operations and stay
reachable with nothing running.

**An act's source is who acted.** For `create` and `generate` that is also the source of the
nodes it produced. For `realise` it is not: a reader acts, and the node carries the source of
the model that ranked the edge.

**An act may produce no new nodes.** If a draw reproduces a path that already exists, every
node merges and the act records that the path was drawn again. That count is the sampling
frequency, and it costs nothing to keep.

| terminator | means |
| --- | --- |
| `eos` | the model emitted an end-of-text token |
| `limit` | it ran out of room — the requested length, or the context; not distinguished |
| `aborted` | the process generating it is gone |

**A `generate` act with no `to` is in flight.** Only `generate` can be — the other two are one
write each. The lock in section 9 makes it decidable: a writer holding the lock knows no other
writer is live, so every such act is abandoned and is recorded `aborted`.

## 7. Ranked edges

The alternatives the model scored at a node. One row per `(node, source, rank)`:

| column | meaning |
| --- | --- |
| `rank` | `0` is highest-ranked; distinct within a node and source |
| `token_id` | the candidate |
| `logprob` | its log probability |

**A ranking belongs to the node, not to the act that found it.** Section 2's fifth guarantee
makes it a pure function of the model and the path, so any two acts reaching a node agree and
the second writes nothing new. That is why the key is `(node, source)` and why merging is
possible at all.

It follows that **the recorded parameters describe which edge was taken, not what the
alternatives were worth**, and that rankings recorded under different parameters are directly
comparable. Values are the model's own and sum to less than one, by the mass of the vocabulary
that was not recorded.

**A node's own logprob is not stored.** It is the ranked edge at its parent, for its source,
carrying its `token_id` — check 7 requires it to be there. What a node was worth and what its
alternatives were worth cannot drift apart, because there is only one record of both.

**Sampling is confined to the top `k` and at least `k` alternatives are recorded** — section
8 — so a drawn token is always among its parent's ranked edges. Rank `0` is frequently not the
token drawn.

## 8. Interned parameters

Every distinct parameter set is written once and referenced by index.

| field | source |
| --- | --- |
| `temperature`, `top_p`, `top_k`, `top_n`, `length` | the caller |
| `n_ctx` | the adapter, reporting the room it had |

**`top_n >= top_k > 0`.** `top_k` confines the draw to raw ranks `0…k−1`; `top_n` is how many
ranked edges are recorded. The model is not here — it is the source, on the node.

## 9. On disk

Two files in a directory.

**`tree.json`** — provenance only. The structure is far too large to read by eye and lives
entirely in SQL.

```json
{
  "marker": "token-loom/nodes-1",
  "created": "2026-08-25T11:56:00Z",
  "vocabulary": "qwen2.5-7b-base"
}
```

A reader that does not recognise `marker` stops.

**`bulk.sqlite`** — everything else. A new record type is a new table, not a new mechanism.

```sql
CREATE TABLE vocab (                       -- one row per id ever stored
  token_id INTEGER PRIMARY KEY,
  bytes    BLOB NOT NULL);                 -- may be a fragment of a character

CREATE TABLE sources (
  id INTEGER PRIMARY KEY, kind TEXT NOT NULL, name TEXT NOT NULL,
  UNIQUE (kind, name));

CREATE TABLE nodes (
  id       INTEGER PRIMARY KEY,
  parent   INTEGER,                        -- NULL for a root
  token_id INTEGER NOT NULL,
  source   INTEGER NOT NULL,
  deleted  INTEGER,                        -- 1 if a delete named this node, else NULL
  UNIQUE (parent, token_id, source));      -- roots are exempt: NULL parents never collide,
                                           -- which is section 5's rule, not an artefact

CREATE TABLE edges (                       -- ranked, not taken
  node INTEGER, source INTEGER, rank INTEGER,
  token_id INTEGER NOT NULL, logprob REAL NOT NULL,
  PRIMARY KEY (node, source, rank));

CREATE TABLE params (id INTEGER PRIMARY KEY, json TEXT NOT NULL);

CREATE TABLE acts (
  id INTEGER PRIMARY KEY,
  op TEXT NOT NULL,                        -- 'create' | 'generate' | 'realise'
  source INTEGER NOT NULL, "from" INTEGER, "to" INTEGER,
  created TEXT NOT NULL,
  params INTEGER, seed INTEGER, terminator TEXT,   -- 'generate' only
  rank INTEGER);                                   -- 'realise' only
```

`bytes` is a BLOB, so no escape is needed anywhere in the store. It lives in `vocab` rather
than on a node because it is a property of the id, not of the occurrence.

**`vocab` is filled by `bytes_for`, never from a generation.** A generation contributes ids,
and the ids are enough: no node and no ranked edge stores bytes at all. This is section 2's
second guarantee, and it is the reason there is no unknown-bytes case in this format.

`vocab` holds only the ids a tree actually stores, so the directory stays self-contained and
small. Whether an adapter answers `bytes_for` per call or from a vocabulary it inflated once
is its own business — the store looks the same either way.

**`lock`** — held with `flock` for the duration of any write, and **not across a model call**.
A generation in flight holds nothing, so several run at once and each takes the lock only to
write. Recording abandoned acts is the first write after acquisition, so **opening a tree for
writing can modify it.** A reader takes no lock and can conclude nothing about whether an
in-flight act is still running.

## 10. The checks

1. Every non-null `parent` names a node that exists; following `parent` reaches a root; there
   are no cycles.
2. `(parent, token_id, source)` is unique.
3. Every `token_id` in `nodes` and `edges` is in `vocab`; every `source` is in `sources`.
4. Ranks within a `(node, source)` are distinct, contiguous from `0`, and ordered by
   descending `logprob`.
5. No `edges` row names a node that does not exist. A soft-deleted node is still held, so its
   rows are not orphans.
6. An act's `from` and `to` exist, and `to` descends from `from`. For `create` and `generate`,
   every node on that path carries the act's source; for `realise` the one node it produced
   carries the source of the edge it took.
7. **A node whose source is a model appears among its parent's ranked edges for that source**,
   unless it was grouped — section 13. This is section 7's guarantee, structural.
8. A `realise` act has `rank` and no `params`, `seed` or `terminator`; `to` is a child of
   `from`; and the edge `(from, to.source, rank)` exists and carries `to.token_id`.
9. A `generate` act has `params` and `seed`, and its `to` and `terminator` are null together
   or non-null together. A `create` act has none of the four.
10. An act's `from` is a boundary node, or `null`.

## 11. Operations

| operation | writes | leaves |
| --- | --- | --- |
| `create(at, bytes)` | one act, and nodes for the tokens | tokenised against the tree's vocabulary; refuses if the round trip does not hold |
| `generate(at, params)` | one act, and nodes for what was drawn | provenance first, then the nodes |
| `realise(node, rank)` | one act and one node | the ranked edge, taken; no model call |
| `delete(node)` | `deleted` on that node alone | descendants untouched |
| `undelete(node)` | clears it | live again only if its ancestry is |

**Creating is bytes in, tokens out.** Authored bytes must be valid UTF-8. The text is
tokenised, the resulting nodes are reassembled exactly as section 12 will, and the result is
compared against what was authored; a mismatch refuses the act. The comparison is against the
reassembly — `tokenize` and then `bytes_for` — and never against a backend's own way of
turning ids back into text, because the reassembly is what a reader will do and is therefore
the thing that has to hold. Section 2 requires `tokenize` to round-trip; this is where that is
checked, on the text at hand, rather than assumed.

This also settles what the bytes cannot: a special-token literal may be read as one token or
as its characters, the two spell the same bytes either way, and the stored ids tell them apart
with no field to record it.

**Generation is two writes.** The act, its params and its seed are written and committed
*before* the model is called; the nodes and the terminator when it answers. An act with no
nodes and no terminator is therefore a generation in flight, and no node can ever belong to an
act the store has not heard of.

**`realise` is one write and no call.** The ranked edge at `(node, source, rank)` is already
recorded, so taking it is a lookup and a node — and if that node already exists, the merge key
finds it and only the act is written. Nothing is in flight and nothing can abort.

**Branching is `realise` then `generate`.** Realising gives the node; generating from it
continues. The two are separate acts, so an alternative can be taken and left unexplored, or
several taken at one node before any is continued, and neither needs an adapter that can
generate.

**Merging is checked, not assumed.** Every node an act produces is looked up by
`(parent, token_id, source)` first and reused if it exists.

**`delete` records an act, not a state.** It says a delete named *this* node; whether a node
is live is derived by walking its ancestry, so a delete is one write, undoing it is one write,
and a descendant deleted on its own account stays deleted when its ancestor comes back.
Deleting what is already effectively deleted is legal and is what makes that work. Because a
node is one token, a delete lands anywhere — there is no such thing as deleting mid-run.

**Nothing is created below a node that is not live**, and every act starts at a boundary.

## 12. Derived reads

Nothing here is stored.

- **A node's bytes** — its `vocab` entry.
- **A path's bytes** — the bytes of each node from the root down, in order.
- **Display text** — a path's bytes, decoded. At a boundary node that is the whole path; at a
  fragment tip the trailing fragment has no string form and is shown as its ids.
- **A node's logprob** — the ranked edge at its parent, for its source, with its `token_id`.
- **An act's tokens** — the path from `from` to `to`.
- **Whether a node is live** — neither it nor any ancestor carries `deleted`. A descent from
  the root carries the answer down and costs nothing.
- **Whether a node is a boundary** — its path bytes decode.
- **Runs** — maximal chains where each node has exactly one live child. Runs have no ids.
- **Branch points** — nodes with more than one child.
- **Unrealised edges** — ranked edges at a node with no matching child. This is the branchable
  set, and it is a `LEFT JOIN`.
- **Sampling frequency** — how many acts' paths pass through a node.
- **Agreement** — nodes reached by more than one source, or by more than one act.
- **Depth** — a node's distance from the root, in tokens.

## 13. Positions with no ranking

**A `generate` may return an id it can give no ranking for.** Section 2 requires that this be
declared rather than guessed, so such a position is recorded as a node with no ranked edges at
its parent — check 7's one exception — and therefore with no derivable logprob.

Nothing else is affected. The id is stored, `bytes_for` answers for it like any other, and the
path's bytes are complete. And every such node is a fragment — a position a model can be given
is one an adapter can describe — so nothing starts there and the gap never compounds.

Backends produce this for their own reasons; why is `docs/SERVER.md`'s business, not this
document's.
