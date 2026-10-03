# The reading surface

**What the surface is.** What it shows, what it lets a reader do, what it reads to do it, and
what it deliberately leaves undecided.

**The test it is written against: can a reader tell what is settled from what is open, and does
each open question say what would settle it?** A design in progress fails by writing an open
question down as a rule so that it reads as finished.

Sections are cited by name, never by position. What the record is, is `docs/CORE.md`; what a
backend must do to produce it is `docs/ADAPTER.md`. No fact about either is restated here, and
nothing here constrains either.

---

## What this is

A reading surface over a trie of tokens. **A generation is not an answer to be accepted or
rerolled** — it is one path among those the model made available, and several are held at once.
The surface exists to read across them.

**The floor case is a text reader.** One path, root to leaf, set as prose: no chrome, no marks, no
panels. Everything else here is something a reader asks for, and a real tree carries alternatives
at nearly every position, so a surface that drew what it knows would be a picture of the tool
rather than of its subject. What gets set as prose is whatever the path holds, degenerate or not.

**One tree at a time, and the surface is its sole writer.**

**The tree is made here as well as read.** Every path the surface reads across is one a reader
made from it, and the acts that make them are as much the instrument as the column is. Where a
tree comes from is where that starts.

## Units

**A token is not the display unit.** A token spells several characters in ordinary English, and a
character can span several tokens — `docs/CORE.md`'s worked example spells one alchemical symbol
with three, none of them valid UTF-8 alone.

**A segment is the shortest run of nodes whose bytes decode.** It is the display unit and the
addressable unit both. In ordinary English every segment is one node; across a multi-token
character it is several.

- **A segment cannot be split.** Nothing addresses a node inside one, so a character spelled by
  three tokens cannot be branched into.
- **A path may end mid-character**, which is a legal path with no string form. Its trailing bytes
  are one segment, marked as not decoding and shown as U+FFFD — the same choice the command line
  makes.
- **A control token displays as the characters it spells.** `<|endoftext|>` is thirteen ordinary
  characters on screen, indistinguishable from authored text spelling the same thirteen, because
  the two spell the same bytes and display is bytes. The store tells them apart by the id.
  Whether the reader should is in What is not decided here.
- **A newline is a newline** in the reading column. Where a construct of the surface is one line
  by its own construction — a row's continuation in Rankings — a newline is shown as a glyph rather
  than obeyed, because obeying it carries everything below out of alignment.

## Where a tree comes from

**A tree starts empty and the reader makes it.** The surface opens against a tree with no nodes
as readily as against one with thousands, and what a reader does from there is a loop: put
something in, continue it, take a position the model offered and did not take, and write one it
would not have offered at all.

**An empty tree is a state and not an error.** There are no roots, so there is no path and the
reading column has nothing to set. What the surface offers is composition, and the tree's name
and vocabulary — which a reader about to write into it needs and cannot read off an empty page.

**A tree holds several roots and the surface lists them.** `docs/CORE.md` has each beginning its
own trie, so the list is of separate readings that happen to share a store and a vocabulary.
Moving between them is a selection: nothing is written, and the position becomes the root taken.

**A root is named by what it opens with** — enough of its first text to be known again, stopping
where the tree first parts. Past a divergence a name would follow whichever continuation rule was
live and change under a parameter of every other read, which is not something a name may do. The
list cuts it again to the room it has, so a name is a line and never a paragraph, and a newline
is shown rather than obeyed. **Where a name stopped is worth marking**, since one cut for room
and one cut at a divergence read the same.

**A root is a `create` with no parent**, and nothing else about it is special. It is the act the
reader makes at every other position, which is why a seed and a branch are one thing the record
does not distinguish — and why the gesture that starts one stands in the list at the row the new
root will occupy, a request appearing where its result will.

**There is no cursor.** Any live node can be written at, and continuing is writing at the end of
the path being read. The tip is where a reader usually is; it is not something the record holds.

**The gestures and the acts are not one to one.**

| what the reader means | acts | what it leaves |
| --- | --- | --- |
| start something | `create` with no parent | a root, and the first path |
| continue what is read | `generate` at the leaf | nodes under it, and a ranking at each |
| take what was offered and not taken | `realise`, then `generate` | a fork, and a path under it |
| write what was not offered | `create` at a live node | a fork with no ranking behind it |
| set aside | `delete`, `undelete` | a fork that stops being one, or resumes |

Taking an alternative the model ranked and did not sample is one intent and two acts — `realise`
makes the node and `generate` continues from it, which is the cost Rankings states for that
row. The reader means one thing and the record keeps two, and neither layer is wrong about it.

**A `create` at a node that already has a live child is a branch with no ranking behind it.**
Every other fork stands on something the model offered; this one stands on nothing but the
reader, which is what makes it the control case — a path the model would not have produced, read
against the ones it did. The record does not distinguish it from any other `create`, and whether
the surface should is in What is not decided here.

**A composition affordance belongs at the position it will write into**, for the reason Writing
gives for the placeholder: a request appears where its result will. What summons it, what it
looks like, and whether the surface holds one that moves or one at each position are settled by
use and not by prose, and are in What is not decided here.

**A complete request leaves the surface, and what completes it is in the record.**
`docs/ADAPTER.md` requires every parameter that something other than the caller would otherwise
decide, and what it forbids is the layers *below* the caller supplying one, where nothing records
it. The surface is a caller. A value it defaults to is a value it sends, so the act's `params`
hold it and what was asked for stays readable; what it may never do is leave a parameter out and
let the sampler chain decide in silence. An adapter that needs one it did not get says so, as a
refusal naming what it wants, in the record like any other.

**The reader is not asked for a seed.** What that costs is replay, which `docs/ADAPTER.md`
already states and which the record stays honest about: no seed was asked for, and that is what
it says. The surface is a playground — it is where a question worth asking under control might be
found, and not where it is answered — and an act that has to be replayed is one the command line
makes, naming its seed.

**A refusal about parameters is where they are edited.** Writing offers a retry exactly where
the same request could succeed and an edit everywhere else, and a request refused for what it
asked for is the second kind: the parameters come back under the reader's hand with the adapter's
own words beside them.

