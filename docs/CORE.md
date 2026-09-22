# The core

**What the format is.** Node, edge, source, ranking, act, the on-disk shape, the invariants and
the operations. **It is never edited in the course of doing something else.** Moving it is its
own piece of work; what that costs a reader is *Conformance and extension*.

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
needed.

A token's bytes may be a fragment of a character — Qwen2.5 spells `🜁` as three tokens, none of
them valid UTF-8 alone. Such a token is a node like any other, and so is a node whose path bytes
do not decode. **The format has no notion of a character boundary**, and nothing here is
conditioned on one: a node has children if something extended it, ranked edges if a generation
computed a distribution at it, and both are takeable.

A control token is not a fragment. `<|endoftext|>` spells the thirteen bytes `<|endoftext|>`,
which tokenise back to it, so it needs no special handling anywhere in this format.

Whether a backend will evaluate a given path is that backend's affair and is stated in
`docs/ADAPTER.md`. What the core forms and what a backend will accept are different questions,
and only the first is answered here.

## Sources

Every node records **who produced it**: a user, or a named model.

| field | meaning |
| --- | --- |
| `kind` | `user` or `model` |
| `name` | who — `alice`, `qwen2.5-7b-base`; the empty name is the unnamed user |

**Source is part of the merge key.** A node is `(parent, token_id, source)`, unique —
`INV-MERGE-KEY`. So:

- two models named apart never factor together, and the split is visible in the tree
- authored text never collapses into a model draw that happens to match
- a draw and a deliberate branch that land on the same token from the same model **do** factor
  together, because they are the same state

**A model is always named** — `INV-SOURCE-NAMED`. Two unnamed models would be one source, and
their draws would factor together as though one had produced both. The empty name is reserved
for the unnamed user and belongs to nothing else.

**The name carries the whole distinction, and the core cannot check it.** A name must separate
everything whose draws must not factor together — the model, its quantisation, and anything else
that makes two servers different models in practice. Two of those served under one name are one
source to this format, and the tree will merge them. Naming is the enforcement.

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

**Two generations may report one row differently, and the value first written stands.** This is
what *never rewritten* means where observations disagree, and it is how they are reconciled: a
reader gets one value per edge, and no record of whether another was ever seen. How far apart two
observations can be is a property of the backend and lives in that backend's notes.

**A node's own logprob is not stored.** It is the ranked edge at its parent, for its source,
carrying its `token_id`. What a node was worth and what its alternatives were worth cannot drift
apart, because there is only one record of both.

**A root has no logprob**, having no parent to carry the edge. It follows that a `generate` that
begins a root cannot record the ranking for its first position: a ranking belongs to the node the
position was computed at, and for that position there is none. The distribution over an empty
context is a real thing this format does not hold.

**A node may be absent from its parent's ranking.** A generation that can give no ranking for a
position declines rather than guesses, a backend may emit a token on a stop condition without it
passing through a sampler, and a draw may land outside the alternatives that were recorded for its
position. Such a node has no derivable logprob until a later generation supplies the covering edge
— which extension then does, with no further mechanism. The store does not require the covering
edge.

**Nothing records why an edge is missing.** A declination is not distinguished from a position
nothing has generated at; in both the absence is the whole record.

**A drawn token is ordinarily among its parent's ranked edges**, which is what makes a node's
logprob derivable in the ordinary case, and rank `0` is frequently not the one drawn: the draw is
a sample from the distribution rather than its maximum. Values are the model's own and sum to
less than one, by the mass of the vocabulary that was not recorded.

## Acts

**What was done**, recorded once. An act starts at one node and either extends the tree from it,
changes whether it is live, or records that it did neither.

| field | on | meaning |
| --- | --- | --- |
| `op` | all | `create`, `generate`, `realise`, `delete` or `undelete` |
| `actor` | all | **who acted** |
| `origin` | all | the node it started from, or `null` if it began a root |
| `tip` | all | the last node it produced, or `null` if it produced none |
| `created` | all | timestamp, ISO 8601, UTC |
| `model` | `generate` | the model it asked |
| `params` | `generate` | index into the interned parameter table |
| `terminator` | `generate` | its outcome; `null` while in flight |
| `rank` | `realise` | the rank of the edge that was taken |

