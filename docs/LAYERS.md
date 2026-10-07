# Layers

> **Lifted whole out of `docs/SURFACE.md` and not yet reviewed, so parts of it may be stale.**
> Read a claim here against the page before building on it. Section names it cites without a
> document are `docs/SURFACE.md`'s.

**What is drawn over the reading column**: overlays, the scales and domains they are read on, the
family of measures that look down the tree, and the mark that says who put a token there.

## Overlays

`docs/SPINE.md` names the objects: a **spine** is a sampled path read as the record of the
decisions that made it, a **deviation** prices a position where the draw went somewhere the model would
not have, and a **stub** is a short greedy rollout from what the draw passed over. An **overlay**
is this document's word, and it is the machinery rather than a measure — a per-position quantity
drawn along the path, whatever computed it. Deviation is one, and so is anything read off a ranking
without regard to what the draw did.

**An overlay is asked for, and the column draws none until one is.** This is what keeps *The
floor case is a text reader* and *Between forks, nothing is drawn* — they describe the column a
reader has not asked anything of, which is still the thing that opens. One overlay at a time.

**The case that looks like it wants two does not.** A reader under drive wants what the model
thought of a position and what the draw did there, which reads as two measures at once. The
second is not one: what the draw did decomposes into *that it diverged*, which the mark carries
and which needs no scale, and *how far past the second row it went*, which is a property of the
sampler's reach and not of what the divergence cost. So one measure and one mark answer it, and
the rule stands on that rather than on frugality.

**An overlay is three separable things**: a **measure**, which is a per-position quantity that
may be absent; a **scale**, which maps it to colour; and a **unit**, which is what a value is
addressed to. Keeping them apart is what lets a quantity the record computes and a quantity some
later analysis computes arrive through the same machinery and be read the same way.

**Deviation is the first overlay and it costs nothing the record does not already hold.** It is
the log-ratio between the top-ranked token and the one the draw took — what the draw paid to go
where it went, and zero where it went nowhere. Both rows are guaranteed: the highest recorded row is
the model's top row, since `docs/ADAPTER.md` has the recorded alternatives reach down from it, and
the drawn token has a row of its own by obligation 7. **So a deviation's value is honest at any
depth**, which no other overlay's is.

**Its value is depth-free and what a reader may conclude from it is not.** The recording rule
spends rows where the ranking is flat, so depth falls as the top-to-second gap rises: a large
deviation at a two-row position may be the only divergence the record offered there, and the same
number at a fifty-row position was chosen past forty-eight alternatives. `docs/SPINE.md` measures
what that does to a reading taken without it — a whole population at 100% on a statistic that
could not have come out otherwise. **So a deviation drawn beside a ranking needs nothing, and a
deviation read across positions wants the depth beside it**, which is the one place the robust
and depth-bound division does not settle what a reader should be shown.

**Overlays divide into the robust and the depth-bound, and an overlay says which it is.** The
robust ones read the top of a ranking and the row the draw took — deviation, top-1 probability,
the top-1 to top-2 gap. The depth-bound ones read a tail: entropy, the mass in the head, how many
options were live. These are not decoration; the distinction between *a decision*, split strongly
between few options, and *a scramble*, where the model had no opinion, is the one `docs/SPINE.md`
turns on, and only a tail tells them apart.

**That is not the division `docs/SPINE.md` makes, and the two cross.** That one sorts measures by
what the draw did — deviation is draw-relative and says nothing wherever the draw did not go, while
anything read off a ranking alone is indifferent to it. This one sorts them by how much of a
ranking they need. The top-1 to top-2 gap is the witness that these are different cuts, being
draw-independent by the first and robust by this, and an overlay declares both: one says where it
has no value at all, and the other says what its values may be compared with.

