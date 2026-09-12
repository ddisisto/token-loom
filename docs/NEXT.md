# Next

**What gets built next, and why in that order.**

This document is living. Items are added as they come up and **deleted** once they close or fall
out of scope — nothing is kept here for the record. What was done is in the history, and a list
that accumulates its own past stops being read.

The ordering is the content. Each item below is cheaper before the one after it and more
expensive after, which is the only reason they are numbered; anything that does not stand in
that relation to the others is a bullet at the end rather than a number.

---

## 1. The descent, and the reads that sit on it

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

**The primitive is specifiable on its own.** A descent carrying liveness down is a property of
the store and does not care what is asked of it, so it is a finished piece of work when it lands.
What is open is which composite reads sit on it.

**That set does not close, and aiming at closing it is the mistake to avoid.** `docs/SURFACE.md`
names three reads and puts two things about them in *What is not decided here*: the continuation
rule, which the path read therefore takes as a parameter rather than embedding, and whether the
reading column marks uncertainty, which would have the path read carry one more value per node.
Build the three, expect churn in them, and keep the primitive clean of it.

## 2. The API

**Before the surface, and after the descent.** An API written against N+1 reads gets shaped around
them, and the shape outlives the fix.

It opens the tree for writing once and verifies once, for the life of the process, which the claim
is what makes sound. `Store.open` already takes the flag; what this item settles is who passes it.

## 3. The surface

**Build the continuation rule swappable.** `docs/SURFACE.md` names a family of them and settles
none, because they are compared by use — and a first build that hard-codes `longest` answers the
question by making it expensive to ask.

---

- **`agreement()` and `frequency()` are out of scope for the read layer.** `agreement()` calls
  `frequency()` once per node and each call is a recursive CTE over every act with a tip, which
  makes it the worst read in `reads.py` by a wide margin; `scripts/scale.py` times `frequency` on
  one node and `agreement` not at all, so the table above understates the ceiling. Nothing the
  surface reads reaches either, and this bullet exists so the measurement is not taken again.
