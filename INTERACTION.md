# Interaction

What is on the screen, what a reader does to it, and what each action does.

`FRONTEND.md` holds the concept and the constraints; this is the thing checked against them.
The two are kept apart deliberately — the constraints should outlive several passes at this
document, and folding the specifics in would leave nothing outside them to hold them to.

Numbers here are starting values. This is a first pass, written before there is anything to
poke at, and the parts of it that are guesses are the parts that will move.

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

On submit the input becomes non-editable and stays on the screen as the head of the path.
That is the format showing through rather than a decision made here: recorded bytes are
immutable, there is no edit route, and the only way to change a seed is to delete it and
start again.

Then two calls — `POST /api/author` with `{at: null, text}`, and `POST /api/generate` from
the new span's tip with `n: 2`.

## The reading surface

Three regions once reading has begun.

**The path** — the main column. Root to tip as continuous prose. Runs are separated subtly,
by alternate background shading or a minimal rule. The boundary is drawn at runs rather than
at spans because a run boundary is where a choice was made, which is what a reader is looking
for; the two coincide everywhere except at a fork inside a span.

**The margin** — to the right of the path, one chip per fork: `⑂3/4`, which alternative is
active of how many exist. A chip sits on the line its fork falls on, and several may share a
line — up to five side by side.

**The card slider** — at the tip, below the path. The alternatives on offer.

## The card slider

One card per alternative, in the order they were generated.

**A card is a run**, not a span. Where an alternative is the remainder of a span that already
exists — which is what a counterfactual branch leaves behind — its card begins partway
through that span. This is invisible to the reader and load-bearing for the render: the
children of a run node are the cards, uniformly, with no case analysis over how each fork
came to exist.

**Layout.** A card is half the width of the path column. The selected card's text is
left-aligned with the path above it, so the eye does not travel between reading and choosing.
Moving the selection slides the whole strip: adjacent cards sit partly outside the viewport,
more distant ones entirely outside.

**Filling.** A generation shows its `n` cards immediately as placeholders, the first active,
and they fill in as the server produces them. A span in flight has provenance and no bytes,
and that is what a placeholder is rendering. The client learns about them by reading
`GET /api/tree` while its generate call is still open — reads do not queue behind writes, and
a batch saves per continuation, so the first card lands while the second is still running.

**Growing.** When the selected card is the rightmost, is fully generated, and nothing of the
client's is in flight, a new empty card appears to its right and one
`POST /api/generate {n: 1}` fills it. Moving right past the rightmost card is unavailable
until that generation is running. Every other movement is always available.

A new card is a fresh draw rather than a repeat: seeds derive from the tree's base seed plus
a call index, so every continuation ever made at a position has its own. A reader who finds
two cards holding the same text and wants a third is asking a reasonable question of the
model.

## Gestures

| gesture | where | effect |
| --- | --- | --- |
| ← → | card slider | move the selection |
| ↓ or Enter | card slider | confirm the selected alternative |
| ↑ | card slider | move the slider back one fork |
| click | a card | select it, or confirm it if it is already selected |
| click | a margin chip | return the slider to that fork |
| click | a token in the path | open the token flyout |
| drag | the chunk slider | set the size of the next chunk |

The chunk slider never moves and is always available. Changing it applies to the next call
and to nothing already made.

## Confirming

Down or Enter on the selected card, in this order:

1. The card's text joins the path, with a separator at the new run boundary.
2. A chip appears in the margin for the fork just left behind.
3. The slider clears and re-forms at the new tip.
4. `PUT /api/cursor` records the new tip.
5. `POST /api/generate {n: 2}` from it.

The cursor is written before the generation rather than after, so a reload during a long call
lands where the reader is and not where they were a step ago.

Clicking a card selects it when it is not selected and confirms it when it is, so a mouse
reader does in two clicks what arrow-then-down does from the keyboard.

## Returning to a fork

Click a chip in the margin, or press up, which is the same operation reached without aiming:
the slider moves one fork back from wherever it is. At the tip that is the last chip in the
margin; at an earlier fork it is the one before. At the first fork there is nowhere further
back and nothing happens.

- The slider re-forms at that fork, with the alternative currently on the path selected.
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
