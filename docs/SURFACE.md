# The reading surface

**What the surface is.** What it shows, what it lets a reader do, what it reads to do it, and
what it deliberately leaves undecided.

**The test it is written against: can a reader tell what is settled from what is open, and does
each open question say what would settle it?** A design in progress fails by writing an open
question down as a rule so that it reads as finished.

Sections are cited by name, never by position. What the record is, is `docs/CORE.md`; what a
backend must do to produce it is `docs/ADAPTER.md`. No fact about either is restated here, and
nothing here constrains either.

---

## What this is

A reading surface over a trie of tokens. **A generation is not an answer to be accepted or
rerolled** — it is one path among those the model made available, and several are held at once.
The surface exists to read across them.

**The floor case is a text reader.** One path, root to leaf, set as prose: no chrome, no marks, no
panels. Everything else here is something a reader asks for, and a real tree carries alternatives
at nearly every position, so a surface that drew what it knows would be a picture of the tool
rather than of its subject. What gets set as prose is whatever the path holds, degenerate or not.

**One tree at a time, and the surface is its sole writer.**

**The tree is made here as well as read.** Every path the surface reads across is one a reader
made from it, and the acts that make them are as much the instrument as the column is. Where a
tree comes from is where that starts.

## Units

**A token is not the display unit.** A token spells several characters in ordinary English, and a
character can span several tokens — `docs/CORE.md`'s worked example spells one alchemical symbol
with three, none of them valid UTF-8 alone.

**A segment is the shortest run of nodes whose bytes decode.** It is the display unit and the
addressable unit both. In ordinary English every segment is one node; across a multi-token
character it is several.

- **A segment cannot be split.** Nothing addresses a node inside one, so a character spelled by
  three tokens cannot be branched into.
- **A path may end mid-character**, which is a legal path with no string form. Its trailing bytes
  are one segment, marked as not decoding and shown as U+FFFD — the same choice the command line
  makes.
- **A control token displays as the characters it spells.** `<|endoftext|>` is thirteen ordinary
  characters on screen, indistinguishable from authored text spelling the same thirteen, because
  the two spell the same bytes and display is bytes. The store tells them apart by the id.
  Whether the reader should is in What is not decided here.
- **A newline is a newline** in the reading column. Where a construct of the surface is one line
  by its own construction — a preview line in The band — a newline is shown as a glyph rather
  than obeyed, because obeying it carries everything below out of alignment.

## Where a tree comes from

**A tree starts empty and the reader makes it.** The surface opens against a tree with no nodes
as readily as against one with thousands, and what a reader does from there is a loop: put
something in, continue it, take a position the model offered and did not take, and write one it
would not have offered at all.

**An empty tree is a state and not an error.** There are no roots, so there is no path and the
reading column has nothing to set. What the surface offers is composition, and the tree's name
and vocabulary — which a reader about to write into it needs and cannot read off an empty page.

**A root is a `create` with no parent**, and nothing else about it is special. It is the act the
reader makes at every other position, which is why a seed and a branch are one thing the record
does not distinguish.

**There is no cursor.** Any live node can be written at, and continuing is writing at the leaf of
the path being read. The tip is where a reader usually is; it is not something the record holds.

**The gestures and the acts are not one to one.**

| what the reader means | acts | what it leaves |
| --- | --- | --- |
| start something | `create` with no parent | a root, and the first path |
| continue what is read | `generate` at the leaf | nodes under it, and a ranking at each |
| take what was offered and not taken | `realise`, then `generate` | a fork, and a path under it |
| write what was not offered | `create` at a live node | a fork with no ranking behind it |
| set aside | `delete`, `undelete` | a fork that stops being one, or resumes |

Taking an alternative the model ranked and did not sample is one intent and two acts — `realise`
makes the node and `generate` continues from it, which is the cost Rankings states for that
row. The reader means one thing and the record keeps two, and neither layer is wrong about it.

**A `create` at a node that already has a live child is a branch with no ranking behind it.**
Every other fork stands on something the model offered; this one stands on nothing but the
reader, which is what makes it the control case — a path the model would not have produced, read
against the ones it did. The record does not distinguish it from any other `create`, and whether
the surface should is in What is not decided here.