**A depth-bound overlay carries the depth it was computed over.** `docs/CORE.md` derives a node's
recorded depth and states why it is not any act's `record_rows`: rankings accumulate. So a path
can hold nodes recorded to different depths — a reader moving the recording bounds mid-session is
enough to do it — and an overlay that did not say so would be colouring incomparable numbers side
by side and looking uniform while it did. **Depth is inflated where it is wanted**, position by
position, by the deepening write Rankings describes.

**A position with no value is not a position with a low one**, and what goes missing is the row
the draw took rather than the ranking. So whether that costs a value is a question about the
measure: a draw-relative one is silent, and a draw-independent one reads the ranking and is not.

An **authored** token stands in a ranking it has no row in, which is the ordinary case and not a
fault — a reader writes at a position a model ranked. It is off the scale rather than at its end.
**A drawn token has a row**, however few alternatives stand beside it: `docs/ADAPTER.md`'s
obligation 7 has the source report what its own draw was worth, so a draw that landed past the
recording bounds is a row like any other and not a value the surface has to reason around. `source`
tells the two cases apart and they do not get one mark.

**Where a backend could not report it, the value is simply absent**, and the surface says so rather
than bounding it. A one-sided reading is available — the unrecorded tokens sit at or below the
lowest row — but it stands on the recorded rows being a prefix of the model's, which nothing in the
record can check and which a set of rows accumulated across acts is not. So the position reads as
having no value, which is what it has.

**The mark under a segment carries three things, and they are three axes rather than one list of
states.** Its **existence** says the token was put here by something other than the model's own
preference. Its **colour** says who took it: the sampler, or a reader taking a row the model
offered. Its **style** says how far the value can be trusted — plain where it is a
reading, and marked where it is not.

**The ways a value can fail to be readable are one mark and not four.** A hole, a segment
holding more nodes than values, a position two sources ranked, and a ranking that is not this
node's source are four different facts, and the record tells them apart — but none has been met
on a worked path, so choosing four appearances is choosing between things nobody has seen beside
each other. One mark meaning **the value here needs handling** is what the tree can currently
support, and each splits off when it is met and there is something to compare. **Nothing is lost
by collapsing them**: the states stay distinct in the read and the segment's title still names
which, so the split is a rule and never a rewrite.

**The two halves of existence are not symmetric, and that follows from the allocation.** A
`realise` is marked whatever it cost, because `docs/SPINE.md` allocates the displacement to the
operator wherever one stands and an operator who takes the top row has displaced nothing and still
acted — the bit does not follow from the scalar. A draw is marked only where it diverged, because
a sampler that took the argmax displaced nothing *and* did nothing, and marking those would draw a
line under the model's own preference, which is most of a cold path. So the mark says *something
other than the model put this here*, which is one sentence over both halves and reads off the
record either way.

**Colour carries the degree as well as the taker, on two scales that do not overlap.** Each
taker owns a hue — warm for the reader, cool for the sampler — and the share locates the
position on its own scale, so the bit picks the scale and the scalar picks the place on it. That
is the allocation drawn rather than described, and it costs no channel: the mark was already
spending colour on the taker and the degree rides the same ink.

**The quantity is the share and not the deviation.** A deviation is unbounded and would want a
domain chosen, which is the fixed-against-relative argument the overlay already has and does not
want a second copy of. The share is bounded by construction, it is the quantity being allocated,
and `docs/SPINE.md` has it as `min_p`'s coordinate exactly — so the axis arrives calibrated and
an operator who has tuned that dial already knows what a third of the way up means.

**Both scales run from legible to strong and never from nothing.** A `realise` of the top row
sits at zero and is still an act; a ramp reaching transparent would erase the mark at precisely
the position that shows the bit does not follow from the scalar. So the floor is where a fixed
colour would have been and the ramp is what rises above it. The sampler's floor is the same
height for the same reason at one remove: its near-zero divergences are the common case, and a
scale that fades them out would say the sampler had done nothing where it had done a little.

