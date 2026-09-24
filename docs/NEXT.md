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
at is a composer that starts a root, a column that sets one path as prose, a caret that says
where the reader is pointing and is where every act at a position lands, the rows at that
position on demand, a scroll that asks for more there, and two panels saying what the draw asks
for and what is drawn over it. This section is what comes after that.

### The increments, in order

**1. A depth limit on the measures that look down.** The family is drawn and the rule is chosen
from the same list, so what is left of this is the bound. It is not a parameter on the end of the
increment: three of the five measures can only fall as a path descends, which makes them a
gradient, and `docs/SURFACE.md` has why a gradient is the wrong thing to spend the column on.
What the limit buys is the two things the drop does not — a fixed domain, which none of these
has and which *fixed before relative* needs, and a name for what branching counts, since the
distinct continuations within *d* are what a slate would hold.

**It is server work and it is not one more fold.** Height and the run to a fork cap at *d* and
cost nothing. Size and forks within *d* do not: a single scalar per node cannot answer at two
depths, so the fold carries counts by level and the descent pays O(*n·d*) for it. Whether the
limit rides on the existing `beneath` flag or becomes its own parameter is decided by whether a
page ever wants two depths at once.

Views follow it rather than accompany it, since a view is a rule, an overlay and a limit set
together and two of the three exist. Branching waits on what it counts and vocabulary on whether
a scale with a middle earns its place; both are open questions in `docs/SURFACE.md`, and neither
blocks anything here.

**2. A way back to where an act began, so one draw can be taken again.** A reader who wants a
different continuation at a position should not have to find that position again: what they want
is the boundary of the act they just read, to draw from it under different settings, at a higher
sample resolution, or simply once more. It is the loop `docs/INTERFERENCE.md` is about, and the
page cannot run it yet — the caret follows the tip of what lands, so taking one draw again means
scrolling back and pointing, which is a search where it should be a gesture.

**The record already answers it and nothing reads it back.** An act's range is `origin` exclusive
to `tip` inclusive, so the boundary above any node is derivable — the same read *What a node was
drawn at* wants under Loose ends, and the same reason it is not free: acts overlap, so a node
reached twice has two answers. Here the reduction has a reading of its own, since what a reader
means by *this draw* is the one they just watched land.

What it does not need is a decision about the tree. Arms accumulate at the position and are
consolidated, pruned or divided out later — the five acts already do all three, and nothing about
drawing repeatedly at one node asks the format for anything it does not have.

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

- **How realisation falls with rank, measured before anything spends inference on hover.**
  `docs/SPINE.md` has the question and what it would settle; what makes it urgent rather than
  interesting is that rolling rows out on a hover would drive the top row's share to one and
  leave the curve measuring a pointer. One query over `data/continuations`, and the tree is
  innocent until it is not.
- **The container is two measures wide and does not fit beside the list of roots.** `--col` is
  `min(34em, 44vw)`, so two of them plus the gutters want 88vw where the nav has already taken
  about 17, and the page has been scrolling sideways since the column was built. Nothing showed
  it while the second measure was empty. It does now: at 1457 CSS pixels the rows run to 1557
  and the last hundred are off the edge unless the nav is folded, which is what `#fold` is for
  and is not an answer. What it wants is a measure reckoned against the room there is rather
  than against the window — and that changes the reading column's width, which was chosen by
  eye against a real tree, so it is worth looking at before it is changed.
- **The composer cannot open at the caret, so writing at a position is not offered.** `create`
  takes a node and `compose` takes one, so the act is there; what is missing is somewhere to put
  the box. Staging one replaces the column, which is right for a root and wrong in the middle of
  something being read — *a request appears where its result will*, and a reader who backed out
  of one would have lost their place. It wants an inline composer at the caret, which is the
  same shape a ranking opened there will want, so the two are worth doing together.
- **One colour scale, chosen without comparison.** A place on the scale reaches the column as a
  number between 0 and 1 and the stylesheet makes the colour, so a second scale is a rule and not
  a rewrite — but only one has been tried, against one palette, in two themes. What would settle
  which are worth keeping is reading the same path under several, since a scale is judged by what
  it lets a reader see and not by anything the code can check.
- **A 500 the adapter blames on the predicate, at a position the predicate was right about.**
  A `generate` of 256 tokens at temperature 2.0 or 1.65 against `data/logozoa` fails repeatedly
  with `the server refused a path 'will_evaluate' accepted`, and the same position at
  temperature 0 succeeds. The predicate cannot be what moved, since the path it was asked about
  is the same one at both settings, so the prompt is not what the server is objecting to.
  `src/tokenloom/adapters/llamacpp/README.md` records that error for a prompt ending inside a
  character, which is where it was first met — but **the message says the model produced the
  output**, and a hot draw is exactly what ends a completion on an under-filled multi-byte
  sequence. That is a hypothesis and not a finding. What would settle it is one request at a
  position known to decode, at a length and temperature that reproduce it, read against whether
  the server's own response is what it could not format. If it holds, the adapter is accusing
  the wrong half: the case is a generation that failed and should be recorded as one, the
  predicate is not wrong, and the assertion says it is.
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
