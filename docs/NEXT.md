# Next

**What gets built next, and why in that order.**

This document is living. Items are added as they come up and **deleted** once they close or fall
out of scope — nothing is kept here for the record. What was done is in the history, and a list
that accumulates its own past stops being read.

The ordering is the content. Each item below is cheaper before the one after it and more
expensive after, which is the only reason they are numbered; anything that does not stand in
that relation to the others is a bullet at the end rather than a number.

---

## 1. The page

**A skeleton, lifting from the probe rather than growing out of it.** `probe/index.html` holds the
band's measured layout, which is the part of `docs/SURFACE.md` nothing else has demonstrated. It
also holds its own CSS, its own reads against a static projection, and controls that are not
carried forward, all of which would have to come apart anyway.

**No build step.** The probe needed none for the hardest thing in the document.

**The continuation rule is a parameter of the read, and the page must not put it back.**
`docs/SURFACE.md` names a family of them and settles none, because they are compared by use.
`longest` is the only member built, a second is a function and an entry in `RULES`, and what the
page owes the question is a way to swap them over one tree.

**The page names the `generate` parameters.** The server names none it was not given: an adapter
that requires one says so itself, as a refusal, and a server filling them in would be deciding
what the store keeps one layer up from where `docs/ADAPTER.md` forbids it. A stochastic draw the
page does not seed is one nothing can replay, which is the command line's reason for seeding and
becomes the page's.

**What the band costs is now measurable and has not been measured against a page.** `/branches`
is bounded by a line's width and by nothing vertical, so on the synthetic twenty-thousand-node
tree a band opened at a root reads in 110 ms and projects to about a megabyte of JSON. A band
opens at a fork rather than at a root, so that is a ceiling and not a typical call — but whether
a band wants a bound in the other direction is an open question in `docs/SURFACE.md`, and the
page is what settles it.

## Loose ends

Not in the ordering; each stands on its own.

- **Whether the command line should keep verifying on every write.** Each invocation is its own
  writer, so each pays a whole-tree read — 330 ms at 20k nodes. The server pays it once for the
  life of the process, which is what a long-running session buys. Nothing forces the question
  yet.
- **The `/evaluable` read does not check that the adapter spells the tree's vocabulary.** It
  asks the backend about ids from a tree that may be in another vocabulary and gets a confident
  answer about nonsense. `put_token` is what catches the mismatch on a write, at the first id the
  two disagree on; a read has no such moment. Harmless while a server is started against the tree
  it matches, and wrong the first time one is not.
