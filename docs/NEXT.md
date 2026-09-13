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

**Two bulk reads are N+1.** Each node walks its own ancestry for liveness, or fetches its own
children. `docs/CORE.md` already says what the fix is and only the single-node form was built:
*a descent from the root carries the answer down and costs nothing.* `scripts/scale.py` measures
it; at 20k nodes, 400k edges and depth 1401:

| read | | what the descent does for it |
| --- | --- | --- |
| `is_live` over 2000 nodes | 387 ms | replaces it |
| `walk()` over the whole tree | 151 ms | replaces it |
| any single-node read | under 3 ms | nothing; they are already cheap |

**One recursion with three anchors.** Read 1 wants root to a node, read 3 wants a subtree, and
`walk()` and bulk liveness want every root. Only the anchor differs, so this is one function
taking one rather than three that converge later.

**The primitive is specifiable on its own.** A descent carrying liveness down is a property of the
store and does not care what is asked of it, so it is a finished piece of work when it lands. What
is open is which composite reads sit on it.

**That set does not close, and aiming at closing it is the mistake to avoid.** `docs/SURFACE.md`
names three reads and puts two things about them in *What is not decided here*. The path read
therefore takes the continuation rule as a parameter rather than embedding one. Marking uncertainty
is
deferred outright: a per-node measure over `edges` decorates the descent's output rather than
joining its recursion, so it composes whenever it is wanted, and it is not well posed until it
says whose ranking it means at a node several models have ranked. Build the three reads, expect
churn in them, and keep the primitive clean of it.

## 2. `violations()` in SQL

**630 ms, and eleven queries.** It is not N+1 — it loads `nodes` and `edges` whole and checks them
in Python, and 89% of the time is two functions grinding 400k edge rows: `_rank_dense_and_unique`
at 0.60 s and `_vocab_closed` at 0.20 s. Rank density and uniqueness is a `GROUP BY`; vocab
closure is a `LEFT JOIN`. Both still check rather than trust the schema, which is what `check.py`
asks of itself and what a declared foreign key would not give.

**This is the one item whose value decays rather than whose cost grows**, which is why it is
numbered here rather than left as a bullet. The command line opens for writing on every write verb
and pays the 630 ms each time. The API opens once for the life of the process, so once that lands
the cost is a startup cost and stops being felt.

## 3. The API

**Before the surface, and after the descent.** An API written against N+1 reads gets shaped around
them, and the shape outlives the fix.

It opens the tree for writing once and verifies once, for the life of the process, which the claim
is what makes sound. `Store.open` already takes the flag; what this item settles is who passes it.

## 4. The surface

**Build the continuation rule swappable.** `docs/SURFACE.md` names a family of them and settles
none, because they are compared by use — and a first build that hard-codes `longest` answers the
question by making it expensive to ask.
