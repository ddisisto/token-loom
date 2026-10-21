# The map

**The column holds one path as text, and the map holds everything else as structure.** The text
is only ever one thing: a single path, set as prose. Where that path stands in the tree, what else
the tree holds and how to get there is structure, and it is drawn beside the text rather than
woven into it. Reading branches against each other — side by side, or as a diff — is built on that
split, and never by putting a second text in the column.

**The tree under the current root, drawn as a shape in the half of the window the column leaves
empty.** Pointing at a place in it is an arrival. The rows open over it where they are on, their
own ground covering it there. It is a way of looking with a switch beside the others, and it is
drawn from the half's edge nearest the text.

`scripts/shape.py` reads a tree's shape and `scripts/shape-sketch.py` draws it, including layouts
not on the page, and *What a tree looks like* is what they showed on `data/daniel`.

## What a tree looks like

**Long runs, with the forks in clusters.** `data/daniel` is 159,339 nodes under 14 roots. Taken
down to strands it is 3,755 of them, and the leaf strands have a median of 37 tokens. The strands
between forks have a median of 2, so forks arrive in bursts, and joining those within 4 tokens of
each other makes 1,319 forks into 509 places.

**Around two fifths of it is fringe.** 1,798 of its 2,436 leaves are stubs, and they hold 41% of
the tokens. Without them and without the other short leaves, what is left is 405 forks and 508
leaves.

**The same few shapes recur:**

- a **trunk**, the path of heaviest children, up to 5,000 tokens;
- **limbs**, long rewrites leaving early: three of 2,000–3,000 tokens leave the largest root's
  trunk at tokens 162 and 163, one knot;
- **ladders**, a fork every token or two along a path, each with a short drawn leaf beside it;
- **fans**, many children at one position: one has 20, 19 of them stubs off its rows and some of
  those 800 long;
- and the **fringe** of stubs at almost every fork.

**Roots are different kinds of tree, and the kind is visible at a glance.** A *writing* tree has
a long trunk with limbs and ladders along it; a *broom* is many medium draws from its first
hundred tokens or so, 17,556 tokens reaching only 883 deep; a *line* holds four fifths of itself
or more on the trunk; a *fan* is 43 leaves 78 deep. Forks sit early: nearly half of them are in
the first fifth of a tree's depth.

## The drawing

**Down the page by default, and across behind a switch.** Drawn down, the map is a scrollbar for
the whole tree: the tokens in view are a thumb on the reader's path, dragged to scroll the column.
Drawn across, it is the same plan turned, with the thumb along the path's row. The two are kept so
that each can be read against the other on any tree.

**A strand is a maximal run of nodes each with one child**, opened at a root or at a child of a
fork and closed at a fork or a leaf. It is the map's unit, since a tree grown by drawing is long
runs with nothing on them and the forks carry all of its shape. `docs/SURFACE.md`'s *segment* is
the display unit and is not this.

**Along a strand is a quantity summed from the root, and says which.** It is tokens, and a strand
runs from where its fork stands to where it ends. An axis that holds a quantity is the rule; one
squeezed to fit what the drawing has room for is not.

**Across is the ranking, and it is local.** At each fork one child continues the row: the one on
the reader's path where there is one, and otherwise the heaviest. The others stand on one side of
it if the model ranked them higher and on the other if lower — above and below across the page,
left and right down it — the nearest rank nearest, each packed as close to
its fork as the strands already placed allow. A child nothing ranked stands below every one that
was. So the reader's path is one straight row, a strand above it is one the model liked better at
the fork it leaves, and a strand far below is one it hardly considered.

**Hair is a leaf the map does not give a row of its own**, drawn as a tick off its fork, to one
side or the other by the same rule, and **a fold is a whole subtree drawn so**: one tick reaching
as far as what it holds and as heavy as its tokens, which a click takes down its heaviest line,
and which says so when a waypoint is folded inside it. The **skeleton** is what is left. What is
cut is one ladder of rungs the reader moves, finest to coarsest: nothing; a hover's stubs, in
`docs/SPINE.md`'s sense; with them, leaves no longer than 4, 8, 16, 32 and 64 nodes; and with
those, subtrees holding no more than 256 tokens, 1,024, and any. The cut is stated by what it does
to the drawing, as strands kept and the share of the tokens drawn as ticks, because what the same
numbers do differs by tree and by what the reader is after. The axis is the whole tree whatever is
cut. The child that continues a fork is never cut, so a tree is never drawn without the path it
mostly is.

