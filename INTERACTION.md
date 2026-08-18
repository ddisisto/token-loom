# Interaction

What is on the screen, what a reader does to it, and what each action does.

`FRONTEND.md` holds the concept and the constraints; this is the thing checked against them.
The two are kept apart deliberately — the constraints should outlive several passes at this
document, and folding the specifics in would leave nothing outside them to hold them to.

Numbers here are starting values, and the parts of it that are guesses are the parts that
will move. The first pass was written before there was anything to poke at; this is the
second, after a session of using it. What that session moved was the layout and nothing else
— the acts, the gestures and the calls behind them all survived contact, which is worth
recording because it is the claim a first pass is least entitled to make.

## The seed

On load, against an empty tree, three elements and nothing else.

- **The input** — a `contenteditable` region, ten lines tall to begin with, growing with what
  is typed into it.
- **The chunk slider** — vertical, top-aligned, to the right of the input. Five stops — 8,
  16, 32, 64, 96 tokens — starting at the middle. The number appears for 1.5 seconds when it
  changes and the control is otherwise bare.
- **Submit** — icon only, bottom-aligned, to the right of the input.

Submit requires at least one character and validates nothing else. There is no tokenizer in
the client, so a seed too long for the context is found out by the server refusing it, which
it does cleanly and with a message worth passing straight through.

On submit the input is replaced by the path it became: the same text, rendered as the first
run, with no editing affordance anywhere near it. That is the format showing through rather than a decision made here: recorded bytes are
immutable, there is no edit route, and the only way to change a seed is to delete it and
start again.

Then two calls — `POST /api/author` with `{at: null, text}`, and `POST /api/generate` from
the new span's tip with `n: 2`.

## The reading surface

**Three parts, and the layout is what happens between them.**

- **above** — the path from the root down to the fork the reader is standing on
- **the target** — that fork, opened out across the page
- **below** — the path onward from it, to the tip

Outside the target the two ends **meet on one line**, where the fork falls mid-line, which is
the ordinary case. The path is one stretch of prose and the join is invisible: reading behind
the tip is reading, and a line break every time a generation ended would turn a page of prose
into a stack of stripes. At the target that meeting comes apart — the sibling stack takes the
full horizontal width of the page, and above and below move *away from it* vertically, and
only vertically.

**Nothing reflows, ever.** Not when the target moves, not when it opens, not when it closes.
That is the whole of the mechanism below and it is not a performance concern: text that
re-wraps as the reader navigates is text they have to find their place in again, and the
instrument is for reading. Each part may translate; none may relayout.

### How the parts come apart

The path is laid out **once**, as one prose flow, and drawn **twice**. Both copies share that
one layout exactly, because they are the same content at the same width.

- The **above** copy is clipped to an L: every line before the target's line, plus the part of
  the target's line that precedes the fork.
- The **below** copy is clipped to the complement: the rest of that line, and every line
  after.

The two L-shapes tile the original with nothing over and nothing missing, so with no
displacement they are indistinguishable from the single flow they came from. Opening the
target translates the below copy down. Moving the target animates two clip paths and one
offset, and no glyph is ever placed a second time.

The alternative — splitting the flow into two blocks and indenting the second to meet the
first — was rejected for one reason: the indent is a function of where the target is, so
every retarget re-wraps everything below it. The clipped pair costs a second copy of the
path in the DOM, which at a full context is tens of kilobytes, and buys the invariant
outright rather than during a movement only.

**One thing to measure before building this**: whether `clip-path` clips hit-testing as well
as painting. If it does, each copy is clickable only where it is visible and the token flyout
needs nothing; if it does not, the invisible half of each copy will answer clicks meant for
the other, and the fix is a hit-test against the clip in the click handler. It is decidable
in a minute and is not worth reasoning about.

### The viewport does not move, and does not need to

Constraint 6 stands unamended: nothing scrolls the page on the reader's behalf. It survives
because **every way of moving the target is already local**. A chip is clicked, so it was on
screen; up and down step one fork. The target therefore never jumps somewhere the reader was
not already looking, and the above copy does not move at all when a target opens — so the
line the reader's eye is on stays exactly where it was, and what moves is what is below it.

