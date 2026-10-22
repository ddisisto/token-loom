# Knots

**Forks close enough along a line to be one place, straightened out so that they are one place.**
Repeated sampling from the same stretch of a path makes them as a matter of course, and drawn as
separate forks they move the drawing and the scan for differences nobody is reading. A knot is
one place in the drawing and in navigation, and the branches leaving it are siblings there.

## What the tree shows

`docs/MAP.md`'s *What a tree looks like*: the strands between forks have a median of 2 tokens, so
forks arrive in bursts, and joining those within 4 tokens of each other makes `data/daniel`'s
1,319 forks into 509 places. Three limbs of 2,000–3,000 tokens leave the largest root's trunk at
tokens 162 and 163, which is one knot drawn as two forks. `data/claude`'s Moths root has a comb of
30 adjacent rank-2 forks, which is a ladder, and what a knot must not swallow whole.

## What a knot is

**A knot is forks joined by being close: each within range of the knot of the nearest fork above
it.** Taken in order along the axis, a fork is judged against everything a knot already holds
short of it, so along a row and on into the branches leaving a knot are the same rule: a branch
that forks again close below a knot is the same knot, and one knot is never drawn inside another.
A fork whose branches are all hair is no part of one, so a fringe of stubs does not chain a trunk
together.

**A knot has a cap on its span**, so a ladder, a fork every token or two for its length, parts
into knots no longer than the cap rather than one as long as the ladder.

**The range is a share of the tokens in view, and the cap is all of them**: 15% on a tall window
and up to half on a short one, where anything finer is too small to point at. Both are stated by
their effect on the bar, so many places of so many forks.

**A tree's knots stand still.** They are cut from the tree alone, with no path in them, when it is
first drawn at a rung of the cut, at the range the window gives then, and again only when the tree
or the rung changes. Reading, scrolling, arriving and zooming move nothing about them, so a knot
is the same knot whichever way the reader came to it.

## How it is drawn

**A knot is one bar**, along its span from its first fork to its last and across every row a
branch leaving it stands on, in place of those branches' links. The axis holds tokens, so each
branch still starts where it really left; what runs between the knot's forks is drawn as the bar
and not as rows of its own, which is what lets the path through it be one row whichever branch it
leaves by.

**Every branch leaving a knot is a sibling at its top**, and stands above or below by its rank
against what the tree's own row took where it really left. Which side a branch is on is the
tree's and not the path's, so stepping from branch to branch moves only the one on the path's row.

**Its branches stand across in the knot's order**: by the depth they leave at, then by rank. The
intended order is by **mean surprisal over a window** of the tokens each branch took: how much the
model preferred that path, which is a different question from how open it was, which entropy
reads. That order is the emergent temperature axis — near-greedy on one side, hot further out,
and authored text, which has no ranking, at the far end. Other measures plug in beside it, and one
is the default. That a one-token stub and a long branch do not compare over one window is the
order's concern, not the knot's.

**Pointed at, a knot shows its structure.** Each branch leaving it is lit where it diverges and
along its first few px, and where the knot is on the path, the column glows across its span.

## Navigation

**A click on a knot arrives at it and zooms in about it**: on its row at its first fork, the window
centred there, two steps in.

**Scanning across walks a knot as one place.** `docs/MAP.md`'s scan orders branches depth-first; a
knot's branches are siblings at its top, in the knot's own order. Nothing else changes: the column,
the rows panel at the caret and the continuation rule read the raw tree, and later work on them
chooses for itself between raw forks and knots.

## What it reads

**`/map` sends the logprobs along each strand**, which the windowed order needs and which is a
surface read and not a core change. What that costs is measured once it is built, against the
largest tree, and moved to the server if it shows.

## Open

- **What a knot looks like opened.** A click zooms in about one, and the knot stays a bar; what of
  its forks is shown within the zoom is the detailed view, and it is designed by looking at one.
- **Whether the gap is the clustering wanted.** A convolution of the forks' depths, with a kernel
  as wide as the range, gives a density whose high stretches are knots and whose shape is the
  fuzz to draw. Settled by reading the comb and the trunk's limbs and seeing where knots part
  wrongly.
- **A count as the control**, the widest gaps parting knots until there are so many places,
  beside the range.