## The path

**The surface shows one complete path**, root to a leaf, and the reader's position in the tree
*is* that path.

**Below a node that has just changed, a continuation rule picks the rest.** The first
implementation is the **longest live continuation** — deepest wins, deleted nodes are not
followed, ties go to insertion order. It is one of a family, the surface takes the rule as a
parameter rather than embedding it, and which member is right is in What is not decided here. On
first open, with nothing yet chosen, the whole path is that rule from the root.

**The path is held rather than re-derived**, and changes when the reader selects a branch or when
an act lands. A reader who takes a shallow alternative and generates five tokens onto it would
otherwise be thrown back onto the two-hundred-token branch they just left, which is still the
longest descent from the root. **The path follows the act:** what an act produced is what the
reader is looking at when it lands.

**Between forks, nothing is drawn.** A stretch where nothing is offered should look like prose,
so the visible object is the fork and the column is otherwise text.

**Where the reader is pointing is a caret, and it sits after a node.** That node is the anchor
every act and every question at a position takes: the ranking to open, the sibling a `realise`
would make, and the branch a draw from here would start are one node and not three. Pointing at
a segment puts the caret *before* it, so what the reader points at is the token they are
reconsidering and the caret lands where an alternative to it would stand — which is the same
node Rankings already names, arrived at from the other end. A root has nothing before it and
nothing acts under what is set aside, so neither takes the caret.

**It is the reader's one piece of state, and the path is drawn through it.** A path read answers
from a node in both directions, so one node is enough to say what is drawn; a second held beside
it would be a second thing that can disagree about where the reader is.

**Pointing is not arriving, and only arriving derives.** A path read is an ancestry and a *fresh*
continuation below the node it is given, so a read at the caret re-chooses what stands under the
reader's finger — and where an arm has been rolled it chooses the arm, that descent being the
taller one. So pointing moves the mark and reads nothing: the node it lands on is the last node
of the segment before it, which is drawn and marked already. What the reader points at holds
still, which is the rule a roll obeys when it leaves the text alone.

**It is the frontier of what has been accepted.** Above it is read and taken; below it is
whatever the tree still holds there, drawn subdued, because the reader has not stood at its end.
Asking for more happens at the frontier rather than at the foot of the page, which is what makes
the gesture work in the middle of something as well as at the end of it.

**What is drawn below the caret is derived on arrival and never remembered.** The rule's
continuation from the caret carries it where there is one, and from the caret's parent where
there is not — which is the case a `realise` makes, the new node being one token long and the arm
it was chosen against being what the reader was looking at a moment before. What stands between
arrivals is the view and not a second opinion about where the reader is: the caret is only ever
placed on a node of it, so the two cannot disagree.

**Left alone it follows the end, which is the batch discipline and not a convenience.** A draw at
the end carries the caret along by as much as it drew, because asking for the next batch is a
deliberate act taken after reading the last — `docs/INTERFERENCE.md` has it carrying acceptance
of everything above it, or at least a wish to see past it. A reader who did not accept it moves
the caret back, which is the same gesture as pointing anywhere else.

**A draw at a fixed position leaves the caret on it, which is the other thing a draw can be.**
The batch discipline is right where the reader is reading on. Where they are asking what else
goes *here* — several continuations from one node, read against each other — the caret is the
position being asked about rather than the frontier of what has been read, so it stays and the
gesture repeats without being aimed again. What is drawn below it is the act's own path, read
through that act's tip, and not what the rule would pick from the node. **The gesture is a key,
because this draw has no place to be arrived at**: the scroll is deliberate by reaching the foot
of the page and an armed caret by the click that armed it, and a draw in the middle of the text
has neither, so the gesture itself is what has to be unmistakable. While it is in flight the text
below the caret is taken down rather than left standing, that being what the draw is about to
replace, and nothing above it moves. **A draw that samples what was already there merges onto it
and moves nothing at all** — the ordinary case at temperature zero, the path below a node being a
greedy descent already — so that outcome is said, being the one the reader cannot see.

**Arming belongs to the tip and nowhere else, which is what keeps one meaning for each gesture.**
A scroll down says *more of this*, and that can be asked where there is nothing below; at a
position with a path already under it the same gesture would fork mid-text without announcing it,
and the key is what asks there. So an act may arm the caret only where it stands at the tip — the
last position an act can be taken at, which is not the last node drawn: a path ending
mid-character, or carrying on into what was set aside, has no tip to arm. It is the resting
position under another name, so the two cannot disagree about where the scroll gesture is live.

**And the tip has to be reachable, or pointing anywhere is a trap.** Every segment is somewhere
to point and the tip is a segment like the rest, so a reader who pointed somewhere would otherwise
have no way back to the gesture that continues what they are reading. `Esc` releases the caret to
the tip, as does a click on the empty part of the column — the same thing spelled where the hand
already is, and the one place a click there can mean nothing else. Releasing does not arm: it is a
navigation, and a reader standing at the tip has the foot of the page for the rest.

**It carries no control, and the reason is reflow.** A thing to press has to occupy room in the
line, so the text moves as the reader points along it — and text that shifts under the eye is
friction in the one thing the surface is for. So the caret is a rule on the inside edge of the
segment it follows, which costs no layout at all, and what it offers is the gesture that was
already there: the scroll, at the caret. One anchor and one gesture, rather than a control per
position.

**It follows the window once it has been placed, and not before.** The gesture that asks for a
draw is the scroll and the draw lands at the caret, so a caret scrolled off the screen would aim
an act at a position nobody is looking at. Three things bound that. A caret already in the window
does not move, because pointing somewhere is deliberate and a scroll is not a retraction of it.
A caret **at rest** does not move either: left alone it follows the end of the path, and the
gesture that draws at it needs the foot of the page, where the end of the path is on the screen
anyway — so a reader who has pointed at nothing scrolls without moving anything. And it costs no
read, for the reason *Pointing is not arriving* gives.

