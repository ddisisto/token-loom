# Next

**What gets built next, and why in that order.**

This document is living. Items are added as they come up and **deleted** once they close or fall
out of scope — nothing is kept here for the record. What was done is in the history, and a list
that accumulates its own past stops being read.

The ordering is the content. Each item below is cheaper before the one after it and more
expensive after, which is the only reason they are numbered; anything that does not stand in
that relation to the others is a bullet at the end rather than a number.

---

## 1. The page

**Built in the order a reader meets it, which is the order it is written in.** A tree starts
empty, so the first thing the page needs is a way to make one, and each rendering after that is
built once there is a way to produce what it renders from the page itself.

**A page grown against an empty tree risks a column shaped by the degenerate case.**
`data/continuations` is twelve thousand nodes and costs nothing to point at, so each increment is
read against a tree the page could not yet have made.

**No build step.** The probe needed none for the hardest thing in the document.

**What exists is `docs/SURFACE.md`'s Status and is not restated here.** What the page has arrived
at is a composer that both starts a root and writes at a position, a column that sets one path as
prose, a scroll at the end that asks for more of it, a panel that says what the draw asks for and
another that says what is drawn over it. This section is what comes after that.

### The increments, in order

**1. Measures that look down.** `docs/SURFACE.md` has the design. What makes this first is that it
is nearly free where it is not free outright. `Subtree` already folds height over the descent
`path` makes; size, forks and the run to the next fork fold over the same pass and cost nothing
more. What is not free is the descent's anchor: a measure drawn along a whole path wants the tree
from the root, and `path` anchors below the node it was asked about. Where the reader is reading a
root that is the same descent; where they are not it is a larger one, which is a reason to ask for
it and not a reason to defer it.

**The rule list stops being written beside the measures and starts being generated from them.**
`longest` is an argmax of a subtree scalar over siblings, so every downward measure is a rule, and
the open question about which continuation rule can finally be answered by reading one tree under
several — which is what that question says would settle it.

The family reaches the panel and the rule is chosen beside it, from the same list. **What is
left is the depth limit, and it turned out to be the whole of the increment rather than a
parameter on the end of it.** Drawn unbounded, three of the four measures can only fall as a path
descends — which `docs/SURFACE.md` now carries as the reason the limit is not a convenience —
so the wash is a gradient from the root and only the run to the next fork reads as a measure.
Bounding the fold to a depth is server work: height and the run to a fork cap, while size and
forks within *d* want the counts by level that a single scalar per node cannot carry.

Views follow it rather than accompany it, since a view is a rule, an overlay and a limit set
together and two of the three exist. Branching waits on what it counts and vocabulary on whether
a scale with a middle earns its place; both are open questions in `docs/SURFACE.md`, and neither
blocks anything here.

**2. A ranking on demand, and `realise`.** Selecting a token asks what else was live at that
position, and the rows with no child are what a `realise` takes. This is where an overlay points:
a position drawn as interesting is a position a reader then opens. It is also the cheapest thing
that makes a fork, which is why it comes before the band rather than after it.

**3. The band, when its need is as clear as theirs.** It displays forks, so until something makes
them it has nothing to display — that was the argument for putting it last and it still holds.
What has changed is that its need is the least established of these: a ranking on demand already
answers *what else was here* at a position, and whether a reader also wants every continuation
below a fork laid out at once is a question use has not asked yet. So it waits on that and not on
its cost, which is known — `/branches` is bounded by a line's width and by nothing vertical, so
on the synthetic twenty-thousand-node tree a band opened at a root reads in 110 ms and projects
to about a megabyte of JSON. A band opens at a fork rather than at a root, so that is a ceiling
and not a typical call, and whether it wants a bound in the other direction is an open question
in `docs/SURFACE.md` that only a page settles.

**The band lifts from the probe rather than growing out of it.** `probe/index.html` holds the
band's measured layout, which is the part of `docs/SURFACE.md` nothing else has demonstrated —
about sixty lines of it, since the tree-walking around it is what `/path` and `/branches` answer
now. It also holds its own CSS, its own reads against a static projection, and controls that are
not carried forward, all of which would have to come apart anyway. One adaptation is not
cosmetic: the probe placed a preview line by segment index, and `parts_at` is characters into the
line above, so the column carries a running offset onto each segment.

### What holds across them

**The reading view renders no act but the one in flight.** An act originates at a node or an edge
regardless of what produced either, and what it leaves behind is nodes and paths — which are what
is read. A generation still running is the exception, because it is the one act whose absence from
the record is something the reader is waiting on. `/acts` answers the whole list unfiltered and
should keep doing so: the rest of it belongs behind a log view, hidden by default, which is worth
having while the page is being built and is not part of reading.

**The continuation rule is a parameter of the read, and the page must not put it back.**
`docs/SURFACE.md` names a family of them and settles none, because they are compared by use.
`longest` is the only member built, a second is a function and an entry in `RULES`, and what the
page owes the question is a way to swap them over one tree.

