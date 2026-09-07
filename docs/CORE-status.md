# The core — status

**Where `docs/CORE.md` stands.** It is cited and must not move, so what is true *for now* about
it lives here instead of in it.

---

## Locked

`docs/CORE.md` is locked at `marker` `token-loom/nodes-1`, on branch `core-design-lock`.

It was written as a plan, transcribed whole, reviewed against itself and its adapter contract,
and amended once. The terminator set was closed at lock rather than deferred, because adding one
later changes the meaning of an existing column and is the one event the conformance rule says
bumps `marker`.

## Built

**The format is implemented and holds.** `src/tokenloom/core/` is the store — the three acts, the
two state edits, the derived reads and a checker for every named invariant. The command line on
top of it is `src/tokenloom/cli.py`. No implementation detail belongs in this section; what
belongs here is that the document has a reader now, and what that reader found.

**The appendix has been replayed against the implementation, stage by stage, and matches.** Its
node numbering comes out 1 through 12 and its source numbering 1 and 2, which is the part worth
stating: node ids are opaque, so reproducing the document's numbering means every merge decision
along the way agreed with it.

**The appendix's logprobs are real, and they reproduce.** All twenty rows at node 2 come back
bit-identical off the running server, ranks 0 through 19 to four places, including the fifteen
that only appear after the ranking is extended. A live test asserts it.

## Specified and unwitnessed

Of the three constructs the lock left unwitnessed, one remains — and it is now expected to stay
that way.

- **`eos`** — witnessed. The earlier note that end-of-text did not appear in the top 40 at three
  document-ending prompts was a fact about those prompts; after ` The end.` it ranks at −1.364 and
  is drawn on most seeds, and it arrives as an ordinary node with a covering ranked edge.
- **`failed`** and **`aborted`** — witnessed. `failed` by a backend raised under a live act;
  `aborted` by killing a writer mid-call in a subprocess and letting the next writer sweep. Both
  are tests rather than anecdotes.
- **`cancelled`** — unreached, and deliberately. It needs a `generate` that can be interrupted and
  that returns what it drew. Streaming was the route to that, and streaming on the one backend
  that exists drops the interior ids of a multi-token character — so an interruptible generation
  there would have to be declined rather than recorded. `docs/ADAPTER.md` has what a client that
  wants to stop a long generation does instead. **This is no longer an open item that a locked core
  is waiting on.** The
  terminator stays specified and unproduced, on the same reasoning as the paragraph below.

**A whole construct is unwitnessed too, and stays that way for the same kind of reason.** No tree
has held two model sources. Source is in the merge key, so two models' draws never factor together
and cross-source agreement is two nodes rather than one — but nothing has built such a tree, and the
`cross_source` derived read has never seen real data. That is not an oversight to be closed: a
tree is expected in practice to explore the paths one model presents, and correctness across
models was kept in the format because it was cheap and might one day matter, not because it was
going to be used. Recorded here so it is not mistaken for a gap and prioritised as one. The cost
of it being wrong is bounded and late; the cost of it not being in the format at all would have
been a marker bump.

## What building it found

- **A generation that begins a root has nowhere to put its first ranking.** A ranking belongs to
  the node the position was computed at, and for position 0 of a root-beginning `generate` there
  is no such node — the distribution over the model's empty context is a real thing that this
  format cannot hold. It is not a fault in the implementation and not something the lock can fix;
  it is a consequence of a node's logprob being the ranked edge at its *parent*. It is also
  unreachable on the one backend that exists: llama.cpp accepts an empty prompt and generates
  nothing, so the adapter refuses the request rather than meeting it approximately, and `create`
  is how a root gets made in practice. Recorded because nothing else records it.
- **The appendix's stage 7 has no llama.cpp analogue, and does not need one.** It refuses `top_n`
  200 because *that* adapter would not report two hundred ranked ids. This build reports up to the
  whole vocabulary. The appendix illustrates the shape of an act with no tip, which is the only
  thing it is there to do, and no fact about a backend was ever in the locked document.

## What the lock does not cover

