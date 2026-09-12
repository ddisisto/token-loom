# The controller

**An instrument for measuring how hard a model resists being moved off the continuation it
prefers.** What it does, what it writes, what it needs that does not exist yet, and what is
deliberately left open.

**The test it is written against: can a reader tell what is settled from what is open, and does
each open question say what would settle it?** Very little here is settled, which makes writing an
open question down as a rule the way this document fails.

Sections are cited by name. What the record is, is `docs/CORE.md`; what a backend must do to
produce it is `docs/ADAPTER.md`; what the reading surface is, is `docs/SURFACE.md`. Nothing here
constrains any of the three, and no fact about them is restated.

---

## What this is

A client that walks a tree, spends model calls where the record runs out, and hands back a set of
paths for a reader to choose among. It writes only the five acts `docs/CORE.md` defines.

**The measurement is resistance, and diversity is the probe.** The question a run answers is how
much has to be spent, under a given policy, to move a model off what it prefers at a position —
and whether it can be moved at all. A run that reaches its diversity target and a run that cannot
are both results, and the second is frequently the more interesting: a prior with one attractor
and a model that will not leave it is the thing the instrument exists to find.

Reading it as a search for good diverse outputs is what would make it a worse tool. A search has an
objective and discards what scores badly against it; this holds everything it touches and leaves
the choosing to a reader. Two constraints keep that true, and the first of them has a price paid
elsewhere:

- **The controller never calls `delete`**, and the reason is not that deleting destroys anything —
  it is a reversible mark and the store keeps what it marks. It is that **the branches that went
  nowhere are the measurement.** Resistance is how much had to be spent to arrive somewhere
  different, which is a quantity computed over the failures, and the map of which signatures
  predict lasting divergence is made of nothing else. A path identical to its sibling but for a
  synonym is not noise in that frame; it is one observation that the position was cosmetic.
  Marking it away by default keeps the finding and discards the evidence for it.
- **Every tip it stops at is resumable.** Stopping is the controller's judgement about where to
  spend; it is not a judgement about what is worth having. A reader takes any tip and goes on from
  it, which is the gesture the whole thing is for.

## The loop

**The frontier is a set of edges, not of paths.** Every ranked edge in the explored region with no
node yet is a candidate, wherever it sits — at the end of a path being extended, or twenty tokens
back on one left an hour ago. The frontier is not in the record and is not a way of looking either;
it is the third category `docs/SURFACE.md` names, state that decides what is seen.

**Extending and branching are one operation.** Taking the best edge at a tip continues a path;
taking one further back starts another. They are not two modes with a rule for switching between
them — they are the same act on edges at different places. What they are not is comparable on one
scale, which is *The ordering*'s problem and not the loop's.

**The frontier grows far faster than it is consumed, and never empties.** One 150-token path
contributes, in the probe, 14 candidate edges above a probability of 0.40, 25 above 0.30, and 118
above 0.10 — and each path those open contributes as many again. So the branching factor is tens,
not two, and a run has an inexhaustible supply of somewhere else to go at every moment of its life.

Three things follow, and they shape everything below. **Nothing terminates structurally**, so every
ending is a policy decision and there is no such thing as a run that finished. **A stall is never a
shortage of candidates** — it is gain dying while good candidates remain plentiful, which is a
stronger signal than running dry but a different one. And **what a run produces outruns what anyone
can read almost immediately**, which makes readability the binding constraint rather than one of
several.

**At any position it meets one of three cases**, and only the third costs a model call:

| the candidate edge | costs |
| --- | --- |
| recorded, with a child node | nothing — walk into it |
| recorded, unrealised | one `realise`, no model call |
| absent — the node's recorded edges are exhausted | a `generate` |

So a run's cost is one call per position where the record runs out, not one per token per path.
It compounds: every generation deepens the rankings at every node it passes, so successive runs
over the same region get cheaper. This falls out of rankings belonging to the node rather than to
the act.

**Two kinds of generation, and they behave differently.** *Deepening* is length-1 with a wide
`record_rows` at a node — it adds edges to the frontier, and under a greedy draw the node it
produces already exists, so the act merges and adds nothing. *Extending* is length-N at a tip and
buys depth. Both are ordinary `generate` acts and the store does not tell them apart.

