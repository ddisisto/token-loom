# Next

**What gets built next, and why in that order.**

This document is living. Items are added as they come up and **deleted** once they close or fall
out of scope — nothing is kept here for the record. What was done is in the history, and a list
that accumulates its own past stops being read.

The ordering is the content. Each item below is cheaper before the one after it and more
expensive after, which is the only reason they are numbered; anything that does not stand in
that relation to the others is a bullet at the end rather than a number.

---

## 1. The server

**Before the surface, and the reads it serves already exist.** One process, started against one
tree, holding its claim and serving both the reads and the five acts over HTTP. `Store.open`
already takes the `write` flag; this is what passes it.

Verifying is a whole-tree read and stays one — 330 ms at 20k nodes with every check in SQL — so
what this removes is not the cost but the repetition. The command line pays it on every write verb
because each invocation is its own writer, and one process that opens once pays it once. Whether
the command line should keep paying it is a separate question and not this one.

**Starlette and uvicorn.** The response shapes are already dataclasses in `src/tokenloom/surface.py`
and `core/reads.py`, so what a validating framework would save is mostly declaring them a second
time; the request side is integer coercion on a handful of query parameters. It is Starlette
underneath if that turns out to be wrong.

**Nothing streams, and that is the backend's shape rather than a simplification.** The adapter
posts `stream: false` and a generation is written whole. Pacing text out is *Cadence* in
`docs/SURFACE.md` and is undecided; inventing a transport for it first would decide it.

**Reads need a connection of their own**, which is the only part of this that touches the core. A
generation is seconds inside `adapter.generate`, and a read served on the writer's connection waits
behind it for no reason the store imposes — WAL takes no lock, and no transaction spans the model
call. One connection per read request, no second claim.

**Five writes named by their verbs, and the reads by what they answer.** A surface write with no
verb would be a new kind of write, so the acts keep their own names on the wire.

**An error's status says that it failed and its body says which of the three it was.** A rejection
left no trace, a refusal is an act with terminator `refused`, a failure is an act with `failed` —
and a refusal has to carry its act id, because `docs/SURFACE.md` has the surface naming that act.
A status code alone collapses the three.

## 2. The page

**A skeleton, lifting from the probe rather than growing out of it.** `probe/index.html` holds the
band's measured layout, which is the part of `docs/SURFACE.md` nothing else has demonstrated. It
also holds its own CSS, its own reads against a static projection, and controls that are not
carried forward, all of which would have to come apart anyway.

**No build step.** The probe needed none for the hardest thing in the document.

**The continuation rule is a parameter of the read, and the page must not put it back.**
`docs/SURFACE.md` names a family of them and settles none, because they are compared by use.
`longest` is the only member built, a second is a function, and what the page owes the question is
a way to swap them over one tree.