**Whether weight is a third channel is open, and it may be the operator's to set.** Hue and
ramp put two things in one ink, which is legible while the ramp is the only thing modulating it
— the line's thickness is untouched and could carry the degree instead, or carry thresholds a
reader places themselves, so that *what counts as far* is a dial rather than a constant. What
recommends the ramp first is that it reuses the machinery the wash already has and needs nothing
new; what recommends weight is that it keeps hue at full contrast at every value. *What is not
decided here* has what would settle it.

**Only the sampler's half needs a ranking.** Whether a `realise` stands at a node is on the wire
whatever was asked for, so the reader's half is drawn against an empty column; the draw's half
needs the top row, which is the ranking read an upward measure also rides on. They are one mark
and are drawn together or not at all, so what a read asks for is the union of what is on rather
than what the overlay panel alone chose.

**An authored token is the reader's, and the record says so in a column.** `docs/CORE.md` has a
node carrying whoever produced it and a `create` naming the source its nodes take, which defaults
to the actor — so a node whose source is of kind `user` is one the reader wrote, and the hue
follows that rather than any act's range. It is not a proxy for provenance; it is the provenance
field. Text a model produced elsewhere is recorded as that model's and draws as the model's, which
is the right answer to *whose voice is this* and the one thing the mark could otherwise lie about.

**So the hue is the reader's where the source is a user or a `realise` stands, and the model's
otherwise.** Two states, from two facts the record keeps, and neither wants a walk over a range.
What the ranking says is a separate axis and stays one: an edge tells what the model thought of a
token, never who put it there, and the two are only correlated while authored positions go
unranked.

**An authored token with no ranking above it draws at the top of the reader's scale, and that is
a placeholder rather than a reading.** The model offered nothing and the reader supplied all of
it, so the top is where it belongs while nothing is known — but it carries no information, and a
seed read this way is one flat block of colour saying only that a person wrote it. The style axis
marks it as a value that needs handling, which is what keeps the convention from reading as a
measurement.

**Ranking those positions is what gives the voice an edge.** Once a share can be read there, the
block resolves: authored text the model would have produced sits low on the warm scale and
authored text that surprised it sits high, so where a reader's own writing stops being
distinguishable from the model's becomes something the column shows rather than something the
reader assumes. The hue cannot do this and was never going to — it is a fact about acts, and the
edge of a voice is a fact about the model. `docs/NEXT.md` has the act that would supply it.

**Who took a token is not a measure, and that is why it is not an overlay.** It has no domain, no
second reading, and nothing to compare across positions — it is a fact with two values. So it
is not in the list a reader chooses from, and it is not subject to *An overlay is asked for*: a
reader reading prose wants to know which words are theirs whether or not they have asked for a
colour over them.

**Nothing read off a ranking can supply it, which is why the record must.** `docs/SPINE.md`
measures the two populations against every split of a deviation the record admits and finds them
in the same place; a large deviation is a reader overriding a confident model and a sampler
wandering in a flat one, and the ranking cannot say which. The acts can, exactly and for one
query, because a `realise` names the node it produced. **So the mark is what makes a deviation
overlay readable under drive at all**, and not an ornament on it.

**A deviation overlay and this mark say the same thing at temperature zero and different things
off it.** Cold, every drawn token is the argmax, so a positive deviation is the reader's by
construction and the mark adds nothing. Under drive the deviation is mostly the sampler's and the
mark is the only thing separating the two. It earns its place at one end of the dial and is
redundant at the other, which is a property to know rather than a reason to gate it.

**Two channels, read together, are four readings.** The column's wash carries a measure and the
mark carries whether anything happened, so a reader scanning has:

| | no mark | marked |
| --- | --- | --- |
| **the model was torn** | a pivot nothing took | the model cared and something moved |
| **the model was settled** | nothing was at stake | a draw wandering where nothing was |

The top right is what `docs/SPINE.md` gates a stub on, arrived at from the reading side rather
than the spending one. The top left is what a cold path is made of and has no other name.