**What it marks**: the reader's path and the caret on it, the waypoints wherever they stand, what
is set aside where the toggle shows it, and a fork three or more strands leave as a dot sized by
how many.

**What the pointer is over is one place on both.** The column and the map hold the same positions
along the reader's path, and a pointer is only ever over one of them, so where it is is marked on
each: a glow on the segment in the column, and a tick across the path on the map, both in a colour
of the pointer's own. A segment out of view keeps its glow out of view, and the tick against the
thumb says where it is.

**A strand pointed at is traced back to the root**, lit along every strand it hangs from, so the
shape it would take and where it leaves the reader's path are both in view before it is taken.

## Zoom

**Zoom is a cut that depends on where the reader is**, and not a magnification: shift with the
wheel turned up draws more of the tree around the thumb and less of it far away, and turned down
evens that out again, down to the bar's cut. It is a degree-of-interest view, after Furnas's
fisheye views. **The focus is the thumb** and stays the thumb, so a zoom is always about what is
being read, scrolling moves it, and there is no pan. **The axis is split into zones about it,
mirrored either side**: the thumb and a focal distance either side, then rings each wider than
the last by a ratio. A step moves the focus a rung of the ladder finer and each zone further out
a scaling's worth of rungs coarser than the one inside it, so with three zones the middle keeps
the bar's rung and the far one is what folds. The focal distance is a share of the axis, a band
of the map of one size whatever the tree's depth. **A strand is in the zone of its nearest
point**, so a limb that left the trunk early and runs alongside the thumb is near, and a subtree
folds only when all of it is far; a switch puts it in the zone its fork is in instead.

**The root and the tree's end are walls.** A zone is not moved off a wall, and what is not drawn
past it is room across for the focus. The axis does not move: it is the whole tree at every step,
so a long path and a short one beside it keep their places while the reader compares them. Zoomed
in, the bar says how many strands are drawn in each zone, from the thumb out, beside what the cut
does. A step glides, quicker than an arrival does. A scroll the reader makes is followed as it
goes, and one the page makes — an arrival carrying the column to its caret — glides there from
wherever the drawing stands, so a jump to somewhere shaped differently reads as one movement.
Shift and the wheel are claimed in full, being neither the draw a wheel at the end of the column
asks for nor the sideways scroll some browsers make of it, and a fine wheel's movement adds up to
a notch.

## Moving through it

**Pointing at a strand is an arrival.** The column reads the path through that strand and puts
the caret on the segment holding the node under the pointer, as taking a waypoint does. The
reader's path is always one straight row and a branch is offset from it, so taking a branch is
that branch straightening, and the drawing moves there over a second rather than jumping, with
what is new fading in. A click while it moves is not taken, since it would land on where
something is going rather than where it is.

**Ctrl and an arrow across the map moves to the next branch over, at the same place along.**
Left and right where the map runs down the page, up and down where it runs across, and Ctrl,
shift and the wheel the same; a text box keeps the keys for itself. Each move is an arrival, so it
glides, and the thumb and the window stay where they were while only the branch changes.

- **The order is depth-first**, with a fork's children in the order the map stands them across:
  ranked higher first, nothing ranked last. It is the tree's and not the path's, so it is the same
  whichever way the reader scans and wherever they land, and a branch shaped nothing like the last
  cannot reshuffle what comes next. The children's order is the part another ordering across
  would replace.
- **What is scanned is every branch the map draws that reaches the focus**: each leaf the cut
  leaves a row of its own, whose end is at or past the start of the thumb's focal zone. A limb
  that left the trunk early and runs beside the thumb is in, and a stub that ended far above it
  is not, so the zoom widens and narrows what is scanned with nothing of its own.
- **It lands at the caret's depth**, or at the branch's end where that is short of it, so a short
  stub ending in the focus is scanned among the longer branches and not passed over. With no
  caret it lands at the middle of the window, and the token it lands on keeps its place there.
- **It stops at either end of the order** and says so, so a sweep has edges.