This is the reason to prefer the above copy as the fixed one. Anchoring the top of the page
instead, and letting the target slide, would make every retarget a small unrequested scroll.

### The margin

To the right of the path, one chip per fork: `⑂3/4`, which alternative is active of how many
exist. A chip sits on the line its fork falls on, and several may share a line — up to five
side by side. The target's own fork gets no chip: it is not a choice already made, and it is
already open.

Chips are read off one copy, not both.

**No run tinting.** An earlier pass separated runs by alternate background shading, which
works on blocks and cannot work here: an inline background wraps raggedly and reads as
highlighter. Nothing is lost — the margin already says where the forks are, and a run boundary
that the reader is not standing on is not information they need marked in the text.

## The target

One card per alternative, in the order they were generated.

**A card is a run**, not a span. Where an alternative is the remainder of a span that already
exists — which is what a counterfactual branch leaves behind — its card begins partway
through that span. This is invisible to the reader and load-bearing for the render: the
children of a run node are the cards, uniformly, with no case analysis over how each fork
came to exist.

**Layout.** *The band* takes the full width of the page, breaking out of the reading column;
*a card* does not, and stays about half the column wide. The two are different claims and
only the first changed: what expands at the target is the room the sibling stack is given,
not the size of any one alternative. The selected card's text is left-aligned with the path
above it, so the eye does not travel between reading and choosing, and moving the selection
slides the whole strip — adjacent cards sit partly outside the frame, more distant ones
entirely outside. The extra width is what makes those neighbours legible rather than implied.

**Filling.** A generation shows its `n` cards immediately as placeholders, the first active,
and they fill in as the server produces them. A span in flight has provenance and no bytes,
and that is what a placeholder is rendering. The client learns about them by reading
`GET /api/tree` while its generate call is still open — reads do not queue behind writes, and
a batch saves per continuation, so the first card lands while the second is still running.

A card can also be **empty and finished** — a generation that produced no bytes at all, from
a batch interrupted and closed as `aborted` or a model that stopped on its first token. That
is a different answer from a placeholder and says so: one will fill and one will not.

**Growing.** When the selected card is the rightmost, is fully generated, and nothing of the
client's is in flight, a new empty card appears to its right and one
`POST /api/generate {n: 1}` fills it. Moving right past the rightmost card is unavailable
until that generation is running. Every other movement is always available.

A new card is a fresh draw rather than a repeat: seeds derive from the tree's base seed plus
a call index, so every continuation ever made at a position has its own. A reader who finds
two cards holding the same text and wants a third is asking a reasonable question of the
model.

## Gestures

**Two axes, and the arrow keys are the whole of it.** Across is the sibling stack at the
target; up and down is the sequence the target sits in. That the same four keys navigate both
is not a convenience — it is the two dimensions of the tree, which is what the surface exists
to move through.

| gesture | where | effect |
| --- | --- | --- |
| ← → | the target | move the selection across the siblings |
| ↑ | the target | move the target back one fork |
| ↓ or Enter | at the tip | confirm the selected alternative |
| ↓ or Enter | behind the tip | move the target forward one fork |
| click | a card | select it, or confirm it if it is already selected |
| click | a margin chip | move the target to that fork |
| click | a token in the path | open the token flyout |
| drag | the chunk slider | set the size of the next chunk |

Down does two things because at the tip there is something to confirm and behind it there is
not — selecting is what re-routes at an earlier fork, and it has already happened by the time
down is pressed. So down is always "towards the tip", and confirming is what that means when
the tip is where you already are.

The chunk slider never moves and is always available. Changing it applies to the next call
and to nothing already made.

## Confirming

Down or Enter on the selected card, in this order:

1. The card's text joins the path — the band **folds into the sequence**, and what was a
   cross-section becomes a stretch of prose continuous with what precedes it.
