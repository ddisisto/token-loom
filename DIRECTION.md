# token loom — direction

**The living document for where this goes, and the authority on it.** It describes what is
wanted. It carries no status and no schedule — nothing here is ticked off, ordered or
sequenced, because a document that tracks progress becomes a roadmap and stops being a thing
that can be locked and pointed at. The order of work, and the only ticks anywhere, are in
`ROADMAP-v1.0.md`, which is deleted when v1.0 lands.

`ROADMAP.md` was the road to the MVP and is superseded; it stays only until whatever survives
of it is here. `LATER.md` is its companion in the other direction — what has been considered
and set aside, kept so the thinking is not done twice, and named there rather than here
because nothing in this cycle turns on any of it.

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

## What exists now

The MVP, as one thing rather than the stages that built it. `core/` is the substrate — a trie
over bytes with tokens as a per-span overlay, the bulk store beside it, the operations and the
derived reads. `loom.py` drives it from the command line and `api/` serves it over HTTP; `web/`
is a client of the API and reaches the core through nothing. Four executable checks:
`core_test.py`, `api_test.py` and `node web/web_test.mjs` need no model, `llama_test.py` needs
the server. Inference is local only, `llama-server` with Qwen2.5-7B base on the native
`/completion` endpoint. One writer per tree directory, enforced by the kernel.

Its surface is a path read top to bottom with a horizontal band of cards inserted at the fork
the reader is standing on: two continuations offered per move, one selected, the path above
and below drawn as two clipped copies of a single layout so that nothing reflows when the band
moves. It works and is in daily use.

**Treat it as the baseline being replaced rather than a stage that was passed.** Everything
below came out of reading through it for an hour, which is an instrument that planning and
testing are not — the band was correct against its own document and wrong against the reading.

Nothing is open at the format level. Nothing below opens one.

## v1.0 — the surface becomes a place

**The reader is not reading one path with alternatives at hand. They are reading across
several paths that already exist.** A card is a preview — something you glance at and then
commit to. A column is a place.

**Reading one path straight through is the floor.** It has to work, and it has to look as good
as any tool that does only that. It is not the reason to use this one. **Branching is what the
design has to get right**: asking for an alternative at a point, holding several beside each
other, and reading down whichever of them earn it. What a reader does with a branch afterwards
— keep it, prune it, carry it a paragraph or a page — is theirs, and the tool holds no opinion
about it.

What that buys is navigation across the what-if questions the reader actually holds. The
deaths — end-of-text, the context wall — stop being terminal and become backtrackable features
of a landscape. Repeated short cycles and mantras become things you can hold beside each other
and see as the same shape. Attention accumulates into paths worth re-reading.

### One act, one generation

**A navigation act that reaches past the tip produces one continuation.** Not two, and never a
number chosen by the surface on the reader's behalf.

The MVP generates two, so that the tip is a choice rather than an announcement. The cost of
that is breadth nobody asked for: every move leaves a sibling behind, forks accumulate wherever
the reader merely walked, and the tree stops being an account of what was wanted. With one, a
reader who reads forward gets a single path however far they go, and every fork in the tree is
one somebody asked for.

Two consequences, both simplifications. *Asking for one more* and *carrying on* become the
same request at different positions, rather than two shapes with different `n`. And "has every
alternative here been seen" — a question `FRONTEND.md` keeps the path and token layers apart in
order to keep answerable — stops being a question at all.

One consequence that is a cost, and belongs to the design rather than to this document. The
MVP's second continuation is what the reader had to look at while the first was still
generating, and what sat ready beside a tip that died on end-of-text. Both of those mitigations
go. Generation stays an ordinary blocking call, so what replaces them is the surface being
honest about the wait and about the death.

**Breadth therefore has to be the most reachable thing on the surface.** Nothing produces it
any more unless it is asked for, so if asking is even slightly buried, a reader drifts into
linear use and never reaches what the instrument is for.

### The seam is a location without length

The fork the reader is standing on is a **position**, not a section. Nothing is lifted out of
the prose, nothing is drawn in two places, and no stretch of text belongs to a third region
between above and below.

The MVP's target *is* a section — the text leaving the fork, taken out of the flow and drawn in
the band — and that single fact is the whole of its layout machinery. A horizontal band with
height has to be inserted mid-flow, so the flow is cut in two and the lower half pushed past it:
the clip polygons, the second copy of the path, the line-box measurement, the translate, the
shift arithmetic. All of it is paid for the band's *extent*. A seam with no extent needs none of
it, and two accepted costs go with it — a selection dragged across the target no longer picks
up an invisible copy, and find-in-page no longer matches everything twice.

The address bar already speaks this model: `#s7+31/1` is a position and which of its children,
and never a section. That grammar describes the seam better than it described the band.

### The seam is a station, and the text moves past it

The seam sits at a fixed place on the screen. The path moves through it.

**Above it the path runs alone at the centre. Below it, more than one path side by side.**
Reading down through the centre is reading a paragraph — not a paragraph with a labelled join in
it — because **flanking columns are the fork, and their absence is its absence.** Nothing has to
be drawn on top of the sentence to say what the geometry already says.

