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

**The record holds no cursor.** Any live node can be written at, and continuing is writing at the
end of the path being read. Where the reader stands is the page's, as *The path* has it.

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

**One composer, and it opens at the caret**, for the reason Writing gives for the placeholder: a
request appears where its result will, and the caret is where every other act already lands.
Writing at a leaf and several segments back read the same under it — anything done at the caret
stands instead of everything below it and hangs off what was there, which is the shape taking a
ranked branch already has. **The draw key under a modifier opens it, with the token after the
caret pre-filled and selected** — the one the rows are alternatives to — so the first keystroke is
the replacement, and a token the model never ranked is reached the way any text is written. What
is below moves along to make room rather than going, being what the new text will stand instead
of, and the composer is set in the prose's own face and measure. The act is `create` at a live
node: a sibling of what stood there, with the old branch and everything below it untouched.

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

## The draw

**Two settings change what kind of act a draw is, and they are on the page; the rest are set once
a session and are under it.** Length and heat are what is moved per draw — sampling the model, or
running the greedy path out where that is cheap to read. The recording bounds, the rest of the
chain and the backend are in a drawer beneath the footer.

**Length is the room below the text.** The space under the last line is where the next draw lands
and how far past the text a reader scrolls before the gesture fires, so it reads as a promise of
how much is coming: read with a shallow room and a deep one, the shallow one invited shorter draws
and the deep one longer, and neither was better. A faint line left of the column sets it, and its
point's height is where the last line will stand when a scroll draws. The room is a share of the
height above the footer, so whatever the footer takes, every position keeps its place on the line.

**Its ends park and the band between them draws, at fixed lengths.** At or below 30% and at or
above 85% a scroll draws nothing, which leaves two ways to read with no gesture writing: near the
foot of the screen, or with the tail high on it. Between them are six log-spaced lengths from 8
to 256 tokens, and they are not derived from the text beside them — a length matching the room
exactly would need tokens per line, which varies with what is drawn and would move under the hand.
Parking wins over an armed caret, and the key that draws at the caret uses the length parked or
not. Length 1 has no place on the line, being how *Rankings* deepens a ranking rather than a
decision about how much to read, and the command line makes it.

**How near a scroll is to drawing is drawn on the same line.** A counter-point stands at the last
line's height and meets the point where a scroll at the end draws. Within a fifth of the room the
two pulse in opposite phase, faster as they close, and within 8% the point grows as it does under
the pointer. The pulse follows the reader's movement and dies away in a second and a half, so a
page left at its end shows the two met and still rather than pulsing while it is read. An armed
caret shows them met, the next scroll down drawing from anywhere; a parked page shows the point
alone. The pulse stops the moment a draw is asked, which is when the placeholders *Writing*
describes take over at the caret.

**Heat is the line between the text and what governs the draw.** It runs across the column at the
footer's top, greedy at the left and 2.5 at the right in steps of 0.05, with its point drawn along
a scale from deep blue through white at 1 to deep red at 2. Zero is an end to slam into rather
than a value to find, which makes greedy a place on the dial — and the only one: `top_k` starts at
2, one candidate being greedy at any heat. The text fades out behind the line so it stands clear
of what scrolls under.

**The drawer lifts on a look and holds on a pull.** Hovering the footer lifts it over the text
after a beat and it falls after another, so passing over does neither and a look at a setting
moves nothing. Dragging the heat's line, or the grip at its right end, more than 80px up holds the
drawer where it is let go — shut or full within 80px of either end, scrolling between — and only a
held drawer takes room from the text. A drag inside that distance is the heat's alone, and a click
on the grip opens or shuts it.

**Each parameter is a line with a point, on a scale that spends the line where the value is
sensitive**: log for `min_p`, `top_k` and `record_rows`, and a log of what is left below 1 for the
two masses. **Off is the end where a sampler does nothing, and there it is left out of the
request** rather than named at a value that does nothing, so an act's `params` say what was asked.
A required bound is sent at its inert value instead, which for `record_mass` is 1.

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
draws. Across sources it does not: a node several models have ranked holds several rankings, and
one order over their union would sit rows side by side that were never alternatives to each other.

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

### Where the rows stand

**Density stays behind intent, and the toggle is not what enforces it.** A ranking can run to
dozens of rows at a position the model was unsure of, and none is shown until that position is
asked about — which pointing does, one position at a time. That is the rule, and it holds
whether or not the rows are switched on. The switch starts **on**: a reader working a path wants
to know what else was there at the position they are at, and reaching for a toggle first makes
that a decision instead of a glance. What the column draws from the rows without being asked
about a position is `docs/LAYERS.md`.