**Where it lands is the last segment the window leaves clear of its edges, and not the nearest
one.** Clear and not merely whole: a caret hard against a border is one the reader has to hunt
for, and the line it marks is worth a line or so of context either side — so the band is a line
and a half in from each edge, reckoned in lines so that it holds whatever the column is set in.
The foot of the page is not a problem for it, the column's own bottom space being deeper than the
band. The rest is two reasons that are one reason. The caret is the frontier of what has been
read, so the edge it belongs against is the one the reader has read down to — which at the foot of
the page is the end of the path, which is what the gesture there has always meant. The nearest
seat would be the *first* in the window on the way down: it would draw thousands of tokens above
the foot of a page the reader scrolled to the foot of, and it would subdue every line they were
looking at.

**An act at a position may arm it, and then reading on is what asks.** The ordinary gesture is
the end of the page, and what makes that deliberate is that the reader had to arrive there. A
`realise` has no such place to offer — it writes one node in the middle of something being read —
so what stands in for the arrival is the click that made it, on a row drawn where the reader was
already looking. The next downward scroll then asks for the draw wherever the page is standing,
and asking disarms it. **Nothing else may arm it**: anything that moves what a draw would land
on clears it, so a page left alone is never a page that will write, and the direction matters
because what lands after an act can shorten the page and move the window on its own. An armed
caret does not follow the window either — it is the one the reader chose, the next downward
scroll is the draw, and drifting off it would both aim the act elsewhere and disarm it on the
way.

## Hidden

**Deleted is the surface's *hidden*, and whether it is shown is one toggle.** `docs/CORE.md` has
`delete` setting a flag on one node and `undelete` clearing it, with liveness derived and nothing
leaving the store — so what a reader means by one is *set this aside*: a root not being read, a
tail that went nowhere. Grown and pruned is the whole of it, and the record needs no other
notion to serve it.

**The toggle governs the page at once**, the list of roots and the reading column together, and a
hidden node that is shown is visually distinct rather than silently ordinary. One state, because
a reader asking *what have I set aside* is asking it of the tree and not of one column.

**Without it, hiding is one-way.** A reader who sets a root aside and cannot list it again cannot
take it back, and an act with a verb of its own would be reachable in one direction only. That is
what the toggle is for, and it is why it comes before anything that makes hiding pleasant.

It is a way of looking and records nothing. What is live is read from the store either way, and
the continuation rule follows liveness whether or not the reader can see what it stepped past —
so **showing what is hidden reveals it and never selects it.** In the column that is a rule about
where hidden text may appear: the live path is chosen first and is the same path either way, and
what is hidden only ever carries it on from where the live one ran out. A hidden node is never
preferred to a live one, because it is never offered beside one.

**Nothing the reader did not ask for need arrive live.** A stub is inference the instrument
spent rather than a continuation the reader chose, so it can be born set aside and be reached the
way everything else set aside is reached. That costs no new field and no new state. **It is
written rather than withheld until it is taken**, which is the answer for a stub the reader never
asked for as much as for one they hovered: a rollout nobody took is still something the instrument
did, and a record that drops what was spent unbidden is a record of a different session than the
one that happened.

**It does load one flag with two meanings**, and they are near enough to share it: *I have put
this away*, and *nobody has taken this up yet*. What tells them apart is the act and not the
node — an act carries its actor — so a reader who needs the difference has it and the column
does not have to draw it. What it does not reach is *where* such a node sits: a stub hangs beside
a path rather than below its end, and the rule above only carries a path on from the end. Seeing
one is Rankings' business and not the column's.

**Anything that spends inference without the reader pointing at it acts as its own source.** A
hover is the reader asking, so a rollout under one is theirs and lands under the actor every other
act of theirs does. A policy that rolls stubs ahead of them is not, and it carries a named source
of kind `user` as its `actor` — separate from the unnamed reader, and free to name the reader it
acts for. `sources` already admits this: the empty name is reserved for the unnamed user rather
than required of every one, so it is a rule about use and changes nothing in the record. What it
buys is that *what the reader did* stays separable from *what the instrument did on its own*,
which `docs/SPINE.md` wants of every aggregate and cannot recover after the fact.

## Forks

**A fork is a node whose parent has more than one live child.** In the reading column it carries a
mark and nothing else — no count, no preview, no affordance beyond being marked.

**A deleted sibling hides a fork.** Liveness is what the surface follows, so a node with two
children of which one is deleted is not a fork and is not marked. The record still holds it, and
whether a reader should be told is in What is not decided here.

## Rankings

**Selecting a token asks what else was live at that position**, which is the ranking at its
*parent* — a node's own ranked edges are the alternatives for what follows it, not for it.

Every ranked edge at that node is shown, and each is one of three things:

| row | what it is | what taking it costs |
| --- | --- | --- |
| the one taken here | the token on the current path | nothing; it is where the reader is |
| realised elsewhere | a node exists for it, off the current path | a selection; no act at all |
| unrealised | no node exists for it | one `realise`, and then a `generate` to continue |

**Rows are shown in descending logprob, and source by source.** The store holds no order at all —
`docs/CORE.md` has a ranking as a set — so the order on screen is the surface's, made each time it
draws. Across sources it
does not: a node several models have ranked holds several rankings, and one order over their union
would sit rows side by side that were never alternatives to each other.

**Each row shows its logprob.** How — a number, a bar, a ramp, a share of the recorded mass — is
in What is not decided here.

**A list of rows has two axes, and the order is only one of them.** The order is the model's
opinion of the position and so is whatever draws each row's logprob; what neither says is what
the reader made of any of it. That is the downward family read across the siblings at one
position instead of down a path — an overlay and a ranking transposed, which is the same
identity Overlays states from the other side — and it is drawn as how much room the token takes.
So the two axes of a row are the two families of measure, and neither needed a name it did not
already have. A row's value is fixed the moment it is recorded and its weight moves with every
act, so the two disagreeing is the whole of what there is to see: **where the heaviest row is
not the top one is where the reader steered.** Over the 53 forks of `data/continuations` that is
17 of them, which `docs/SPINE.md` records along with what it does and does not settle.

**Which downward measure weighs the rows follows the overlay, and rests on size.** They are one
quantity, so a reader comparing along the path and across it should be reading the same thing —
and where the panel has no answer, because nothing is chosen or because what is chosen looks up,
the rows still have the axis. A measure read against its parent is not one of these: across
siblings its argmax is *take the smallest arm*, which is the same reason it generates no rule.

