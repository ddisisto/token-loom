# The front end

What it is, what the reader does with it, and the constraints a wireframe gets checked
against. `ROADMAP.md` Phase 3 carries the shape and how it bears on the phases before it;
the specifics are here. `INTERACTION.md` is what gets checked against them — the elements,
the gestures, and what each action does.

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

### One context, shared

The model's context is the active path, whole and from the root — not a window onto it, and
not a length chosen against it. What the reader can scroll through is what the model was
given, and the two are one object.

That is a claim about attention rather than about buffers. A reader building an intuition for
how a model branches is trying to relate what came out to what went in, and every byte of
difference between the text on the screen and the text in the prompt is a place where that
relation has to be taken on trust instead of read. Holding them identical is what makes the
surface an instrument: the prior is not described anywhere, it is the thing being scrolled.

**The symmetry holds behind the tip and breaks at it**, and the break is where the reader's
work is. Each alternative on offer was generated from the shared prefix and from nothing
else — no continuation saw its sibling. So at the frontier the reader holds more than any
model did, which is what makes choosing among them a contribution.

Two things follow, both consequences rather than settings:

- `prompt_length` is fixed at a value larger than any path can reach, so the slice always
  resolves to the root and every span records the whole path as its context. It is sent as
  one fixed number and never as the path's measured length, which would mint a fresh interned
  parameter set on every single generation — the trap `FORMAT.md` names when it explains why
  the slice *length* interns and the resolved start sits on the span.
- The prompt only ever grows by appending, so a prefix-matching cache hits completely and
  keeps hitting.

### Chunk size, the one dial

How much text arrives per choice is the reader's, and it is the only generation parameter the
surface exposes. Thirty-two tokens to start.

It stays available and never moves. Changing it applies to the next call and to nothing
already made, so a session can be steered coarsely and then finely without starting over. A
tree therefore records where its reader changed pace, since each value interns as its own
parameter set — which is interning working as intended rather than the trap above.

It is exposed on a distinction rather than as a carve-out. Temperature, top-p and top-n change
what the model does; chunk size changes how much lands between one choice and the next. It is
the one parameter whose effect is felt as pacing, and pacing is a reader's business. That it
is nonetheless `n_predict`, interned with the rest and recorded on every span, is why the
exception is written down rather than assumed.

**It sets how finely the reader steers, not how long the session runs.** The wall below is a
count of path tokens, so the text a session holds is the same either way: thirty-two-token
chunks give somewhere near five hundred choices across it, eight-token chunks two thousand
across the same text. Small chunks are a reader who wants the tiller, large ones a reader who
wants to read. Neither buys more session.

It is also the opposite end of the call from the slice, and the two are easy to run together:

| | direction | unit | value |
| --- | --- | --- | --- |
| `prompt_length` | what goes in | bytes of path | fixed above any path the context can hold |
| `length` | what comes out | tokens generated | the dial, thirty-two to start |

### The end of a session

A shared context has a size, and the path outgrows it. At the sixteen-thousand-token context
the local server is set up with, that is somewhere near five hundred continuations of
thirty-two tokens: after it, the prompt does not fit and `llama-server` refuses it outright.

The core is deliberately unforgiving there. An over-long prompt raises `Truncated` and
nothing is generated at all, because a span recording a slice the model never saw would be
the one kind of lie immutable bytes exist to prevent. So the wall is real, and the surface's
job is to be honest about approaching it. What to do when it arrives — slide the window,
restart from a summary, branch to a fresh root — is deferred, and it is the only case that
would want the slice to stop being the whole path.

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

Returning to a fork behind the tip does not shorten the path. Choosing the alternative
already taken changes nothing; choosing another re-routes there and then carries forward, to
the deepest point previously visited down that branch. What leaves the path stays on the tree
and is reached by coming back. Moving between alternatives resolves immediately either way,
since all of them were generated when the fork was made.

Where the path resumes after a re-route is view state rather than a record. It keys off
`(span, offset)` like everything else, and a session that has forgotten it lands at the fork,
which is the honest fallback rather than a degraded one.

**What a fork offers is runs, not spans.** They are the same thing wherever a span was
generated whole, and they come apart at a fork inside a span — where one alternative is the
remainder of a span that already exists. `core/ops.py` computes the distinction and the API
carries it, so a client that renders the children of a run node is right in both cases
without knowing there were two.

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
makes it a tip like any other, and the forward reflex applies to it unchanged. Nothing is
divided to make room for it: the fork that appears is between the alternate and the remainder
of the span the reader was reading, and that remainder becomes a sibling of it. So prose that
had no choice point in it acquires one, mid-span, and the path the reader was on stays whole
and reachable by coming back to the fork.

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
request, which is what keeps each span's record complete. Chunk size aside, nothing in the
surface names a parameter or offers to change one.