**What this does not carry is how far past the second row the taker went.** That is a real
quantity and the column has no channel left for it: the wash holds a measure, the mark holds who,
and weight is claimed, for telling the newest stretch from what was continued past — the most
recent act's origin marks that boundary, read off the acts and with no reader state. Whether the four readings above suffice is in What is not decided here.

**A node two sources ranked has no single value, and the surface refuses rather than choosing
one.** Picking a source silently would make an overlay mean different things at different
positions with nothing saying so. Whether the interesting quantity there is their *disagreement*
is in What is not decided here.

**A value is addressed to a span of the path.** The record holds quantities per node; the column's
display and addressable unit is the segment; and analysis over decoded text will want words and
character ranges, which is the vocabulary the surface and a reader actually share. One node to one
segment is the common case and not the definition, so the column takes spans and later data needs
no second mechanism.

**Where a segment holds more than one node, it is marked rather than coloured.** A character
spelled across several tokens has as many values as it has nodes and no single one, and the path
read already says where this is: a segment with more than one node that nonetheless decodes. The
breakdown is shown on demand. *Nothing is addressed inside a segment* is why this cannot be
resolved by colouring the part of it that a value belongs to.

**A scale is fixed before it is relative.** A fixed domain makes a colour mean the same thing in
every path and every tree; a path-relative one makes a single path maximally legible and
comparable to nothing. The first is the default and the others are further scales, not another
system.

**There are three and each answers a different question.** Fixed says *how much, absolutely*.
Path-relative says *how much, for this path*. And a third says *how much, compared to what is in
front of me* — its domain taken from the segments currently in view. They are not ranked against
each other past the default: a reader looking for a position that stands out among its neighbours
is asking the third, and one asking whether a whole passage is open is asking the first, and
neither answer substitutes.

**The third is wanted because a fixed scale spends its resolution where a reader has already
stopped looking.** `docs/SPINE.md` measures the top-to-second gap over 77,565 ranked positions of
a worked tree: a median of 5.73 nats, a quartile above 8.37, and 55% above the 5 nats the fixed
domain ends at. So more than half a greedy path pins to one end of the scale, correctly and
uselessly, while a passage that sits entirely between two and four nats draws as an even wash
with its own structure inside it.

**A viewport scale moves when the reader scrolls, and that is the reading and not a fault.** The
neighbourhood it is relative to is what is in view, so a token's colour is a fact about where the
reader is as much as about the record. What follows is that it wants to be visibly a mode and not
a third entry in a list, since a reader who took it for a fixed one would read a scroll as a
change in the text.

**Zoom is what keeps it from chasing itself.** A position drawn brightly is approached, and as it
centres the neighbourhood becomes the region around it and the brightness can fall. Widening the
view is the answer and it needs no machinery: the browser's own zoom changes how many segments
are in the viewport, so the axis from *this sentence* to *this passage* to *this document* is
already a gesture the reader has. Whether that is sufficient, or whether the domain wants
hysteresis or a window wider than the view, is in What is not decided here.

**The visible set is the page's to determine and the scale's to be handed.** Which segments are
in view is geometry and the domain over their values is arithmetic, and they are kept apart here
for the reason they are kept apart everywhere else on this page: a scale that went and read the
viewport for itself would be the one part of the overlay machinery that could not be checked
without a browser.

**Linear against log is a choice on the same measure**, since a logprob and a probability are one
number read two ways, and it is the axis a scale is not: every scale above takes either reading.

**An overlay and a ranking are one quantity read along different axes.** A row's logprob against
the top row is exactly the deviation a draw taking that row would pay. So an overlay draws one row's
value along the text and a ranking draws every row's value at one position, and what follows is
that the measure a reader has chosen is the number the rows should show — not a second scale to
reconcile with it.

