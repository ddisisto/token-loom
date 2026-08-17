# The front end

What it is, what the reader does with it, and the constraints a wireframe gets checked
against. `ROADMAP.md` Phase 3 carries the shape and how it bears on the phases before it;
the specifics are here.

Written greenfield. The front end has no code, and nothing below is described by reference
to anything that came before it.

## The instrument

A given goes in at the root. Everything after that is navigation, and generation happens as
a consequence of navigating.

There are two acts in the thing:

- **supply** — the model produces continuations
- **selection** — the reader chooses among them

The reader's agency is entirely in the second. Supply runs at the rate the reader consumes
text, triggered by movement, and stays out of sight.

That gives one test, and every feature is held to it: **does it serve seeing the
alternatives and picking one?** Most of what an instrument built on this core could offer
does not, and is therefore later work rather than this work. What is left is the smallest
thing that is the instrument rather than a demonstration of it — one seed, one surface, and
a reader moving through what the model offers.

The appeal is that the friction is nearly all gone. Building an intuition for how a model
branches under itself currently costs a working knowledge of positions, spans, temperature
and top-N. Here it costs scrolling.

## Vocabulary

`FORMAT.md`'s terms keep their meanings: **span**, **position**, **run**, **batch**. Three
more belong to the reading surface:

- **the active path** — root to a chosen tip, as one continuous stretch of text. It crosses
  several spans and several runs. A run is a derived stretch with no branch point in it; the
  active path is a chain of them, chosen by the reader.
- **the tip** — the end of the active path. Where the reader is, and where generation
  attaches.
- **an alternative** — one continuation on offer at the tip, or one of the branches leaving
  a fork the path has already passed through. Unqualified it means the path layer; a token's
  alternatives are the finer grain below, and are always named as such.

## Reading

The reading surface shows the active path as continuous prose, root to tip.

**Behind the tip, reading flows.** Every fork the path passes through is a choice already
made: the text carries on through the branch that was taken, and the fork is marked where it
sits so the other way stays reachable. Scrolling back over what has been read is reading.

**At the tip, reading stops.** Nothing continues from there — that is what makes it the tip
— so the path ends in the alternatives on offer, and the reader picks one. Choosing extends
the path and moves the tip forward.

The division is the whole of the interaction, and it is why the same surface can be both
relaxed and pointed. Behind the tip there is nothing to decide and the reader is carried
along by prose. At the tip there is nothing but the decision.

Taking a fork behind the tip makes that fork the new tip: the path is re-chosen from there,
and what was read past it is still on the tree and no longer on the path. Moving between
sibling alternatives at any fork resolves immediately, because both were generated when the
fork was made.

### The finer grain

Every sampled token carries the alternatives the model ranked and did not take. They are in
the store already, so reaching one costs no generation at all — the fastest move the
instrument has.

They are **potential rather than actual**. The surface does not mark them and the text reads
as text; any token can be asked, and answers with what else it could have been. Taking one
anchors a branch at that token's offset, and that fork becomes real — sparse, and only where
a reader made it.

Two layers, and they do not interact:

- **the path layer** — spans, siblings, tips. An alternative here is one of the continuations
  a generation call produced, and this is the layer the reflexes below operate on.
- **the token layer** — always present, never marked, revealed on request. It makes forks and
  participates in nothing.

Keeping them apart is what lets "every alternative here has been seen" stay a question with
an answer. It is a question about the path layer, where alternatives are countable and few.

Taking a token alternative gives a span one token long with nothing continuing from it, which
makes it a tip like any other, and the forward reflex applies to it unchanged.

**What this costs from the start is one property of the surface**: a point in the rendered
prose is always resolvable to `(span, byte offset)`, and a span is never an opaque string.
Token boundaries themselves are a per-span read, fetched when a reader asks for them, so
nothing is materialised for text nobody interrogates. The addressing underneath has to be
there from the first version, though — it is not something a finished surface can be opened
up to accept later.

## Generation

Two reflexes, both consequences of movement.

- **Forward.** Choosing an alternative extends the path, and the new tip has nothing
  continuing from it. Generating continuations is what makes it a place to stand and read
  on from.
- **Breadth.** A reader who has looked at every alternative at a tip and wants none of them
  asks for another, and gets it. "Every alternative" counts the path layer — the
  continuations of a generation call — which is what keeps it a small number.

**Two continuations per call to begin with.** Two is enough for the tip to be a choice
rather than an announcement, and small enough that the wait is one call's worth. A third and
beyond arrive on request. Generating them ahead of the request — so a reader who exhausts
two finds a third already there — is available once the feel of two is known, and is a
tuning decision rather than a structural one.

**Parameters are chosen once and stay chosen.** `GET /api/settings` at startup gives the set
the server would fill in; the client holds it for the session and sends it whole with every
request, which is what keeps each span's record complete. Nothing in the surface names a
parameter or offers to change one.

**Waiting is expected and is not designed around.** Generation blocks for as long as it
blocks, and latency is not this document's problem. Two structural properties make it
tolerable. Every movement whose answer already exists resolves immediately, so only movement
past the tip waits — a reader flicking between alternatives, scrolling back, taking an old
fork or asking a token what else it could have been never waits at all. And the prompt cache
is on in the core, which makes reading forward its best case: each continuation extends a
prompt the server processed moments ago.