**A row weighs nothing for two reasons and they are not one.** Nothing realised it, so there is
no node to measure; or what realised it is set aside and the toggle is hiding it. Both sit at the
floor of the axis and only one of them is somewhere the reader has already been, so the row says
which. It is the disagreement the downward family already has with the continuation rule, read
across a position rather than along a path.

**The rows hold less than the whole distribution.** They sum to less than one because the rest of
the vocabulary was never recorded, not because anything was truncated, so *where the recorded mass
runs out* is a quantity the surface can draw, labelled as being over the recorded mass. It belongs
to the node: a ranking extends across acts and is never rewritten, so the rows are the union of
what everything that passed through recorded, and the number is not the `record_mass` of any one
act.

**Deepening a ranking is a `generate`.** A reader who wants more alternatives at a position asks
for them, and the request is a length-1 `generate` with a wider `record_rows` — rankings extend
and are never truncated, so new rows accumulate onto the ones already there. Under a greedy draw
the token drawn is the top-ranked one and a node for it usually exists, so the act merges rather
than adding a child. It is a write with a verb of its own, so *Nothing written is only here*
holds.

**Density stays behind intent, and the toggle is not what enforces it.** A ranking can run to
dozens of rows at a position the model was unsure of, and none is shown until that position is
asked about — which pointing does, one position at a time. That is the rule, and it holds
whether or not the rows are switched on. The switch itself starts **on**, because use settled
it: a reader working a path wants to know what else was there at the position they are at, and
reaching for a toggle first makes that a decision instead of a glance. What the reading column
draws from those rows without being asked about a position is Overlays.

**The rows stand beside the column, at the line they are about.** The reading column is half
of a container two measures wide and the other half is empty; a ranking answers *what else was
here* at a position, and it is the only thing that answers it, so there is one place to look
and no second answer to keep in step. They sit against the column rather than
over the window, so they scroll with the text they belong to.

**Hovering is a caret that has not been committed.** With the rows shown, moving over a segment
shows what pointing there would give — by the same rule, the ranking at the node before it — and
the click that places the caret is what commits it. So a reader sweeping the column reads the
alternatives along it without moving from where they are, and nothing new is named to allow it.

**A hover's list cannot be reached, and the click is the way to it.** Leaving the segment takes the
rows with it, so a reader moving towards rows they only hovered arrives after they have gone. That
is what the preview being a preview costs rather than a fault in it: the rows that stay are the
caret's, and a click on the token asks for exactly those. What it does not excuse is being
illegible — a list that went away on the approach and a list that was never there look the same —
so each list is drawn as what it is. The caret's is solid and carries the accent the caret itself
is marked with, which is also what this surface already draws the root the reader is in with; a
hovered one is dashed and has none. **Said in how it is drawn and not in a line of words**, which
would be read on every list opened and wanted on none of them after the first. A click on the
token a list was hovered from changes nothing in the rows, only the claim standing over them,
which is all that click changed.

**Which token a list is about is marked in the column.** The caret and the pointer each say where
they are and neither says what the rows are alternatives to: a position sits before a token, so
the list is rival to the segment *after* the caret, and nothing marked it. It is the same token the
row drawn as *the one taken here* is, said at the other end of the list — one derivation, because a
column and a list that disagreed about which token the position was choosing between would both
look right.

**The caret's own mark stays under a hover, drawn back rather than put out.** A mark around the
segment after the caret says where that boundary stands more exactly than a rule on an edge does,
and a reader following a hover across the page is further from the caret than at any other time —
which is the worst moment to stop saying where it is.

**A row can carry what follows it, and where that comes from is the realised line again.** A row
some node realised has a continuation the store already holds, so showing it follows the same
rule selecting it would and costs nothing, being a path the store already holds. A row
nothing realised has nothing to follow, so showing it is a stub: inference the instrument spends,
and an act. The two wear one appearance and are not one thing, so a row says which it is rather
than leaving a reader to infer it from whether anything appeared.

**Previews and the rankings are one mechanism, and the rows are where it lives.** Both follow
the continuation rule below a node that exists, and what stood between them was a width budget:
whether the previews wanted a surface of their own or the rows given more room. Use answers
rows. A row carries what follows it inline, set below the weight of the branch token itself, so
*what else was here* and *where each of those goes* are read in one place at one glance. There
is no second surface, and the half of the container the rows stand in is what pays for it.

**Clicking inside what follows a row is placing the caret inside it.** Once a stub has landed its
nodes are ordinary nodes, so what a row shows is the record drawn ahead of where the reader
stands rather than a picture of it, and moving into one asks for no operation that does not
already exist.

**Looking may spend inference, and a hover is what asks.** Resting on a row rolls it out, so the
model's own continuation becomes visible wherever the reader looks — continuously, without
running a second arm, and it is the one thing that shows a repetition loop, which
`docs/SPINE.md` has no measure able to mark. What it costs is the page's own rule that a way of
looking is free, and three things make that smaller than it sounds. *Hidden* already has a stub
born set aside, so what a hover writes enters neither the live path nor the rule. Rows at one
node share the path above them, so the second and later rollouts there reprocess a single token
and trying several is a glance rather than a decision. And it is asked for rather than assumed:
a fling across the list skips what it passes over, and a row already rolled out is not rolled
again.

**What it costs in exactness is stated rather than hidden.** A rollout is a pure function of the
position only cold, and a hover is the warm case — `docs/SPINE.md` carries the adapter's
measurement of what a partial cache hit moves. So **the row's token is a fact and its
continuation is advisory**: the token is read from the stored ranking and cannot drift, while
what follows it is what the model would do from there under the cache state that obtained. A row
says which of the two it is offering, because a reader taking a token and a reader taking a
continuation are relying on different things.

**Clicking a row nothing realised is the `realise`, and that is its primary meaning.** Not one
entry on a menu the row might later carry: the row exists to be taken, and the only one of the
three that needs an act is the one nothing has taken yet. What it writes is a node and no
ranking, so the caret lands on the sibling it made with nothing below it, and the arm it was
chosen against is drawn subdued below — derived from the rule at the caret's parent, as
*The path* has it. Asking for the continuation is the act it always was, and the caret is armed
so that reading on is what asks.

