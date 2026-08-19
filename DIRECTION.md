# token loom — direction

**The living document for where this goes.** `ROADMAP.md` was the road to the MVP, and the
MVP has landed; `BEYOND-MVP.md` was written before there was anything to use, and most of it
has not survived contact with using it. This file replaces both. They stay until it has
absorbed whatever of them is still true, and then they go together rather than one at a time.

Its companions outlive it and are not summarised here. `FORMAT.md` is the on-disk format and
the reasoning behind it. `FRONTEND.md` holds the concept and the numbered constraints;
`INTERACTION.md` holds the elements and the gestures and is the thing checked against them —
they are two documents on purpose, and the first specific that conflicts with a constraint is
a finding rather than a licence to soften the constraint. `RESEARCH.md` is the other thread.

## What this is

**A machine output research tool. Givens go in, generations come out, and the surface exists
to read across them.**

That is a different object from the writing instrument this began as. Upstream describes
loom as a multiversal tree writing interface for human-AI collaboration; here nobody is
collaborating with anything. The reader supplies a given and then reads what the model does
when iterated against itself — attractors in the prior, how temperature gates access to them,
how framing acts as a change of basis, what survives repeated retransmission. Authoring
exists so that a given can exist, and stops there.

**The fork relationship is conceptual, not structural.** No upstream code survives anywhere
in the repository: core, inference, storage, API, surface and documents are all new. What
does survive is a debt worth stating plainly — socketteer's loom demonstrated that other
people think in these terms, and supplied a vocabulary and a running starting point that
made the first hour of this possible. The name stays.

Two things pull on every decision below, and they are the same two that always did:

- **Base-model behaviour matters more than chat quality.** A chat-templated reply is a
  different object than a continuation of the prior. Where they conflict, the raw
  continuation wins.
- **Headless and batch use are first-class.** Anything that only works by clicking is
  half-built. `loom.py` is the reference client and the floor for what the surface must be
  able to reach.

## Where it stands

The MVP works and is in daily use. `core/` is the substrate — a trie over bytes with tokens
as a per-span overlay, the bulk store beside it, the operations and the derived reads.
`loom.py` drives it from the command line and `api/` serves it over HTTP; `web/` is a client
of the API and reaches the core through nothing. Four executable checks: `core_test.py`,
`api_test.py` and `node web/web_test.mjs` need no model, `llama_test.py` needs the server.
Inference is local only, `llama-server` with Qwen2.5-7B base on the native `/completion`
endpoint.

Phases 0 through 3 — clear the ground, the token core, the API, the front end — are done. The
record of what each settled is in `ROADMAP.md` until it goes, and in git afterwards. Nothing
is open at the format level, which is what lets the surface change without the format moving.

## v1.0 — the surface becomes a place

The MVP proved the model. What it did not settle is what the surface *is*, and reading
deeply through it answers that differently than designing it did.

**The reader is not reading one path with alternatives at hand. They are reading across
several paths that already exist.** A card is a preview — something you glance at and then
commit to. A column is a place. The current surface is built on the first reading and the
second one is what the instrument turned out to want.

So the card band becomes columns, and three things fall out of that:

1. **The path to the root, above.** Unchanged: one measure, continuous prose, every fork it
   passes already chosen.
2. **A standing location at the seam**, opening onto N potential paths — actualised or not,
   and each potentially containing its own multitudes already.
3. **The below, as more than one path at once**, laid out side by side with the rest further
   out of view. A column is not a preview of one generated span; it owns its column and fills
   to the bottom with whatever the reader last navigated down that path, if anything. How
   many are visible, and whether what flanks the centre is a single neighbour or a stack, is
   a design question and is left to the design — this document commits to *more than one*,
   which is the part that changes what the surface is.

What that buys is navigation across the what-if questions the reader actually holds. The
deaths — end-of-text, the context wall — stop being terminal and become backtrackable
features of a landscape. Repeated short cycles and mantras become things you can hold beside
each other and see as the same shape. Attention accumulates into paths worth re-reading.

### Pruning is the other half of it

**Never selected and never viewed means pruned. Delete is normalised rather than
exceptional.** If the reader *looks*, the branch becomes real and theirs to keep or discard;
if they never did, it was never anything.

This is what makes the column model tractable rather than merely wide. Depth down a branch
exists *because* someone went down it, so an unvisited alternative has no path below it to
choose between and the question of which continuation a column should show mostly dissolves.
It only returns where a reader deliberately kept both halves of a fork, which is exactly the
case where showing them a choice is right.

**Soft delete is already the primitive this needs**, and it costs the other thread nothing:
`tree.live` keeps every byte on disk and merely out of view, so `loom.py` still sees the whole
record and an experiment tree stays complete. The tree becomes an account of attention
without becoming a lossy one.

### What retires