**Where a measure looks is the next thing it declares, and it cuts deeper than either division
above.** Everything so far reads the ranking a node stood in, which is to look *up*. A measure can
instead read the tree below a node — how far it reaches, how much of it there is, how often it
parts, how far it runs before it parts at all. Three things follow at once, which is why this is
a declaration and not a remark. One that looks up rides on the path read; one that looks down
wants a descent. One that looks up never changes again, while one that looks down changes every
time the reader generates. And **only a measure that looks down can be a continuation rule**,
because a rule chooses among children by what lies beneath them.

**That last is not an analogy.** `longest` takes the child of greatest height, which is a measure
of the subtree below each candidate used as an argmax over siblings. So every downward measure
yields a rule, mechanically and with no second vocabulary. **Neither family contains the other**:
a rule may read insertion order or what the reader last took, and neither is a quantity worth
drawing along a path, since every node on one is the node that was taken. What the two share is
the part where a reader would otherwise set two things to get one behaviour, and that part is
large enough that the rules are generated from the measures rather than listed beside them.

**The rules divide again, into those that aggregate and those that do not.** Size and the count
of forks below sum over everything a subtree holds, so they are estimators: draw a position often
enough and the arm with the most below it is the arm most often taken, which is the model's modal
token — the one a greedy draw would have picked. Height and the run to a fork are extremal, set
by one long descent whoever made it, so no amount of sampling moves them toward anything. That is
the sharpest thing yet said about which continuation rule is right, and it is not an argument
from use: a rule that aggregates tells a reader about the model, and one that does not tells them
about their own exploration. What muddies it is that a subtree's size is draw counts multiplied
by how far each draw was carried, and how far to carry one is the reader's decision — so the
estimate holds where they are not steering, and `docs/SPINE.md` has what the disagreement is
worth where they are.

**A rule and an overlay share the scalar and not the liveness.** *Hidden* has the rule take the
live path first and admit what is set aside only below a live leaf, so it is never offered a live
node and a hidden one at one parent. A measure drawn on the page has no such need and follows the
toggle, since a reader asking how much is below here is asking it of the tree they are reading.
**So the two disagree whenever what is hidden is shown, and the disagreement is the point**: the
darkest child is not the one the path takes, which is how a reader sees what they pruned and how
much of the tree it was.

**A measure that looks down is about the reader and not about the model.** A deviation is a fact
about a draw and stays true for as long as the record holds it. What lies below a node is a fact about
where the reader has been and what they have spent. Both arrive as a wash over the same text, so
an overlay says which it is — *dark is interesting* means two different things across the two, and
a reader carrying one reading into the other is wrong half the time.

**A depth limit is a parameter of a downward measure and not a convenience.** Subtree size has no
domain: it runs from one to the size of the tree and the tree grows, so *fixed before relative* is
unavailable to it and a colour could not mean the same thing twice. Bounded to a depth it has a
ceiling, and the ceiling is the same in every tree. The limit also names what it bounds — the
distinct continuations reachable within it are what a slate of previews would hold, so the measure
and the interaction reachable from it are one number.

**Unbounded, three of the four are monotone along the path they are drawn over, and that is a
theorem rather than a property of a tree.** A node's subtree contains its child's, so height,
size and the count of forks below can only fall as a path descends. Drawn as a wash they are a
gradient from the root, and everything they say is carried by where the steps are — which is
where the tree parts, and the column has a mark for that already. Only the run to the next fork
rises, resetting past every fork it reaches, and it is the one of the four that reads as a
measure rather than as a ramp. **A depth limit is what makes the others local**: bounded to *d*,
what lies below rises where the tree widens ahead and falls in a corridor, which is the quantity
the wash was wanted for in the first place.