**Waiting is expected and is not designed around.** Generation blocks for as long as it
blocks, and latency is not this document's problem. Two structural properties make it
tolerable. Every movement whose answer already exists resolves immediately, so only movement
past the tip waits — a reader flicking between alternatives, scrolling back, taking an old
fork or asking a token what else it could have been never waits at all. And the prompt cache
is on in the core, which makes reading forward its best case: each continuation extends a
prompt the server processed moments ago.

That second property does not decay, which it would if the slice were a window. Because it is
the whole path, reading forward appends and hits completely every time. Branching backwards
hits as well: a generation from an earlier position sends a prefix of what was just
processed. Any two generations in the tree share their prompt back to their common ancestor,
so a jump costs in proportion to how far it jumped, and the common case costs nothing.

## Constraints

Numbered so that a wireframe can be checked against them one at a time.

### From the instrument

1. **The seed is the only text the reader supplies.** One given span at the root, once.
2. **Every generation is a consequence of a navigation act.** Movement is the trigger.
3. **The model's context is the active path, whole.** What the reader can scroll through is
   what the model was given. The scrollable extent, not the visible region — the window onto
   the page is the reader's business and no part of the claim.
4. **Parameters are chosen at startup and stay out of the surface, with one exception.**
   Chunk size is the reader's, because its effect is pacing rather than behaviour. Everything
   else is a condition of the session and is named nowhere in it.
5. **Movement whose answer already exists resolves immediately.** Only movement past the tip
   waits on the model.
6. **The viewport is the reader's.** It moves when the reader moves it. Text that arrives
   lands where it belongs and waits to be scrolled to.

### From the substrate

7. **Positions are the only durable handle, and the surface addresses in them throughout.**
   Runs are derived and renumber the moment a branch appears, so every piece of view state —
   which alternatives have been seen, where the reader was last, what is marked — keys off
   `(span, offset)`. So does the rendered text: a point in the prose resolves to a byte
   offset in a span, which is what keeps the finer grain reachable.
8. **The client never diffs.** It issues every mutation, so it already knows what changed:
   the request says where, and the response's `created` names what appeared. The whole-tree
   response is the new source of truth and not the change description. Updates into the
   reading surface are therefore targeted by construction, and scroll stability follows from
   that rather than needing to be defended.
9. **One writer, and generation holds it.** Every mutation serialises through the server's
   lock, including the model call. The client owns one request queue and keeps speculative
   work from being enqueued where a request the reader is waiting on could land behind it.
10. **A span in flight is a state to render.** Provenance is written before the model is
    called, and a batch saves per continuation — so with two continuations, the first is
    readable while the second is still being generated. Showing it then is honest, and it is
    the same render path that later work would drive.
11. **Reading works with no model server.** Every route except `GET /api/settings` answers
    without one. Opening a tree and reading it through is a property of the format, and the
    surface keeps it.
12. **Refusals reach the reader as themselves.** A prompt that does not fit is refused
    outright and generates nothing; so is a response that lost bytes, and a request with no
    model server behind it. Each is reported and dismissed rather than worked around or
    retried quietly. Seeing the context wall *before* it arrives is later work.

### From the deployment

13. **One process.** The API serves the front end's files itself, on its own origin. One
    tree per process is what the server already promises, and the reading surface is its
    only writer.
14. **No build step.** ES modules and custom elements, served as they are written. The
    project's dependency floor is a thing worth keeping, and the front end has no problem
    that needs a toolchain to solve.

## What the core needs

Nothing. The front end sits on the API, which sits on the substrate, and it asks the
substrate for no change at all.

> **Two things, as it turned out, and the claim above is left standing so the correction has
> something to be a correction to.** Both were found by building against it, both are small,
> and neither is the core having been wrong — they are places where this document's own
> position needed the core to say what it already meant.
>
> - **A zero-width run node is spliced only when it has children.** The splice exists to lift
>   a fork point's branches into its parent's list; a childless one has none to lift, so
>   splicing it was a deletion, and what it deleted was a span in flight and one completed
>   with no bytes. Constraint 10 says the first of those is a state to render, and a client
>   cannot render what the layout it was handed does not mention. The CLI reaches neither
>   state, because it renders only finished generations.
> - **`prompt_length: null` means the whole path, and is now the default.** "One context,
>   shared" above asked for a fixed sentinel above anything the path can hold. That was the
>   wrong shape and the section says why in its own next sentence: the value interns, so
>   every time the guess had to be raised, the tree would record a change of framing that
>   never happened. A third answer costs nothing and cannot drift.
>
> Neither reached the format's decisions and neither needed a version bump. The estimate this
> section was making — that the front end sits on the substrate rather than reaching into it
> — held; what did not hold was "no change at all", which was a stronger claim than the
> argument supported.

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

- **Reading past the context window.** The one case that wants the slice to stop being the
  whole path, and with it the only reason to find out how a prefix-matching cache behaves
  when the window slides.
- **The slice viewport** — seeing what was in context for a span, and re-selecting the range
  to generate again under a different framing. It is the same idea as the symmetry above,
  made adjustable: the shared object stops being the whole path and becomes a choice.
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