**The rows stand beside the column, at the line they are about.** The reading column is half of a
container two measures wide and the other half is empty; a ranking answers *what else was here*
at a position, and it is the only thing that answers it, so there is one place to look and no
second answer to keep in step. They sit against the column rather than over the window, so they
scroll with the text they belong to.

**Hovering is a caret that has not been committed.** With the rows shown, moving over a segment
shows what pointing there would give — by the same rule, the ranking at the node before it — and
the click that places the caret is what commits it. So a reader sweeping the column reads the
alternatives along it without moving from where they are, and nothing new is named to allow it.

**A hover's list cannot be reached, and the click is the way to it.** Leaving the segment takes
the rows with it, so a reader moving towards rows they only hovered arrives after they have gone.
That is what the preview being a preview costs: the rows that stay are the caret's, and a click
on the token asks for exactly those. What it does not excuse is being illegible — a list that
went away on the approach and a list that was never there look the same — so each list is drawn
as what it is. The caret's is solid and carries the accent the caret itself is marked with, as
the root the reader is in is; a hovered one is dashed and has none. **Said in how it is drawn
and not in a line of words**, which would be read on every list opened and wanted on none of
them after the first.

**Which token a list is about is marked in the column.** A position sits before a token, so the
list is rival to the segment *after* the caret, and neither the caret nor the pointer says which
that is. It is the token the row drawn as *the one taken here* is, said at the other end of the
list — one derivation, because a column and a list that disagreed about which token the position
was choosing between would both look right. **The caret's own mark stays under a hover**, drawn
back rather than put out, since a reader following a hover across the page is further from the
caret than at any other time.

**One list changes hands by moving the way the reader is moving, and nothing is spent while it
does.** A list already answering for the position under the pointer is left alone rather than
rebuilt, which is what keeps a row from being replaced by a copy of itself under the reader's
hand. When the position does change, the list arriving comes from the side the new one lies on
and the list leaving goes the other way, crossing over rather than blinking, and the one leaving
stops taking the pointer so that *what is hovered* keeps meaning the live one. **Following a
pointer across the column and arriving where it stopped are paced differently** — the first is
quick because the reader is not reading yet, the second slower because they stopped and a list
that snapped into place would have to be found again. A row may not be pointed at until the list
has stopped, and the list asks who is under it once it has, so a hand already resting on a row
is answered rather than ignored.

**A ranking read earlier stops being true when an act lands, and not because the rows changed.**
Rankings only grow, so what a position holds keeps for the life of the page; what does not keep
is which rows a node has realised.

### How a row is drawn

**The row is the token, and both of its axes are drawn as sizes.** One is the model's opinion of
the position, drawn as a bar that is the row's own ground rather than a thing behind it, so
whatever is hung in a row later is drawn over the bar and a list filling with text still reads
as the distribution it is. How the bar is scaled is in What is not decided here. Neither axis is
written out beside the row: a column of figures is read down rather than across, and it would
stand against the one thing in a list that is not a measurement. The numbers are in the row's
title, which is the one place a reader asks about a row rather than two.

**The other axis is what the reader made of the position.** That is the downward family read
across the siblings at one position instead of down a path — an overlay and a ranking transposed,
the identity `docs/LAYERS.md` states from the other side — and it is drawn as how much room the
token takes. A row's value is fixed the moment it is recorded and its weight moves with every
act, so the two disagreeing is the whole of what there is to see: **where the heaviest row is not
the top one is where the reader steered.** Over the 53 forks of `data/continuations` that is 17
of them, which `docs/SPINE.md` records along with what it does and does not settle.

**Which downward measure weighs the rows follows the overlay, and rests on size.** They are one
quantity, so a reader comparing along the path and across it reads the same thing — and where
the panel has no answer, because nothing is chosen or what is chosen looks up, the rows still
have the axis. A measure read against its parent is not one of these: across siblings its argmax
is *take the smallest arm*, which is the same reason it generates no rule. The weight is what has
been grown from a token over the heaviest row of its source, drawn in two channels and not one,
because the reading is usually the log of a count and a log over a log is narrow: an arm three
times another draws two pixels above it on size alone. It is the descent the path read asks for,
anchored at the node the rows belong to, and costs 3–5 ms at an ordinary position and 20 at the
root of a fourteen-thousand-node tree. Log keeps a small explored arm legible beside a large one;
linear states the ratio and puts the small one on the floor beside the arms nobody ever took.