The centre can join the text above directly, because the text it continues sits above it at the
same measure and the same x. Nothing above a flanking column is the text *it* continues, so it
has no line to resume.
Since a branch point generally falls mid-line and often mid-word, the line holding it belongs
to the **above**, and a flanking column starts flush at the next line box; the centre may
complete that line as prose, since the centre is the path and the flanks are not. No byte is
rendered in two places.

### An alternative sits beside its own text

The lanes flanking the path are not empty above the seam. **An alternative is drawn beside the
fork it leaves, at that fork's own height**, and it stays there as the reader carries on past.

So the page reads in two directions that mean different things. Down the centre is the path.
Across, at any height, is what else was on offer at that point. A fork passed an hour ago still
has its unchosen branches beside it, aligned with the prose that was chosen instead, and
scanning up the page is scanning back through the choices that made it. That is the multiversal
read, anchored to where the reader is rather than drawn as a diagram somewhere else.

This asks for no new word and no new state. `FRONTEND.md` already defines an alternative as a
continuation on offer at the tip **or one of the branches leaving a fork the path has already
passed through** — the second half of that has simply never had a place on the screen. What one
holds is derived exactly as a column's content is: its own text to its own next branch point,
and then a summary. Nothing about what the reader happened to have on screen earlier is
remembered, so the page survives a reload and two readers at one address see the same thing.

**An alternative occupies the band between its own fork and the next fork on the path**, clipped
there rather than flowing past it. Alternatives that pushed each other down would destroy the
one thing vertical position means here, and clipping also puts the page's own rhythm in charge
of how much is shown: a stretch the reader moved through quickly gives its alternatives a
sliver, one they dwelt on gives them paragraphs.

Two things follow, and both remove something rather than adding it.

- **Nothing collapses at the station.** The alternatives at the current fork are not a different
  object from the ones above them — they are the same object with no next fork below them yet,
  which is why they run to the foot of the page. Scrolling past and generating onward is what
  gives them a bottom edge. So there is no transformation to design at the seam and nothing that
  has to animate into a mark as it crosses.
- **A fork the path has passed needs no marker.** It is marked by there being something beside
  it, and how many ways it went is legible as how many lanes are occupied. The MVP's margin chip,
  `⑂3/4`, says that as a glyph; this says it as substance, and the glyph has no job left.

**Reading one is going there.** An alternative on the page is a preview — glance at it, then
commit — and committing is the operation the surface already has: the seam moves to that fork
and selects that branch. Nothing gives a preview a scroll region of its own. The page's scroll
is the reader's input and the trigger for generation, so a wheel event captured by an inner box
is a navigation act that did not happen.

**This stays sparse only because one act makes one generation.** Under two, every step of the
path would leave an alternative behind and the lanes would be a wall of text from root to tip.
The two decisions need each other.

### One measure throughout

The path above and every column below share a single measure, and the page is laid out on that
grid throughout.

This follows from the station rather than being chosen beside it: text crossing the seam must
not re-wrap, and it re-wraps the moment the width above differs from the width below. On a
1280px window that is somewhere near 25rem against the MVP's 34rem — a better measure for prose
rather than a compromised one.

How many columns are visible, and whether what flanks the centre is fully readable or peripheral,
is left to the design. This document commits to *more than one*.

### The viewport is the input

**Up and down scroll the page, as they do in any document.** The cursor follows the viewport
rather than the viewport following the cursor: as the reader scrolls, the cursor moves to the
span end the seam has reached. Scrolling past the tip is what asks for more text.

This is `FRONTEND.md` constraint 6 carried to its end rather than a break with it. That
constraint already conceded, after a session of use, that pressing up or down *is* the reader
moving the viewport. Going the rest of the way lets the concession retire and promotes what it
protects to be the whole of the constraint: **text arriving must never move the page.** Under a
station that stays exactly true — the page grows below a stationary viewport, and nothing chases
a target around.

Four things the design has to carry with it:

- **Position sets the cursor; direction and rest trigger generation.** Keeping them apart is
  what makes the cursor — and therefore the fragment, which is written on every draw — a pure
  function of where the page is. A cursor that depended on which way the reader arrived would
  differ between two readers at the same scroll offset.
- **Generation triggers on the scroll coming to rest**, past a threshold, once per rest and
  never queued. A keypress is discrete; a trackpad fling is inertial and overshoots. Every
  generation spends real time on the GPU and writes durable spans, so a fling is too weak a
  signal of intent to spend three of them — the same standard deletion is held to.
- **The runway below the tip is a design object.** A page cannot be scrolled past its own
  bottom, so reaching past the tip means there is manufactured empty extent there to reach into.
  Tying its height to the chunk size makes that dial spatial: the gap below the tip is roughly
  what the next chunk will fill, so the control that sets pacing also sets how far the reader
  reaches for more. A token count is not a fixed number of lines, so the arriving text will
  over- or under-fill it and nothing may depend on it landing flush.