**An act's tokens are the path from `origin` (exclusive) to `tip` (inclusive).** Nothing else is
stored, because each node has one parent and that path is therefore unique.

**An act that produced nodes covers a non-empty range.** This is not the same as producing no
*new* nodes: the range is reckoned before merge, so acts may overlap in part or in full, and an
act whose every node already existed is legal and records that the path was taken again.

**Only `generate` calls a model.** `create` tokenises text someone wrote, which needs the
vocabulary but not the model. `realise` turns a ranked edge that is already recorded into a node,
and `delete` and `undelete` change one flag — all three are reachable with nothing running at
all, and `create` with a tokeniser alone.

**An act records who acted; a node records who produced its token.** These are different
questions. Authoring text, asking a model to continue and taking a ranked edge are all things a
reader does, so `actor` is a user in every case. What a node carries is whoever produced it: the
model a `generate` asked, the model that ranked the edge a `realise` took, or the source a
`create` names.

**A `create` names the source its nodes carry, and it need not be the actor.** Text a model
produced elsewhere is recorded as that model's, with the act naming whoever entered it. The core
cannot check such a claim, and Sources has already said that naming is the enforcement.

`origin` may be null for `create` and for `generate`, each of which then begins a root. It may not
be null for `realise`, which needs an existing edge to take, nor for `delete` and `undelete`, which
name in `origin` the node whose flag they change and produce no nodes at all.

| terminator | means |
| --- | --- |
| `eos` | the model emitted an end-of-text token |
| `limit` | it drew the requested `length` |
| `cancelled` | a caller stopped it |
| `failed` | the backend broke mid-call |
| `aborted` | the writer is gone |
| `refused` | the adapter declined the request, and no model was called |

**`terminator` is null exactly while a `generate` is in flight, and `tip` is null exactly when an
act produced no nodes.** An `aborted`, `failed` or `refused` generation wrote nothing and names no
tip. A `cancelled` one names what it drew before it stopped, or no tip if it stopped before
drawing. `eos` and `limit` always name a tip.

**The end-of-text token a model draws is a node**, and it is the tip of the act that drew it. It
may arrive with no covering ranked edge, which Rankings provides for.

**Refusal is the adapter's answer and is recorded; rejection is the core's and is not.** A
generation the adapter declines is an act with terminator `refused`, holding the parameters it was
asked for. A `create` whose round trip fails, and one that would add no tokens, are rejected before
anything is written and leave no trace. Only a `generate` has a terminator, so only a `generate`
can record its own undoing.

**Parameters are what was asked for.** The core records the request, and reads one field of it.
There is no effective parameter set and no second version to reconcile: an adapter either meets a
request or refuses it, and one that would substitute a value refuses instead. A parameter set is
therefore complete when the act is written, and nothing in it is revised when the answer comes
back.

**`length` is the field the core reads** — how many tokens to draw, required, a positive finite
integer. `limit` means it was reached. Every other key is passed through uninterpreted.

A generation that would not fit the room a backend has is refused rather than truncated, so
running out of context is not a way for a generation to end. That is why `limit` means one thing.

Every distinct parameter set is written once and referenced by index. Distinctness is on a
canonical serialisation — object keys sorted, no insignificant whitespace — so two spellings of
one request intern to one row.

**A `generate` act with a null `terminator` is in flight.** Only `generate` can be; the others
are one write each. The claim makes it decidable: one claim is one writer, so an act still in
flight when a claim is taken is one whose writer is gone, and is recorded `aborted`.

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
an absent ranked edge, not an estimate; a request that cannot be met is refused rather than met
approximately, and the refusal is the act's outcome.

An adapter absorbs its backend's faults rather than passing them through, so what the core sees
is a repaired stream. Where it gets an answer, and from how many sources, is not the core's
concern.

## On disk

Two files and a lock, in a directory.

