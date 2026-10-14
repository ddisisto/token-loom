# Map

**The map is the tree drawn as a shape, beside the text it holds.** The column is where all
attention lands, and it shows one path. What it cannot show is where that path stands in the
tree, and what else the tree holds besides — waypoints mark positions to come back to, and still
leave the reader without a picture of the whole. The map is that picture, and it is a way in:
pointing at a place in it is an arrival, as taking a waypoint is.

**It is first because it is already demonstrated.** `scripts/shape.py` reads a tree's shape and
`scripts/shape-sketch.py` draws it, and what is below is what they showed on `data/daniel`.

---

## What a tree looks like

**Long runs, with the forks in clusters.** `data/daniel` is 159,339 nodes under 14 roots. Taken
down to runs without a fork in them it is 3,755 of them, and the leaf runs have a median of 37
tokens. The runs between forks have a median of 2, so forks arrive in bursts, and joining those
within 4 tokens of each other makes 1,319 forks into 509 places.

**Around two fifths of it is fringe.** 1,798 of its 2,436 leaves are runs drawn greedily past
their first token, which is what a hover's arm leaves, and they hold 41% of the tokens. Without
them and without the other short leaves, what is left is 405 forks and 508 leaves.

**The same few shapes recur:**

- a **trunk**, the path of heaviest children, up to 5,000 tokens;
- **arms**, long rewrites leaving early: three of 2,000–3,000 tokens leave the largest root's
  trunk at tokens 162 and 163, one knot;
- **ladders**, a fork every token or two along a path, each with a short drawn leaf beside it;
- **fans**, many children at one position: one has 20, 19 of them greedy arms off its rows and
  some of those 800 long;
- and the **fringe** of hover arms at almost every fork.

**Roots are different kinds of tree, and the kind is visible at a glance.** A *writing* tree has
a long trunk with arms and ladders along it; a *broom* is many medium draws from its first
hundred tokens or so, 17,556 tokens reaching only 883 deep; a *line* holds four fifths of itself
or more on the trunk; a *fan* is 43 leaves 78 deep. Forks sit early: nearly half of them are in
the first fifth of a tree's depth.

## Words

These are the map's own, and they move to `docs/SURFACE.md` when it is built. *Segment* is that
document's, for the shortest run of nodes whose bytes decode, and is not one of them.

- **Strand**: a maximal run of nodes each with one child, opened at a root or at a child of a
  fork and closed at a fork or a leaf. The map's unit.
- **Knot**: forks close enough along a path to be drawn as one place.
- **Hair**: a leaf strand the map does not give a row of its own, drawn as a tick off the fork
  it leaves. The strand that is a fork's heaviest child is never hair, so a tree is never drawn
  without the path it mostly is.
- **Skeleton**: what is left with the hair taken out.
- Trunk, arm, ladder and fan, as above.

## What the map draws

**x is a quantity summed from the root, and says which.** Tokens by default, with a switch to log.
The quantity is replaceable: summed entropy shrinks what the model was sure of and opens out
where it was not, and that is the second axis wanted. It is depth-bound in `docs/LAYERS.md`'s
sense — the recorded rows count and the rest of the mass does not — and authored text has no
ranking, so a prompt is no width on it at all. An axis that says what it holds is the rule; one
squeezed to fit is not.

**y is local, and is the ranking.** At each fork one child continues the row: the one on the
reader's path where there is one, and otherwise the heaviest. The others stand above it if the
model ranked them higher and below it if lower, the nearest rank nearest, each packed as close to
its fork as the drawing allows. So a strand above the reader's path is one the model liked
better, and a strand far below is one it hardly considered. Nothing ranks the root's children
against each other. What a global order made of only local ones looks like is the open part of
this, and the sketches are where to see it first.

**Hair is cut by its effect.** What counts as hair is today greedy past its first token, or
short, and both will move: arms drawn at a position will not all be greedy once the hover draws
under other settings. So the cut is stated as what it does to the drawing — rows kept, share of
the tokens set aside — and is the reader's to move, per tree and per purpose.

**What it marks:** the reader's path, the waypoints, what is set aside, and a knot or fan as a
dot sized by how many strands leave it.

## The first cut

**One root's map, as the background of the right margin.** The rows and `#read` sit over it when
they are open, and dismissing them gives it back. Where it finally lives is not decided; this is
where it can be lived with first.

**The skeleton in the ranked layout, on tokens with a log switch.** Hair as ticks, up or down by
the same rule as strands. The reader's path straight through it and marked, which is where the
column is.

**Pointing at a strand is an arrival.** The path through the point in the column and the caret
on it, as taking a waypoint does. Waypoints are drawn where they stand.

**The read is the record's, and the packing is the page's.** Strands, their extents on the
chosen axis, the rank each had at its fork and whether it is hair are a read: the record half in
`core/reads.py` and the rest in `surface/reads.py` beside segmentation. Which row a strand takes
is arithmetic over those extents and nothing else, so it is a page module with a driver under
`scripts/`, and it is checked without a browser.

**Nothing new is written.** Every write the map will make — pruning, taking a branch — is a
verb already, so it is inside *No write may be surface-only* from the start.

## What follows

**Other axes.** Entropy first, then surprisal and anything summable a layer reads. The axis is
chosen as a measure is chosen, from the same panel.

**The layers' colours on it.** A strand coloured by a measure along it, as the column is.

**The icicle, and zooming by drawing a box.** Each strand a band as tall as the tokens below it:
it says where the material is, as the ranked layout says where the reader can go. A box drawn
over either zooms to what it holds, and the zoomed map is where details are picked between.

**Pruning from the map.** Choosing strands and setting them aside, which is `delete` and needs
nothing else.

**Local maps, bounded where the tree is.** A knot and what is below it, the trunk the reader is on
and what leaves it, or the tree down to some order of branching: each is the same drawing at its
own scale, and the global map is the case with no bound.

**Other orderings for y.** The rank is the first; weight, age or a measure are others, and the
switch is what makes them askable.

**The parting.** Waypoints has it as a read of where a set of paths part, and the map is that read
for every path at once. Whichever of the two is built first, the other is built on it.

## Open

- **What the ranked layout does globally.** Each fork orders only its own children. *Settled by
  looking at it on trees of each kind.*
- **What is hair, by default.** Stated as an effect, its default is whatever a reader leaves it
  at. *Settled by use, with the switch.*
- **Whether knots are drawn as one place.** Forks a token apart read as a smudge on tokens and
  may not on entropy. *Settled by looking at it.*
- **How the map and the column stay in step.** The column moves with the caret and the map
  could follow, or hold still until it is asked. *Settled by use.*
- **Where it lives.** The margin is where it starts, and Arms wants room there too. *Settled by
  use, alongside Waypoints' nav with room.*
