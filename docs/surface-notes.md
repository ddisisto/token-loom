# Surface — notes

**Not a design.** What has been decided, what building a probe found, and what is still open,
collected in one place so none of it has to be remembered or re-derived. There is no layout here
and no gesture, because neither has been settled and writing either down would give it a standing
it has not earned.

**This document is consumed and deleted.** `docs/SURFACE.md` is what the surface is designed in,
and everything above *Sampling vs. greedy decoding considerations* has either moved into it or been
struck out. Nothing cites this file, and nothing should — a note that outlives the document it fed
is the dangling copy the project keeps paying for.

**The sampling section is the exception, and is why this file is still here.** It is held rather
than superseded: it is taken up after the core changes land, and it is the one thing here that
`docs/SURFACE.md` does not yet say.

---

## Decided

Each of these closes a question rather than opening one. The reasons are what matter, since a
decision whose reason is lost gets re-argued at the first inconvenience.

- **Characters are displayed natively, and a token is not the display unit.** A token spells
  several characters in ordinary English and a character can span several tokens, so the two are
  not in correspondence. What the surface renders is a **segment**: the shortest run of nodes
  whose bytes decode. Ordinary English gives one node per segment; `🜁` gives three. Addressing
  is per segment, so a character spelled by several tokens cannot be branched *into* — that is
  the accepted gap, and it is the whole of it.

- **The surface is the sole writer of any tree it holds open**, with at most one write in flight.
  It follows that the store is opened for writing once per process and verified once, not per
  request — which is the choice `docs/NEXT.md` says has to be made and written down, and which
  takes the 613 ms verification off the interactive path. The assumption is discipline and not
  enforcement; `docs/CORE-status.md` holds what the core would need to enforce it, and the cost
  of breaking it is a blocked call rather than a damaged store.

- **Density is hidden behind intent.** The main view shows realised nodes. What else was ranked
  at a position is reached by asking, not offered everywhere at once — there are twenty
  alternatives at nearly every position in a real tree, and a surface that displayed them
  unprompted would be showing its instrument rather than its subject.

- **Chunking is a technique, not an inheritance.** A long generation may be issued as consecutive
  short `generate` acts, and stopping is declining to issue the next. Whether the surface does
  this is the surface's decision. `docs/ADAPTER.md` currently states it as though every client
  inherits it, and `docs/NEXT.md` carries the edit.

- **Cadence is not measured yet, and deferring it costs nothing.** Text arrives in whole acts,
  roughly half a second for sixteen tokens at 32 tok/s. A chunk boundary moves the logprobs
  recorded there by up to 0.057, which is real and in the record — but chunk length *is* `length`
  in `params`, recorded per act, so a later reader can select on it. The question stays
  answerable whenever it is asked.

## What building the probe found

Findings, not decisions. Each is a thing looking produced that reading had not.

- **The display gap is cheaper than it was priced at.** Segmenting at decode boundaries is
  fifteen lines and renders the multi-token character correctly. Only sub-segment addressing is
  lost. Verified against the core's worked example: three tokens become one segment spelling one
  character, and a path stopping mid-character yields a segment with no string form.

- **A deleted node hides a fork.** `data/example` has one, so the reader shows one fork passed
  where the record holds two. The liveness rule working as specified — and it means the shape a
  reader sees is a function of what is deleted, with nothing currently saying more was here.
  Whether that is right is open.

- **A control token is visually ordinary.** `<|endoftext|>` renders as its own thirteen
  characters, which is what the core prescribes and is indistinguishable from text that spells
  the same thing. Whether the surface marks it is open, and the store cannot answer it: the two
  readings differ only in the stored id.

- **The ranking wants the taken token in it.** Not `unrealised_edges()`, which is the branchable
  set alone. A reader looking at a position wants to see what was taken sitting at its own rank
  among the alternatives — rank 1 of 20, against what else — and the branchable set is then the
  rows with no child. **This is a bulk read the read layer should have**, and it fell out of
  building a panel rather than out of reading the documents.

- **The actionable row is the under-marked one.** A ranking shows rows that are unrealised, rows
  realised elsewhere in the tree, and the row that was taken here. The middle kind is the one a
  reader can move to with no model call, and it currently looks like the rest.

## Open, and not decidable in prose

The gesture questions. These are what a probe is for, and a document that answered them from an
armchair would be the one-line rejection the method warns about.