`#below` and the entire two-copy apparatus. It exists for exactly one reason — the band is a
horizontal slice inserted mid-flow, so the path has to be cut in two and the lower half
pushed past it — and under the column model the card becomes the column becomes the below.
The clip polygons, the translate, `--tall`, `fit`, the cut marker and the `shift` arithmetic
all go with it. This is a smaller surface than the one it replaces, not a larger one.

The property those two copies bought — nothing reflows when the target moves — is given up
knowingly. Each sibling has its own distinct below, replaced entire when the reader slides
rather than shifted vertically, so there was never one flow to preserve.

### What it keeps

Every point in the rendered text resolving to a `(span, offset)`, which is `FRONTEND.md`
constraint 7 and the one property a finished surface cannot be opened up to accept later. The
flyout onto counterfactuals. The writer queue and its single pending slot. The viewport
belonging to the reader.

### The seam stops being marked at all

The MVP's target section reads as continuous prose and is still *announced* — a tint, and two
rules where a border used to be. In v1.0 it should not be announced, because it no longer has
to be: **one column above and more than one below is the fork.** The geometry says it, so
nothing needs to be drawn on top of the sentence to repeat it, and reading down through the
centre is reading a paragraph rather than reading a paragraph with a labelled join in it.

Two consequences the design has to carry, and they are the same one seen twice:

- **The centre can join the text above directly, and the others cannot.** What lets the MVP
  indent the selected card's first line into blank space is that the real text sits directly
  above it at the same measure and the same x. Nothing sits above a flanking path, so it has
  no line to resume — the seam that is free in the centre has to be paid for at the sides.
- **The likeliest payment is a copy of the shared tail.** A flanking path opening with the
  last words the reader just read is self-evidently resuming from there, which orients all the
  paths against one another without a mark. It is the first place the surface would show one
  byte in more than one location — no format consequence, since it is one `(span, offset)`
  rendered more than once and a click means the same thing from anywhere, but whether the
  repeated stretch is live or inert context is a real decision.

**The space above the flanking paths is load-bearing, not slack.** The path above occupies
one measure, so whatever flanks the centre has empty space over it whose height is however
long the path is — and that is the gap the reader's eye crosses to get from what they have
read to what they are comparing. How it is used is critical and unsettled. It is the strongest
argument for the copy over a drawn connector: a connector has to span a distance that changes
every time, and a repeated fragment does not care how far apart things are.

### Not yet decided

Three questions the design has to answer, none of which has an obvious right answer:

- **Measure against how many paths are visible.** Several columns at the MVP's 34rem measure
  is wider than most windows, so either the measure narrows or what flanks the centre is
  peripheral rather than fully readable. Both are viable and the choice is the design's. Worth
  knowing before it is made: if flanking paths repeat a shared tail, the tails only orient
  against each other when they wrap identically, which wants one measure across all of them —
  and a page laid out on that grid throughout, with the path above sitting in the centre of
  it, changes no width at the seam at all. On a 1280px window that puts the measure near 25rem
  against the present 34rem, which is a better measure for prose rather than a compromised
  one.
- **What counts as "looked at", and whether it is durable.** *Has descendants* is a free
  approximation needing no new state — a branch generated from was the cursor at some point.
  It fails for the branch you read, considered and left, which is then indistinguishable from
  one you never opened; seeds being per-call, pruning it is not reversible by regenerating.
- **What an out-of-view path says about itself.** Something is needed at the foot of a
  column, or on a chip in its place, that says how much has been actualised beyond it —
  depth, breadth, whether it ends in a wall. Exact form open.
- **How much shared tail, and what happens at a line start.** The natural unit is the line the
  branch falls on, so every path opens with the same partial line and visibly diverges partway
  through it. It degrades at exactly the case that has to work: where the branch point *is* a
  line start, that tail is empty and there is nothing to orient against. A floor under it is a
  token or character count, which is the arbitrariness the line unit was chosen to avoid.

## The way there

### Phase 4 — the reading surface

**The document first.** `INTERACTION.md` is rewritten for columns and checked against
`FRONTEND.md`'s constraints before any of it is built; where a specific genuinely conflicts
with a constraint, that is put as a question rather than fixed by editing the constraint in
the same pass. This is the sequence that paid for itself in every phase so far, and this is
the first change big enough to test the two-document split properly.

Three faults found by reading are fixed regardless of the redesign, because they are wrong
under any layout:

- **The strip animates from zero on every draw.** `surface.mjs:slide` clears the transform to
  measure, which commits a computed value of `none`, so the CSS transition runs from the
  origin rather than from where the strip was. Correct only when moving one step right from
  the leftmost card, disorienting everywhere else, and re-triggered by every poll during a
  generation.
- **The seam does not line up.** The selected card's first line sits a border and two
  paddings below the line it continues. Lining it up means the band's vertical padding and
  the selected card's top and bottom borders go, and the left and right borders become
  vertical rules flanking the column — a mark that lands in the line rather than across it.