**What a row shows of its continuation follows the rule that taking it would**, so it is a
truthful prefix of what the reader gets and not a separate rendering of the same tree. Taking a
row whose continuation already exists writes nothing: it is a path the store holds, so the
gesture is a selection. Only a row nothing has realised costs an act.

**A continuation is clipped by the room the row has, and the row says when it was.** What is
left beside the token and its number is a line's worth at most, and a silent truncation reads
as *that is all there was*. The count is what keeps a reader from taking a short-looking arm
for a short one.

**A row says how its continuation ended, because the three ways mean different things.** It ran
out of length and there is more to be had; it cycled, and the model's preference from there is
an attractor; or it reached EOS, and the model would have ended the document at that point. The
record tells them apart already — `docs/SPINE.md` has which and why — and collapsing them would
tell a reader that an exhausted model and a finished document are the same event. It is the
same discipline Overlays applies to a position with no value: the ways of arriving at one are
marked apart, and none of the marks can be read as a quantity.

**Taking a row is taking as much of it as the reader points at.** Clicking the token takes the
token; clicking into the continuation takes it up to there; clicking the end takes all of it.
That is *clicking inside what follows a row is placing the caret inside it*, and prefix-of-any-
length falls out of it rather than needing a gesture of its own. Underneath, a row whose stub
exists is brought back rather than made — `undelete` where the flag sits, and a `delete` after
the cut where the reader stopped short of the end, so the record says what happened: *I took
this token and set aside what the model did next.* A row with no stub yet is the `realise` it
always was.

**Clicking away from everything puts the caret back at the end of the path.** A reader who
pointed somewhere has no way to stop pointing, and the caret at rest — following the end, which
is where the scroll gesture wants it — is currently reachable only by reloading. A click that
lands on nothing is the release, and it is the same rest position *The path* already derives
rather than a second idea of where the caret belongs.

**How much a row holds is drawn, and not only printed.** A ranking's rows carry probabilities
that sum to less than one because the rest of the vocabulary was never recorded, and both halves
of that are worth seeing: what each row holds, and how much of the distribution the recorded
rows account for between them. Whether a bar is read against the top row or against the whole
is open below.

**A ranking read earlier stops being true when an act lands, and not because the rows changed.**
Rankings only grow, so what a position holds keeps for the life of the page; what does not keep
is which rows a node has realised. Hovering is what makes this load-bearing, since it is what
makes holding them worth doing at all.

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
and weight is claimed — `docs/INTERFERENCE.md` gives prominence to the watermark at the most
recent act's origin. Whether the four readings above suffice is in What is not decided here.

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

## Writing

The surface offers the five acts and nothing else. What each one is, is `docs/CORE.md`; what a
reader means by one is Where a tree comes from; what it costs is here.

| operation | needs | can fail as |
| --- | --- | --- |
| `create` | a tokeniser | rejected — the round trip does not hold, or it adds no tokens |
| `generate` | a model | refused by the adapter, or failed mid-call, or rejected before the call |
| `realise` | neither | rejected — no such edge, or the node is not live |
| `delete` / `undelete` | neither | rejected — no such node |

**One write is in flight at a time, and while one is, no other may be requested.** There is no
queue.

**The surface writes at the last addressable position, which is not always the last node.** A
path may end mid-character, and those trailing bytes are a segment that has not closed — inside
which, by Units, nothing is addressed. So a continuation hangs under the last node whose path has
a string form, and the nodes past it are not a position the surface acts at. What the record does
with the ones it re-draws is the merge key's business: under a draw that repeats them they are the
same nodes, and under one that does not they are a sibling, which is a fork like any other.

**Not every position can be generated from, and the surface asks rather than finds out.** Ending
mid-character is not the only reason a backend may decline a path, so the predicate is asked at
the position the act would use. `docs/ADAPTER.md` provides for exactly this: asking is not
declining, it writes nothing, and the real request still goes through `generate`. **The answer is
advisory**: a request that goes anyway is refused by the adapter and recorded, and the surface
shows that refusal rather than suppressing one it predicted. `create` and `realise` call no model
and are never gated by it.

**A request appears where its result will.** An inline placeholder at the position the act will
occupy, replaced by the nodes when they land — not a spinner elsewhere on the page, and not
optimistic text.

**The placeholder is read rather than remembered.** `docs/CORE.md` commits a `generate` act before
the model is called, and an act with no terminator is a generation in flight, so what the
placeholder stands for is in the record. A page opened while one is running draws it, and a page
reloaded mid-generation does not lose it.

**Reading goes on while a write is in flight.** A generation is seconds of waiting, and the reader
is not held at the page they asked from: the store's journal mode lets a read take no lock, and
`docs/CORE.md` is explicit that no transaction spans a model call. What the reader cannot do is ask
for a second write.

**A failure becomes a dismissable error in the placeholder's position**, and it says which kind it
was, because the record does.

- **A refusal is in the record.** The adapter declined, no model was called, and the act stands
  with the parameters it was asked for and terminator `refused`. The error names that act.
- **A rejection is not.** The core declined before writing anything and left no trace. The error
  says so.
- **A failure is in the record.** The call happened and nothing could be recorded from it.

**A retry is offered exactly where the same request could succeed:** `failed`, and transport
errors that never reached an act. A refusal and a rejection are answers about the request itself,
so what they offer is an edit — repeating either unchanged gets the same answer.

**The surface is started against one tree and claims it for as long as it runs**, which is what
lets it open for writing once and verify once for the life of the process rather than before every
write. Verifying is a whole-tree read. A tree another process is holding cannot be opened, which
the surface reports naming the tree rather than starting and showing a page that never resolves.

**Opening for writing can change the tree, and that is the surface's first write.** Claiming the
tree is what records abandoned generations as `aborted`, so a tree left in flight by a writer that
died — a killed command line, most likely — is swept the moment the surface opens it. That
terminator is therefore something the surface *finds*: a request the surface itself loses, it
loses along with the process holding it.

## What the surface reads