**A composition affordance belongs at the position it will write into**, for the reason Writing
gives for the placeholder: a request appears where its result will. What summons it, what it
looks like, and whether the surface holds one that moves or one at each position are settled by
use and not by prose, and are in What is not decided here.

**The reader names the `generate` parameters.** `docs/ADAPTER.md` requires them of every caller
and the server names none it was not given, so a surface that fills them in is deciding what the
store keeps one layer up from where that document forbids it. An adapter that needs one it did
not get says so — as a refusal, naming what it wants, in the record like any other. **A draw the
page does not seed is one nothing can replay**, which is why the command line seeds and why the
surface does.

**A refusal about parameters is where they are edited.** Writing offers a retry exactly where
the same request could succeed and an edit everywhere else, and a request refused for what it
asked for is the second kind: the parameters come back under the reader's hand with the adapter's
own words beside them.

## The path

**The surface shows one complete path**, root to a leaf, and the reader's position in the tree
*is* that path.

**Below a node that has just changed, a continuation rule picks the rest.** The first
implementation is the **longest live continuation** — deepest wins, deleted nodes are not
followed, ties go to insertion order. It is one of a family, the surface takes the rule as a
parameter rather than embedding it, and which member is right is in What is not decided here. On
first open, with nothing yet chosen, the whole path is that rule from the root.

**The path is held rather than re-derived**, and changes when the reader selects a branch or when
an act lands. A reader who takes a shallow alternative and generates five tokens onto it would
otherwise be thrown back onto the two-hundred-token branch they just left, which is still the
longest descent from the root. **The path follows the act:** what an act produced is what the
reader is looking at when it lands.

**Between forks, nothing is drawn.** A stretch where nothing is offered should look like prose,
so the visible object is the fork and the column is otherwise text.

## Forks and the band

**A fork is a node whose parent has more than one live child.** In the reading column it carries a
mark and nothing else — no count, no preview, no affordance beyond being marked.

**A deleted sibling hides a fork.** Liveness is what the surface follows, so a node with two
children of which one is deleted is not a fork and is not marked. The record still holds it, and
whether a reader should be told is in What is not decided here.

### The band

The band was built against a real tree before it was written down, so this section describes
something that ran.

Opening a fork **inserts the alternatives into the line they part from**, and moves nothing
sideways.

1. **The line splits** at the column the fork's first token occupies. Above the split nothing
   changes. Below it, the current path resumes **at the column it left** and continues wrapping at
   the measure, dimmed — dimmed because opening a fork is asking what would replace it.
2. **Preview lines go in the gap.** Each begins at the column its own first token would occupy in
   the line it parts from, and shows text only from its own divergence onward.

**The indentation is where paths part, not how deep they are.** Two alternatives at the split
share a column; one that parts three tokens later sits three tokens further right. Shared prefix
is shared screen position, which is the trie drawn as text rather than as a diagram beside it.

**Order is depth-first.** The path already being read comes first — it is what every other line
aligns against, and selecting it is a cancel. Then its siblings at the split, and within each
line, the lines that part from *it*, in the order they part.

**A preview follows the same continuation rule that selecting it would**, so what it shows is a
truthful prefix of what taking it gives.

**Selecting a preview makes it the path and closes the band.** Everything above the fork is
untouched: the reader has not moved, the continuation has. Nothing is written — a preview is a
path that already exists, so taking one is a selection and not an act. Taking an alternative that
has *no* node is a different operation and lives in Rankings.

**Each preview is one line.** It gets a reading measure of width, or whatever is left of the page
if it starts late — which is why the reading column is half the page and the other half is empty
until a fork opens. A preview that starts at the end of a line still has a line's worth of room,
and the reading column never moves to make it.

**The band bounds itself by room, and by nothing else.** A line clipped before its own inner fork
has nowhere to hang that fork's alternatives, so they are dropped, and a dropped line takes its
own alternatives with it rather than letting them fall back to the split column and claim to part
where they do not. **The band says how many it dropped**, since a silent truncation reads as *that
is all of them*.

**Room there is a line's width.** Nothing bounds the band in the other direction: a divergence
inside a line that is shown is followed however deep it nests, so a band opened high in a branchy
tree holds most of what is under it. Whether that needs a bound is in What is not decided here.

**Nothing about the band is expressible in flow layout.** A column is a measured position in
proportional text, and each line's children can only be placed once that line is rendered. It is
laid out again whenever the geometry changes.

