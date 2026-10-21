# Knots

**Forks close enough along a path to be one place, straightened out so that they are one place.**
A rough first draft: the notes as they were written, and what came up beside them. A design
pass turns it into decisions and open questions.

## The notes

- Knots are inevitable from same-position repeated sampling.
- We need to straighten them out for consistent UX: it fixes real navigation consistency and
  excessive movement.
- Range is a setting, but could be set by the user or auto-mapped per tree.
- Those within range of each other collapse both visually and functionally.
- When looking in detail, the path-averaged entropy (?) is wanted for sorting, over equivalent
  lengths. Maybe other options here too to explore: make it pluggable?
- Path temperature as an emergent axis, with the model-preferred on the left and the
  human-entered (currently unsorted) on the right.

## What the tree shows

`docs/MAP.md`'s *What a tree looks like*: the strands between forks have a median of 2 tokens, so
forks arrive in bursts, and joining those within 4 tokens of each other makes `data/daniel`'s
1,319 forks into 509 places. Three limbs of 2,000–3,000 tokens leave the largest root's trunk at
tokens 162 and 163, which is one knot drawn as two forks. The zoom thins what is around a knot
and does not pull its forks apart, which is why the fisheye on the axis comes first: it is what
a knot is inspected with while this is built.

## Proposals from the discussion

- **A knot is a run of forks along one line, each within range of the next**, and collapsed it
  is one fork in the drawing and in navigation: every branch leaving anywhere in it is a sibling
  at one place, so the same knot always resolves the same way.
- **The range by its effect**, as the cut is stated — so many places from so many forks — which
  is what a per-tree default is set from.
- **The range may vary by zone**, wide far from the thumb and narrow at the focus, on the zoom's
  own machinery.
- **Sorting by mean surprisal over a window** of the tokens each branch took, rather than entropy:
  surprisal reads how much the model preferred that path, and entropy how open it was at each
  position, which is a different question. Entropy and the rest plug in beside it. Branches leave
  a knot at different depths, so the first-token rank the map sorts by now does not compare them.
- **That ordering is the emergent temperature axis**: near-greedy on one side, hot further out, and
  authored text, which has no ranking, at the far end.
- **What it reads**: `/map` sends a strand's first logprob only, and a windowed mean wants the
  logprobs along each branch, which is a surface read and not a core change.