**Deepening moves a derived read.** An act's range is reckoned before merge, so a deepening call
increments sampling frequency at every node it passes. After a run, *how often was this sampled*
and *how often did anything pass through here* are no longer the same number.

## The policy

**A diversity function takes paths, not tokens.** Its argument is a set of node-id sequences, or
windows over them. Keeping the interface there is what lets a token-level measure and a
text-level one sit behind it, and what lets a finished run be re-scored under a different function
with no further generation.

The family is open and comparison is the point of having one. Vijayakumar et al.'s *Diverse Beam
Search* is where several of the candidates come from — Hamming at matched position, a cumulative
form that backs off once paths have parted, and an embedding distance. Their reported ordering was
against an oracle metric, which is not a criterion this project holds, so it carries no weight
here.

**A diversity score says what a run achieved, and it is not a claim about how different two paths
are.** A token-level measure reads two paths as maximally different when they say the same thing in
other words, and as nearly identical when they diverge on one decisive token. A reader judges
difference; the score says whether the frontier is still moving and when spending has stopped
buying anything.

**It does not decide where the controller goes.** That is *The ordering* below, which runs on
probability alone. Whether the two should be joined is the first entry in *What is not decided
here*, and keeping them apart until then is what makes the comparison between functions cheap —
a finished run can be scored under any of them without generating again.

## The ordering

**Edges are ordered by their own probability, highest first** — not by their distance from the top
token at their node, and not weighted by the probability of the path that reaches them.

**It is the temperature analogue, and the alternatives are not.** Raising temperature is what makes
tokens of low absolute probability reachable, so an ordering on absolute probability is an ordering
on what temperature would be needed to reach a thing — which is the quantity *as much divergence as
possible at as little effective temperature* actually names. A distance from the local top measures
something else: what was given up against the best option at that position, which says nothing
about whether the result is a path the model would produce.

**It prefers bimodality and skips scrambles**, which is the behaviour wanted rather than an
accident of the metric. A flat five-way split is a position the model has no opinion about, and
taking one of five near-equal options rolls a die instead of exploring a decision. A position split
two ways strongly is a decision, and its second option carries high absolute probability. An
ordering on the margin between the top two cannot tell those apart; an ordering on absolute
probability separates them.

**Measured, the difference is not marginal.** Over the 12,683 recorded positions of the
continuation probe, the top five per cent of nodes selected by each criterion: by absolute
probability, a top token of 0.479 and a second of 0.352, the two carrying 83% of the mass between
them; by margin, 0.144 and 0.138; by ratio, 0.198 and 0.191. The last two select positions where
the *winning* token is worth 0.14 — the flattest population in the tree, and the one where the
model has no opinion to explore.

**Not weighting by the path that reaches an edge is a deliberate departure.** Multiplying through
by the prefix probability is proper best-first search, and what that returns is the set of
most-probable paths — which are near-duplicates of each other and of the greedy one. Leaving the
weight off is what lets a path that has already diverged three times compete on equal terms with a
path that has not, and it is the difference between an exploration and a search.

**Its cost is that effective temperature is unbounded.** Nothing stops a run wandering arbitrarily
far from the prior, and a path assembled from many divergences is not comparable to ordinary output
however fluent it reads — presenting one as though it were is the dishonesty available here.
**Accumulated deviation therefore travels with a path**: the summed log-ratio of each divergence
against the token it passed over, derivable from `edges` with nothing new stored. It is what a
run's paths are read stratified by, and it is the axis diversity is plotted against, so a run
traces the whole tradeoff rather than picking a point on it. Whether it should *also* be bounded is
in *What is not decided here*.

**A tip's own probability cannot serve as the admission bar for branching.** One ordering over both
moves makes it one: a branch is taken exactly when it outranks continuing, so the bar is whatever
the model's confidence happens to be wherever the path has got to. Simulated on the probe's spines,
that bar swings between 0.02 and 1.0 and decides everything. On a prior whose spine stays flat,
nothing below 0.233 was ever admitted; on the other three the queue drained to 0.03. Same ordering,
same tree, and the quality of what gets branched settled by a quantity with no relation to the
branches.

**So the correction is separate admission, not a discount.** A multiplier applied to a bar that is
already noise leaves it noise. What the two moves want is a floor on a branch that is the branch's
own business, and an allocation deciding how often each move acts — which is a different shape from
the single ordering above, and the one thing in this document that has to be built before anything
else does anything at all.