**Three reads, and each is one descent.** A read that asks per node — its own ancestry for
liveness, its own children for what parts — is the one shape these cannot have, and `docs/CORE.md`
says what the fix is: *a descent from the root carries the answer down.* These are stated as what
must be answerable that way, not as an interface.

**1. A path.** From the root to a node: the segments in order, each carrying the node ids it
spells, and for each node its source, its logprob, whether it is live, and whether it is a fork.
One descent, carrying liveness down rather than asking per node. **For an overlay it also carries
a per-node aggregate of the ranking its *parent* held**, and the recorded depth that aggregate was
taken over — decorating the descent's output rather than joining its recursion. **Which overlays
to compute is a parameter of the read**, the way the continuation rule is, so the floor case pays
for none of them.

**2. A ranking.** Every ranked edge at one node, each with the bytes its token spells, its
logprob, and **the child that realised it, if any**. Not the branchable set alone: a reader
looking at a position needs to see what was taken sitting among the alternatives, and the
branchable set is then the rows with no child.

**3. A branch subtree.** Below one node: each divergence, the run of nodes from it, bounded by a
character budget, depth-first, with the nested divergences inside each run and the index each
parts at. **A divergence with no index is counted rather than returned** — one past the budget's
cut, and one inside a segment, which nothing addresses — since what a reader is owed is how many
are not there. What the rows are laid out from is this and measurement, and nothing else.

Point reads — a node, a tree's roots, the act list — are already cheap and need nothing.

## Nothing written is only here

**No write may be surface-only**, and the surface satisfies this by construction. Everything it
writes is one of the five acts `docs/CORE.md` defines — `create`, `generate`, `realise`, `delete`
and `undelete` — and each has a verb of its own name, `undelete` being `tokenloom delete --undo`.
A long generation stopped by declining to issue the next act is consecutive `tokenloom generate`,
and so is deepening a ranking.

Everything else here is a way of looking. The reading column, a ranking and what it previews,
moving between forks, whether what is hidden is drawn, and whatever comparison across branches
turns out to be are the surface's own, record nothing, and are owed no counterpart.

**Reader state is a third thing.** A continuation rule that follows what the reader most recently
took is neither a write nor a way of looking that records nothing: it is state that decides what
is seen, held where the record cannot follow. The cost is that *what this branch is* can no longer
be read off the page without also reading *what you did here last time* — least visibly inside a
ranking, where every row's continuation follows the rule at once and the reflection is spread
across all of them. Three things hold it in place:

- **It is updated by selection only** — never by preview, render or hover. Otherwise a preview
  perturbs the thing it previews and the rows reorder under their own gaze.
- **It lives in the session and nowhere else.** Durable storage outside a browser session is out
  of scope. `docs/CORE.md`'s *Conformance and extension* makes it cheap to add later, which is a
  reason to shape the session form as a cache of something recordable rather than as something
  only a browser can hold.
- **It orders and selects; it does not describe.** What is live, what is a fork and what a ranking
  holds are read from the store every time.

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

- **How composition is summoned at a position.** Starting a root is answered: a row where the
  root will appear, staging a composer in the column that a submit turns into the act, so the
  gesture that offers a place to write is not the write. Whether continuing at a leaf and
  branching at a node several segments back want that same gesture is not answered — they are
  the same act and may not read the same, and the surface may hold one composer that moves or
  one at each position. What settles it is writing into a tree at both, and finding which of the
  two the other's gesture reads wrong at.
- **Whether a branch with no ranking behind it is marked.** A `create` at a node that already has
  a live child makes a fork the model had no part in, and the record holds the source that says
  so. Marking it puts a second kind of mark in a column *Between forks, nothing is drawn* keeps
  bare; not marking it leaves a reader to open the ranking to find out. What settles it is a
  tree with both kinds of fork in it, read for whether the difference is wanted at the fork or
  only inside the rows.
- **Which `generate` parameters come under the reader's hand, and when.** A complete request
  leaves the surface whatever the reader does, so this is a question about what is exposed and
  never about what is sent. The first pass puts all of them under it at once — `length`, the
  recording bounds, and the samplers a draw names, in a panel that holds them for as long as the
  page is open — because that is the arrangement that shows which ones a reader actually reaches
  for. What it does not settle is whether they survive a reload, whether the ones nobody touches
  should be on the page at all, and whether a refusal is better met by editing them in place
  than in a panel elsewhere. What settles those is running the loop and watching which get
  touched.
- **Which continuation rule.** Longest, first, last, most-recently-used, cumulative open time —
  each is defensible and they are comparable only by use. `longest` is the first implementation
  because it is the one member that needs nothing but the tree; ties bite only for it, and are
  insertion order. What settles it is reading one tree under two of them, which is why the path
  read takes the rule as a parameter. A rule that reads what the reader did is what puts reader
  state in *Nothing written is only here*.
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
- **How a magnitude is drawn.** A number, a bar, a ramp, a share of the recorded mass. Each
  reads differently at a sharp position than at a flat one, and a real ranking is often one and
  sometimes the other. The bar drawn now is each row against the top row of its source, which
  keeps a flat position from reading as a page of empty bars and says nothing about how much
  was recorded; a bar against the recorded mass says the second and loses the first. What
  settles it is drawing a real tree several ways. **A number beside the bar is one of the ways
  and has been drawn**: it was a column read down while the list is read across, and it was
  carrying what the bar beside it already said. It is in the title now, which is where the
  other axis's number went for the same reason.
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
- **What a node two sources ranked should show.** Refusing is what the surface does and not an
  answer. Their disagreement may be the interesting quantity, in which case the overlay is a
  measure over sources rather than one that has to pick among them. What settles it is a tree two
  models have both ranked, which nothing has yet produced.
- **Keyboard.** A ranking's rows are already the natural arrow-key sequence, but what the whole
  reader does under a keyboard — moving between positions, into a ranking and along it, taking
  a row in part or whole, back out without losing one's place — is unsettled. Hovering a row to
  roll it out has no keyboard equal at all, and it is now how a stub is asked for. *Keyboard and
  mouse first* is the target and only half of it exists. What settles it is working a real tree
  with the mouse put away.
