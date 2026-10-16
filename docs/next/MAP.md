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

**The branched scrollbar.** Turned so that paths run down the page, with lines of the column as
the quantity along them, the map is a scrollbar for the whole tree. The reader's path is the
column it scrolls, the window in view is the thumb on it, and the caret and the waypoints are marks
inside and along it. Taking a branch moves the thumb onto another column. The packing does not
change: it places strands along one axis and in integer rows across it, and turning the drawing is
a transpose of the plan.

- **Lines and not newlines.** A paragraph with no newline in it is still many lines, so the
  quantity is lines as the column wraps them. On the reader's path that is measured: the page has
  the geometry and hands it to the arithmetic as arguments. Off the path nothing is rendered, so
  a strand's length is estimated from its characters and its newlines at the current measure,
  which wants both on the read. Arriving on a branch makes its estimate a measurement, and the
  drawing says which is which.
- **The thumb is dragged to scroll**, and a strand clicked is still an arrival.
- **As broad as the view asks.** Width is what a broad tree costs, and pruning is how it is
  reclaimed.
- **Its first cut sits beside the browser's own scrollbar** and does not replace it, and the map
  drawn across stays behind a switch so the two can be read against each other.

**The position axis stays one quantity.** Tokens across and lines down are both counts of what is
there, and a measure squeezing or stretching it would cost the scrollbar its thumb. What the model
was sure of goes on as colour instead.

**The layers' colours on it.** A strand coloured by a measure along it, as the column is: summed
entropy first, so a greedy stretch reads apart from an exploration. It is depth-bound in
`docs/LAYERS.md`'s sense — the recorded rows count and the rest of the mass does not — and
authored text has no ranking, so a prompt has no value on it. Then surprisal, and anything a layer
reads, chosen as a measure is chosen, from the same panel.

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

**Other orderings across.** The rank is the first; weight, age or a measure are others, and the
switch is what makes them askable.

**The parting.** Waypoints has it as a read of where a set of paths part, and the map is that read
for every path at once. Whichever of the two is built first, the other is built on it.

## Open

- **Whether knots are drawn as one place.** Forks a token apart read as a smudge across a map of
  a long tree, and may share a line of a scrollbar outright. *Settled by looking at both.*
- **Where the path's column stands in the scrollbar.** In the middle with the ranking either
  side of it, as the map across has it, or nearest the text with every branch extending away,
  which reads more like a scrollbar and gives up the side a rank puts a branch on. *Settled by
  drawing root 1 both ways.*
- **Whether a scrollbar of lines hands the thumb a usable size.** Branches running past the end of
  the path set the bottom of the scale, so a short path can be a small thumb on a long bar.
  *Settled by reading root 1 with it.*
- **What a local map is bounded by.** A knot, a trunk and an order of branching are three
  candidates and each cuts a different tree well. *Settled by building the first and reading
  trees of each kind with it.*