**What the rule passed over is the transition drawn on its own, and it is the downward analogue
of a deviation.** Its value at a position is the total size of the arms the rule did not take
there — none in a corridor, and the whole of a declined subtree at a fork. The parallel is exact:
a deviation prices the draw against what the model offered and this prices the rule against what
the tree offered, and both are placed on the node the choice selected, because a node stands among
its parent's alternatives the same way it stands in its parent's ranking. Read in log it is
nothing where there was no choice, so it draws across a corridor exactly as much as a deviation
draws at a token that took the top row.

**So it is the one of the four a reader should meet first, and the other three are rules before
they are overlays.** Use bears the theorem out: drawn as a wash, height, size and the forks
below run as one long fade down a page and the steps that carry their whole meaning are the
hardest thing on it to see. What the reader wanted from them is *what else is reachable from
here, besides what I am already looking at* — which is this measure and not those, since a
count of everything below a node includes the path being read and is mostly it. The other three
keep their place as continuation rules, where an argmax over siblings is exactly what they are
for, and a depth limit is what would make them legible as overlays too.

**An overlay should not spend the column on what the page says already.** How far along a path a
reader is, and how much is still below them, is told by the text around them, by the length of
the page and by the scrollbar — so a wash that restates it has spent the column's one channel and
added nothing. That is why the transitions carry the signal where the levels do not, and it is a
constraint on every measure here rather than on these.

**Its support is the fork mark, and what it adds is what the mark could not carry.** A drop is
non-zero exactly where a node's parent parts, which the path read already reports, so this puts a
size on a mark the column could make without it. What it is not is *how many* ways the tree parts
there, which is the branching measure and still open.

**It is also where the toggle's disagreement becomes a quantity.** What the rule passed over
counts only what the liveness the measure follows admits, so an arm the reader set aside is worth
nothing with hidden off and its own size with hidden on. The difference between the two readings
at one position is what the reader pruned there, and how much of the tree it was.

**And it is a measure that is not a rule**, which is the half of *neither family contains the
other* that had no instance. It is not a scalar of the subtree below a node at all but of that
subtree against its parent's, and its argmax over siblings would be *take the smallest arm*.

**A downward measure reads the shape of what is below, or its substance.** Height, size, branching
and the run to the next fork are properties of the tree alone: relabel every token and they do not
move. What vocabulary lies below does move, and it is the only kind that can mark a repetition
loop, for the reason `docs/SPINE.md` gives.

**Counting vocabulary is counting size unless the count is windowed.** Types grow with tokens, so
a large subtree out-vocabularies a small one whatever is in either, and a plain count is subtree
size arrived at expensively. A depth limit is the window that fixes it, and it is the limit the
shape measures already carry.

**A token is not a word, and where that breaks is where the measure is working.** A rare word is
split, so it raises the count once by being split and again by being rare; a script away from the
vocabulary's centre raises it far more, because the merges a vocabulary is made of are a
compression of what the model saw most and they fit such text worst. That is not a bias to correct
out. **Types accumulate fastest where the vocabulary fits worst** — and the surface is for an eye,
which follows what it can read. Dense CJK, symbol runs and ASCII art are texture rather than text
to a reader of prose, and a measure that marks them is marking something real about the reading.

**Whether that is one fact or two is not settled here.** The vocabulary's fit and the reader's
legibility agree for a reader whose language is the vocabulary's centre, and nothing in this
document tells them apart; they would come apart for a reader whose language is not. So a measure
of vocabulary is not script-neutral, and should not be offered as though it were.

**A measure need not run from calm to hot, and one that does not wants another kind of scale.**
Vocabulary below has both ends pathological — too little is repetition, too much is a scramble —
so a scale running from one end to the other paints two opposite faults alike. That asks for a
scale with a middle and two directions, a third kind beside fixed and path-relative. Measuring
distance from what is typical gives one number back instead, at the cost of no longer saying which
fault it found.