- **What a click means.** A token opens a ranking, a row is taken at the depth it is clicked at,
  and a click on nothing releases the caret to the end of the path. Three meanings for one
  gesture, told apart by what is under it. It works and it is not obviously right. What settles
  it is finding where the wrong one fires.
- **Whether a control token is marked.** The store can tell a control token from text spelling the
  same characters. Whether the reader should is a question about honesty against clutter, and what
  settles it is a tree with control tokens in ordinary positions, read both ways.
- **Whether a hidden fork is announced.** A deleted sibling makes a fork vanish. Saying nothing is
  consistent; saying something may be truer. Hidden's toggle is not the answer — it is page-wide
  and shows everything set aside, where this asks for a mark at one position while the rest stays
  out of sight. What settles it is using `delete` in earnest and seeing whether a tree becomes
  unreadable without the mark.
- **Cadence.** Text arrives in whole acts. Whether the surface reveals a block at once or paces it
  out — which invents a timing the record does not hold — is a choice, and no measurement has been
  taken. Nothing is lost by waiting: chunk length *is* `length` in `params`, recorded per act, so
  the question stays answerable whenever it is asked.
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
- **Everything past the first gesture.** Comparison across branches, and what the instrument does
  that a reader could not get from reading one path at a time. Nothing settles this but use.

---

## Status

**A page that starts a tree, reads one path of it, and asks for more.** `tokenloom serve` holds
one tree for as long as it runs and serves the three reads, the path predicate and the five acts
over HTTP, each act under its own verb, with the page mounted at the root so that what it reads
and the page itself arrive from one origin. The page lists the tree's roots and names each by
what it opens with, starts new ones through a composer that a submit turns into a `create`, sets
one path as prose, and continues it at the end — reaching the end of what there is to read is
how more of it is asked for, and what the draw asks for is set in a panel at the foot of the
side. A root or a tail can be set aside and brought back, and one toggle says whether what has
been is drawn.

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

**A caret says where the reader is pointing, and every act at a position lands on it.** Pointing
at a segment puts it before that segment; what is drawn past it is subdued, being the rule's
continuation rather than anything the reader accepted. Pointing takes no read: it moves the mark
over text that holds still, which is what keeps a position the reader has rolled an arm at from
rearranging itself under the click that selects it. It carries no control — a thing to press in
the line moves the text as the reader points along it, so it is a rule on the segment's inside
edge and the gesture that asks for a draw is the scroll, at the caret. That is the first act the
page can make that produces a fork, the tokens either merging onto what already follows or
parting from it.

**A key draws at the caret without moving it**, which is the variation the scroll cannot ask for:
several continuations from one position, each read through its own act's tip, the text below taken
down while one is in flight and the gesture repeating with nothing to aim again. Where the draw
reproduces what was already there it merges and the column does not move, and that is said rather
than shown.

**Clicking a row nothing realised makes it, and the next scroll down draws from there.** The act
writes one node and calls no model, so the caret lands on the sibling with nothing below it and
armed: the arrival at the end of the page that makes an ordinary scroll deliberate is spent
instead on the click, on a row drawn in front of the reader. Only that act arms it, only at the
tip, only a downward move fires it, and anything that moves what a draw would land on clears it.
`Esc` and a click on the empty part of the column release the caret back to the tip, which is what
keeps the restriction from being a trap.

**A caret the reader placed follows the window, to the last segment it shows clear of its
edges** — a line and a half in, so there is context around it rather than a mark on the border.
One at rest does not follow, and neither does an armed one. So a reader who
pointed at something and then scrolled to the foot of the page draws at the foot and not where
they were pointing, which is what that gesture meant before there was a caret to disagree with
it.

**The page is served `no-store`.** Its files are the surface's own source and they change while
it is being written, so a browser holding one holds a version nobody is looking at — and the
failure is silent, since the modules that did load are the new ones calling into the stale one.
Nothing here is worth a cache: a handful of files, from the process that holds the tree, over a
loopback socket, once per load.

**What else was live is shown on demand, and all three of its rows can be taken.** The rows stand
in the half the column leaves empty, at the line they are about, following the caret and softly
following the pointer while they are shown — each list saying which of the two it is up by, and
marking the token in the column that it is the alternatives to. Each is marked by what taking it would cost: the one
the path took is where the reader already is, one realised elsewhere is a selection and is the
way back to an arm a draw parted from, and one nothing took is the only one that writes. A row
draws its probability as a bar scaled to the top row of its source and as nothing else, which is
one answer to *how* and not the settled one. **The bar is the row's own ground and not a thing
drawn behind it**, so whatever is hung in a row later is drawn over the bar rather than in front
of it and a list filling with text still reads as the distribution it is.

**The row is the token, and both of its axes are drawn as sizes.** Neither is written out beside
it: a column of figures is read down rather than across, and it would stand against the one
thing in a list that is not a measurement. A glance is still not a number, so the numbers behind
both axes are in the row's title, which is also the one place a reader asks about a row rather
than two.

**The rows carry the other axis too, and it is the downward family transposed.** How much room
a token takes is what has been grown from it, over the heaviest row of its source, by whichever
downward measure the panel is on and resting on size. Two channels and not one, because the
reading is usually the log of a count and a log over a log is narrow: an arm three times another
draws two pixels above it on size alone. It is the same descent the path read asks for, anchored
at the node the rows belong to and so bounded by the subtree they partition, and it costs 3–5 ms
at an ordinary position and 20 at the root of a fourteen-thousand-node tree. The reading is the
whole trade and the panel already owns it: log keeps a small explored arm legible beside a large
one, linear states the ratio honestly and puts the small one on the floor beside the arms nobody
ever took.

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

**Pointing at a row reads the model's own continuation from it, at once.** The reference arm
`docs/SPINE.md` names is read from the record rather than rolled: a greedy rollout merges onto
what an earlier one wrote, so the descent that never leaves the top row is what asking again
would produce, and it costs no inference and takes no lock. **What is already paid for is not
paced** — it unfurls in one gesture on arrival, because a wait before it would be charging the
reader for looking. Pacing belongs to what has to be bought.

