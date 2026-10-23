# Next

**What gets built next, and in what order.**

This document is living. Items are added as they come up and **deleted** once they close or fall
out of scope — nothing is kept here for the record. What was done is in the history, and a list
that accumulates its own past stops being read.

**It holds the index of the epics, and whatever is not yet one.** An epic is a piece of work too
large to be an item, and it is a file under `docs/next/`. What is below the index is the rest:
items too small to need a file, epics not yet formed enough to be written as one, and the work
written here before epics existed. That last is recast as an epic when it is next designed or
reworked, and not before.

## Epics

**The order is the content.** Each is cheaper before the one after it and dearer after, and that
is the only reason they are numbered. One that has no file yet points at where it stands below.

1. **Map**: what `docs/MAP.md`'s Status names as designed and not built — the layers' colours on
   the strands, and the trail moving to the halo — and a drawer of the map's own for its
   controls, as the column has for the draw's. The scales and bounds are worked through here:
   zoomed in, a strand is coloured on `docs/LAYERS.md`'s third scale, whose domain is what is in
   view, and the cut and the reed's dial are the map's bounds on size and on closeness. The
   overlay panel offers the third scale to the column once the map has shown it reads, and a
   depth limit waits on whether the map leaves the column a use for one.
2. **[Waypoints](next/WAYPOINTS.md)**: positions the reader marks to find again, standing in the
   nav under their roots. Its first cut is in, and the map is where what follows it is drawn
   as well as listed.
3. **Threads**: how a path is decoded and drawn, reconsidered as primitives that the column, a
   one-line view of a thread wherever one is useful and a passage shown over the map all compose,
   so the page of the day is an arrangement of them. Where a thread holds a fork past what is in
   view, it is a distribution there and not one branch picked, which is where Alternation comes
   in. Past the primitives, and the transitions and links between them, the page is a grid each
   place of which holds a list of threads, a thread or a map, sized by the reader rather than a
   margin and a nav fixed by design. That is in tension with what `docs/SURFACE.md` fixes about
   where things stand, which is settled by splitting it or by stating its placements as the
   defaults of a control. A reed is the rows panel at a coarser range and the column at the
   widest, and Threads starts from that. No file yet.
4. **[Alternation](next/ALTERNATION.md)**: a fork's branches taking turns in one place, weighted,
   and what is shown when the reader acts is what they get. It starts in the nav's trails, which
   Waypoints made, and it may change what Arms has to lay out. It is recast as part of Threads
   when that is designed.
5. **Arms**: draws stacked at the row they were bought from, under the settings on the page
   rather than greedy only. Where a stack is read, and where an arm gets the room to run, is
   Threads' question, since the margin it was meant to use is the map's. *Arms*, below. The read
   that shows where a set of paths part is shared with Waypoints, and whichever of the two comes
   first builds it.

**Layers, not ordered against each other.** Each is a colour or mark on the map's strands, and
perhaps on the column, and each is taken up when it is wanted.

- **Acts read back**: what a node was drawn under, and the condition its act was taken in.
  *Acts read back* and *The act's condition*, below. The two open `acts` once.

---

## Arms

**A bought arm is greedy, which makes it the reference and only that.** Drawn under the settings
on the page instead, heat and floor included, a dwell buys several draws from the row rather than
one. When the settings are greedy nothing changes. When they are not, a greedy arm still heads
the stack, being the mode the draws spread around. A hot arm is not on the reference arm, by
`docs/SPINE.md`'s rule, so a measure reading the arm must not take one for it.

**The first cut is a line per draw, default on and with a switch.** What the stack turns out to
need — how many lines, how long, whether a trie earns its place — is decided by reading it. The
trie is the expected layout: draws from one node share prefixes by construction, since
`(parent, token_id, source)` merges, so agreement is a run printed once and divergence is where it
splits, which is the reading `docs/INTERFERENCE.md`'s *Interference* has for a spread. Agreement
that did not share a first token is invisible to it, which is *Whether two greedy rollouts from
distant nodes ever produce the same token sequence*, under Loose ends.

**How long the pointer rests is how many draws are bought.** Whether they should be shorter and
more numerous where the position is flat is open, and the entropy that would decide it is in the
ranking before anything is spent, read after the floor and the heat. `--parallel` above one would
draw several at once and split the cache, and a probe decides whether it pays. A stack makes a
position as wide as the reader's patience, so a bound on how wide is designed with it.