**A terminal loop is where the single ordering fails worst.** Inside one the top token averages
0.879 while the second collapses to a median of 0.001, so continuation is maximally attractive and
branching maximally starved at exactly the position with least to offer.

**The known defect that survives the correction is that it still buys phrasing.** Absolute
probability cannot tell two strong options that mean different things from two that say the same
thing — it only rules out the scrambles, which were the worse half of the problem. The probe's
highest-ranked branch candidates are plainly mixed: on the memorised prior an inflection
(`impression`/`impressions`) outranked a genuine fork (`gave`/`danced`), and on the survey passage
the entire top of the frontier was arbitrary digits and list punctuation, the model having fallen
to enumerating dates. The candidate fix puts the diversity function into the *cost* rather than the
objective: divide an edge's probability by the semantic distance between it and the token it
displaces, so a cheap swap to a near-synonym prices higher than a cheap swap to a different word.
That would make divergence and diversity one quantity instead of two terms needing a weight between
them, and it is the strongest reason to want embeddings stored.

**Whether any of this is right is measurable, and the instrument measures it.** A position the
model is unsure of is not necessarily a position where anything downstream changes, and there is no
telling in advance which is which — following it is how you find out. The fraction of branches that
produce lasting divergence is a measurement rather than a parameter, and accumulating it across
runs is the map this is for.

## Detectors and stopping

**A detector computes and records; a policy decides what to do about it.** Writing the response
into the measurement is how an observation worth having on its own becomes unavailable — a path
recognised as looping is a finding about the model when it is marked and a hole in the record when
it is halted.

**What a detector does to a run is gate the frontier**, which is narrower than stopping and is
reversible by a later policy reading the same tree. A tip a detector has fired on leaves contention
for extension while every edge beneath it stays available.

The candidates, none of them settled:

- **Near-certainty.** A tail whose top token has been near-certain for many consecutive
  positions. How many is empirical and larger than it sounds: at near-greedy sampling the probe
  found 42% to 78% of a path's positions already above 0.9, with unbroken runs past a hundred.
- **Periodicity.** The token sequence repeating at some period. A pure function of the ids,
  needing no probabilities and exact. **It is not implied by near-certainty**, which is the reason
  it is listed apart: three of the nine loops the probe produced ran at a *lower* top-token
  probability than the path around them, so a detector built on certainty alone misses them
  entirely. Loops appeared in a quarter of near-greedy paths, at periods from 7 to 26, in four cases
  from the very first generated token, and not once at the highest temperature — and they are the
  case that matters most to the ordering above, for the reason given there.
- **Crossing an end-of-text token.** A node like any other, and what a base model does after the
  end of a document is worth asking. What changes at the crossing is what a diversity function is
  measuring — variation within a document becomes variation across documents — so a frontier
  holding one is no longer comparing what it was comparing before. Whether that is cheap diversity
  or the interesting kind is a property of the prior: a context that has established a strong
  pattern can make the continuation after a crossing *more* determined than what preceded it.
- **Accumulated deviation**, per path, as above.
- **Diversity across the paths the run has opened**, under whichever functions are being compared.
- **Gain per unit spent**, which is the one below.

**The stall detector is the instrument, and the allocation cap is not optional.** A run that ends
because diversity gain per unit spent has died has reported something about the model; a run that
ends on its cap has reported that someone picked a number. The two must be told apart, or the
interesting outcome arrives wearing the uninteresting one's name. But *The loop* is why the cap is
not merely a guard against a pathological case: with a frontier that never empties, a run without
one does not end.

**What the cap bounds is what arrives to be read.** Attention is the scarce resource and the
frontier outruns it quickly, so the bound wants a unit that tracks it — surviving distinct paths at
depth — with tokens generated as a separate runaway rail rather than as the primary bound.

**A run ends for a reason and says which**, per path and for the run. The reason is the result as
much as the paths are.

## What it needs from the record

Stated as what must be answerable, not as an interface. **None of it exists, and landing any of it
is a change to `docs/CORE.md`, made as its own deliberate work or not at all.**

**A run must be identifiable from the acts it produced.** A run is a set of existing acts plus the
policy that drove them, which is a grouping and not a new kind of write: a table and a nullable
column on `acts`, neither of which changes `marker`. A sixth `op` would be a new value in an
existing column, which does. Same information, and the prices are not close.

