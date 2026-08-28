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

Of the three constructs the lock left unwitnessed, one remains.

- **`eos`** — witnessed. The earlier note that end-of-text did not appear in the top 40 at three
  document-ending prompts was a fact about those prompts; after ` The end.` it ranks at −1.364 and
  is drawn on most seeds, and it arrives as an ordinary node with a covering ranked edge.
- **`failed`** and **`aborted`** — witnessed. `failed` by a backend raised under a live act;
  `aborted` by killing a writer mid-call in a subprocess and letting the next writer sweep. Both
  are tests rather than anecdotes.
- **`cancelled`** — still unreachable. It needs a `generate` that can be interrupted and that
  returns what it drew, which nothing in the three-operation surface can be. This is the one open
  item a locked core is already waiting on, it belongs to the adapter, and it arrives with
  streaming.

**A whole construct is unwitnessed too, and stays that way deliberately.** No tree has held two
model sources. Source is in the merge key, so two models' draws never factor together and
cross-source agreement is two nodes rather than one — but nothing has built such a tree, and the
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