**An arm is forty tokens and one line** (`stub.js`'s `CAP`). Read to about a page, it would be
judged by its shape rather than scrolled — a repeater stops being looked at as fast as it
arrives, and a rollout with somewhere to go is conspicuous for as long as it keeps going. A click
inside an arm taking the prefix up to there, which `docs/SURFACE.md` leaves open, is built with it.

## Acts read back

**What a node was drawn at is recorded and nothing reads it back.** Every `generate` carries
`model` and `params`, and an act's range is `origin` exclusive to `tip` inclusive, so the acts
covering a node are derivable. The recorded logprobs are pre-temperature
(`src/tokenloom/adapters/llamacpp/README.md`), so the act is the only place a draw's heat is
written down. It wants a read from node to acts, the direction `act_tokens` does not go. **Acts
overlap**, since the range is reckoned before merge, so a node reached twice has two answers, and
`min` is the reduction with a reading: this token was reachable at *at least* this much noise.
It is provenance of the sampler and not a measure of the model — `docs/SPINE.md` puts the
realised perturbation on the axis and calls the intended one metadata.

**Drawn, it is a layer**: a strand or a token coloured by the heat it was drawn at. Beside a
deviation the two halve the question, one saying how much noise was permitted at a position and
the other how far the draw then went. On the map it is `docs/MAP.md`'s act-span unit.

## The act's condition

**A recorded logprob is a measurement and the record gives it no error bar.** Two observations of
one row agree bit for bit when the conditions match and disagree by up to a third of a nat when
they do not — `src/tokenloom/adapters/llamacpp/README.md` measures both — and *Rankings* resolves
the disagreement by keeping the first. What is missing is not the second value. It is what either
value is a value *under*: an edge observed once, which is nearly every edge, carries no way to say
how far it could have fallen.

**The realised disagreement and the permitted uncertainty are different quantities, and only the
second attaches to a single observation.** A span between two observations exists only where a node
was reached twice — 167 of the 23,592 ranked nodes in `data/continuations` have more than one
child — so a span is silent on almost every edge, and silent in the direction of asserting
exactness. What the conditions admitted is knowable without resampling anything, which is what
makes it the half that can be put beside every value.

**Most of the condition is already in reach and one piece of it is computed and thrown away.**
`cache_prompt` is required of every request, so it reaches `params` and is in the record already —
but the flag says what was asked for, and a full hit and a partial one move the values by different
amounts. `timings.prompt_n` separates the three states exactly, and the adapter reads it to
cross-check the flag and then drops it. `build_info` and `model_ftype` come from a `/props` call the
adapter already makes, and **token-loom's own commit belongs beside them**: which code wrote a row
is a condition of the act that wrote it, which is why `tree.json`'s `writer`, `repo` and `commit`
are admitted and left unfilled — a tree is written by however many versions of this it outlives, so
naming one of them on the tree names the wrong thing most of the time. Hardware is the one part no
endpoint offers, so it is asserted or it is absent, and `CLAUDE.md`'s rule that the alias names the
vocabulary and not the source is the same problem one level up.

**It is additive.** New columns leave an older reader incomplete rather than wrong, which is
`docs/CORE.md`'s *Conformance and extension*, so a tree written before it simply has no condition
recorded. Making `logprob` a value derived from the condition would change what `logprob` means,
and that would change `marker`.

**It is read with Acts read back**, since both want the read from node to acts, and opening
`acts` twice is the thing to avoid.

**What would sit on an edge, and what would not.** The condition gives every value an *a priori*
bound. A second observation that disagrees under conditions recorded as identical is the residual,
and it is the only thing that can find a variable nobody listed — so an observed span beside a value
is calibration and not a copy of it.

**A value and a spread, not two endpoints** — and what happens when a new observation disagrees is
the question rather than a detail of it. Widening on every disagreement is what makes a span grow
with visit count; the alternative is a threshold, past which an observation is not folded in but set
apart as having been taken elsewhere. **That is only decidable with the condition**, which is what
turns the condition record from context into the thing the estimator runs on. What the threshold is,
and whether a rejection leaves a trace, is open. As columns beside a `logprob` that still means *the
first observation*, it is additive.

**The cost is a derived value that moves.** *Rankings* has it that nothing derived from a ranking
changes retroactively, which a refined measurement breaks by design. The surface is already
indifferent — `reads.py` sorts rows by value and the page addresses a row by its token, so an
order that differs between renderings is current rather than wrong. What is left is that a figure
quoted from a tree is a figure against a state of it, which is *Whether stamping wants an
occasion beyond the command* under Loose ends.

## Loose ends

- **A scan stops short at a reed.** Ctrl and an arrow at the head of a reed with teeth that way
  has said there is no branch further, where the drawing shows one. Found in use, and reproduced
  now that the footer names the place.

- **The column and the map are split where the reader drags**, and a window too narrow for both
  flips them, so the page is one column wide.

- **`docs/SPINE.md`, `docs/INTERFERENCE.md` and `docs/PREMISE.md` are reread against how the
  instrument is used now.** Some of what they say predates shifts in what it is for. Greedy is
  still drawn regularly, for reasons that are specific and can be stated, and stating them is
  part of the reread.

- **Zoom in past the window.** The zoom stops where the thumb is the whole column, and reading
  finer structure up close wants it to go on: past 1.0 the thumb flips to an overlay saying how
  much of the window the fisheye has compacted at the edges, and bands pushed out to their
  least height spawn new ones, building a wall of the densest. It changes what the thumb and the
  lens mean, which the scale and the scan both stand on, so it is a branch of its own.

- **The trail walked back.** `docs/MAP.md` keeps the last twenty paths a reader
  was on, and back is the gesture that takes the last one off: each arrival a history entry, so
  the browser's back, a mouse's and a key all pop it, forward puts it back, and it stops at the
  start of the trail rather than leaving the page. Two things want deciding with it: an entry
  keeps only its path, so where the caret stood on it has to be kept too for back to land where
  the reader was; and the page opens on a root's resting path, which a reload then puts on top of
  the trail, where opening on the top of the trail instead would be the reader picking up where
  they left off.

Not in the ordering; each stands on its own.

- **A scan that lands short draws on.** Scanning across lands at a short branch's end when the
  caret is deeper. Drawing that branch on toward the caret's depth, as an option, in modest
  increments and rate-limited, would make a sweep read every branch at one place; streaming
  would make it continuous and is the larger piece of work.

- **A server that opens trees on request.** It is started against one tree, so the address can
  name a node but never which tree the node is in. Opening on request makes a tree part of the
  address. It also turns one claim per server into one per open tree, and that is a decision
  about the claim and not only about routing.

- **`README.md`'s picture is chosen again.** It predates the map, so it should show the draw's
  controls worked into the reading, and the map beside it.
- **Every title on the page is a browser tooltip, and none of them was designed.** They carry
  real content — what a row's two axes are worth, what a measure read at a segment, which of
  the ways of having no value this one is — and the browser draws all of it the same, late,
  in one place, as a block of plain text that cannot be styled, cannot hold a number set apart
  from its name, and goes away if the reader moves to read it. The page already knows how to
  put something beside a thing without moving it, which is what the arm and the price do. What
  settles the shape is the content: these say different kinds of thing and only one of them
  needs to be dwelt on, so the question is whether that is one treatment or two.
- **A worked sample, which is a different thing from a picture and which nothing produces.**
  What it would show is a path read against an alternative it parted from, which is the thing
  the format is for and the thing prose about the format cannot do. `README.md` now carries the
  picture, so what is left is the text beside it. `scripts/dump.py` projects a tree and decodes
  nothing, so it is not that; whether a sample is generated or hand-cut from a real tree is open,
  and `data/demo` is what either would come from.
- **Whether two greedy rollouts from distant nodes ever produce the same token sequence.** A
  trie merges shared prefixes, so `docs/SPINE.md` has re-convergence as a comparison over token
  sequences and never a merge — and says the tree will not hand that analysis its answer. It
  will hand it the input: hashing each rollout's tokens and grouping is one query. What a
  collision would be is the thing *Nothing prices a sequence the model did not draw* says
  nothing produces — **the same sequence under two contexts, position-aligned by construction
  and priced on both sides**, since each was drawn rather than judged against the other. It does
  not wait on the hover that makes stubs: 5,087 of `data/3`'s 6,063 generations are greedy and
  2,251 of `logozoa`'s 2,641, so the reference arms are already in the record, live rather than
  set aside. Whether any two of them coincide is unmeasured, and a null result costs one query.
- **Two pages on one server change the store under each other.** A revision on each read and
  `If-None-Match` against it is about ten lines: the sole writer counts its writes, and a token
  minted per process covers a restart. What a page can hold with no protocol is the immutable
  half: a node's parent, token and source, a token's bytes, and a ranking's rows. Only liveness,
  and what lies below a node, has to be asked again. The rows are dropped on every change today
  (`ranking.js`).
- **Whether the command line should keep verifying on every write.** Each invocation is its own
  writer, so each pays a whole-tree read — 330 ms at 20k nodes. The server pays it once for the
  life of the process, which is what a long-running session buys. Nothing forces the question
  yet.
- **The `/evaluable` read does not check that the adapter spells the tree's vocabulary.** It
  asks the backend about ids from a tree that may be in another vocabulary and gets a confident
  answer about nonsense. `put_token` is what catches the mismatch on a write, at the first id the
  two disagree on; a read has no such moment. Harmless while a server is started against the tree
  it matches, and wrong the first time one is not.
- **Whether stamping wants an occasion beyond the command.** `docs/CORE.md` specifies the digest
  and leaves the occasion open, and `tokenloom stamp` is the only one built. A hash wants taking
  *when a figure is*, and a timer would stamp between figures rather than at them — which invites
  reading the nearest stamp as the one a figure came from. A hook on server close is the better of
  the two if either is wanted, because closing is a moment a reader can point at. Nothing forces
  it while figures are quoted by hand.
- **Nothing prices a sequence the model did not draw, and one reading wants it.** The three
  producing operations cover authored bytes, a draw, and a ranked edge taken; none of them puts a
  value on a known token sequence under a context. So the same text cannot be laid under two
  contexts and read against itself, which is what `docs/PREMISE.md`'s generalisation test now asks
  for — and it is the one configuration where two paths are position-aligned by construction
  rather than compared by judgement, which is what *Stubs* leaves to the reader because a trie
  never merges them back. The workaround with the acts that exist is a length-1 `generate` per
  position and a `realise` of the token wanted, which costs a call a token **and fails exactly
  where it would say the most**: where the second context makes the sequence unlikely, the token
  falls outside the recorded rows and there is nothing to take. That is `docs/SPINE.md`'s
  censoring finding in a second place, and obligation 7 does not reach it — a source reports what
  its *own draw* was worth, and this token was not drawn. **The backend is not what blocks it.**
  `src/tokenloom/adapters/llamacpp/README.md` now records both halves: nothing reports the
  prompt's own tokens, so a sequence cannot be scored in one pass — but a request at the full
  vocabulary prices every token at a position in a single call, so the token wanted is always
  among the rows and the walk never fails. Asking narrowly and widening only where the token is
  absent needed 14 wide calls in 154. **So what is missing is an act and not a capability**: a
  source that reports what a *named* token was worth, which is obligation 7 generalised from the
  draw it made to a token it was asked about. Whether that is a sixth write, a parameter on
  `generate`, or something that records nothing and only reads, is the open part — and it is a
  `docs/CORE.md` change either way, so it moves as its own piece of work.
  **A second reading wants it, and it is the nearer one.** Until an authored position is ranked
  the mark over it is a placeholder — one flat block of the reader's hue over the part of a
  document that is most theirs, carrying nothing but *a person wrote this*. Ranked, the block
  resolves into where the reader's own writing stopped being distinguishable from the model's,
  which `docs/LAYERS.md` has as the edge of a voice and the one thing the hue cannot supply.
  Three things narrow it. **A seed's positions are wanted branchable on the same footing as any
  others**, the unit being a position in a context and not a token of a particular origin, so the
  generalisation test is one caller and not the reason. **The operation stands on its own whatever
  `create` does with it**, because the trees that exist already hold authored runs nothing ranked
  and an operation that only ran at authoring time would leave them dark for good — `create`
  calling it is then a policy on top rather than the thing itself. And **keeping `create` workable
  with no model running is not a reason to prefer one shape**: what has to hold unattended is that
  existing text renders and reads, an authoring act that prices what it writes is one that wants a
  server, and `README.md`'s line about what runs without one moves when this does.