**Nothing can change the store under the page, and what to do with that is the page's to
settle.** The server holds the claim, so it is the only writer there is — but that is true of
the server and not of a page, since two pages on one server change it under each other. A
revision on each read and `If-None-Match` against it is about ten lines and needs nothing from
the core: the sole writer can count its own writes in memory, and a token minted per process
covers a restart. It buys nothing on a first read, which is the one that is large.

**What a page can cache with no protocol at all is the immutable half, and it is most of what a
page pulls.** A node's parent, token and source never change and only `deleted` does; a token's
bytes never change, because `put_token` refuses a vocabulary that disagrees at an id already
held; and a ranking only grows, because `_extend_ranking` appends and never rewrites. Spellings
and rankings are therefore cacheable for the life of the page, and liveness is the only thing
that has to be asked again. **A measure that looks down joins liveness rather than the spellings.**
What lies below a node changes every time the reader generates, so the structural family is the
first thing the page draws that cannot be held across an act — which is a reason to keep the
descent it rides on cheap, and not a reason to defer it.

## Loose ends

Not in the ordering; each stands on its own.

- **One colour scale, chosen without comparison.** A place on the scale reaches the column as a
  number between 0 and 1 and the stylesheet makes the colour, so a second scale is a rule and not
  a rewrite — but only one has been tried, against one palette, in two themes. What would settle
  which are worth keeping is reading the same path under several, since a scale is judged by what
  it lets a reader see and not by anything the code can check.
- **Whether the command line should keep verifying on every write.** Each invocation is its own
  writer, so each pays a whole-tree read — 330 ms at 20k nodes. The server pays it once for the
  life of the process, which is what a long-running session buys. Nothing forces the question
  yet.
- **The `/evaluable` read does not check that the adapter spells the tree's vocabulary.** It
  asks the backend about ids from a tree that may be in another vocabulary and gets a confident
  answer about nonsense. `put_token` is what catches the mismatch on a write, at the first id the
  two disagree on; a read has no such moment. Harmless while a server is started against the tree
  it matches, and wrong the first time one is not.
- **What a node was drawn at is recorded and nothing reads it back.** Every `generate` carries
  `model` and `params`, and an act's range is `origin` exclusive to `tip` inclusive, so the acts
  covering a node are derivable and the sampler settings arrive with them. Nothing in the
  numbers could stand in for that — `src/tokenloom/adapters/llamacpp/README.md` measures the
  recorded logprobs as pre-temperature, so the act is the only place a draw's heat is written
  down at all. It needs a read from node to acts, which is the direction `act_tokens` does not
  go. **Acts overlap**, since the range is reckoned before merge, so a node reached twice has two
  answers and whatever draws it must reduce them — and `min` is the reduction with a reading. It
  is the floor: this token was reachable at *at least* this much noise, every other draw that
  produced it having used strictly more.
  It is **provenance and not measure** — `docs/SPINE.md` puts the realised perturbation on the
  axis and calls the intended one metadata — and what it is provenance *of* is the sampler, not
  the model. The learned part has no say in it: temperature scales a distribution the model has
  already produced, which is the same fact the adapter's notes record as the logprobs being
  pre-temperature. So beside a flag the two halve the question — one says how much noise was
  permitted at a position, the other how far the draw then went.

## 2. The next marker

**A marker bump is what makes an older reader wrong rather than merely incomplete, so it is paid
once and carries everything that wants it.** A new table or column does not change `marker`;
changing what an existing one means does. That makes this a bundle and not a task — items land
here as they are found, and it is opened when something in it is worth the bump on its own.

**It sits last because everything in it buys clarity and no capability.** Nothing becomes
reachable that is not reachable now, and the cost of waiting is accretion rather than a cliff: a
tree built meanwhile is not wrong, it spells a column differently. So new work is scoped ahead of
this rather than behind it, and being pushed down is the expected thing to happen to it.

### `rank` → `ordinal`, on `edges` and on `acts`

**The column holds arrival order and is named for the model's ranking.** *Rankings* spends a
paragraph un-teaching it — *rank means the k-th alternative recorded here, not the model's k-th
choice* — and the two readings coincide right up until a second generation extends a node, which
is the merge this format exists for. A name that is right until the central case is the wrong
name, and it is close enough to the term every inference setting uses that a reader will not
notice they have the other one.

**The column stays; only the name moves.** `UNIQUE (node, source, token_id)` already identifies a
row, so nothing needs it for that. It earns its place twice over anyway: `realise` addresses an
edge by a small readable integer rather than by an opaque id, and contiguity from `0` is what
keeps accumulation order recoverable.

**`ordinal`, not `index`.** SQLite parses `index` as a keyword and refuses it as a bare column
name, and *On disk* is DDL a reader implements from — a column needing quotes everywhere is a
cost carried for the life of the format. `ordinal` means arrival position and nothing else.

**What it reaches**: the `edges` and `acts` DDL, `INV-RANK-DENSE`, `INV-RANK-ANCHORED` and
`INV-RANK-UNIQUE`, the reads and the checker that name them, the `--rank` argument and the
surface's use of it, and `docs/CORE.md` throughout. Every existing tree is rebuilt or migrated;
`data/` is disposable, so that is free now and less free the longer the bundle stays shut.
