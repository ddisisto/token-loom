# Next

**What gets built next, and why in that order.**

This document is living. Items are added as they come up and **deleted** once they close or fall
out of scope — nothing is kept here for the record. What was done is in the history, and a list
that accumulates its own past stops being read.

The ordering is the content. Each item below is cheaper before the one after it and more
expensive after, which is the only reason they are numbered; anything that does not stand in
that relation to the others is a bullet at the end rather than a number.

---

## 1. Streaming and cancellation

`cancelled` is the one open item a locked core is already waiting on. `docs/CORE.md` specifies
the terminator and nothing in the adapter's three-operation surface can produce it: reaching it
needs a `generate` that can be interrupted and that returns what it drew, which the blocking
form is not. `docs/ADAPTER.md` has the shape already — the same operation with a way in and the
same return.

**This is adapter work, not surface work**, and it is what a reading surface needs before it can
show tokens as they land or offer a stop. Built after the HTTP API, the API's shape changes
under it: a blocking `generate` and a streaming one are not the same endpoint with a flag.

Note what it does *not* need. The store already writes provenance before the model is called and
nodes after it, so a cancelled generation lands in the same second write as any other. Only the
adapter has to change.

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

## 3. `docs/SURFACE.md`, before the surface is built

Design and constraints in prose first. This is the method the project has already been paid by
twice, and the reading surface is the largest thing that has not had it.

It settles what the surface actually reads, which is what decides the shape of 2 — the read
layer should be built against a known set of questions rather than a guessed one. It is also
where **no capability may be surface-only** is enforced at design time rather than discovered
late: every operation the surface offers has to be reachable from the command line already, and
that is cheap to check against a document and expensive to retrofit.

Open questions it will have to close, at least: what a run is on screen when the record has no
run ids; how an unrealised edge is offered without implying the model recommends it; what is
shown in place of bytes that do not decode, which `docs/CORE.md` leaves explicitly to the
reader; and how a client shows that a write is blocked behind another writer's generation.