The adapter contract is `docs/ADAPTER.md` and is deliberately unlocked; its own open items are
stated there and are not repeated here. The reading surface has no document yet.

## Held for a possible future core

**Not defects, and not work outstanding.** What follows is what a reopening would carry, kept as
one list rather than a queue. The worth of a document that does not move is that citing it is safe,
and that worth is spent the first time it moves — so it is spent once, on everything at once, or
not at all. Anything that arrives after the edit waits for a next one, and there is not expected to
be a next one.

**`marker` bumps to `token-loom/nodes-2`.** The item below adds a kind of act, which makes a
reader written to the current document wrong rather than merely incomplete — the one circumstance
*Conformance and extension* says bumps it.

### Deleting is an act

**Recorded in `acts` with the others; the `deleted` flag stays exactly as it is.** What changes is
that the two writes leave a trace, not how liveness is derived.

`acts` is where a reader goes to find what was done, and it does not hold the mutation with the
largest effect on what a reader sees. A deleted sibling hides a fork, so the shape of the tree a
client draws is a function of what is deleted — and that is the one change with no history, no
time and no actor. `realise` already establishes that an act's source is *who acted* rather than
what the node carries. Deletion is that same shape, with no node produced at all.

**Additive, and not a replacement.** *Whether a node is live* stays derived from `deleted` by
walking ancestry. Deriving liveness from an act log instead would cost more than the read it
replaced, and making that read cheap is work outstanding elsewhere. **The flag is the state; the
act is the record of the state changing**, and both are needed.

What moves:

- **`op`, in `acts`.** `'create' | 'generate' | 'realise'` gains `'delete'` and `'undelete'`.
- **`INV-ACT-PATH`.** *Only a `generate` may have a null `tip`* stops being true: a delete produces
  no nodes, so `origin` names the node acted on and `tip` is null.
- **A new `INV-ACT-DELETE`.** `origin` is non-null, and `tip`, `params`, `seed`, `terminator` and
  `rank` are all null.
- **`INV-ACT-SOURCE`.** Gains a third case: for `delete` and `undelete` the source is the actor,
  and no node carries it.
- **Nothing in `Delete`.** *A delete names one node*, the ancestry walk, and *deleting what is
  already effectively deleted is legal* are all unaffected. A repeated delete now records an act
  that changed no state, and the precedent is already in `Acts`: *an act whose every node already
  existed is legal and records that the path was taken again*.
- **`Conformance and extension`.** Its two extension clauses are made disjoint — see below.

**This item is what bumps `marker`.** An older reader reads `acts` as the whole of what was done.
That is true today and false after, which is *wrong rather than merely incomplete* — the one
circumstance *Conformance and extension* names.

**It also settles an ambiguity in that section, and the edit must settle it either way.** *Adding
a record type does not change `marker`* and *`marker` changes only when an existing table changes
meaning* both reach a new `op` value in an existing table, and they give opposite answers. The
second governs, because the test it states is whether an older reader becomes **wrong** rather
than incomplete, and a reader that takes `acts` for the whole of what was done becomes wrong.

**The two are made disjoint rather than adjudicated case by case**, which is what keeps the next
one from having to be argued at all:

> A new **table** is a record type, and adding one does not change `marker`. A new **value in an
> existing column** changes what that column means, and does.

This costs nothing that the extension rule was for. A reader still ignores tables and columns it
does not know, so a record type added later is still free — the clause keeps its whole purpose,
and only stops reaching a case it was never about. Left unresolved, the question is decided by
whichever second reader is written first, and by then `docs/CORE.md` is locked again.

**Rejected: a separate `edits` table.** It is unambiguously a new record type, so `marker` would
not move and an older reader would ignore it by rule. It is cheaper on that one axis and worse on
every other: what was done would live in two tables, every reader of the history would union them,
and the command line would have to explain why. The marker exists to say that a format changed,
and declining to use it so that a number can stay still is a compromise bought with the format's
consistency. **It is also bought with nothing**: the bump is only expensive where stores exist
that predate it, and here the only ones are validation data on the machine that made them.

