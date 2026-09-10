# Next

**What gets built next, and why in that order.**

This document is living. Items are added as they come up and **deleted** once they close or fall
out of scope — nothing is kept here for the record. What was done is in the history, and a list
that accumulates its own past stops being read.

The ordering is the content. Each item below is cheaper before the one after it and more
expensive after, which is the only reason they are numbered; anything that does not stand in
that relation to the others is a bullet at the end rather than a number.

---

## 1. `docs/SURFACE.md`, revised — and `docs/surface-notes.md` dies

The draft predates the last two core changes and has now had one review. What that review
settled, and what the revision has to carry:

- **Retract *a logprob is shown as a number and never as a length*.** Where a ranking is clear
  and consistent there is no reason to refuse a display method, and the borderline case wants the
  inconsistency shown directly rather than designed around. The argument the draft gives for the
  blanket rule is also wrong: values sum to less than one because the rest of the vocabulary is
  unrecorded, not because anything was truncated, so proportion-of-recorded-mass is honest and the
  shortfall is a nameable quantity. What the surface may *not* read off that quantity is a
  request: a ranking extends across acts, so a node's stored rows are a union and its recorded
  mass is a property of what has accumulated there rather than of any one `record_mass`.
- **The continuation rule is a family, not a rule.** Longest, first, last, most-recently-used,
  cumulative open time — comparable only by use, so this belongs in *What is not decided here*
  with `longest` named as the first implementation rather than as the design. Ties bite only for
  `longest`, and are insertion order.
- **Reader state is a third category the doctrine does not have.** MRU is not a write to the tree
  and it is not *a way of looking that records nothing and costs nothing* either — it is state
  that decides what is seen, held where the record cannot follow. Naming it is what licenses it,
  and the reader must be able to tell *what this branch is* from *what you did here last time*,
  including inside the band, where each preview line follows the same rule and the reflection is
  least visible. **MRU is updated by selection only** — never by preview or render, or previews
  perturb the thing they preview and the band reorders under its own gaze. Session storage only;
  durable is out of scope, and `docs/CORE.md`'s *Conformance and extension* makes it cheap later,
  which is a reason to shape the session form as a cache of something recordable.
- **Deepen a ranking is a gesture the draft does not have.** Rankings lists three row kinds and no
  way to ask for more. It needs no new write — it is a `generate`, and `tokenloom generate` makes
  it — so *Nothing written is only here* is untouched.
- **The claim locks the command line out.** For as long as the surface runs, every write verb
  fails against that tree. This is intended, and the draft states only the converse. It is also
  not freely relaxable: verify-once rests on the claim, and `violations()` is 613 ms at 20k nodes.
- **The floor case's *reads well* is about presentation and holds no opinion on content** —
  whether the content came from `create` or from `generate`, and whether it degenerates.
- **The test at the top is the wrong one for this document.** *Could someone build this from it
  alone* is `docs/CORE.md`'s test and earns its place there, where completeness is the property
  wanted. Here it pushes an open question into a stated decision so the document can pass it —
  which is how the continuation rule and *never as a length* came to be written as rules — and the
  pressure then leaks into Status. What wants asking of this document is whether a reader can tell
  what is settled from what is open, and what would settle each open one. That makes **What is not
  decided here** the centre of it rather than an apology at the end, and leaves Status holding only
  what has no home yet, which is what `CLAUDE.md` now asks of one.

`docs/surface-notes.md`'s sampling argument is settled and the revision above is its last
reader, so the file goes in the same edit. `CLAUDE.md`'s description of it goes with it.

## 2. The descent, and the reads that sit on it

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

**The primitive does not wait for the revision above.** A descent carrying liveness down is a
property of the store and does not care what is asked of it, so it is specifiable now and is a
finished piece of work when it lands. What waits is which composite reads sit on it.

**That set does not close, and aiming at closing it is the mistake to avoid.** The path read has
to take the continuation rule as a parameter rather than embedding one, because the revision
above puts that rule in *What is not decided here* and the comparison is made by using the
surface. Build the reads `docs/SURFACE.md` names once it is revised, expect churn, and keep the
primitive clean of it.

## 3. The API

**Before the surface, and after the descent.** An API written against N+1 reads gets shaped around
them, and the shape outlives the fix.

It opens the tree for writing once and verifies once, for the life of the process, which the claim
is what makes sound. `Store.open` already takes the flag; what this item settles is who passes it.

## 4. The surface

**Build the continuation rule swappable.** The family named two items above is compared by use,
and a first build that hard-codes `longest` answers the question by making it expensive to ask.

---

- **`agreement()` and `frequency()` are out of scope for the read layer.** `agreement()` calls
  `frequency()` once per node and each call is a recursive CTE over every act with a tip, which
  makes it the worst read in `reads.py` by a wide margin; `scripts/scale.py` times `frequency` on
  one node and `agreement` not at all, so the table above understates the ceiling. Nothing the
  surface reads reaches either, and this bullet exists so the measurement is not taken again.