**A row weighs nothing for two reasons and they are not one.** Nothing realised it, so there is
no node to measure; or what realised it is set aside and the toggle is hiding it. Both sit at the
floor of the axis and only one of them is somewhere the reader has already been, so the row says
which.

### Arms

**A row carries what follows it, set after the token.** *What else was here* and *where each of
those goes* are then read in one place at one glance, so previews and the rankings are one
mechanism and the half of the container the rows stand in pays for it. What follows a row some
node realised is in the store already, under the rule that selecting it would follow. What
follows the model's own choice from there is the reference arm `docs/SPINE.md` names, and it too
is read from the record rather than rolled: a greedy rollout merges onto what an earlier one
wrote, so the descent that never leaves the top row is what asking again would produce. **So
pointing at a row draws its arm at once, costs no inference and takes no lock**, and what is
already paid for is not paced, since a wait before it would charge the reader for looking.

**It is one line and nothing in the list moves.** The arm sits on the row's own line after the
token and leaves by the right edge of the page rather than wrapping or scrolling; newlines are
escaped as the rows escape theirs. A list a reader is scanning must not move the next row out
from under the pointer about to reach it, which is also why the price below sits out of flow.
`docs/NEXT.md` has the layout this is provisional against — where the arm takes the space beside
the column it gets the page's height, and the break comes back.

**An arm says why it stopped, and only one of the reasons is a price.** It filled the room it was
given, and says so, since a silent truncation reads as *that is all there was*; the record has no
more, and a roll would extend it; the top row continues under a flag the reader set; two sources
ranked the position and there is no one top row to follow; or the model ended it, by cycling into
an attractor or by EOS. The record tells these apart — `docs/SPINE.md` has which and why — and
collapsing them would tell a reader that an exhausted model and a finished document are the same
event, the discipline `docs/LAYERS.md` applies to a position with no value. **Only *the record
has no more* can be bought**: a roll under a flag or at a two-source position merges onto what the
record holds and writes nothing, so reading *stopped* as *for sale* would charge for what cannot
be delivered.

**A pulse in the left margin is that price and not a progress bar.** It marks a row where reaching
further would cost inference — one with nothing realised under it, or one whose arm the record
ran out of short of the length — so a row without one is free to look at and the column of them
is what a reader scans to find where spending begins. It follows the pointer and not the reading,
appearing on arrival rather than when an answer comes back.

**The arm belongs to the row and the price belongs to the pointer**, and nothing else divides what
the two do. An arm is drawn wherever its row is — when it lands, whether or not the hand stayed,
and again in a list built later, which goes up already carrying what has been read from that
position. What a reader does with two of them is compare them, and a comparison they can look
away from and still have is the one worth drawing. So pointing at a row only ever says *there is
more here*, and a row the record has no arm for says it by showing a price and nothing else.

**Resting on a price is what pays it.** Pointing and paying are one gesture held for different
lengths of time, so a reader never has to decide what a row is before looking at it: they point,
they read what the record had, and where it ran out under a pulse they can stay. What is bought is
proportional to what was looked at — crossing a row on the way elsewhere buys nothing, moving on
stops the spending at the part in flight, and a row already rolled is not rolled again. It is
what shows the model's preference wherever the reader looks, and the one thing that shows a
repetition loop, which `docs/SPINE.md` has no measure able to mark. It spends against the page's
rule that a way of looking is free, and two things keep that small: *Hidden* has a stub born set
aside, so what is bought enters neither the live path nor the rule, and rows at one node share
the path above them, so a second rollout there reprocesses a single token.

**A row nothing realised is bought the same way, and the fork comes first.** It is two acts rather
than one and the `realise` is free, so resting on a row the record has never been down makes the
node and then rolls from it. They are one gesture because they answer one question — *what does
the model say here* — and a reader comparing several continuations at one position wants each
fork made by looking at the row rather than by committing to it first. The row changes kind under
the pointer rather than the list being rebuilt around it, so the hand keeps its place and what has
already been read stays drawn.

**It arrives in parts, and each part is an act.** A forty-token arm is about a second even with
the prompt cache warm, which is too long to read as an arrival, so it is bought four tokens at a
time and the page reads the record again between them — the same free read pointing makes, so an
arm is drawn from the record whether the record or the model last answered and no bought token
reaches the page by a second route. Only one arm is rolled at a time and a scroll during one is
dropped: there is one writer, and `--parallel 1` is one prompt cache that a draw from elsewhere
would truncate.

