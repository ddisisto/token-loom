# Reed

**Forks close together, combed straight: a tree on the inside, a comb on the outside.** On a
loom the reed is the comb that keeps the warp side by side, evenly spaced and straight. Here a
reed is the same for the paths leaving a cluster of forks: one input, every path out of it
standing beside the others as a straight tooth, and the cluster itself not drawn. Repeated
sampling from one stretch of a path makes these clusters as a matter of course, and drawn fork
by fork they move the drawing and the scan for differences nobody is reading.

## What the tree shows

`docs/MAP.md`'s *What a tree looks like*: the strands between forks have a median of 2 tokens, so
forks arrive in bursts, and joining those within 4 tokens of each other makes `data/daniel`'s
1,319 forks into 509 places. Three limbs of 2,000–3,000 tokens leave the largest root's trunk at
tokens 162 and 163, which is one place drawn as two forks. `data/claude`'s Moths root has a comb
of 30 adjacent rank-2 forks, which is a ladder, and what a reed must not swallow whole.

## Combing is a dial between the map's two axes

**The range trades along for across.** At nothing, the map is the raw tree, every fork at its
depth and the structure all along the axis. At its widest, the whole root is one reed: every path
side by side across and no structure along at all, which is a list of paths. Between, the dial
moves as much branching from one axis to the other as the reader wants. It is a way of looking,
like the cut and the zoom, records nothing, and belongs as much at hand as they are.

**The dial runs the whole way**, from nothing through doubling ranges to the depth of the tree,
where each root is one reed and every leaf a tooth: one comb, one set of alternatives. Any stop
short of that would be arbitrary, and none is added until a tree shows it is needed. The range is
stated by its effect, so many places of so many forks, on the bar beside the cut's, and it starts
at 4 tokens, from the evidence above.

**At a setting, the reeds stand still.** They are combed from the tree alone, with no path in
them, and again only when the tree changes or the reader turns the dial. Reading, scrolling,
arriving and zooming move nothing about them, so a reed is the same reed whichever way the reader
came to it.

## What a reed holds

**A fork belongs to the reed of the nearest fork above it when it is within range of that reed.**
Taken in order along the axis, each fork is judged against everything a reed already holds short
of it, so along a row and on into what leaves a reed are one rule: a branch that forks again close
below a reed is the same reed, and no reed is ever drawn inside another. A fork whose branches are
all hair is no part of one, so a fringe of stubs does not chain a trunk together.

**A reed has a cap on its span**, four times the range, so a ladder parts into reeds no longer
than the cap rather than one as long as the ladder. At the dial's widest there is none.

## Its teeth

**A tooth is one way out**: the whole route from the reed's input to a strand leaving it, which is
the whole of what distinguishes that path inside the reed. What ends inside a reed is a tooth like
any other, and the cut treats it as it treats any short leaf.

**The teeth stand in a fixed order**, which is the tree's and not the path's: out from the tooth
the tree's own row takes, its ranked continuation, the others above or below it by their rank
against what the row took where each really left. Among themselves they
stand by where they left and then by rank. The intended order is by **mean surprisal over a
window** of the tokens each tooth took: how much the model preferred that path, which is a
different question from how open it was, which entropy reads. That order is the emergent
temperature axis — near-greedy on one side, hot further out, and authored text, which has no
ranking, at the far end. That a one-token stub and a long branch do not compare over one window is
the order's concern.

## How it is drawn

**A reed is a rail at its top**, across every tooth's row and as thin as a strand, so it reads as
a fork with width at any zoom. Each tooth is drawn from the rail as its whole route, the stretch
the teeth share drawn in each of them, so the teeth are straight and parallel however they really
left, and the strands between the reed's forks are not drawn on their own. The axis still holds
tokens: a tooth's tokens stand where they are along it, and the ones it shares with the others
are drawn again beside them.