1. What the reader does at a fork — showing that siblings exist, and moving between them, without
   the linear case paying for it.
2. Getting from reading to a ranking and back without losing one's place.
3. What taking an alternative feels like: whether the text changes underneath, or the reader moves.
4. Whether block-arrival reads as alive or as stutter, and whether pacing within a block — which
   invents a timing the record does not hold — is worth it.

## Still owed to the floor

**No capability may be surface-only**, which is checked against a document cheaply and retrofitted
expensively.

- `will_evaluate` has no command-line verb, though `docs/ADAPTER.md` says explicitly that the
  command line should be able to answer the same question a surface asks.

## Prior art

**mikupad** is the closest thing that exists: one self-contained HTML file, raw completion rather
than chat, hover a token for what else was ranked, click to swap. The gesture vocabulary is a good
floor and there is no reason to invent a worse one.

**Where it stops is where this starts.** Its probabilities are ephemeral — attached to the current
text, discarded when a token is swapped, with no record of what was ranked at positions already
passed. Everything downstream of the first gesture is unprecedented here: a ranking that persists
at a node, a branch that can be taken and left, paths that merge, and acts that say what was done.


## Sampling vs. greedy decoding considerations
On greedy: I think you're right, and for a stronger reason than flat rows
Sampling and branch exploration do the same job, and the tool only needs one. Sampling explores the distribution by rolling dice and discarding what wasn't rolled. This tool explores it by recording everything ranked and letting you take any of it, keeping what you don't. For exploration the second strictly dominates — nothing is lost, and you choose rather than the RNG. Temperature's remaining jobs are cheap varied continuations with no human in the loop, and being a research variable in its own right. Both real. Neither is the floor.

Two things follow that I think are worth more than the original complaint:

The record becomes interpretable. Under greedy, every node is either the model's top choice given this prefix or a human took rank k. Every edge has a reason. Under sampling the reason is a seed. For something whose premise is that the record goes down to the token, that's a large gain.

It makes deepening a ranking free. "Show me more alternatives here" is a generate of length 1 with a larger top_n — rankings extend and are never truncated, so you can deepen wherever you care and the record accumulates. Under greedy the drawn token is the argmax and almost always already exists, so it merges and costs one act. Under sampling it litters the tree with children you didn't ask for. This is also what takes the pressure off top_n: the default no longer has to be right, because it's revisable per position.

Two costs, one of which you should measure before committing
Greedy base-model text degenerates. Repetition and looping are what temperature 0 does, especially a 7B base over a story prompt. data/example reads well and was drawn at 1.0. Your floor case may read materially worse. That's cheap to check — same prompt, greedy and 1.0, read both — and worth checking, because "the floor case is a clean text reader" is load-bearing. Though note the tension cuts both ways: for a tool aimed at attractors in the prior, watching greedy collapse into a loop is the phenomenon, not a defect.

Greedy is not quite canonical, and you'd be assuming it is. ADAPTER.md measures chunk-boundary and cache-state shifts up to 0.057 that reorder ranks. At a near-tie, argmax can flip — so the greedy path is stable except at exactly the high-uncertainty positions you're planning to branch at. I'd call that good for an instrument, since it surfaces an artefact rather than hiding it under sampling noise. But it needs writing down, because "greedy is reproducible" is the natural assumption and it isn't true where it matters most.

The presentation half, and a tension with what I just wrote
My draft says a logprob is shown as a number and never as a length. Your complaint is that twenty flat rows misrepresent a distribution where three hold the mass. Those pull against each other, and the resolution is a distinction I should have drawn:

The magnitude of one alternative is never drawn — that implies recommendation. The shape of the distribution at a position may be drawn — that describes the model's state. Only the first misleads. So: no bars on individual rows, but do show where the recorded mass runs out, labelled as being over the recorded mass since values sum to less than one.

And the larger idea your framing points at: mark uncertain positions in the reading column itself. You said high-uncertainty positions are the basis for branch exploration — if the text shows you where the model was undecided, that's the instrument, and it's far better than twenty rows available everywhere on demand. Top-1 probability or the top-1/top-2 margin is robust even on a truncated tail.

One consequence you should know, since you said the read set was closed: that needs read 1 to carry, per node, something about the distribution it came from — the parent's top-1 logprob, say — not just the node's own. Cheap in the same descent, but it is a change.

