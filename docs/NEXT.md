# Next

**What gets built next, and why in that order.**

This document is living. Items are added as they come up and **deleted** once they close or fall
out of scope — nothing is kept here for the record. What was done is in the history, and a list
that accumulates its own past stops being read.

The ordering is the content. Each item below is cheaper before the one after it and more
expensive after, which is the only reason they are numbered; anything that does not stand in
that relation to the others is a bullet at the end rather than a number.

---

## 1. The API

**Before the surface, and the reads it serves already exist.** What is left is who opens the tree,
who holds the claim, and what goes over the wire.

It opens the tree for writing once and verifies once, for the life of the process, which the claim
is what makes sound. `Store.open` already takes the flag; what this item settles is who passes it.
Verifying is a whole-tree read and stays one — 330 ms at 20k nodes with every check in SQL — so
what this removes is not the cost but the repetition: the command line pays it on every write
verb, and a process that opens once pays it once.

## 2. The surface

**The continuation rule is a parameter of the read, and the surface must not put it back.**
`docs/SURFACE.md` names a family of them and settles none, because they are compared by use.
`longest` is the only member built, a second is a function, and what the surface owes the question
is a way to swap them over one tree.