**`tree.json`** — provenance only. The structure is far too large to read by eye and lives
entirely in SQL.

```json
{
  "marker": "token-loom/nodes-2",
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

CREATE TABLE params (
  id   INTEGER PRIMARY KEY,
  json TEXT NOT NULL UNIQUE);              -- canonical: keys sorted, no insignificant whitespace

CREATE TABLE acts (
  id      INTEGER PRIMARY KEY,
  op      TEXT NOT NULL,                   -- 'create' | 'generate' | 'realise'
                                           --   | 'delete' | 'undelete'
  actor   INTEGER NOT NULL,                -- who acted; a source of kind 'user'
  origin  INTEGER,                         -- NULL if the act began a root
  tip     INTEGER,                         -- NULL if the act produced no nodes
  created TEXT NOT NULL,                   -- ISO 8601, UTC, ending 'Z'
  model   INTEGER, params INTEGER, terminator TEXT,  -- 'generate' only
  rank    INTEGER);                                  -- 'realise' only
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

**The database runs in WAL journal mode**, which is what lets a reader take no lock and not be
blocked by a writer. The SQLite transaction is not what spans a model call: an act's first write
commits and the transaction closes.

Timestamps everywhere in this format are ISO 8601 in UTC, ending `Z`.

**`lock`** — a writer's claim on the tree. One `flock`, taken when a store is opened for writing
and held until it is closed or the process dies. **One claim is one writer, and what that buys is
two things a writer can read off the store rather than guess at.** What it verified cannot change
beneath it, so verifying is once per claim and not once per act. And an act still in flight when a
claim is taken is one whose writer is gone, because a claim dies with its holder. Recording those
acts as `aborted` is the first write after claiming, so **opening a tree for writing can modify
it.** The `flock` is taken without blocking, so a second writer is told at once rather than left
waiting. A reader takes no lock.

## The invariants

- **`INV-TREE-PARENT`** — every non-null `parent` names a node that exists.
- **`INV-TREE-ROOTED`** — following `parent` from any node reaches a root; there are no cycles.
- **`INV-MERGE-KEY`** — `(parent, token_id, source)` is unique.
- **`INV-VOCAB-CLOSED`** — every `token_id` in `nodes` and `edges` is in `vocab`.
- **`INV-SOURCE-CLOSED`** — every source named in `nodes`, `edges` and `acts` is in `sources`.
- **`INV-SOURCE-NAMED`** — a source of kind `model` has a non-empty `name`. The empty name is
  the unnamed user and belongs to nothing else.
- **`INV-RANK-ANCHORED`** — no `edges` row names a node that does not exist. A deleted node is
  still held, so its rows are not orphans.
- **`INV-RANK-DENSE`** — ranks within a `(node, source)` are distinct and contiguous from `0`.
- **`INV-RANK-UNIQUE`** — a `token_id` appears at most once within a `(node, source)`.
- **`INV-ACT-PATH`** — an act's non-null `origin` and non-null `tip` each name a node that
  exists; a `tip` descends from `origin` — or from a root, if `origin` is null — and the range
  from `origin` exclusive to `tip` inclusive is non-empty.
- **`INV-ACT-ACTOR`** — an act's `actor` is a source of kind `user`. A `model` is what produces
  tokens, and acting is not producing.
- **`INV-ACT-SOURCE`** — every node an act produced carries one source: for `generate` the act's
  `model`, for `realise` the source of the edge it took, and for `create` one source along the
  whole path.
- **`INV-ACT-CREATE`** — a `create` act has a non-null `tip`, and no `model`, `params`,
  `terminator` or `rank`.
- **`INV-ACT-GENERATE`** — a `generate` act has `model` and `params`, and no `rank`. A null
  `terminator` means in flight. A null `tip` requires a `terminator` of `cancelled`, `failed`,
  `aborted` or `refused`, or none at all.
- **`INV-ACT-LIMIT`** — a `generate` act with terminator `limit` covers exactly the `length` its
  parameters name. It is the one terminator whose meaning the record can be held to.
- **`INV-ACT-REALISE`** — a `realise` act has `rank` and a non-null `origin` and `tip`, and no
  `model`, `params` or `terminator`; `tip` is a child of `origin`; and the edge
  `(origin, tip.source, rank)` exists and carries `tip.token_id`.
- **`INV-ACT-DELETE`** — a `delete` or `undelete` act has a non-null `origin`, and no `tip`,
  `model`, `params`, `terminator` or `rank`.

Descending logprob within a ranking is **not** an invariant. Rankings says why.

## Operations

### Producing nodes

| operation | writes | leaves |
| --- | --- | --- |
| `create(at, bytes, source)` | one act, and nodes for the tokens | tokenised against the tree's vocabulary; rejected if the round trip does not hold |
| `generate(at, params)` | one act, and nodes for what was drawn | provenance first, then the nodes |
| `realise(node, source, rank)` | one act and one node | the ranked edge, taken; no model call |

**Creating is bytes in, tokens out.** Authored bytes must be valid UTF-8. The text is tokenised,
the resulting nodes are reassembled exactly as Derived reads will reassemble them, and the result
is compared against what was authored; a mismatch rejects the act. The comparison is against the
reassembly and never against a backend's own way of turning ids back into text, because the
reassembly is what a reader will do and is therefore the thing that has to hold.

This also settles what the bytes cannot: a special-token literal may be read as one token or as
its characters, the two spell the same bytes either way, and the stored ids tell them apart with
no field to record it.

**Generation is two writes.** The act and its parameters are written and committed *before* the
model is called; the nodes, the ranked edges and the terminator when it answers. An
act with no terminator is therefore a generation in flight, and no node can ever belong to an act
the store has not heard of. A refusal comes back on the same path as an answer, and lands in the
same second write.

**`realise` is one write and no call.** The ranked edge at `(node, source, rank)` is already
recorded, so taking it is a lookup and a node — and if that node already exists, the merge key
finds it and only the act is written. Nothing is in flight and nothing can abort.

**An edge is named by node, source and rank.** Two sources may rank at one node, so a rank alone
names nothing. The act stores `origin`, `tip` and `rank`; the edge's source is `tip`'s, so the
record needs no column for it.

**Branching is `realise` then `generate`.** Realising gives the node; generating from it
continues. The two are separate acts, so an alternative can be taken and left unexplored, or
several taken at one node before any is continued, and neither needs an adapter that can
generate.

**Merging is checked, not assumed.** Every node an act produces is looked up by
`(parent, token_id, source)` first and reused if it exists.

**Liveness constrains where an act starts, not what it produces.** The acts that produce nodes
begin at a live node. What they produce may pass into ground that is not: a generation whose path
merges into a deleted node extends below it, and those nodes are recorded and are not live — the
same answer `delete` gives for every descendant.

### Changing liveness

| operation | writes | leaves |
| --- | --- | --- |
| `delete(node)` | one act, and `deleted` on that node alone | descendants untouched |
| `undelete(node)` | one act, and the flag cleared | live again only if its ancestry is |

**These two begin anywhere.** Liveness is what they change, so requiring a live node would put
`undelete` out of reach.

**A delete names one node.** Whether a node is live is derived by walking its ancestry: it is
live when neither it nor any ancestor is deleted. So a delete touches one node, undoing it touches
one, and a descendant deleted on its own account stays deleted when its ancestor comes back.

**The flag is the state; the act is the record of it changing.** Liveness comes from `deleted` and
never from `acts`. Deleting what is already effectively deleted is legal — it is what makes the
paragraph above work — and records an act that changed nothing, exactly as an act whose every node
already existed does.

## Derived reads

Nothing here is stored. **These are the derivations a reader would otherwise get wrong**; what
else the tables admit is a query rather than a fact about the format.

- **A node's bytes** — its `vocab` entry.
- **A path's bytes** — the bytes of each node from the root down, in order.
- **A node's logprob** — the ranked edge at its parent, for its source, with its `token_id`.
- **A node's recorded depth** — how many ranked edges stand at it, counted **per source**. It is
  not the `record_rows` of any act: *Rankings* is why, since rows accumulate and what has landed
  is not recoverable from the parameters of any one generation that passed. One count over a node
  two sources ranked adds two rankings together and is a depth of nothing. Depth is a count of
  rows and not a share of the distribution — the rows carry the probabilities, they reach no
  particular total, and anything read off a ranking is read off what this count says is there.
- **An act's tokens** — the path from `origin` exclusive to `tip` inclusive.
- **Whether a node is live** — neither it nor any ancestor carries `deleted`. A descent from the
  root carries the answer down.
- **Unrealised edges** — ranked edges at a node with no matching child. This is the branchable
  set, and it is a `LEFT JOIN`.

## Conformance and extension

- A reader that does not recognise `marker` stops.
- **A reader ignores tables and columns it does not know**, and neither a new table nor a new
  column changes `marker`. This is what allows the format to grow without invalidating a reader:
  what a reader already understands still means what it did.
- **A new value in an existing column changes what that column means, and does change `marker`**,
  as does any other change to what an existing table means — the one circumstance that makes an
  older reader wrong rather than merely incomplete.
- A store that fails an invariant is not repaired silently. A reader reports it; a writer will not
  write.

## What this does not specify

- How a backend produces any of this. That is `docs/ADAPTER.md`.
- Which paths a backend will evaluate. The core forms positions; a backend accepts them or
  refuses, and the refusal is recorded.
- Sampling parameters and what they mean, beyond the length limit the core imposes.
- Any reading surface — layout, navigation, selection, or what a client chooses to show, bytes
  that do not decode included.
- Concurrency beyond the claim: no protocol across machines.
- Import, export, and conversion between vocabularies, beyond the statement that a tree in a
  second vocabulary is a second tree.
- Performance, indexing beyond the keys stated here, and reclaiming space.
- Any interpretation of logprobs — comparison, aggregation, or what a distribution means.

---

## Appendix — a worked example

One tree, built in seven stages. The rows are exact. Every construct in this document appears in
it but four terminators — `eos`, `cancelled`, `failed` and `aborted` — a `create` attributed to a
source that did not act, and `delete` and `undelete`. None of those shapes a row differently from
one that is here: a delete is an act with an `origin`, no `tip` and nothing else, and its effect
is one flag.

**The ids and logprobs below are real**, taken from `Qwen2.5-7B.i1-Q4_K_M` served by llama.cpp
over Vulkan, 16k context. Logprobs are shown to four places; nothing else is rounded or invented.
The parameters are chosen to make each stage legible, and are neither defaults nor
recommendations.

### Sources

| `id` | `kind` | `name` |
| --- | --- | --- |
| 1 | `user` | *empty* |
| 2 | `model` | `qwen2.5-7b-base-q4km` |

The name carries the quantisation, per Sources. A server alias is not a source name; what names
the source is whatever must not factor together with anything else.

### Stage 1 — `create(null, "The sky")`

Authored by the unnamed user. Tokenises to two ids, and begins a root because `origin` is null.

| node | `parent` | `token_id` | bytes | `source` |
| --- | --- | --- | --- | --- |
| 1 | *null* | 785 | `The` | 1 |
| 2 | 1 | 12884 | ` sky` | 1 |

Act 1: `create`, actor 1, `origin` *null*, `tip` 2.

### Stage 2 — `generate(at=2)`, `top_k` 5, `top_n` 5, `length` 3, `seed` 42

| node | `parent` | `token_id` | bytes | `source` |
| --- | --- | --- | --- | --- |
| 3 | 2 | 5023 | ` currently` | 2 |
| 4 | 3 | 702 | ` has` | 2 |
| 5 | 4 | 220 | ` ` | 2 |

Act 2: `generate`, actor 1, `model` 2, `origin` 2, `tip` 5, `params` 1,
`terminator` `limit`.

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

### Stage 3 — `generate(at=2)`, `top_k` 5, `top_n` 20, `length` 2, `seed` 99

| node | `parent` | `token_id` | bytes | `source` |
| --- | --- | --- | --- | --- |
| 6 | 2 | 702 | ` has` | 2 |
| 7 | 6 | 6519 | ` turned` | 2 |

Act 3: `generate`, actor 1, `model` 2, `origin` 2, `tip` 7, `params` 2,
`terminator` `limit`.

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

The same parameters, seed included. The model reproduces the path exactly, so every node merges
and nothing new is written but the act.

Act 4: `generate`, actor 1, `model` 2, `origin` 2, `tip` 5, `params` 1,
`terminator` `limit` —
every field but the id identical to act 2.

**An act that produces no new nodes still covers a non-empty range.** The range is reckoned before
merge, so this act covers nodes 3, 4 and 5 — every one of them already covered by act 2. The
rankings it reported were already recorded, so extension appends nothing.

### Stage 5 — `realise(node 2, source 2, rank 0)`

The unnamed user takes ` is` — the alternative the model ranked highest at node 2 and that neither
generation drew. No model is called.

| node | `parent` | `token_id` | bytes | `source` |
| --- | --- | --- | --- | --- |
| 8 | 2 | 374 | ` is` | 2 |

Act 5: `realise`, actor 1, `origin` 2, `tip` 8, `rank` 0.

**The node carries the model, and no act named it.** A `realise` takes an edge the model ranked,
so the node's source comes from the edge rather than from anything the act stores. Node 8 has no
ranking, because nothing has generated from it.

### Stage 6 — `create(node 8, "<|endoftext|>🜁")`

Authored bytes: the thirteen characters `<|endoftext|>`, then `F0 9F 9C 81`.

| node | `parent` | `token_id` | bytes | `source` |
| --- | --- | --- | --- | --- |
| 9 | 8 | 151643 | `<\|endoftext\|>` | 1 |
| 10 | 9 | 9284 | `F0 9F` | 1 |
| 11 | 10 | 250 | `9C` | 1 |
| 12 | 11 | 223 | `81` | 1 |

Act 6: `create`, actor 1, `origin` 8, `tip` 12.

**The special-token literal read as one token.** This `create` went through the adapter's
special-token path, so the tokeniser returned id 151643 for those thirteen characters rather than
thirteen characters' worth of ids; the plain path would have given the second reading and the same
bytes. Which path an adapter offers, and which is the default, is `docs/ADAPTER.md`. The stored id
is what tells the two apart, and no field records which was meant. End-of-text is otherwise a node
like any other.

**Nodes 10 and 11 spell fragments, and the record treats them as it treats any node.** They have
children, they could be given more, and their ranked edges — had a generation left any — would be
takeable. Whether a backend will evaluate the path ending at one of them is a question for
`docs/ADAPTER.md` and never for these rows.

### Stage 7 — `generate(at=12)`, `top_k` 5, `top_n` 200, `length` 4, `seed` 7

The adapter will not report two hundred ranked ids, and reducing the request is not open to it, so
it refuses. No model is called.

Act 7: `generate`, actor 1, `model` 2, `origin` 12, `tip` *null*, `params` 3,
`terminator` `refused`.

**An act with no tip, and the one place `model` is the only record of who was asked.** Nothing was
drawn, so no node carries the model and the act's own column is what says which one refused. Params
row 3 holds the request and stays there — a parameter set is written before the answer comes back,
so the store keeps what was asked for whether or not it was met.

### Reading the finished tree

- **Path bytes to node 5** — `The sky currently has `.
- **Path bytes to node 12** — `The sky is<|endoftext|>🜁`. Display shows the end-of-text token
  literally.
- **Node 3's logprob** — −2.0363, the edge at node 2 for source 2 carrying token 5023. Stored
  once, derived rather than duplicated.
- **Unrealised edges at node 2** — ranks 3 through 19. Ranks 0, 1 and 2 have children: nodes 8, 6
  and 3. This is the branchable set.
- **An act's tokens for act 4** — nodes 3, 4 and 5, the same three act 2 covered. An act's range
  begins below its origin, so neither covers node 2.
