# Next

**What gets built next, and why in that order.**

This document is living. Items are added as they come up and **deleted** once they close or fall
out of scope — nothing is kept here for the record. What was done is in the history, and a list
that accumulates its own past stops being read.

The ordering is the content. Each item below is cheaper before the one after it and more
expensive after, which is the only reason they are numbered; anything that does not stand in
that relation to the others is a bullet at the end rather than a number.

---

## 0. `docs/CORE.md`, reopened once

The locked document moves once: a session lock in place of the per-act one, `Runs` removed, and a
clause keeping the appendix's parameters from reading as a recommendation. `marker` does not
change. **The list, the sentences it touches and the knock-ons outside the core are
`docs/CORE-status.md`'s *Held for a possible future core*, and are not repeated here.**

**First, because what follows is written against it.** `docs/SURFACE.md` already carries two
paragraphs the lock change deletes, and `docs/ADAPTER.md` carries two the same change makes moot
and false. Every week it waits is a week more written against a lock that is going to move.

## 1. `docs/SURFACE.md`, before the surface is built

Design and constraints in prose first. This is the method the project has already been paid by
twice, and the reading surface is the largest thing that has not had it.

**It comes before the read layer, not after.** It settles what the surface actually reads, and
the read layer should be built against a known set of questions rather than a guessed one. The
N+1 fix below is specified either way — `docs/CORE.md` already says what it is — but *which* bulk
reads exist is decided here.

**It is drafted, and it is not accepted.** The four questions this item once listed as open are
answered in the draft, and one of them — what a run is on screen — stops being a question at all
once item 0 lands. What it waits on is item 0, and one thing it does not yet say: whether a
first-pass generation is greedy rather than sampled, and what a surface shows of a distribution
whose mass sits in three of twenty recorded alternatives. `docs/surface-notes.md` holds that
argument until the core has moved.

**It has one technique available to it that the record does not name.** A caller that wants to
stop a long generation can issue it as consecutive short `generate` acts — `docs/ADAPTER.md`'s
*Cancellation* has the reasoning — so a block of output a reader sees may be a construct of the
surface rather than a unit of the record. Whether the surface works that way is its own decision;
what follows if it does is the adapter's to state, and the bullet below says why that is not how
the contract currently reads.

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

---

- **`docs/ADAPTER.md`'s *Cancellation* over-prescribes.** The finding it rests on stands and is
  not in question: streaming loses ids on this backend, so an interruptible generation would have
  to be declined, so `cancelled` is unreachable and stopping is declining to continue. What
  over-reaches is what follows it. *A caller who wants to stop asks for less at a time*, and the
  three consequences under it, are written as though every client inherits them — and they read
  that way, which cost a round of confusion in surface design, where chunking arrived as a
  constraint the surface had been handed rather than a technique it could pick up. The command
  line has never chunked and has never needed to. The edit is contained: keep the measurement,
  keep the terminator's fate, demote the prescription to a note that a client *may* issue a long
  generation as consecutive acts, and keep the three consequences attached to that note rather
  than standing free. Unnumbered because it is cheap at any point and nothing waits on it.
