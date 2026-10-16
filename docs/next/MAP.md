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

**Arriving reads as straightening.** The reader's path is always one straight column and every
branch is offset from it, so taking a branch is that branch straightening out. Three pieces make
that seen rather than inferred:

- **A hovered strand traced back to the root**, lit along every strand it hangs from, so the shape
  it would take and exactly where it leaves the reader's path are both in front of them.
- **The re-packing eased** over a quarter of a second rather than jumping, with clicks held until
  it lands.
- **A preview under the pointer.** A strand held for half a second shows what it says, and a click
  then moves the caret into it. The column taking the strand's path until the pointer leaves is
  one way; something local at the strand is another and smaller. A preview is not a selection, so
  `docs/SURFACE.md`'s reader state does not move under it.

**What changed in the column arrives as colour.** Any change to the tokens in the column, an
arrival or a draw, is laid out at once in the background's colour with the layers already applied.
The new caret glows, the point where the path diverged above it is plain if it is in view, and the
text in view fades in over a second.

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
- **Whether the drawing holding still matters more than where the path stands in it.** The
  drawing starts at the margin's edge, so the path's column moves across whenever an arrival
  changes how much is ranked above it. *Settled by moving around root 1 with it.*
- **Whether the scrollbar hands the thumb a usable size.** Branches running past the end of the
  path set the bottom of the scale, so a short path can be a small thumb on a long bar.
  *Settled by reading root 1 with it.*
- **What a local map is bounded by.** A knot, a trunk and an order of branching are three
  candidates and each cuts a different tree well. *Settled by building the first and reading
  trees of each kind with it.*