**The paths a reader has left stay on the map, as a trail.** The trail is the last twenty paths
they were on in this tree, newest first, kept in the browser as waypoints are, so it follows a
reader between visits and is drawn again on the way back in. The four most recent paths behind
the current one are drawn, each in a colour of its own that steps away from the accent through
red as it ages, so each can be told from the next; a strand takes the colour of the most recent
it was on, and the change is eased over the same glide. A path that only grew past the last one
takes its place rather than being another, so moving along a path or a draw extending it leaves
nothing behind. A point
on nothing is a point on nothing, and releases the caret as before. The thumb is taken and not
pointed at: dragging it scrolls, the column's own scroll is not a reader reading on and asks for
nothing, and the caret follows the window once it is let go, as after any scroll.

**What it is drawn from is read once per root and per act**, and once again when the toggle or
the waypoints change. Moving along a path or arriving on another redraws it from what is held,
and the packing is laid again around the new path.

## The axis

**The position axis stays one quantity.** Tokens are a count of what is there, and a measure
squeezing or stretching it would cost the scrollbar its thumb. What the model was sure of goes on
as colour instead. **What changes is the function from tokens to the axis**, and its extent never
does: the axis is the whole tree at every step, so nothing moves while the reader compares a
short path with a longer one.

**Zoomed in, the axis is a fisheye about the thumb, on the zoom's own zones.** Each zone's share
of the axis is the tokens it spans, weighted: the focus by a gain for each step, the middle by
one, and the far zone by the gain's inverse, so a step gives the focus more of the axis and takes
it from far away. Within a zone the function is linear, so it is continuous and only rises, and
the thumb, the caret and a click are drawn and read through it and stay honest. **A wall needs
nothing of its own**: a zone past the root or the tree's end spans no tokens and has no share,
and what it would have had goes to the zones that do. So a thumb near the root opens into the
room the root side does not need, and forks a token apart in the focus stand as far apart as the
gain makes them, which is what a knot is read with.

- **One gesture, both halves.** A step of shift and the wheel moves the cut and the gain
  together, so it keeps feeling like one zoom, and a switch on the bar turns the gain off and
  leaves the cut.
- **Packed on the straight axis and drawn through the fisheye.** The packing measures its gap
  in px, so packing through the fisheye would move rows as the thumb moves; packed straight, a
  scroll moves no strand across and only stretches what is there. Far strands squeezed together
  may then crowd on a row, where the cut is coarse anyway.
- **A scale says what the axis is doing**: dim ticks along the map's outer edge at round counts
  of tokens, drawn through the same function, so they spread where the axis is magnified and
  bunch where it is squeezed, and the thumb's length can be read against them.
- **The zones' bands are markers on that scale**, later, for the reader to drag.

Long empty stretches given less of the axis, so the forks get the resolution, is the same
function read off the tree rather than off the thumb.

## Channels

**Each channel has one owner**, as the column's do, so that anything drawn can be drawn alongside
anything else without one hiding the other. The column's stylesheet names its own: the inset
for the caret, the shadow for the glows, the ground for the overlay, the underline for the taker.
The map's:

| channel | carries |
|---|---|
| position | the structure: depth along, rank across |
| stroke colour | the layer chosen in the panel, on the column's measure and scale |
| stroke width | a strand's role — the path, a strand, hair — and what a fold holds |
| dash | set aside |
| a halo under the stroke | the reader: what the pointer is over, and the trail |

**The path needs no colour of its own once a layer is on**, since it is the one straight column
and position already says so. Until a layer exists the accent and the trail keep stroke colour,
which is the case with nothing chosen.

**The layers' colours on it.** A strand coloured by a measure, as the column is: summed entropy
first, so a greedy stretch reads apart from an exploration. It is depth-bound in
`docs/LAYERS.md`'s sense — the recorded rows count and the rest of the mass does not — and
authored text has no ranking, so a prompt has no value on it. Then surprisal, and anything a layer
reads, chosen as a measure is chosen, from the same panel. A value is addressed to a span, which
`docs/LAYERS.md` calls its unit, and **the strand is the first unit**: one colour a strand.
An act's span and each token's are the later ones, a token's smoothed wherever a strand has more
tokens than pixels, and everything else is built to work at a strand's grain first, at the cost
of reworking it when a finer one comes. Zoomed in, the scale to match is `docs/LAYERS.md`'s third,
whose domain is what is in front of the reader, and the strands near the focus are that.

**The trail moves to the halo when a layer takes stroke colour back.** There it is in one neutral
hue and in two or three steps told apart by intensity alone, and always on, since walking it
back and forward shows any older order without losing anything.

