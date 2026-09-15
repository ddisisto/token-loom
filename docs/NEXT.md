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

**Built in the order a reader meets it, which is the order it is written in.** A tree starts
empty, so the first thing the page needs is a way to make one, and each rendering after that is
built once there is a way to produce what it renders from the page itself. The band is the far
end: it needs a fork, a fork needs a second live child, and that needs a `realise` and a
`generate` or a second `create`. Building it last is what puts the gesture that makes forks in
hand before the thing that displays them is designed.

**A page grown against an empty tree risks a column shaped by the degenerate case.**
`data/continuations` is twelve thousand nodes and costs nothing to point at, so each increment is
read against a tree the page could not yet have made.

**The band lifts from the probe rather than growing out of it.** `probe/index.html` holds the
band's measured layout, which is the part of `docs/SURFACE.md` nothing else has demonstrated —
about sixty lines of it, since the tree-walking around it is what `/path` and `/branches` answer
now. It also holds its own CSS, its own reads against a static projection, and controls that are
not carried forward, all of which would have to come apart anyway. One adaptation is not
cosmetic: the probe placed a preview line by segment index, and `parts_at` is characters into the
line above, so the column carries a running offset onto each segment.

**No build step.** The probe needed none for the hardest thing in the document.

**Where it goes, and what is already there.** `src/tokenloom/surface/page/` is mounted at the
root of the process that answers the reads, so the page and what it reads arrive from one origin
and there is nothing between them to arrange. What is there now is a sentence saying the page is
not built, which gets replaced whole.

**The reading view renders no act but the one in flight.** An act originates at a node or an edge
regardless of what produced either, and what it leaves behind is nodes and paths — which are what
is read. A generation still running is the exception, because it is the one act whose absence from
the record is something the reader is waiting on. `/acts` answers the whole list unfiltered and
should keep doing so: the rest of it belongs behind a log view, hidden by default, which is worth
having while the page is being built and is not part of reading.

**The continuation rule is a parameter of the read, and the page must not put it back.**
`docs/SURFACE.md` names a family of them and settles none, because they are compared by use.
`longest` is the only member built, a second is a function and an entry in `RULES`, and what the
page owes the question is a way to swap them over one tree.

**What the band costs is now measurable and has not been measured against a page.** `/branches`
is bounded by a line's width and by nothing vertical, so on the synthetic twenty-thousand-node
tree a band opened at a root reads in 110 ms and projects to about a megabyte of JSON. A band
opens at a fork rather than at a root, so that is a ceiling and not a typical call — but whether
a band wants a bound in the other direction is an open question in `docs/SURFACE.md`, and the
page is what settles it.

**Nothing can change the store under the page, and what to do with that is the page's to
settle.** The server holds the claim, so it is the only writer there is — but that is true of
the server and not of a page, since two pages on one server change it under each other. A
revision on each read and `If-None-Match` against it is about ten lines and needs nothing from
the core: the sole writer can count its own writes in memory, and a token minted per process
covers a restart. It buys nothing on a first read, which is the one that is large.

**What a page can cache with no protocol at all is the immutable half, and it is most of what a
page pulls.** A node's parent, token and source never change and only `deleted` does; a token's
bytes never change, because `put_token` refuses a vocabulary that disagrees at an id already
held; and a ranking only grows, because `_extend_ranking` appends and never rewrites. Spellings
and rankings are therefore cacheable for the life of the page, and liveness is the only thing
that has to be asked again.

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