**What a purchase costs in exactness is stated rather than hidden.** A rollout is a pure function
of the position only cold, and buying under a pointer is the warm case — `docs/SPINE.md` carries
the adapter's measurement of what a partial cache hit moves. So **the row's token is a fact and
its continuation is advisory**: the token is read from the stored ranking and cannot drift, while
what follows it is what the model would do from there under the cache state that obtained. A row
says which of the two it is offering, because a reader taking a token and a reader taking a
continuation are relying on different things.

**Looking does not move the text, and there is no exception to it.** The rule that picks the path
is a parameter of the read, so a rollout the reader merely pointed at would otherwise win the
branch point it hangs under — a fresh forty-token descent is taller than the standing one at about
a third of the positions in the trees here. Everything bought is bought where it stands, and a
purchase reaches the page as the arm in its own row and by no other route.

**What that protects is the comparison and not only the reader's place.** The rows at a position
are alternatives to each other, and the row the path already takes is one of them — so letting
*its* arm continue the column would read it in the column's measure while its rivals stay clipped
to a line, which puts the incumbent ahead of them for a reason about the page and not the model.
So every arm is read in the room a row gives it, and the room a row gives an arm is what has to
grow.

**What the rule still decides is where a reader arrives**, and a tree that has been read over is a
tree whose default path leans toward where the reading went. So the column falls behind the record
while a reader looks: a bought arm is live and in the tree, the column goes on showing the path
that was read before the purchase, and the next arrival may descend an arm nobody chose. That is
the rule doing its job rather than the page failing at its own — a page that keeps up with every
purchase keeps up by choosing one. `docs/NEXT.md` has what would change it and why nothing has.

### Taking a row

**Clicking a row nothing realised is the `realise`, and that is its primary meaning.** The row
exists to be taken, and the only one of the three that needs an act is the one nothing has taken
yet. What it writes is a node and no ranking, so the caret lands on the sibling it made with
nothing below it, and the arm it was chosen against is drawn subdued below — derived from the
rule at the caret's parent, as *The path* has it. Asking for the continuation is the act it always
was, and the caret is armed so that reading on is what asks.

**What a row shows of its continuation follows the rule that taking it would**, so it is a
truthful prefix of what the reader gets and not a separate rendering of the same tree. Taking a
row whose continuation already exists writes nothing: it is a path the store holds, so the gesture
is a selection.

**Taking a row is taking as much of it as the reader points at.** Once an arm has landed its
nodes are ordinary nodes, so clicking inside it places the caret inside it: the token takes the
token, a click into the continuation takes it up to there, and the end takes all of it — a prefix
of any length, with no gesture of its own. Underneath, a row whose stub exists is brought back
rather than made — `undelete` where the flag sits, and a `delete` after the cut where the reader
stopped short of the end, so the record says what happened: *I took this token and set aside what
the model did next.*

**A closed continuation is marked where it closed, and the mark is the way back.** *Nothing has
run here* and *this was shut deliberately* end the same way with the toggle off — the text simply
stops — and the difference is between somewhere to spend and somewhere to reopen. One mark says
which, at the end of the column's path and at the end of an arm cut short of its cap, and it is
the same boundary that stands between live text and hidden when the toggle is on: with it off
there is nothing drawn after it, and taking it draws what was set aside rather than restoring it.
So the reader sees what they closed before deciding to reopen it, and nothing a click does puts
back a node they put away. **The mark costs a view and never an act**, which is what lets it sit
in a panel a pointer summons.

## Overlays

What is drawn over the column — overlays, their scales and domains, the downward family, and the
mark that says who put a token there — is `docs/LAYERS.md`.

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

**A request appears where its result will.** A row of placeholders stands straight after the
caret, one for each token of the draw's length — not a spinner elsewhere on the page, and not
optimistic text. A longer draw is a longer row and a longer wait, so the row is where a reader
learns what length costs.

**What lands is marked as what landed.** Its segments take the placeholders over one after
another, pushing what is left of the row ahead of them, and a draw cut short leaves some over,
which go when its last segment is in. The run they make glows as one band along each line, with
nothing between one token and the next, holds a beat past the last arrival, sinks to a remnant and
goes out — so draws in quick succession leave a trail. It is shadow and not ground, which is left
to the layers that use it. **The pace is the page's and not the model's**: an act arrives whole,
so spreading it out invents a timing the record does not hold, and it is capped so that a long
draw is no slower to read than a short one. What it is for is a reader who looked away finding
their place, and a draw makes *where was I* and *what is new* the same question; the mark answers
the second.