A third — **the placeholder being a second object**, where asking for one more continuation
makes the request button vanish and a differently-sized box appear elsewhere — is deliberately
*not* fixed. Its own fix is the column model: the slot that absorbs the request becomes the
column that fills, so building the intermediate shape would be building it to throw away. The
flicker that made it urgent was the strip, and that is fixed.

Then the columns, and pruning as an ordinary gesture beside them.

### Phase 5 — the release

Enough for someone else to run it and understand what they are looking at.

- ✅ **A licence.** MIT, as of this cycle.
- ✅ **`PLAYBOOKS.md` retired**, at `f3118a3`, the last commit that holds it. It quoted the
  demo tree line by line as though one generation's specifics were findings, and that quoting
  was the *only* reason `data/demo/` could not be rebuilt. `demo.py` is the construction and
  the tree is the artefact; `RESEARCH.md` points at the commit for the five impressions that
  predate pre-registration.
- ✅ **`CLAUDE-HANDOVER.md` retired.** It was a message between sessions and had outlived its
  context entirely; every live item in it was settled, superseded, or the two-writer thread
  below.
- **Drop the fork relationship** in the repository metadata and the README, with the credit
  above kept explicitly rather than implied by a fork badge. Detaching on GitHub is in hand.
- **The README as a front door**, for a reader who has never seen the model and does not yet
  know why a position is a pair. Its state paragraph is currently stale in both directions.
- **Retire `ROADMAP.md` and `BEYOND-MVP.md`** once this file has absorbed what survives.

✅ **The two-writer guard**, built at the front of Phase 4 rather than deferred a fourth
time. It had been carried as a known gap across three phases and referenced from four files,
which was itself the argument: cheap, and costing more in re-explanation than in construction.
Both halves are in `core/` and `CLAUDE.md` has what is easy to get wrong about them.

- **An exclusive lock on the tree directory** — `flock` on the directory's own file
  descriptor, in `core/lock.py`, taken by `Session` when it opens for writing and held for the
  process's life. Nothing is created, so nothing has to be gitignored and a committed
  `experiments/` tree gains no stray file. The loser refuses cleanly with the directory named;
  `loom.py` exits non-zero, the API refuses to start. Reads take no lock at all and never
  wait, which is what makes `loom.py show` against a served tree work.
- **Validator check 8: no bulk row names a span the tree lacks.** The half that catches damage
  already done, where the lock only prevents new damage. A soft-deleted span is still in
  `tree.spans` and is emphatically not damage.

The one real design decision was where the read/write line falls. It is per **session** rather
than per operation: a `Session` is opened for reading or for writing and stays that way, so
nothing serialises a read against a write inside one process. `loom.py` decides from the
subcommand — a `READS` set, with anything absent treated as a writer — because the lock is
taken at open time and "does this write" therefore has to be answerable before the tree is
open. The alternatives rejected were a lock per operation, which would have serialised
`GET /api/tree` against a running generation, and inferring read-ness from whether a handler
happened to call `save`, which is only knowable too late.

## Out of scope for v1.0

Recorded so they are not re-litigated, not because they are rejected.

- **The research thread**, parked deliberately. The instrument works; the questions are
  getting better as the patterns become visible, and they are better asked after more use
  than before it. `RESEARCH.md` and `experiments/` stay exactly as they are.
- **Streaming.** The format support it needs — in-flight spans — is already in, so deferring
  costs nothing later. It would reintroduce asynchrony deliberately, and generation being an
  ordinary blocking call is worth keeping until something needs otherwise.
- **Hosted providers.** No hosted provider returns logprobs on a raw continuation, so none of
  them can feed the token core at all. Adding one later is a second adapter beside
  `core/llama.py`, never an entry in a capability table.
- **A test suite in the pytest-and-fixtures sense.** What exists instead is four executable
  checks, each a script that prints what it asserted and why. The clean-break format with no
  migration is what makes that affordable, and it has found more than a fixture suite would
  have.
- **Vacuum and compaction of the append-only store.** `FORMAT.md` holds the one hard
  constraint it must satisfy when it lands.
- **Several trees in one process**, a session registry, or a save endpoint. Several trees are
  several processes; `core/session.py` writes after every mutation, so saving is not something
  a client does.
- **Appending text after a generation.** Needs more thought first, and nothing is blocked on
  it.

## Pending fold-in from `BEYOND-MVP.md`

Deferred entire, to be reviewed once the v1.0 cycle above is locked in, and then removed and
recreated rather than edited. Its sections, so the review has a checklist: reads and
annotation; the reading surface's next layer; generation control; the prompt cache and
byte-exact replay; streaming; embeddings and distances; the generation controller; sibling
divergence; token replay instead of re-tokenisation.

Two of those have already come due in a form that document did not anticipate. The prompt
cache argument was settled from the research thread and is recorded in `CLAUDE.md`. Token
replay now has three entries on its ledger rather than one, the third being the UTF-8
regrouping that silently corrupted records rather than merely refusing them — still not worth
pulling forward, but the ledger is what will eventually decide it.
