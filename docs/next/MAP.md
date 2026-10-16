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

**Other axes.** Summed entropy first: it shrinks what the model was sure of and opens out where it
was not, so a greedy stretch is short and an exploration is long. It is depth-bound in
`docs/LAYERS.md`'s sense — the recorded rows count and the rest of the mass does not — and
authored text has no ranking, so a prompt is no width on it at all. Then surprisal, and anything
summable a layer reads. The axis is chosen as a measure is chosen, from the same panel.

**The layers' colours on it.** A strand coloured by a measure along it, as the column is.

**The icicle, and zooming by drawing a box.** Each strand a band as tall as the tokens below it:
it says where the material is, as the ranked layout says where the reader can go. A box drawn
over either zooms to what it holds, and the zoomed map is where details are picked between. It is
also what a tall root on a short window needs, which the first cut draws with its rows squeezed
and its path's row kept in the middle.

**Pruning from the map.** Choosing strands and setting them aside, which is `delete` and needs
nothing else.

**Local maps, bounded where the tree is.** A knot and what is below it, the trunk the reader is on
and what leaves it, or the tree down to some order of branching: each is the same drawing at its
own scale, and the global map is the case with no bound. More than one root at once is the other
direction.

**Knots.** Forks close enough along a path to be drawn as one place, which `data/daniel` has more
of than single forks. The first cut draws each fork where it stands.

**Other orderings for y.** The rank is the first; weight, age or a measure are others, and the
switch is what makes them askable.

**The parting.** Waypoints has it as a read of where a set of paths part, and the map is that read
for every path at once. Whichever of the two is built first, the other is built on it.

## Open

- **Whether knots are drawn as one place.** Forks a token apart read as a smudge on tokens and
  may not on entropy. *Settled by looking at it on both axes.*
- **What a local map is bounded by.** A knot, a trunk and an order of branching are three
  candidates and each cuts a different tree well. *Settled by building the first and reading
  trees of each kind with it.*