**The grouping must reach `realise`, not only `generate`.** The map of which uncertainty
signatures predicted lasting divergence is fully derivable from what is already stored — branch
points are `realise` acts, the ranking at the branch node is in `edges` and is never rewritten, and
whether the paths later parted is in the tree. It is derivable only if the realises say which run
they belonged to.

**A run must name the state it started from.** Its behaviour is a function of the tree, and the
tree grows as it goes, so two runs with identical parameters and different results are ordinary.
The highest act id at the start is one integer and makes the difference legible.

**A branch that went nowhere wants its verdict recorded, not acted on.** This is what stands in
for the `delete` the controller does not call: the run says that a branch was taken, extended, and
found to differ from its sibling only cosmetically under a named diversity function. A reader's
view filters on that and sees a clean tree; the evidence stays; the function stays swappable, which
it would not be if the verdict had been frozen as a mark on the nodes. A dead subtree costs nothing
further either way, because what stops the controller spending on it is leaving its edges out of
the frontier, and the frontier is session state.

**Token embeddings want a home.** Storing them is the same move `vocab` already makes — bytes are
derivable without a tokeniser, and embeddings would make a tree analysable without the model. One
row per id, parallel to `vocab`, ignorable by a reader that does not know it. At full width on a
7B model this is on the order of ten kilobytes per token and hundreds of megabytes for a worked
tree, which is worth starting with and optimising later rather than the reverse.

**Whatever produced them must be named.** An embedding table is a measure, and the same discipline
`docs/CORE.md` applies to source names applies here: two embedding sources under one name over the
life of a tree is the failure, and it costs a string now.

## Measurement hygiene

What a run gets quietly wrong, and what it costs to avoid.

**Send `cache_prompt` false, and hold the extend step constant.** Cold-against-cold is
bit-identical on the backend measured; warm against cold is not, by enough to move a value where it
sits against a neighbour. The frontier is ordered on exactly those values, and two edges a hundred
tokens apart are ranked against each other, so a perturbation that would be invisible at one node
decides which of two gets taken. Worse, a step size that varies with the policy puts chunk
boundaries at positions the policy chose, so the artefact correlates with the decision instead of
averaging out. Cache off is slower, which is not the binding constraint; it is held as something to
revisit when performance is wanted.

**The ordering's input is conditioned on exploration order and cannot be corrected.** The first
value written for a token is the one kept, so the ranking at a node is whatever the first act to
reach it measured, in whatever state that act was in. Later measurements append below and do not
replace. Nothing is corrupted — this is the format's answer to backend non-determinism working as
designed — but the quantity the frontier sorts on carries a systematic, order-dependent floor.

**Name whether end-of-text stops a draw.** It is a backend parameter, and
`docs/ADAPTER.md` requires a caller to name anything something else would otherwise decide. Left
unnamed it decides the controller's step size for it: an act that stops early returns fewer tokens
than it asked for, which perturbs any accounting of gain per token spent.

**Short extend steps are what make a run interruptible.** The only way to stop a writer is to kill
it, which records the in-flight act as `aborted` and loses its tokens. Acts short enough to be
stopped between are interruptible for free, and the loop wants them short anyway.

## Nothing written is only here

**The controller writes only the five acts**, so `docs/CORE.md`'s closed set is not touched and
every write it makes has a verb. The run is a grouping over acts rather than an act. What is new
is the relationship: one gesture, many acts, and the record holding the acts. `docs/ADAPTER.md`
has the precedent in a chunked generation — the block is a client's construct and not a unit of
the record — and the same answer applies, with the difference that a run's policy is the thing
worth keeping and a block's presentation is not.

**A controller is a client, so it needs a verb of its own** for the same reason the rule exists:
a capability reachable only from a surface has put itself where the record cannot follow, even when
every individual write it makes has a name.

**`actor` is a user in every case, and that needs review.** `docs/CORE.md` grounds the rule in a
claim — that authoring, asking a model to continue and taking a ranked edge are all things a reader
does — which a controller falsifies. The sentence moves whether or not the column does. Whether
`actor` should admit a third kind is a `marker` bump and is held: a client is not a reason to move
the core, and the question is one only use can answer.

## What is not decided here

**Questions prose cannot close.** Each says what would settle it.

