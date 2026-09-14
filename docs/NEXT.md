# Next

**What gets built next, and why in that order.**

This document is living. Items are added as they come up and **deleted** once they close or fall
out of scope — nothing is kept here for the record. What was done is in the history, and a list
that accumulates its own past stops being read.

The ordering is the content. Each item below is cheaper before the one after it and more
expensive after, which is the only reason they are numbered; anything that does not stand in
that relation to the others is a bullet at the end rather than a number.

---

## 1. `violations()` in SQL

**630 ms, and eleven queries.** It is not N+1 — it loads `nodes` and `edges` whole and checks them
in Python, and 89% of the time is two functions grinding 400k edge rows: `_rank_dense_and_unique`
at 0.60 s and `_vocab_closed` at 0.20 s. Rank density and uniqueness is a `GROUP BY`; vocab
closure is a `LEFT JOIN`. Both still check rather than trust the schema, which is what `check.py`
asks of itself and what a declared foreign key would not give.

**This is the one item whose value decays rather than whose cost grows**, which is why it is
numbered here rather than left as a bullet. The command line opens for writing on every write verb
and pays the 630 ms each time. The API opens once for the life of the process, so once that lands
the cost is a startup cost and stops being felt.

## 2. The API

**Before the surface, and the reads it serves already exist.** What is left is who opens the tree,
who holds the claim, and what goes over the wire.

It opens the tree for writing once and verifies once, for the life of the process, which the claim
is what makes sound. `Store.open` already takes the flag; what this item settles is who passes it.

## 3. The surface

**The continuation rule is a parameter of the read, and the surface must not put it back.**
`docs/SURFACE.md` names a family of them and settles none, because they are compared by use.
`longest` is the only member built, a second is a function, and what the surface owes the question
is a way to swap them over one tree.

---

- **`cmd_tree` asks `unrealised_edges` per node** — 0.1 ms each, so seconds on a 20k tree. It is
  the last N+1 in a client, and a bullet rather than a number because nothing waits on it: one
  `LEFT JOIN` over the whole tree answers it for every node at once.