**The placeholder is read rather than remembered.** `docs/CORE.md` commits a `generate` act before
the model is called, and an act with no terminator is a generation in flight, so what the
placeholder stands for — its length included — is in the record. A page opened while one is
running draws it, and a page reloaded mid-generation does not lose it.

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

- **Whether a branch with no ranking behind it is marked.** A `create` at a node that already has
  a live child makes a fork the model had no part in, and the record holds the source that says
  so. Marking it puts a second kind of mark in a column *Between forks, nothing is drawn* keeps
  bare; not marking it leaves a reader to open the ranking to find out. What settles it is a
  tree with both kinds of fork in it, read for whether the difference is wanted at the fork or
  only inside the rows.
- **Whether the length stays at the edge.** *The draw* has it as the room below the text, and
  that has not been lived with long. What would move it is the edge's line turning out to be
  hunted for, or the parked ends going unused.
- **Whether the draw's settings survive a reload.** None do, every act carrying its own. Settled
  by whether a reader finds themselves setting the same ones again after every load.
- **Which continuation rule.** Longest, first, last, most-recently-used, cumulative open time —
  each is defensible and they are comparable only by use. `longest` is the first implementation
  because it is the one member that needs nothing but the tree; ties bite only for it, and are
  insertion order. What settles it is reading one tree under two of them, which is why the path
  read takes the rule as a parameter. A rule that reads what the reader did is what puts reader
  state in *Nothing written is only here*.
- **How a magnitude is drawn.** A number, a bar, a ramp, a share of the recorded mass. Each
  reads differently at a sharp position than at a flat one, and a real ranking is often one and
  sometimes the other. The bar drawn now is each row against the top row of its source, which
  keeps a flat position from reading as a page of empty bars and says nothing about how much
  was recorded; a bar against the recorded mass says the second and loses the first. A number
  beside the bar is out, for the reason *How a row is drawn* gives. What settles it is drawing a
  real tree several ways.
- **What a node two sources ranked should show.** Refusing is what the surface does and not an
  answer. Their disagreement may be the interesting quantity, in which case the overlay is a
  measure over sources rather than one that has to pick among them. What settles it is a tree two
  models have both ranked, which nothing has yet produced.
- **Keyboard.** A ranking's rows are already the natural arrow-key sequence, but what the whole
  reader does under a keyboard — moving between positions, into a ranking and along it, taking
  a row in part or whole, back out without losing one's place — is unsettled. Resting on a row,
  which is how an arm is bought, has no keyboard equal at all. *Keyboard and mouse first* is the
  target and only half of it exists. What settles it is working a real tree
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
- **What the glow marks besides a draw.** *Writing* has it on what a draw brought. Taking a row,
  switching branches and showing what was set aside also put text in front of the reader that was
  not there a moment before, and none of them has placeholders or a pace to go with it. Marking
  whatever is new to the view would cover them all and makes a long re-derived path light up
  whole after a shallow row is taken, which is either noise or the point. What settles it is
  marking them and reading a tree with them marked.
- **Everything past the first gesture.** Comparison across branches, and what the instrument does
  that a reader could not get from reading one path at a time. Nothing settles this but use.

---

## Status

**What is built is the body above, and `docs/LAYERS.md` for what is drawn over the column.**
`tokenloom serve` holds one tree and serves the three reads, the path predicate and the five acts
over HTTP, with the page at the root so the two arrive from one origin. The page starts roots and
names them, sets one path as prose with a caret that every act at a position lands on, continues
it by a scroll at the end or a key at the caret, writes at the caret through a composer, takes a
ranked row or reads and buys its arm, and sets the draw beside the text.

**What does not exist is everything past that**: nothing shown beside a row unasked — what the
reader already grew there is still only a size — no depth limit and so no view that presets one,
and no way back to the boundary of an act to take one draw again. **The gesture that sets a
segment aside is a modifier-click and is the weakest part of this**, chosen because a plain click
is already spoken for and not because it is right. What else exists is the core, the llama.cpp
adapter, the command line, and a throwaway probe that reads a static projection of a tree and
cannot write — which is what demonstrated laying previews out against real text.