That second one has a limit worth predicting now and probing before it is relied on. The
slice is the last `prompt_length` bytes ending at the tip, so while the whole path is shorter
than that the prompt only grows and a prefix-matching cache hits completely. Once the path is
longer, the window slides, the prompt's first token changes, and the hit is expected to
collapse. At the default six thousand bytes that arrives somewhere around forty continuations
of thirty-two tokens — early enough in a reading session to be felt. Whether it behaves that
way is a measurement nobody has taken, and it is cheap to take.

## Constraints

Numbered so that a wireframe can be checked against them one at a time.

### From the instrument

1. **The seed is the only text the reader supplies.** One given span at the root, once.
2. **Every generation is a consequence of a navigation act.** Movement is the trigger.
3. **Parameters are chosen at startup and stay out of the surface.**
4. **Movement whose answer already exists resolves immediately.** Only movement past the tip
   waits on the model.
5. **The viewport is the reader's.** It moves when the reader moves it. Text that arrives
   lands where it belongs and waits to be scrolled to.

### From the substrate

6. **Positions are the only durable handle, and the surface addresses in them throughout.**
   Runs are derived and renumber the moment a branch appears, so every piece of view state —
   which alternatives have been seen, where the reader was last, what is marked — keys off
   `(span, offset)`. So does the rendered text: a point in the prose resolves to a byte
   offset in a span, which is what keeps the finer grain reachable.
7. **The client never diffs.** It issues every mutation, so it already knows what changed:
   the request says where, and the response's `created` names what appeared. The whole-tree
   response is the new source of truth and not the change description. Updates into the
   reading surface are therefore targeted by construction, and scroll stability follows from
   that rather than needing to be defended.
8. **One writer, and generation holds it.** Every mutation serialises through the server's
   lock, including the model call. The client owns one request queue and keeps speculative
   work from being enqueued where a request the reader is waiting on could land behind it.
9. **A span in flight is a state to render.** Provenance is written before the model is
   called, and a batch saves per continuation — so with two continuations, the first is
   readable while the second is still being generated. Showing it then is honest, and it is
   the same render path that later work would drive.
10. **Reading works with no model server.** Every route except `GET /api/settings` answers
    without one. Opening a tree and reading it through is a property of the format, and the
    surface keeps it.

### From the deployment

11. **One process.** The API serves the front end's files itself, on its own origin. One
    tree per process is what the server already promises, and the reading surface is its
    only writer.
12. **No build step.** ES modules and custom elements, served as they are written. The
    project's dependency floor is a thing worth keeping, and the front end has no problem
    that needs a toolchain to solve.

## What the core needs

Nothing. The front end sits on the API, which sits on the substrate, and it asks the
substrate for no change at all.

That is worth recording rather than assuming, because it was nearly not true. The one thing
this design wanted from the core was the prompt cache on, since reprocessing a
fifteen-hundred-token prompt before every continuation is most of the wait between choices.
The research thread got there first and from the other side, in `ca1373d`: the cache is a
pure function of the prompt tokens, no seed reaches it, so warm and cold are two draws from
one distribution rather than one right answer and one wrong one. `cache_prompt` is on for
everything, the research thread's findings are stated as distributional, and
`BEYOND-MVP.md` now holds the routes back to byte-exact replay. So the front end inherits a
fast core and the question never reaches it.

**Research trees and reading trees separate by path, not by label.** Committing an
experiment's tree beside its write-up at `experiments/001-temperature/` is the convention as
of `86036ca`, and `data/` is ignored scratch, which is where a reading session lands. The
separation is therefore already made and already enforced by where a file sits, at the
granularity that matters: a whole tree is one thing or the other. It needs no field on a
span, no change to the format, and no discipline beyond not pointing the reading surface at
an experiment. Opening one read-only, or read-write on a copy, both keep it.

The question that a per-span label would answer comes back if either of two things does:
generation the reader did not ask for, which is the eager third alternative and is deferred;
or a reading tree becoming an artefact somebody cites. Neither is now, and a settings key
marking the initiator stays available for free whenever one of them arrives — parameters
intern by hashing an open dict, so an unrecognised key travels with every span that carried
it without reaching the request or the validator.

## What follows this

The order things arrive in after the MVP lands, most likely first:

- **The slice viewport** — seeing what was in context for a span, and re-selecting the range
  to generate again under a different framing.
- **Parameter control**, and with it sweeps and named batches.
- **Bookmarks and tags**, anchored to positions.
- **Sibling divergence** as a read the surface can show.
- **Streaming**, which is the only one of these that needs generation to stop blocking.
- **Reading a research tree**, read-only or read-write on a copy. Nothing in the surface
  prevents it and nothing here is designed for it.

## What this implies for the other documents

In principle. None of it is detail yet.

- **`ROADMAP.md`** — Phase 3 becomes a short high-level statement and a pointer here. Its
  current text describes changes to a front end that has since been removed, so it does not
  survive as a description of this one.
- **`BEYOND-MVP.md`** — receives the list above.
- **`CLAUDE.md`** — the stack note counts the clients on the core. The front end is a client
  of the API rather than of the core, which is a third shape and worth being exact about.
- **`README.md`** — the state paragraph, and the table of where to start.
- **`CLAUDE-HANDOVER.md`** — the two-writer thread is unchanged and stays deferred. The
  reading surface is the only writer to its own tree, and the separation of `data/` from
  `experiments/` is what keeps it away from anything that would hurt to lose.
