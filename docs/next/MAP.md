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

**Zoom is a cut that depends on where the reader is.** It should feel like zooming and is not a
magnification: shift with the wheel turned up shows more of the tree around the thumb and less
of it far away, and turned down evens that out again, down to the cut as it is now. This is a
degree-of-interest view, after Furnas's fisheye views: how much of a strand is drawn depends on
how far it stands from the focus, and the wheel sets how much that distance counts. The hair cut
is already a threshold, the same everywhere; zoom makes it vary with distance.

- **The focus is the thumb**, which already has the window's bounds, and it stays the thumb: a
  zoom is always about what is being read, and scrolling the column moves it. There is no pan.
- **The cut is `docs/SURFACE.md`'s ladder**, whose last rungs fold whole subtrees, since hair is
  only ever a leaf and cannot thin out the distance enough. The bar's rung is the base every zone
  starts from.
- **The axis is split into zones about the focus, mirrored either side of it.** The focus zone
  is the thumb and a focal distance either side; past it are rings, each wider than the last by a
  ratio. A step of the wheel moves the focus zone one rung finer and each zone further out a
  scaling's worth of rungs coarser than the one inside it, so with three zones and a scaling of
  one the middle keeps the base. Turned back to none, every zone is on the base. Three zones
  start it, and more is a finer fisheye with nothing else changed. The focal distance is a share
  of the axis, so it is a band of the map of one size whatever the tree's depth. All three are
  constants first, and a control comes when using it says which one is reached for.
- **A strand is in the zone of its nearest point**, so a limb that left the trunk early and runs
  alongside the thumb is near, and a subtree folds only when all of it is far. Which zone its
  fork is in is the other way to read it, and it is behind a switch beside the cut: what is
  wanted may turn on the structure in view.
- **The root and the tip are walls.** A zone is not moved off a wall; what lies past it is empty,
  and what is not drawn there is room across for the focus. **The tip is the reader's path's.**
  With no steps the axis is the whole tree; from the first step it runs from the root to the
  path's end wherever that is short of the tree's deepest, so the thumb is the column's share of
  the map, and strands that run past the end are clipped at the edge and marked there. A short
  path in a long tree makes that first step a sharp one, and that is accepted.
- **Otherwise the axis does not move.** It stays a count in tokens, so the thumb stays honest.
  What changes is which strands have a column of their own: more near the focus, fewer far from
  it, and the room across that freeing columns far away leaves goes to those near it.
- **Distance is along the axis only, to start.** How many forks a strand is off the reader's path
  is the other half of it, and the first of what an interest might take in beside distance.
- **The bar says what a step does**, as the cut already is stated: how many strands are drawn
  near the focus, and how many far.
- **Each step moves the packing**, and the glide carries it so it reads as motion, on a pace of
  its own: a second and more for every notch would be far too slow.
- **Shift and the wheel are claimed in full.** A wheel at the end of the column asks for a draw,
  and shift turns a wheel sideways in some browsers, so the gesture is taken before either and
  does neither. A notch is a step and a fine wheel's movement adds up to one.
- **Resolution along the axis is not what this changes.** Forks a token apart still stand a token
  apart. If knots still smear, giving the focus more of the axis is the long empty stretches
  given less of it, above, and is decided apart from this.
- **A measure on a map like this has a scale to match.** `docs/LAYERS.md`'s third scale takes its
  domain from what is in front of the reader, and the strands near the focus are that.

The axis magnified about the thumb, with a pan, a rail and the edges marked where strands ran out
of the window, was built first and is kept on the `zoom-svg` branch: it worked, and was not what
was wanted.

**A preview under the pointer.** A strand held for half a second shows what it says, and a
click then moves the caret into it. The column is fixed by selection, so a preview is at most a
layer over it, which may cover the column but never changes what it holds: something local at
the strand, and `docs/SURFACE.md`'s reader state does not move under it.

**What changed in the column arrives as colour.** Any change to the tokens in the column, an
arrival or a draw, is laid out at once in the background's colour with the layers already applied.
The new caret glows, the point where the path diverged above it is plain if it is in view, and the
text in view fades in over a second.

**The icicle.** Each strand a band as tall as the tokens below it: it says where the material
is, as the ranked layout says where the reader can go. A box drawn over it, or over the ranked
map, is a second way to zoom, to what the box holds.

**Pruning from the map.** Choosing strands and setting them aside, which is `delete` and needs
nothing else.

**Local maps.** A smaller map already cut to a knot, a trunk, or the tree down to some order of
branching. Zoom may be all that reading at different scales needs, and a local map is built only
if it is not. More than one root at once is the other direction.

**Knots.** Forks close enough along a path to be drawn as one place, which `data/daniel` has more
of than single forks. The first cut draws each fork where it stands. Zoom thins what is around a
knot and does not pull its forks apart, so whether they are drawn as one place is still open.

**Other orderings across.** The rank is the first; weight, age or a measure are others, and the
switch is what makes them askable.

**The parting.** Waypoints has it as a read of where a set of paths part, and the map is that read
for every path at once. Whichever of the two is built first, the other is built on it.

## Open

- **Whether knots are drawn as one place, or given more of the axis.** Forks a token apart read
  as a smudge across a long tree, and zoom thins what is around them without spreading them.
  *Settled by zooming into root 1's and reading whether they still smear.*
- **What interest a strand has beside its distance along.** Distance out from the path, weight,
  the waypoints in it, how recently it was on the trail, or nothing. *Settled by starting with
  distance along alone and reading where it folds something wanted.*
- **Whether a strand is near by its nearest point or by its fork.** *Settled by the switch, on
  the trees that have limbs.*
- **What the focal distance, the ratio and the scaling start at.** *Settled by zooming long roots
  and short ones, and only then by a control.*
- **Whether zoom is enough to read at every scale.** If it is, local maps are never built.
  *Settled by navigating long roots with zoom alone.*