- **Which diversity functions, and whether one dominates.** The family is the point and the
  interface is built to swap them. What settles it is scoring one recorded exploration under
  several and reading the results — which costs no generation, and is why the interface takes
  paths.
- **Whether diversity feeds the ordering or only the reporting.** As written the ordering is
  probability alone and diversity is measured over what comes back; the candidate in *The ordering*
  puts a semantic term into the cost, which is the other arrangement. What settles it is running
  the same prior both ways and reading whether the branches bought are better ones, not whether the
  score is higher.
- **Where a branch's admission bar comes from, once it is no longer the tip.** *The ordering* says
  what it cannot be and not what it is. A fixed floor, a floor that moves with the run's own
  spending, or a quota that simply alternates the two moves are all available and none has been
  tried. What settles it is running one prior under each and reading what came back, since the
  probe already shows the failure is legible by eye.
- **Whether a branch found redundant should be marked rather than only recorded.** Read-time
  filtering keeps the evidence and keeps the diversity function swappable, which is why it is the
  answer above. Two things would overturn it: filtering proving too expensive to do on every read
  at the sizes a run produces, or trees turning out to be unreadable in practice without a
  persistent mark. Both are cheap to discover, and `delete` is cheap to add afterwards and awkward
  to take back once a run has used it.
- **Whether accumulated deviation is bounded as well as recorded.** A run that wanders far enough
  produces paths that are fluent and unrepresentative, and a bound is the only thing that stops
  them being produced at all. What settles it is reading paths from the far end of the axis: if
  they are uniformly noise the bound is worth its cost, and if any of them are interesting it is
  not.
- **Whether the run belongs in the record.** A table costs no `marker` bump and makes a run
  resumable and its frontier recoverable after a restart; session state costs nothing and loses
  both. What settles it is whether the repeat-from-a-chosen-tip gesture is wanted across sessions.
- **Which embeddings.** The model's own input rows, its unembedding rows, or a separate small model
  embedding text. The last decouples the measure from the generating model, which is what would
  make runs comparable across models, and it is a second vocabulary and a new dependency. What
  settles it is probing one against another on a tree that already exists; everything that does not
  depend on the answer is buildable first — with the caveat that the question above changes what is
  at stake, since a semantic term in the cost makes embeddings a dependency of the loop rather than
  a convenience for reading it afterwards.
- **How a run is read.** `docs/SURFACE.md`'s band answers *what else could go here* in one line per
  alternative, and a run asks *how do these part over fifty tokens*, which is not that question.
  Whether it is a mode of the band or a view of its own is not worth deciding before a run exists
  to look at. What is not optional either way is that a path's accumulated deviation is legible
  wherever the path is: text that reads as ordinary output and was reached at an effective
  temperature far above anything a sampler would use is the one thing here that can mislead by
  omission.
- **Whether `actor` admits a controller.** Above.

---

## Status

**Nothing here is built. The continuation probe has been run and read, and what it settled is
above; what it left open is here.**

- **The cost half of the premise holds; the diversity half is untested.** Opening seven branch
  points off a near-greedy spine cost 1.8 to 3.2 nats of deviation, against 122 to 204 for a single
  path sampled at the highest temperature — of which the probe drew eight per group. Whether paths
  branched that cheaply are as *different* as paths bought at that price cannot be read from a tree
  with no continuations below the branch points, which is to say it needs the controller. Until
  then the allocation is known to be cheaper and not known to be better.
- **A branch's admission bar is the first thing to build and the first thing to measure.** Nothing
  else in the loop does anything until it exists, and simulating the alternative on the probe was
  enough to rule out the obvious form, so it cannot be arrived at by tuning around a default.
- **What a run hands back has no form yet.** The probe produced paths that a person read; a run
  produces paths plus the reasons each stopped plus where each sits on the deviation axis, and
  none of that has been put in front of anyone. *The loop* is why this is urgent rather than
  cosmetic.
- **`record_rows` of 20 was ample, which was not the expectation.** The ceiling truncated 40% of
  positions, and at those the twentieth row carried a median probability of 0.0054 — so everything
  it cut sits far below anything the ordering reaches. What a narrow tree would cost a *different*
  policy is untested, and a ranking extends without being rewritten, so the choice is still one
  that a later widening pays for a generation at a time.
