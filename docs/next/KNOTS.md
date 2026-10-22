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

**A knot is a run of forks along one row of the map.** A row is the line the drawing already
continues through each fork: the reader's path where there is one, and the heaviest child
otherwise. So knots on the path are formed from the path and move when it does, as what the scan
reads already does. A fork just below a knot, on a branch leaving it, is on another row: it is a
fork there or starts that row's own knot, and nothing about the first knot changes.

**Which forks on a row are one knot is a cut on the gaps between them.** Along one line, the
forks are depths, and a knot is a run of them with no gap wider than the cut. The cut has two
controls on the one mechanism:

- **a range**: every gap wider than so many tokens parts two knots;
- **a count**: the widest gaps part knots until there are so many places.

Either is stated by its effect, so many places from so many forks, and is a setting, per tree
and per reader, as the map's cut is.

**A knot has a cap on its span**, so a ladder, a fork every token or two for its length, is not
one knot as long as the ladder. The cap is the first cut; a ladder read in pixels says whether it
parts in the right places.

**The range follows the zoom's zones**, wide far from the thumb and narrow at the focus. It moves
one axis, the same way across the other, as the cut and the fisheye already do, and what a scan
returns to is already read in the window and not by leaf.

## How it is drawn

**A knot is drawn across its span and read at its top.** The axis holds tokens, so the forks in a
knot stay where they are along it and the knot is drawn as the stretch between its first and
last, fuzzed so that it reads as one uncertain place and not several exact ones. Every branch
leaving it is laid out and navigated as leaving at its top.

**Its branches stand across in the knot's order.** The first cut orders them by the depth they
leave at, then by the rank the map sorts a fork's children by now, which is consistent and
already drawn. The intended order is by **mean surprisal over a window** of the tokens each
branch took: how much the model preferred that path, which is a different question from how open
it was, which entropy reads. That order is the emergent temperature axis — near-greedy on one
side, hot further out, and authored text, which has no ranking, at the far end. The path stands
among the branches by its own surprisal over the same span. Other measures plug in beside it,
and one is the default.

**A knot is formed without regard to its branches' lengths.** That a one-token stub and a long
branch do not compare over one window is the order's concern and the layout's, and what is
scanned is already the subset the cut draws.

## Navigation

**Scanning across walks knots and not raw forks.** `docs/MAP.md`'s scan orders branches
depth-first; a knot's branches are siblings at it, and the depth-first order is taken there in
the knot's own order. Nothing else changes: the column, the rows panel at the caret and the
continuation rule read the raw tree, and later work on them chooses for itself between raw forks
and knots.

## What it reads

**`/map` sends the logprobs along each strand**, which the windowed order needs and which is a
surface read and not a core change. What that costs is measured once it is built, against the
largest tree, and moved to the server if it shows.

## Open

- **Whether the gap cut is the clustering wanted.** A convolution of the forks' depths along a
  row, with a kernel as wide as the range, gives a density whose high stretches are knots and
  whose shape is the fuzz to draw. Settled by drawing the gap cut on the comb and the trunk's
  limbs and seeing where it parts them wrongly.
- **Whether a knot's line is the path or the tree's own.** Formed along the path, a knot can
  re-form as the reader moves. Settled by navigating a root with knots on and noting where one
  changes under the reader; a fixed row is the alternative.
- **Range or count, as the default control.**
