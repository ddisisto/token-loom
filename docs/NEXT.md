# Next

**What gets built next, and why in that order.**

This document is living. Items are added as they come up and **deleted** once they close or fall
out of scope — nothing is kept here for the record. What was done is in the history, and a list
that accumulates its own past stops being read.

The ordering is the content. Each item below is cheaper before the one after it and more
expensive after, which is the only reason they are numbered; anything that does not stand in
that relation to the others is a bullet at the end rather than a number.

---

## 0. `docs/ADAPTER.md`'s Status, groomed

The section has outlived several of its items. Some ask for work that is now cheap; some hold a
fact a reader would go looking for in the body of the contract; and at least one had settled
without being closed — `will_evaluate` has a signature, a stated obligation and a live test, and
was still listed there as a shape nobody had fixed.

**Stale status is written against.** A claim that a question is open is an invitation to leave it
open, and it travels: that one reached a docstring in `src/tokenloom/core/ports.py` and sat there
saying the shape was unsettled long after it was not. Every item this section keeps past its life
is one the surface and the read layer get built around.

## 1. `docs/SURFACE.md`, before the surface is built

Design and constraints in prose first. This is the method the project has already been paid by
twice, and the reading surface is the largest thing that has not had it.

**It comes before the read layer, not after.** It settles what the surface actually reads, and
the read layer should be built against a known set of questions rather than a guessed one. The
N+1 fix below is specified either way — `docs/CORE.md` already says what it is — but *which* bulk
reads exist is decided here.

**It is drafted, and it is not accepted.** One thing stands between the two: whether a first-pass
generation is greedy rather than sampled, and what a surface shows of a distribution whose mass
sits in three of twenty recorded alternatives. `docs/surface-notes.md` holds that argument and
nothing else.

## 2. The read layer

Point reads are cheap and bulk reads are not. `scripts/scale.py` is what measured this and what
re-measures it; at 20k nodes, 400k edges and depth 1401:

| read | |
| --- | --- |
| `violations()` — runs on **every** open for writing | 613 ms |
| `is_live` over 2000 nodes | 400 ms |
| `walk()` over the whole tree | 166 ms |
| any single-node read | under 3 ms |

**Every bulk read is N+1.** Each node walks its own ancestry for liveness, or fetches its own
children. `docs/CORE.md` already says what the fix is and only the single-node form was built:
*a descent from the root carries the answer down and costs nothing.*

There is also a decision here the command line never had to make. It verifies once per
invocation, which is a fair reading of *a writer will not write* to a store that fails an
invariant. A server holding a store open for its lifetime would verify once per process, which
is an equally fair reading and a different cost. Neither is wrong; one has to be chosen and
written down.

**Before the API, not after.** An API written against N+1 reads gets shaped around them, and the
shape outlives the fix.