**The one to try first is not the plain count.** Vocabulary below that is not already above is
one-sided: it rises with departure and falls with recombination, so it needs no middle, and what
it measures is whether a continuation is drawing on its context or leaving it. It also folds the
script question into the thing it is for rather than beside it — where a context is already in one
script its continuation's vocabulary is largely above it, so what lights up is a continuation that
changes script partway, which is a departure and not a property of the script.

**A view is a preset and not a mode.** A rule, an overlay and a depth limit set together make the
page behave one way — stepping to the next decision, filling the screen with what could be chosen,
or reading one document forward and back — and naming those saves setting three things to get one
behaviour. Underneath they stay separately settable, because the case that pays is navigating by
one measure while seeing another drawn over it, and a locked mode takes exactly that away.

**A stub is an ordinary branch and needs no new field to find.** A greedy rollout is deterministic,
so it merges rather than accumulating duplicates, and the stub at a divergence is the child
that realised the top row — which the ranking read already reports. What a stub costs is a
`generate`, and *Nothing written is only here* holds for it like any other.

## What is not decided here

**Questions prose cannot close.** Each says what would settle it, and moves into the body above
when it is settled.

- **Whether the mark's ramp says enough, or wants weight beside it.** *Colour carries the degree
  as well as the taker* answers the question this entry used to ask — how far past the top row a
  taker went had no channel, and now it has the one the taker was already spending. What is open
  is whether one ink can hold both: a strongly-ramped cool line and a weakly-ramped one have to
  read apart at a glance, and a line that also carries a style for an unreadable value is
  carrying three things. Settled by reading a driven passage with it. If the ramp is not enough,
  `text-decoration-thickness` is the untouched channel and takes either the degree or a threshold
  the reader places — which would make *what counts as far* an operator's dial rather than a
  constant, and is the first thing in the column that would be.
- **Whether a viewport scale needs more than zoom to stay still.** A position approached can dim
  as it centres, and widening the view is the answer the reader already has. What is open is
  whether that is enough in practice or whether the domain wants a window wider than the view, or
  hysteresis, or to recompute only once scrolling stops. Settled by scrolling a long path with it
  and seeing whether anything is lost track of.
- **Whether the mark should be drawn when no overlay is.** Who put a token there is not a measure
  and so is not covered by *An overlay is asked for*, which argues it is always on; *The floor case
  is a text reader* argues the column a reader has asked nothing of stays plain. It is **drawn by
  default and carries a switch**, which is what makes the question askable rather than argued —
  what is still open is the answer, settled by whether a reader with no overlay up keeps it on.
  Density is lighter than the divergence rate suggests and is the thing to watch: over
  `data/logozoa` the mark stands under 3.6% of nodes, 1.2% the reader's and 2.4% the sampler's,
  and over `data/continuations` 18.2%, almost all of it the sampler's. A passage drawn near the
  top of the dial diverges at three positions in five, so it is a hot *stretch* and not a tree
  that fills with lines — which makes the sampler's half the one that would want a switch of its
  own, if either does.
- **What a branching measure counts.** Immediate children, forks below, forks per node, distinct
  continuations within a depth — each answers a different question, and unqualified branching has
  no scalar at all. The depth limit narrows it to one candidate, being the count of continuations
  reachable within the limit, which is also what a slate of previews would hold. What settles it
  is building that slate: the number that makes one legible is the number the measure wants.
- **Whether a scale with a middle earns its place.** A measure with both ends pathological cannot
  be drawn on a scale that runs from one end to the other, and vocabulary below is the first such
  measure proposed. The alternative is to measure distance from what is typical, which restores
  one direction and stops saying which fault was found. What settles it is whether a non-monotone
  measure is kept at all once one has been read over a real tree.
- **What a downward measure costs where the cost would bite.** Height, size, forks and the run to
  the next fork accumulate in the descent the path read already makes, so they are cheaper than
  the code they replace. A count of continuations within a depth does not: it is a fold over
  depths and not over nodes. What settles it is measuring that one before it is offered, and the
  numbers belong beside the code that pays them.
