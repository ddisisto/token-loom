# Waypoints

**A waypoint is a position the reader chose to be able to find again.** Exploring around something
worth keeping is what loses it: a few draws at one position, a few rows taken, and the exact path
back is in the tree and nowhere in the reader's head. `delete` can carve it out after the fact,
by setting aside everything that is not it, but only where the reader deleted as they went. The
record can say *this one does not matter* and has no way to say *this one does*, and a waypoint
is that half.

**The nav is where they stand.** The work so far has gone to the column and the drawer, and the
nav is still the list of roots it began as. Waypoints make it a map of the tree the reader has
marked, which makes this the epic that moves the nav on.

---

## What a waypoint is

**A node, and nothing else is needed to find the path to it.** A node is a token in a context,
so its ancestry is the path, and a waypoint stores no more than the id. Nothing about it can
drift from the record.

**A span is two of them, and needs no more than that.** Between a node and any descendant of it
there is exactly one path, so a stretch of text worth marking is a pair: where it starts, and
where it ends below that. A waypoint is the span that starts and ends at one node. The first cut
builds only that case, and what it stores has room for the other.

**It carries when it was set, from the first one written.** Nothing reads it yet. A time not
recorded at the start cannot be recovered later, and that is the one piece of metadata the first
cut cannot leave for later. What a waypoint marks has a second age, which is when its node was
drawn, and that age is already in the record on the act that made it.

## The first cut

**Set and cleared at the caret, and taken from the nav.** A key toggles one at the caret, and the
token it marks is drawn much as the caret is drawn, but still reads as distinct while the caret
sits on it. A waypoint at a token inside a segment marks the whole segment, which is the mapping
the caret already makes. Taking one from the nav is an arrival: the path through it in the
column, the caret on it, and the continuation rule deciding below it as it does everywhere.

**Each one is named by the text leading up to it, with its own token picked out.** The text
before a position is what lets a reader recognise it, which is the same reason a root is named
by what it opens with. Names the reader writes come later, and nothing in the first cut stands
in their way.

**The hierarchy needs no new read.** A waypoint stands under its root, and under any other
waypoint that is its ancestor. Two waypoints that part somewhere unmarked show as siblings, and
the place they part is not shown. Drawing it is the next step.

**It lives in the browser, keyed by the tree.** Per-origin storage would hand one tree's
waypoints to the next tree served on the same port, so the key is the tree's own: `tree.json`'s
`created`. A copied tree keeps its ids and so keeps its waypoints, which is correct.
Navigation belongs to the page, so this is within *No write may be surface-only*. It is also what
makes the first cut one that can be lived with before the format is asked for anything.

**What it has to show is a waypoint whose node is gone.** A node set aside after it was marked
is not a waypoint to drop silently. It is shown as set aside, which also says the reader set
aside something they had marked.

## What follows

**A nav with room.** A row is a line of text either side of the token it marks, and at a
sixth of the window that is a few words. The nav should open toward a third of the window on
hover and be dragged to any width up to the whole window, the way the drawer is opened and
held below the column. What has to be decided first is whether it moves the column or covers
it. The column, the edge and the heat line are all placed from where the nav ends, so moving
them is a reflow on every drag, and covering them leaves a reader unable to see the text and
the map of it at once.

**The waypoints on the path, while the reader moves along it.** Once the arrival's flash
is over, nothing says the reader is still on a path a waypoint marks, or how far they have
come from it. The nav could keep saying so as the reader scrolls: which waypoints are on the
path in front of them, and how far each is from the caret, above or below. What is open is
the measure (tokens, lines, or the rows and the column scrolling together) and the channel
(the glow's strength, a position along the row, or a figure).

**The parting.** Given a set of nodes, the skeleton of their paths is where they agree, printed
once, and where they part. With that the nav shows where two waypoints parted. It is the same
read that stacked arms need at the scale of tokens, so whichever of the two comes first builds
it, and it is arithmetic over ids with a driver of its own.

**The caret in the address.** A fragment naming the caret's node is correct while one server
serves one tree, and with it back and forward retrace where the reader has been, which may answer
much of what loses a reader. Every caret move replaces the entry and only an arrival adds one, or
every click becomes a step back. A tree in the address as well needs a server that opens trees
on request, and that is its own piece of work.

**Waypoints in the tree.** In the record a waypoint is a write, so it needs a verb, and it is a
`docs/CORE.md` change: a sixth act, or something kept beside the acts. What use of the first cut
shows it needs is what decides which. Browser storage is the right place until that is known.

**Deleting around what is kept.** A draw repeated at one position leaves every earlier draw
live. A rule that sets aside what the reader moved past, unless it is kept, would clean that up.
It waits on waypoints being in the tree: a write that depends on browser storage deletes
something different once the storage is cleared.

**A book's apparatus, as it earns its place.** Names, colours, a highlighter matching a ribbon's
colour over a span, marginalia, tags. Each is metadata on a waypoint or a span and none needs the
shape to change.

## Open

- **Which ordering the nav shows.** Structural is the default, chronological is the second. *Settled
  by having both and a switch.*
- **Whether age is shown on another channel.** The glow already means *new to you*, and
  `docs/SURFACE.md` asks what else it may mark. A waypoint that dims as it ages, or one that glows
  again on arrival, are both candidates. *Settled by use, once waypoints exist.*
- **How the caret and a waypoint read on one token.** Both mark a token, and each has to read as
  itself when they coincide. *Settled by looking at it.*
- **What arriving at a waypoint does below it.** The rule's descent is the default, and the path
  the reader was on when they set it is the alternative. That path is not stored, and storing it
  would make the waypoint a span by another name. *Settled by use.*