2. A chip appears in the margin for the fork just left behind.
3. The target clears and re-forms at the new tip.
4. `PUT /api/cursor` records the new tip.
5. `POST /api/generate {n: 2}` from it.

**Returning to a fork is this run backwards**, and the two being inverses is the point rather
than a symmetry noticed afterwards: a section of the sequence opens back out into the
cross-section it was chosen from. Every operation the surface has is one of those two, or a
move along one of the two axes.

The cursor is written before the generation rather than after, so a reload during a long call
lands where the reader is and not where they were a step ago.

Clicking a card selects it when it is not selected and confirms it when it is, so a mouse
reader does in two clicks what arrow-then-down does from the keyboard.

## Returning to a fork

Click a chip in the margin, or press up, which is the same operation reached without aiming:
the slider moves one fork back from wherever it is. At the tip that is the last chip in the
margin; at an earlier fork it is the one before. At the first fork there is nowhere further
back and nothing happens.

- The target opens at that fork, with the alternative currently on the path selected. The
  band appears where the fork is, which is what makes a chip worth clicking: at any depth the
  choice arrives beside the text it belongs to rather than at the foot of the page.
- The path below the fork stays where it is, moderately muted — it is what the reader is
  about to leave rather than something already lost.
- Selecting the alternative already on the path does nothing at all.
- Selecting another re-routes: the path from that fork onward becomes the chosen branch,
  followed forward to the deepest point previously visited down it. With no such memory it
  stops at the fork and the slider stays open there.

Backing out undoes nothing and deletes nothing. The path stays routed as it was and every
span stays where it was written; what moves is where the reader is standing.

## The token flyout

On the path only, and never on a card. A card is an alternative not yet taken; the finer
grain belongs to text the reader has committed to.

Click a token and a small flyout carries its own record — its text and its logprob — and the
alternatives the model ranked and did not take, with theirs.

Some tokens have none. A character whose encoding spans several tokens is recorded as a
single entry with no id and no alternatives, so the flyout says so plainly rather than
appearing empty.

Some alternatives are shown and cannot be taken. A byte-fallback token is a fragment of a
character, and a span holding one has no string form at all — so the flyout lists it,
unselectable, with the reason. Declining is the surface's choice and not the core's:
`loom.py` takes these, and a tree that already holds one is refused whole rather than drawn.
What that buys is decoding the path piece by piece instead of as one buffer; the byte offset
to string index conversion is needed either way, because a curly quote breaks the identity
just as thoroughly.

Choosing an alternative sends `POST /api/branch {span, index, rank}`. It is instant and calls
no model — the alternative was recorded when the span was. What comes back is a span one
token long, anchored at that token's offset. The path re-routes onto it, the remainder of the
span being read becomes its sibling, a chip appears in the margin where there was none, and
the slider forms at the new tip with `POST /api/generate {n: 2}` behind it.

## Requests

**One generation in flight at a time.** The reading surface is the only writer to its tree,
so its own outstanding request is the server's writer lock, and the client needs nothing from
the server to know it.

**One pending slot beside it.** A speculative call that has been decided on but not yet sent
is discarded when a confirm arrives. So right-then-immediately-down costs a wait only in the
case where the speculative call had already started, which is the only case where nothing can
be done about it.

**Reads never queue.** `GET /api/tree` runs underneath a generation and is what fills the
placeholders.

## What survives a reload

The tree, which is on disk, and the cursor, which is in it. From the cursor the whole active
path follows by walking parents, so a reload restores what was being read without the client
having stored anything.

Everything else is session state and may go: which alternatives have been looked at, where
the path resumed after a re-route, the muting. A reader who reloads lands at their tip with
no memory of the branches they had explored, which is honest about what was written down.

## Failure

Every refusal reaches the reader as a dismissable banner carrying the server's own message.
Nothing is retried quietly. Four will happen:

- the seed does not fit the context
- the path has grown past the context, and generation stops entirely from then on
- a response lost bytes to a character split across tokens — rare, reliable on emoji, and
  usually cleared by a different chunk size, which is a dial the reader already has
- there is no model server, where everything except generation still works