## Rankings

**Selecting a token asks what else was live at that position**, which is the ranking at its
*parent* — a node's own ranked edges are the alternatives for what follows it, not for it.

Every ranked edge at that node is shown, and each is one of three things:

| row | what it is | what taking it costs |
| --- | --- | --- |
| the one taken here | the token on the current path | nothing; it is where the reader is |
| realised elsewhere | a node exists for it, off the current path | a selection; no act at all |
| unrealised | no node exists for it | one `realise`, and then a `generate` to continue |

**Rows are shown in descending logprob, and source by source.** In the store, rank is recorded
order and descending is expected rather than enforced — a ranking deepened by a later act appends
rows, and a near-tie at the join can leave the two apart, so the surface sorts. Across sources it
does not: a node several models have ranked holds several rankings, and one order over their union
would sit rows side by side that were never alternatives to each other.

**Each row shows its logprob.** How — a number, a bar, a ramp, a share of the recorded mass — is
in What is not decided here.

**The rows hold less than the whole distribution.** They sum to less than one because the rest of
the vocabulary was never recorded, not because anything was truncated, so *where the recorded mass
runs out* is a quantity the surface can draw, labelled as being over the recorded mass. It belongs
to the node: a ranking extends across acts and is never rewritten, so the rows are the union of
what everything that passed through recorded, and the number is not the `record_mass` of any one
act.

**Deepening a ranking is a `generate`.** A reader who wants more alternatives at a position asks
for them, and the request is a length-1 `generate` with a wider `record_rows` — rankings extend
and are never truncated, so new rows accumulate onto the ones already there. Under a greedy draw
the token drawn is the top-ranked one and a node for it usually exists, so the act merges rather
than adding a child. It is a write with a verb of its own, so *Nothing written is only here*
holds.

**Density stays behind intent.** A ranking can run to dozens of rows at a position the model was
unsure of, and none is shown until that position is asked about. Whether the reading column should
nonetheless mark where the model *was* unsure is in What is not decided here.

## Writing

The surface offers the five acts and nothing else. What each one is, is `docs/CORE.md`; what a
reader means by one is Where a tree comes from; what it costs is here.

| operation | needs | can fail as |
| --- | --- | --- |
| `create` | a tokeniser | rejected — the round trip does not hold, or it adds no tokens |
| `generate` | a model | refused by the adapter, or failed mid-call, or rejected before the call |
| `realise` | neither | rejected — no such edge, or the node is not live |
| `delete` / `undelete` | neither | rejected — no such node |

**One write is in flight at a time, and while one is, no other may be requested.** There is no
queue.

**Not every position can be generated from, and the surface asks rather than finds out.** A path
whose bytes end mid-character is a legal path that a backend may decline to evaluate, so at such a
position `generate` is offered as unavailable while `create` and `realise` — which call no model —
are not. `docs/ADAPTER.md` provides for exactly this: asking is not declining, it writes nothing,
and the real request still goes through `generate`. **The answer is advisory**: a request that
goes anyway is refused by the adapter and recorded, and the surface shows that refusal rather than
suppressing one it predicted.

**A request appears where its result will.** An inline placeholder at the position the act will
occupy, replaced by the nodes when they land — not a spinner elsewhere on the page, and not
optimistic text.

**The placeholder is read rather than remembered.** `docs/CORE.md` commits a `generate` act before
the model is called, and an act with no terminator is a generation in flight, so what the
placeholder stands for is in the record. A page opened while one is running draws it, and a page
reloaded mid-generation does not lose it.

**Reading goes on while a write is in flight.** A generation is seconds of waiting, and the reader
is not held at the page they asked from: the store's journal mode lets a read take no lock, and
`docs/CORE.md` is explicit that no transaction spans a model call. What the reader cannot do is ask
for a second write.

**A failure becomes a dismissable error in the placeholder's position**, and it says which kind it
was, because the record does.

- **A refusal is in the record.** The adapter declined, no model was called, and the act stands
  with the parameters it was asked for and terminator `refused`. The error names that act.
- **A rejection is not.** The core declined before writing anything and left no trace. The error
  says so.
- **A failure is in the record.** The call happened and nothing could be recorded from it.