## What is not decided here

**Questions prose cannot close.** Each says what would settle it, and moves into the body above
when it is settled.

- **What the ranked map does to a whole tree.** Each fork orders only its own children, and what
  a global picture made of only local orders looks like is open. Settled by reading it on trees
  of each kind — one long writing, one many draws from near its start, one a fan of greedy arms.
- **What the cut is by default.** It is a hover's stubs and leaves of sixteen nodes or fewer,
  which is a first number, and stubs will stop being one thing when a hover draws under other
  settings than greedy. Settled by use, with the ladder: the default is whatever a reader leaves
  it at.
- **Where the zones stand and how they step.** Three zones, a focal distance of a twentieth of
  the axis, rings three times wider each, a rung a step and a gain of two a step are first
  numbers, and how many steps there are is as far as the cut or the gain still changes
  something. More zones is a
  finer fisheye with nothing else changed. Settled by zooming long roots and short ones, and only
  then by a control.
- **Whether a strand is near by its nearest point or by its fork.** Settled by the switch, on the
  trees that have limbs.
- **What interest a strand has beside its distance along.** Distance out from the path, weight,
  the waypoints in it, how recently it was on the trail, or nothing. Settled by starting with
  distance along alone and reading where it folds something wanted.
- **Whether zoom is enough to read at every scale.** If it is, a local map — one already cut to a
  knot, a trunk, or the tree down to some order of branching — is never built, and more than one
  root at once is the other direction. Settled by navigating long roots with zoom alone.
- **Whether a scan always steps to the strand drawn next to it.** The packing nests a subtree on
  its side of its fork wherever it fits, so cousins can stand interleaved where the depth-first
  order has them apart. Settled by scanning a broad root and noting where a step lands somewhere
  unexpected.
- **Whether the map holds still.** It is laid again around every arrival, so the shape moves
  whenever the path does, and it is the path that stays put. A map that held its shape while the
  reader moved through it is the other way to have it. Settled by use.
- **Where the rows stand while the map has the margin.** They open over it, which is easy to
  dismiss and covers what is under them. Settled by placing them somewhere else and reading with
  both.
- **Whether the thumb is in tokens or in lines.** A paragraph with no newline in it is still many
  lines, so a thumb in tokens is long over dense text and short over sparse. Lines as the column
  wraps them would make it the window's true share, measured on the path and estimated off it from
  characters and newlines, at the cost of a strand's place moving when the column renders it.
  Settled by reading with tokens and finding the thumb lies.
- **How broad the drawing is.** Width is what a broad tree costs, and pruning is how it is
  reclaimed; the drawing squeezes its columns to the margin instead. Settled by trees too broad
  to read squeezed.
- **Which side the path's column stands on.** Leftmost, with every branch extending away from the
  text, gives up the side a rank puts a branch on. Settled by a switch beside the ranked layout,
  read for whether a reader keeps their bearings better with it.
- **Which orderings across.** The rank is the first; weight, age or a measure are others, and a
  switch is what makes them askable.
- **What a strand held under the pointer shows.** Held for half a second, what it says, and a
  click then moving the caret into it. The column is fixed by selection, so a preview is at most a
  layer over it, local at the strand, and the reader state does not move under it. Settled by
  building it and reading whether it is looked at.
- **How a change to the column arrives.** An arrival or a draw laid out at once in the
  background's colour with the layers applied, the new caret glowing, the point where the path
  diverged plain if it is in view, and the text in view fading in over a second. Settled by
  reading arrivals with it.
- **Whether an icicle earns a place.** Each strand a band as tall as the tokens below it says where
  the material is, as the ranked layout says where the reader can go; a box drawn over either is
  a second way to zoom, to what the box holds. Settled by drawing one beside the ranked map.
- **Whether pruning happens from the map.** Choosing strands and setting them aside is `delete`
  and needs nothing else. Settled by pruning a broad tree in earnest.
- **Where paths part.** Waypoints has it as a read of where a set of paths part, and the map is that
  read for every path at once; whichever is built first, the other is built on it.

---

## Status

**What is built is the body above, except two things designed and not built**: the layers'
colours on the strands, and the trail moving to the halo.
An axis magnified about the thumb, with a pan and a rail, was built and set aside and is on the
`zoom-svg` branch.