- **The cursor write coalesces rather than queues.** It moves continuously now rather than once
  per keystroke, and `PUT /api/cursor` rewrites the tree file whole. The client's single pending
  slot is the right mechanism, with the right behaviour for a stream of positions: drop all but
  the last, and never stand ahead of a generation.

### Across is the branch axis

Left and right move among the columns at the seam. Where there is only one — which is the
ordinary state, since one act makes one generation — **left or right asks for an alternative at
that point.**

That is the gesture the whole instrument turns on, and it is why it belongs on a key that is
always live rather than on a control somewhere. The two axes now differ in kind as well as in
direction: vertical is continuous and is the reader's viewport, horizontal is discrete and is
the reader's choice.

Selecting a column routes the path onto it, and the seam does not move while it happens: what
changes is what lies below the station, not where the station is.

### What a column holds

**Everything down to the next actualised branch point, and then a summary of what diverges
there.** No branch is privileged over another. Where the reader has generated or kept only one
path, that path simply shows in full.

The centre differs in one way only: it continues past its branch points along **the path to the
cursor**, so the reader's own path reads through to its end. The cursor is already durable, in
the tree, so this records nothing new.

That is the whole of it, and it is what makes the design cheap. There is no notion of a branch
having been looked at, no per-branch memory of where the reader last was, and nothing anywhere
that has to be written down to make a column show the right thing. A column shows what is
actually there.

What a column says about what lies beyond its own foot — how much has been actualised down
there, in depth and in breadth, and whether it ends in a wall — is a real design question and
needs no new read: the run tree the API already sends is the whole subtree, so the answer is a
client-side derivation over data that is on hand.

**One rule, and it governs the lanes too.** An alternative beside a passed fork is a column with
a bottom edge; a column at the seam is an alternative with nothing under it yet. The surface is a
spine with alternatives hanging at every fork it passes, and it has one rule for what any of them
holds.

### End-of-text is not special

A generation that stops on end-of-text is a span like any other, and the tip it leaves is a
place to ask again from. End-of-text emits no bytes, so the path is unchanged by it and the
next call from that tip sends a byte-identical prompt — asking again is a genuine second draw
at the same position rather than a retry of a failure. The model may well answer the same way,
and repeatedly; then that is the answer, and it is one worth being able to see.

**The share of draws that come back as end-of-text is a property of the prior**, in the same
family as everything `RESEARCH.md` asks about. Special-casing the tip to stop offering would
spend that measurement to save a wait.

What the surface owes the reader here is not a restriction but a mark: **why a span stopped,
read off its recorded terminator and shown whenever that is not `length`.** Nothing is derived
and nothing is counted — the reason is on the wire on every span already, and the same mark
covers the case that matters more, a span cut short by the context wall.

### Deleting is ordinary, and always asked for

Delete is a normal gesture beside the others rather than an exceptional one. **Nothing is
deleted on the reader's behalf** — not on a heuristic, not on inattention, not on a rule about
what was never looked at.

Soft delete is already the primitive: `tree.live` keeps every byte on disk and merely out of
view, so `loom.py show -a` still sees the whole record and a committed experiment tree stays
complete. The tree becomes an account of what the reader wanted without becoming a lossy one.

### What the format is asked for

Nothing. Positions stay the only durable handle, the cursor stays the only piece of reader state
in the tree, and every derived thing above — runs, depth, breadth, what a column holds — is
derived from what is already sent. That is what lets the surface be rebuilt without the format
moving, and it is worth checking any later idea against.

## What has to be proved

None of these is settled by writing about them, and the first is the reason to build a crude
version early rather than a considered one late.

- **That the single rule holds on a real page.** A spine with alternatives hanging at every fork
  it passes is a large simplification if it survives contact and an over-generalisation if it
  does not. It is cheap to find out and expensive to assume.
- **Lane assignment where there are more alternatives than lanes.** The same problem the column
  count has at the seam, but at a passed fork there is no room to be peripheral in, and stacking
  them vertically makes it bite more often.
- **An alternative that itself forks, in a band a few lines tall.** The rule says content and
  then a summary; in a short band the summary is the whole of it. A band saying only *three ways
  from here* may be the right degradation or may be noise, and only a real page tells which.
- **What a lane does while a generation is running.** The alternatives at the seam are the thing
  being generated and the ones above are static, so one lane holds two states at two heights.

The token flyout is deliberately not among these: it survives as the finer grain and is taken up
on its own, once the layout it sits in exists.

## Out of scope for v1.0

Recorded so they are not re-litigated, not because they are rejected.

- **The research thread**, parked deliberately. The instrument works; the questions are getting
  better as the patterns become visible, and they are better asked after more use than before
  it. `RESEARCH.md` and `experiments/` stay exactly as they are.
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
- **Vacuum and compaction of the append-only store.** `FORMAT.md` holds the one hard constraint
  it must satisfy when it lands.
- **Several trees in one process**, a session registry, or a save endpoint. Several trees are
  several processes; `core/session.py` writes after every mutation, so saving is not something a
  client does.
- **Appending text after a generation.** Needs more thought first, and nothing is blocked on it.