**A retry is offered exactly where the same request could succeed:** `failed`, and transport
errors that never reached an act. A refusal and a rejection are answers about the request itself,
so what they offer is an edit — repeating either unchanged gets the same answer.

**The surface is started against one tree and claims it for as long as it runs**, which is what
lets it open for writing once and verify once for the life of the process rather than before every
write. Verifying is a whole-tree read. A tree another process is holding cannot be opened, which
the surface reports naming the tree rather than starting and showing a page that never resolves.

**Opening for writing can change the tree, and that is the surface's first write.** Claiming the
tree is what records abandoned generations as `aborted`, so a tree left in flight by a writer that
died — a killed command line, most likely — is swept the moment the surface opens it. That
terminator is therefore something the surface *finds*: a request the surface itself loses, it
loses along with the process holding it.

## What the surface reads

**Three reads, and each is one descent.** A read that asks per node — its own ancestry for
liveness, its own children for what parts — is the one shape these cannot have, and `docs/CORE.md`
says what the fix is: *a descent from the root carries the answer down.* These are stated as what
must be answerable that way, not as an interface.

**1. A path.** From the root to a node: the segments in order, each carrying the node ids it
spells, and for each node its source, its logprob, whether it is live, and whether it is a fork.
One descent, carrying liveness down rather than asking per node. **If the column comes to mark
uncertainty this read grows a per-node measure of the ranking its *parent* held** — an aggregate
over ranked edges, decorating the descent's output rather than joining its recursion.

**2. A ranking.** Every ranked edge at one node, each with the bytes its token spells, its
logprob, and **the child that realised it, if any**. Not the branchable set alone: a reader
looking at a position needs to see what was taken sitting among the alternatives, and the
branchable set is then the rows with no child.

**3. A branch subtree.** Below one node: each divergence, the run of nodes from it, bounded by a
character budget, depth-first, with the nested divergences inside each run and the index each
parts at. **A divergence with no index is counted rather than returned** — one past the budget's
cut, and one inside a segment, which nothing addresses — since what a reader is owed is how many
are not there. The band is laid out from this and from measurement, and from nothing else.

Point reads — a node, a tree's roots, the act list — are already cheap and need nothing.

## Nothing written is only here

**No write may be surface-only**, and the surface satisfies this by construction. Everything it
writes is one of the five acts `docs/CORE.md` defines — `create`, `generate`, `realise`, `delete`
and `undelete` — and each has a verb of its own name, `undelete` being `tokenloom delete --undo`.
A long generation stopped by declining to issue the next act is consecutive `tokenloom generate`,
and so is deepening a ranking.

Everything else here is a way of looking. The reading column, the band, a ranking on demand,
moving between forks, and whatever comparison across branches turns out to be are the surface's
own, record nothing, and are owed no counterpart.

**Reader state is a third thing.** A continuation rule that follows what the reader most recently
took is neither a write nor a way of looking that records nothing: it is state that decides what
is seen, held where the record cannot follow. The cost is that *what this branch is* can no longer
be read off the page without also reading *what you did here last time* — least visibly inside the
band, where every preview line follows the rule at once and the reflection is spread across all of
them. Three things hold it in place:

- **It is updated by selection only** — never by preview, render or hover. Otherwise a preview
  perturbs the thing it previews and the band reorders under its own gaze.
- **It lives in the session and nowhere else.** Durable storage outside a browser session is out
  of scope. `docs/CORE.md`'s *Conformance and extension* makes it cheap to add later, which is a
  reason to shape the session form as a cache of something recordable rather than as something
  only a browser can hold.
- **It orders and selects; it does not describe.** What is live, what is a fork and what a ranking
  holds are read from the store every time.

## What is not decided here

**Questions prose cannot close.** Each says what would settle it, and moves into the body above
when it is settled.

- **How composition is summoned, and how many there are.** A request appears where its result
  will, which places the affordance and says nothing about what opens it, what it looks like, or
  whether the surface holds one that moves between positions or one at each. Continuing at the
  leaf and branching at a node several segments back are the same act and may not want the same
  gesture. What settles it is writing into a tree at both, and finding which of the two the
  other's gesture reads wrong at.