- **Which overlay finds the positions worth branching at.** Entropy, the top-1 to top-2 gap, the
  mass in the head, or something composite — Overlays says what each can be computed from and not
  which is worth reading, and `docs/SPINE.md`'s *Evidence in hand* already rules out the obvious
  answer — selecting by the gap picks the flattest positions in the tree, which is the opposite of
  what it looks like it does. That is a finding about choosing where to spend and not about
  reading a deviation, where the same quantity is the honest price of a divergence already observed.
  What settles it is that document's fork map.
- **Whether a depth-bound overlay is legible when depth varies along a path.** Carrying the depth
  is what stops it lying; it is not what makes it readable. Depth varies without anyone having
  moved the recording bounds, and it varies *with* the thing that makes depth matter —
  `docs/SPINE.md`'s *Evidence in hand* measures a factor of five along one path, the rows spent
  where the distribution is flat. So a uniform-depth pass is not the repair of an inconsistency
  but a decision to buy depth the recording rule declined to, and a pass is cheap because
  deepening merges. What settles it is reading one tree as recorded and the same tree levelled.
- **Whether the two families should be drawn in different channels.** Colour for what the model
  said and typographic weight for what the tree holds would make the column say at a glance
  which kind of fact it is reporting, and the rankings already speak that grammar — the bar is
  the model's and the size of the spelling is the tree's. Two things stand in the way and both
  are about the column rather than the idea. Font weight moves advance widths, so it reflows
  prose, which is the friction *The path* refuses; it works in a ranking because each row is its
  own clipped line. And the ink itself is already carrying the caret's frontier, so a third
  state on that channel fights it. The version worth trying is background for the model and ink
  density for the tree, which reflows nothing. Deferred rather than open: what settles whether
  it is wanted at all is whether *what the rule passed over* and the rankings between them
  already answer *what else is here*, and that is knowable only once both are in use.

## Status

**An overlay is drawn over that column and is chosen in a panel beside the toggle**, which holds
what is read as the other holds what is written. Three measures stand in the three corners the
two divisions make — deviation, the top-to-second gap, and the mass the recorded rows hold — and
each declares both its sides, so the machinery is exercised rather than described. A scale is
fixed or path-relative and is read in log or in linear, and a measure carries both readings with
a domain apiece, a domain running high to low being how a descending reading states its polarity.
A span of more than one node is marked and never coloured, and the panel says how much of the path
the measure reached and at what depths.

**The family that looks down reaches the same panel, and the rule the path follows is chosen
from the same list.** Height, subtree size, the forks below and the run to the next fork come
from one descent the path read carries when it is asked for. Each is offered twice — as a
measure to draw and as the rule to continue by — because they are one scalar read two ways, and
the two are set separately, so a path laid out by one can be read under another. None of them
carries a fixed domain, so the scale is the path's own and the panel does not offer to fix it.
A fifth is drawn and is not offered as a rule: what the rule passed over, which is nothing along
a corridor and the size of the declined arm at every fork.

**A mark under a segment says who put the token there and how far past the model they went, and
it is not an overlay.** It is drawn whether or not a measure is, and carries a toggle beside the
two that say what is set aside and whether the rows are shown. A `realise` is marked whatever it
cost and a draw only where it left the top row, so what a line means is *something other than the
model put this here*. Each taker owns a hue, the balance of the share locates the token on that
taker's own scale, and neither scale reaches transparent at its foot. The reader's half is read
off a `realise` or a source of kind `user`, so authored text draws as the reader's — at the top
of the warm scale where nothing ranked the position, marked as a placeholder rather than a
reading. **Every way of arriving at an unreadable value now draws the same**, the four overlay
states and that placeholder together; they stay apart in the read and the title still names
which. The set of realised nodes crosses the wire as a plain boolean per node and the source
kinds as a map beside the names, since who took a token has no domain and nothing to compare
across positions.