**It is one line and nothing in the list moves.** The arm sits on the row's own line after the
token, keeps the token beside it, and leaves by the right edge of the page rather than wrapping
or scrolling; newlines are escaped as the rows escape theirs. A list a reader is scanning must
not move the next row out from under the pointer about to reach it, which is also why the price
below sits out of flow. `docs/NEXT.md` has the layout this is provisional against — where the
arm takes the space beside the column it gets the page's height, and the break comes back.

**An arm says why it stopped, and only one of the reasons is a price.** It filled the room it
was given; the record has no more and a roll extends it; the top row continues under a flag the
reader set; or two sources ranked the position and there is no one top row to follow. **The
last two cannot be bought** — a roll at either merges onto what the record already holds and
writes nothing — so reading *stopped* as *for sale* would charge for what cannot be delivered.
The page prices the second alone.

**A pulse in the left margin is that price and not a progress bar.** It marks a row where
reaching further would cost inference — one with nothing realised under it, or one whose arm
the record ran out of short of the length — so a row without one is free to look at and the
column of them is what a reader scans to find where spending begins. It follows the pointer and
not the reading, appearing on arrival rather than when an answer comes back.

**A closed continuation is marked where it closed, and the mark is the way back.** *Nothing has
run here* and *this was shut deliberately* end the same way with the toggle off — the text
simply stops — and the difference is between somewhere to spend and somewhere to reopen. One
mark says which, at the end of the column's path and at the end of an arm cut short of its cap,
and it is the same boundary that stands between live text and hidden when the toggle is on:
with it off there is nothing drawn after it, and taking it draws what was set aside rather than
restoring it. So the reader sees what they closed before deciding to reopen it, and nothing a
click does puts back a node they put away. **The mark costs a view and never an act**, which is
what lets it sit in a panel a pointer summons.

**The arm belongs to the row and the price belongs to the pointer**, and nothing else divides
what the two do. An arm is drawn wherever its row is — when it lands, whether or not the hand
stayed, and again in a list built later, which goes up already carrying what has been read from
that position. What a reader does with two of them is compare them, and a comparison they can
look away from and still have is the one worth drawing. So pointing at a row only ever says
*there is more here*, and a row the record has no arm for says it by showing a price and
nothing else.

**Resting on a price is what pays it.** Pointing and paying are one gesture held for different
lengths of time, so a reader never has to decide what a row is before looking at it: they
point, they read what the record had, and where it ran out under a pulse they can stay. What
is bought is then proportional to what was looked at — crossing a row on the way elsewhere
buys nothing, and moving on stops the spending at the part in flight.

**A row nothing realised is bought the same way, and the fork comes first.** It is two acts
rather than one and the `realise` is free, so what rests on a row the record has never been
down makes the node and then rolls from it. They are one gesture because they answer one
question — *what does the model say here* — and a reader comparing several continuations at
one position wants each fork made by looking at the row rather than by committing to it
first. The row changes kind under the pointer rather than the list being rebuilt around it,
so the hand keeps its place and what has already been read stays drawn.

**It arrives in parts, and each part is an act.** A forty-token arm is about a second even
with the prompt cache warm, which is too long to read as an arrival, so it is bought four
tokens at a time and the page reads the record again between them — the same free read a
hover makes, so an arm is drawn from the record whether the record or the model last answered
and no bought token reaches the page by a second route. Only one arm is rolled at a time and a
scroll during one is dropped: there is one writer, and `--parallel 1` is one prompt cache that
a draw from elsewhere would truncate.

**Looking does not move the text, and there is no exception to it.** The rule that picks the path
is a parameter of the read, so a rollout the reader merely pointed at would otherwise win the
branch point it hangs under — a fresh forty-token descent is taller than the standing one at
about a third of the positions in the trees here. Everything bought is bought where it stands,
and a purchase reaches the page as the arm in its own row and by no other route.

**What that protects is the comparison and not only the reader's place.** The rows at a position
are alternatives to each other, and the row the path already takes is one of them — so letting
*its* arm continue the column would read it in the column's measure while its rivals stay clipped
to a line, which puts the incumbent ahead of them for a reason that is about the page and not
about the model. An arm that would lengthen the text is the same arm either way; what differs is
how much room it is read in, and a comparison where one side is set in prose and the others in a
truncated line is not one. So every arm is read in the room a row gives it, and the room a row
gives an arm is what has to grow.

**What the rule still decides is where a reader arrives**, and a tree that has been read over is
a tree whose default path leans toward where the reading went. So the column falls behind the
record while a reader looks: a bought arm is live and in the tree, the column goes on showing the
path that was read before the purchase, and the next arrival may descend an arm nobody chose.
That is the rule doing its job rather than the page failing at its own, and the alternative was
worse — a page that keeps up with every purchase keeps up by choosing one. `docs/NEXT.md` has
what would change it and why nothing has.

**One list changes hands by moving the way the reader is moving, and nothing is spent while it
does.** A list already answering for the position under the pointer is left alone rather than
rebuilt, which is what keeps a row from being replaced by a copy of itself under the reader's
hand. When the position does change, the list arriving comes from the side the new one lies on
and the list leaving goes the other way, crossing over rather than blinking, and the one
leaving stops taking the pointer so that *what is hovered* keeps meaning the live one.
**Following a pointer across the column and arriving where it stopped are paced differently** —
the first is quick because the reader is not reading yet and the panel is only keeping up, the
second is slower because they stopped and a list that snapped into place would have to be
found again. A row may not be pointed at until the list has stopped, and the list asks who is
under it once it has, so a hand already resting on a row is answered rather than ignored.

What does not exist is everything past that: nothing shown beside a row unasked — what the
reader already grew there is still only a size — no depth limit
and so no view that presets one, and no way back to the boundary of an act to take one draw
again. **Writing at the caret is
not offered either**, though `create` takes a position and the composer takes a node: it would
replace the column with a box, and a request should appear where its result will. **The gesture
that sets a segment aside is a modifier-click and is the weakest part of this**, chosen because a
plain click is already spoken for above and not because it is right. What else exists is the core,
the llama.cpp adapter, the command line, and a throwaway probe that reads a static projection of
a tree and cannot write — which is what demonstrated laying previews out against real text.