- **Whether a branch with no ranking behind it is marked.** A `create` at a node that already has
  a live child makes a fork the model had no part in, and the record holds the source that says
  so. Marking it puts a second kind of mark in a column *Between forks, nothing is drawn* keeps
  bare; not marking it leaves a reader to open the band to find out. What settles it is a tree
  with both kinds of fork in it, read for whether the difference is wanted at the fork or only
  inside the band.
- **Which `generate` parameters the reader sees.** The adapter requires several and refuses
  naming any it did not get, so the floor is whatever the backend at hand demands. Whether the
  rest — `length`, `record_rows`, the temperature, the seed — sit under the reader's hand at
  every request, persist for the session, or are set once and edited on refusal is a question
  about how often a reader changes them, and nothing has measured that. What settles it is
  running the loop and watching which get touched.
- **Which continuation rule.** Longest, first, last, most-recently-used, cumulative open time —
  each is defensible and they are comparable only by use. `longest` is the first implementation
  because it is the one member that needs nothing but the tree; ties bite only for it, and are
  insertion order. What settles it is reading one tree under two of them, which is why the path
  read takes the rule as a parameter. A rule that reads what the reader did is what puts reader
  state in *Nothing written is only here*.
- **Whether a band has a height.** Its width is a reading measure taken from the page; its depth
  is whatever the tree holds below the fork, which on a branchy tree is nearly all of it. A bound
  would have to say what it drops and where, the way the width already does, and a band that
  silently stopped going down would read as *that is all of them* — the failure the drop count
  exists to prevent. What settles it is opening a band on a tree deep enough to need one and
  seeing where a reader loses the thread.
- **How a magnitude is drawn.** A number, a bar, a ramp, a share of the recorded mass. Each reads
  differently at a sharp position than at a flat one, and a real ranking is often one and
  sometimes the other. What settles it is drawing a real tree several ways.
- **Whether the reading column marks uncertainty.** A mark on the prose where the model was
  undecided — top-1 probability, or the top-1 to top-2 margin, either of which is robust on a
  truncated tail — would show a reader where branching is worth doing, instead of leaving them to
  ask position by position. It cuts against *Between forks, nothing is drawn* and against *Density
  stays behind intent*, and it is the one open question here that changes what a read must carry.
  It is also not yet well posed: a node several models have ranked holds several rankings, and the
  measure has to say whose — or whether the interesting quantity there is their disagreement.
  What settles it is reading a real tree with the mark and without it, and what keeps that cheap
  to try is that the measure decorates a descent already being made rather than needing one of its
  own.
- **Keyboard.** The band's depth-first row order is already the natural arrow-key sequence, but
  what the whole reader does under a keyboard — moving between forks, into a ranking, back out
  without losing one's place — is unsettled. *Keyboard and mouse first* is the target and only
  half of it exists. What settles it is working a real tree with the mouse put away.
- **What a click means.** A fork opening a band and any other token opening a ranking are two
  meanings for one gesture. It works and it is not obviously right. What settles it is finding
  where the wrong one fires.
- **Whether a control token is marked.** The store can tell a control token from text spelling the
  same characters. Whether the reader should is a question about honesty against clutter, and what
  settles it is a tree with control tokens in ordinary positions, read both ways.
- **Whether a hidden fork is announced.** A deleted sibling makes a fork vanish. Saying nothing is
  consistent; saying something may be truer. What settles it is using `delete` in earnest and
  seeing whether a tree becomes unreadable without the mark.
- **Cadence.** Text arrives in whole acts. Whether the surface reveals a block at once or paces it
  out — which invents a timing the record does not hold — is a choice, and no measurement has been
  taken. Nothing is lost by waiting: chunk length *is* `length` in `params`, recorded per act, so
  the question stays answerable whenever it is asked.
- **Everything past the first gesture.** Comparison across branches, and what the instrument does
  that a reader could not get from reading one path at a time. Nothing settles this but use.

---

## Status

**A process with a placeholder where the page goes.** `tokenloom serve` holds one tree for as
long as it runs and serves the three reads, the path predicate and the five acts over HTTP, each
act under its own verb, with the page mounted at the root so that what it reads and the page
itself arrive from one origin. What does not exist is the page: `/` answers with a sentence
saying so, and nothing reads any of the rest. What else exists is the core, the llama.cpp
adapter, the command line, and a throwaway probe that reads a static projection of a tree and
cannot write — which is what demonstrated the band.
