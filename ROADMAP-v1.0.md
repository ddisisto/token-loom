# Roadmap — v1.0

**Order and status. Nothing else.** Every item points at the document that says what it is
and why; if an item here needs a paragraph of justification, that paragraph belongs in
`DIRECTION.md` or `FORMAT.md` and this file links to it. That rule is what stopped the last
roadmap from being deletable, and it is the whole discipline of this one.

**This is the only file that carries status.** `DIRECTION.md` says what is wanted and says it
in the present tense whether or not it exists yet. Anything that answers *is it done* is here.

**It is deleted when v1.0 lands, not archived.** Rule one is what makes that safe: nothing
unique is ever in it. `ROADMAP.md` is the MVP's, is historical, and goes in stage 5.

---

## Stage 1 — the two probes

Cheap, and first because they are the only items that could change a document.

- [ ] **Does llama-server accept an empty prompt?** Generating at the root with no given is
      reachable and has never been run. `CLAUDE.md`, *Open threads*.
- [ ] **Does `/completion` accept a prompt as an array of token ids?** Decides whether token
      replay is an adapter change or an engine overhaul, and therefore what the ledger means.
      `CLAUDE.md`, *Open threads*.

## Stage 2 — the constraints

`FRONTEND.md` is edited before anything is written against it, so that a specific never gets
to soften a constraint in the same pass.

- [ ] **Constraint 6 retires its clarification.** Viewport-as-input replaces
      target-follows-cursor, and *text arriving must never move the page* is promoted to be
      the whole of the constraint. `DIRECTION.md`, *The viewport is the input*.
- [ ] **Re-read the other thirteen against the v1.0 sections.** Anything that conflicts is
      raised as a question here, not fixed in place.

## Stage 3 — the document

- [ ] **`INTERACTION.md` rewritten for the station, the lanes and the two axes.** Checked
      against `FRONTEND.md`; conflicts become questions. `DIRECTION.md`, *v1.0 — the surface
      becomes a place*, is the whole of the input.

## Stage 4 — the surface

**The crude column build comes first**, because *that the single rule holds on a real page* is
the item everything else leans on. `DIRECTION.md`, *What has to be proved*.

Then, from the state the MVP is in:

- [ ] `web/main.mjs` has three `generate(at, 2, …)` calls and one `generate(at, 1, …)`. They
      become one request shape.
- [ ] There is no scroll listener in `web/` at all. `surface.mjs` only ever scrolls *to* follow
      a target, and that following retires with the target it follows. The input path is new.
- [ ] The band and its apparatus — the clip polygons, the second copy, `--tall`, `fit`, the
      shift arithmetic in `surface.mjs`, and the band rules in `style.css` — retire whole.
- [ ] The margin chips in `surface.mjs` retire with them, along with the displacement
      arithmetic that keeps a chip past the target aligned with the copy that draws it.
- [ ] The single pending slot in the client's request queue changes from queueing to
      coalescing.
- [ ] A span's terminator is marked whenever it is not `length`, rather than only on a span
      with no bytes at all. `DIRECTION.md`, *End-of-text is not special*.
- [ ] Deleting becomes an ordinary gesture. `DIRECTION.md`, *Deleting is ordinary, and always
      asked for*.

`GET /api/divergence` will have nothing to say about a tree the surface made, once one act
makes one generation. That is correct rather than broken and needs no work — it is a research
read, and the research thread keeps its own trees.

## Stage 5 — the release

Enough for someone else to run it and understand what they are looking at.

- [ ] **The README as a front door**, for a reader who has never seen the model and does not
      yet know why a position is a pair. Its state paragraph is stale in both directions.
- [ ] **Retire `ROADMAP.md`**, once nothing live depends on it. `LATER.md` and `DIRECTION.md`
      have already taken what survives.
- [ ] **Delete this file.**