**The path is one straight row through reeds as through any fork.** At a reed the path's tooth
goes straight on from the input, and the other teeth stand out from it in their order, each
further out than the last, so whichever tooth the path takes the teeth keep their order and
their spacing.

**The drawing is held by the reed the window is at, and what is above it moves.** Across the
page, the map keeps the tooth in slot 0 of the last reed on the path at or above the window
where it stood, so a step from one tooth to another leaves every tooth in place and slides the
input, the path above it and what hangs from that across to meet the tooth taken. With no reed
above the window, it keeps the root where it stood. Rows that fit stay inside the margin, and
rows that do not are cut off at the edges, with the edge marked, and move only to keep the
path's row where the window is in view.

**Pointed at, a reed shows its teeth**, each lit where it leaves the rail, and where the reed is
on the path, the column glows across its span.

## Navigation

**Scanning across a reed steps from tooth to tooth in order, and the teeth hold still**: what
moves is above the reed, the path sliding across to the tooth taken. `docs/MAP.md`'s depth-first scan takes a reed's teeth as siblings at its input, in the
reed's order.

**A click on a reed arrives at its input and zooms in about it**: the window centred there, two
steps in.

Nothing else changes: the column, the rows panel at the caret and the continuation rule read the
raw tree.

## Where it goes

**Combing is self-similar, and every range is one cut through one hierarchy.** Forks joined by
distance form a dendrogram, and a range is a height to cut it at, so a tooth can hold a smaller
reed at a finer range and turning the dial walks the hierarchy rather than reshuffling it. That is
what makes a range that varies along the axis possible — fine about the thumb and coarse far
from it, on the zoom's own zones — and none of it is built here.

**Every piece of decoded text is read against what else**, and a reed is that question drawn at a
scale. The rows panel at the caret is the finest reed there is: one input, every ranked row a
tooth side by side, and a hovered row's stub that tooth's continuation. At the widest range the
whole root is one reed and every path a tooth, and the column is one of them, the thread picked
and stretched out to be read. So the map, the panel and the column are one object at three
ranges.

**Two dials may be the map's whole control.** The cut says what is too small to give a row and
the range what is too close to tell apart, and a stub on the map is then only a short leaf near a
fork: cut by its size or combed into a tooth, with no rung of the cut of its own. The stub as
`docs/SPINE.md` has it, the reference arm, is a measurement and is untouched by this.

**The loom is a fabric loom only so far.** Its warp is linear and its output many identical
threads made into cloth. Here the warp branches, so a reed is needed wherever it does and of
whatever width it does, and what comes off is not cloth: any one thread, read as text, and the
branching itself, read as a map. Both are true at once, which is what the two halves of the page
are.

## What it reads

**`/map` sends the logprobs along each strand**, which the windowed order needs and which is a
surface read and not a core change. What that costs is measured once it is built, against the
largest tree, and moved to the server if it shows.

## Open

- **Which gesture turns the dial**, beside shift and the wheel for the zoom.
- **What a reed looks like opened.** A click zooms in about one and it stays a rail; what of its
  inside is shown within the zoom is designed by looking at one.
- **Whether plain forks hold still too.** An arrival still straightens the path at every fork not
  in a reed. Settled by reading with combing on at the default range and noting where that moves
  more than it should.
- **Whether the gap is the clustering wanted.** A convolution of the forks' depths, with a kernel
  as wide as the range, gives a density whose high stretches are reeds. Settled by reading the comb
  and the trunk's limbs and seeing where reeds part wrongly.
- **A count as the control**, the widest gaps parting reeds until there are so many places,
  beside the range.
- **Whether the cut's stub rung goes**, once both dials are at hand and reading with them says
  whether it still separates anything.
- **Whether the column's path is a thread.** The word fits what it is against a reed, and
  `docs/SURFACE.md`, `docs/MAP.md` and the code all say *path*; it is decided once reeds have been
  read with, and moved everywhere at once if it is.
