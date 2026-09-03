# Surface — notes

**Not a design.** What has been decided, what building a probe found, and what is still open,
collected in one place so none of it has to be remembered or re-derived. There is no layout here
and no gesture, because neither has been settled and writing either down would give it a standing
it has not earned.

**This document is consumed and deleted.** `docs/SURFACE.md` is what the surface is designed in,
and when it exists everything below has either moved into it or been struck out. Nothing cites
this file, and nothing should — a note that outlives the document it fed is the dangling copy the
project keeps paying for.

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
