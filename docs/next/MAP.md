# Map

**The map is the tree drawn as a shape, beside the text it holds, and its first cut is in.**
`docs/SURFACE.md`'s *The map* has what it is: one root's strands in the margin, ranked above and
below the reader's path, hair cut by its effect, and a strand pointed at as an arrival. This is
what follows it.

`scripts/shape.py` reads a tree's shape and `scripts/shape-sketch.py` draws it, including the
layouts not yet on the page, and what is below is what they showed on `data/daniel`.

---

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

## What follows

**The branched scrollbar, past its first cut.** `docs/SURFACE.md` has it drawn down the page in
tokens with the window in view as a thumb. What follows:

- **Lines, if tokens do not hold.** A paragraph with no newline in it is still many lines, so a
  thumb in tokens is long over dense text and short over sparse. Lines as the column wraps them
  would make the thumb the window's true share, measured on the path and estimated off it from
  characters and newlines, which wants both on the read. What it costs is that a strand's place
  moves when the column renders it, so a click lands somewhere that then shifts. Tokens come
  first, and lines only if reading with them says the thumb lies.
- **As broad as the view asks.** Width is what a broad tree costs, and pruning is how it is
  reclaimed; the first cut squeezes the columns to the margin instead.
- **Long empty stretches given less of the axis**, so the forks get the resolution. The thumb is
  what makes this thinkable: it says what the window holds whatever the axis does between forks.
- **The path's column leftmost**, with every branch extending away from the text, behind a switch
  beside the ranked one. It gives up the side a rank puts a branch on, and whether a reader keeps
  their bearings better with it is what the switch would ask.

**The position axis stays one quantity.** Tokens are a count of what is there, and a measure
squeezing or stretching it would cost the scrollbar its thumb. What the model was sure of goes on
as colour instead.

**Each channel has one owner**, as the column's do, so that anything drawn can be drawn alongside
anything else without one hiding the other. The column's stylesheet names its own: the inset
for the caret, the shadow for the glows, the ground for the overlay, the underline for the taker.
The map's:

| channel | carries |
|---|---|
| position | the structure: depth along, rank across |
| stroke colour | the layer chosen in the panel, on the column's measure and scale |
| stroke width | a strand's role: the path, a strand, hair |
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
of reworking it when a finer one comes.

**The trail moves to the halo when a layer takes stroke colour back.** There it is in one neutral
hue and in two or three steps told apart by intensity alone, and always on; fewer steps than now,
since walking it back and forward (`docs/NEXT.md` has it) shows any older order without losing
anything.

**Zoom, by shift and the wheel.** Shift with the wheel turned up zooms the map in by a step,
wherever on the page the pointer is, and turned down zooms it out. A step is a tenth of the
whole: from 100%, which is the whole tree as now and the default, up to 500% to start with. A
zoom is along the axis only, and bounded by the root at one end and the deepest tip at the other,
so the map never shows past either. Shift with the left button dragged on the map pans it.
Without shift, a drag on the thumb scrolls and a click arrives, as now.

- **The thumb is what a zoom is held about**, since it already has the window's bounds. Zooming
  in first brings the window back to the thumb wherever it was panned to, then zooms about it;
  zooming out holds wherever the reader panned. And the window follows the thumb as the column
  scrolls, so what the reader is reading stays on the map.
- **Across follows from what is left, and is not zoomed.** A strand wholly outside the window is
  not drawn, which takes a branch whose fork was clipped with it. Each strand left keeps the
  column the whole packing gave it, so nothing moves sideways against anything else, and the
  spacing is taken from the columns still in view, so fewer of them spread wider, as far as the
  clamp allows.
- **What is clipped says how much, and which way.** A rail along the map's edge shows the window
  against the whole depth, as the thumb shows the column against the path, and a strand running
  out of the window is marked where it leaves, so the edges a reader cannot see say what is past
  them.
- **It is what a small thumb on a long bar needs**, and what a tall root on a short window needs,
  which the first cut draws with its rows squeezed.
- **A measure on a zoomed map has a scale to match.** `docs/LAYERS.md`'s third scale takes its
  domain from what is in front of the reader, and a zoomed window is that for the map.
- **Shift and the wheel are free now and are claimed in full.** A wheel at the end of the column
  asks for a draw, and shift turns a wheel sideways in some browsers, so the gesture is taken
  before either and does neither.

**A preview under the pointer.** A strand held for half a second shows what it says, and a
click then moves the caret into it. The column is fixed by selection, so a preview is at most a
layer over it, which may cover the column but never changes what it holds: something local at
the strand, and `docs/SURFACE.md`'s reader state does not move under it.

**What changed in the column arrives as colour.** Any change to the tokens in the column, an
arrival or a draw, is laid out at once in the background's colour with the layers already applied.
The new caret glows, the point where the path diverged above it is plain if it is in view, and the
text in view fades in over a second.

**The layers' colours on it.** A strand coloured by a measure along it, as the column is: summed
entropy first, so a greedy stretch reads apart from an exploration. It is depth-bound in
`docs/LAYERS.md`'s sense — the recorded rows count and the rest of the mass does not — and
authored text has no ranking, so a prompt has no value on it. Then surprisal, and anything a layer
reads, chosen as a measure is chosen, from the same panel.

**The icicle.** Each strand a band as tall as the tokens below it: it says where the material
is, as the ranked layout says where the reader can go. A box drawn over it, or over the ranked
map, is a second way to zoom, to what the box holds.

**Pruning from the map.** Choosing strands and setting them aside, which is `delete` and needs
nothing else.

**Local maps.** A smaller map already zoomed to a knot, a trunk, or the tree down to some order of
branching. Zoom may be all that reading at different scales needs, and a local map is built only
if it is not. More than one root at once is the other direction.

**Knots.** Forks close enough along a path to be drawn as one place, which `data/daniel` has more
of than single forks. The first cut draws each fork where it stands, and zooming in is expected to
pull most of them apart.

**Other orderings across.** The rank is the first; weight, age or a measure are others, and the
switch is what makes them askable.

**The parting.** Waypoints has it as a read of where a set of paths part, and the map is that read
for every path at once. Whichever of the two is built first, the other is built on it.

## Open

- **Whether knots need drawing as one place once there is zoom.** Forks a token apart read as a
  smudge across a long tree at 100%. *Settled by zooming into root 1's.*
- **Whether zoom is enough to read at every scale.** If it is, local maps are never built.
  *Settled by navigating long roots with zoom alone.*
