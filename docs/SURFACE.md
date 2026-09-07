# The reading surface

**What the surface is.** What it shows, what it lets a reader do, what it reads to do it, and
what it deliberately leaves undecided.

**The test it is written against: could someone build this from it alone?**

Sections are cited by name, never by position. What the record is, is `docs/CORE.md`; what a
backend must do to produce it is `docs/ADAPTER.md`. No fact about either is restated here, and
nothing here constrains either. This document is **not locked** and carries its own Status at the
end.

---

## What this is

A reading surface over a trie of tokens. **A generation is not an answer to be accepted or
rerolled** — it is one path among those the model made available, and several are held at once.
The surface exists to read across them.

**The floor case is a text reader and nothing else.** One path, root to leaf, set as prose. No
chrome, no marks, no panels. Everything else in this document is something a reader asks for, and
until they ask, the page is text. This is not modesty about the instrument; it is the instrument.
A surface that displayed what it knows would be showing twenty alternatives at every one of a
thousand positions, which is a picture of the tool rather than of its subject.

**One tree at a time, and the surface is its sole writer.** Writing rests on this twice over — for
the whole of its concurrency, and for verifying a store once rather than once per request.

## Units

**A token is not the display unit.** A token spells several characters in ordinary English, and a
character can span several tokens — `docs/CORE.md`'s worked example spells one alchemical symbol
with three, none of them valid UTF-8 alone. The two are not in correspondence and no arrangement
of them makes one.

**A segment is the shortest run of nodes whose bytes decode.** It is the display unit and the
addressable unit both. In ordinary English every segment is one node; across a multi-token
character it is several.

- **A segment cannot be split.** Nothing addresses a node inside one, so a character spelled by
  three tokens cannot be branched into. That is the whole of what this costs, and it is accepted.
- **A path may end mid-character**, which is a legal path with no string form. Its trailing bytes
  are one segment, marked as not decoding, shown as U+FFFD — the same choice the command line
  makes and says it makes. `docs/CORE.md` leaves this to the reader; this is the reader.
- **A control token displays as the characters it spells.** `<|endoftext|>` is thirteen ordinary
  characters on screen, and on the page it is indistinguishable from authored text spelling the
  same thirteen characters — the two readings spell the same bytes, and display is bytes. **The
  store does tell them apart**, by the id, and records no intent beyond that. So this is a
  distinction the surface declines to draw rather than one it cannot: whether it should draw it is
  in What is not decided here.
- **A newline is a newline** in the reading column. Where a construct of the surface is one line
  by its own construction — a preview line in The band — a newline is shown as a glyph rather
  than obeyed, because obeying it would carry everything below out of alignment.

## The path

**The surface shows one complete path**, root to a leaf, and the reader's position in the tree
*is* that path.

**The path is held, not derived.** It changes when the reader selects a branch or when an act
lands, and at no other time. Below a node that has just changed, the continuation is the **longest
live continuation** — deepest wins, deleted nodes are not followed. On first open, with nothing
yet chosen, the whole path is that rule from the root.

**It must be held rather than re-derived, and a write is why.** A reader who takes a shallow
alternative and generates five tokens onto it would be thrown back onto the two-hundred-token
branch they just left, because that branch is still the longest descent from the root. **The path
follows the act.** What an act produced is what the reader is looking at when it lands.

**Between forks, nothing is drawn.** A stretch where nothing is offered is a stretch that should
look like prose, so the visible object is the fork and the reading column is otherwise text.

## Forks and the band

**A fork is a node whose parent has more than one live child.** In the reading column a fork
carries a mark and nothing else — no count, no preview, no affordance beyond being marked.

**A deleted sibling hides a fork.** Liveness is what the surface follows, so a node with two
children of which one is deleted is not a fork and is not marked. The record still holds it. This
is `docs/CORE.md`'s rule applied honestly, and whether a reader should be told that more was here
is in What is not decided here.

### The band

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

**A preview follows the same descent that selecting it would produce**, so what a preview shows is
a truthful prefix of what taking it gives. Anything else would be a promise the surface breaks on
the click.

**Selecting a preview makes it the path and closes the band.** Everything above the fork is
untouched — the reader has not moved, the continuation has — which is the same thing The path says
about an act landing, and for the same reason. Nothing is written: a preview is a path that
already exists, so taking one is a selection and not an act. Taking an alternative that has *no*
node is a different operation and lives in Rankings.

**Each preview is one line.** It gets a reading measure of width, or whatever is left of the page
if it starts late — which is why the reading column is half the page and the other half is empty
until a fork opens. A preview that starts at the end of a line still has a line's worth of room,
and the reading column never moves to make it.

**The band bounds itself by room, and by nothing else.** A line clipped before its own inner fork
has nowhere to hang that fork's alternatives, so they are dropped, and a dropped line takes its
own alternatives with it rather than letting them fall back to the split column and claim to part
where they do not. **The band says how many it dropped.** Silent truncation would read as *that is
all of them*, which is a lie the surface is not entitled to tell about the record.

**Nothing about the band is expressible in flow layout.** A column is a measured position in
proportional text, and each line's children can only be placed once that line is rendered. It is
laid out again whenever the geometry changes.

## Rankings

**Selecting a token asks what else was live at that position**, which is the ranking at its
*parent* — a node's own ranked edges are the alternatives for what follows it, not for it.

Every ranked edge at that node is shown, in recorded order, and each is one of three things:

| row | what it is | what taking it costs |
| --- | --- | --- |
| the one taken here | the token on the current path | nothing; it is where the reader is |
| realised elsewhere | a node exists for it, off the current path | a selection; no act at all |
| unrealised | no node exists for it | one `realise`, and then a `generate` to continue |

**Rank is presentation order and is never re-sorted.** `docs/CORE.md` is explicit that rank means
*the k-th alternative recorded here*, not the model's k-th choice, and that descending logprob is
expected but not enforced. A surface that sorted by value would be inventing an ordering the
record declines to guarantee.

**A logprob is shown as a number and never as a length.** No bars, no ramps, no share-of-mass. This
is what answers *how an unrealised edge is offered without implying the model recommends it*: rank
order is the model's presentation and is shown as given, magnitude is shown as a figure the reader
may read or ignore, and nothing on screen encodes value as size or colour. Values are the model's
own and sum to less than one; a surface that drew them as a proportion would be asserting a whole
the record does not have.

**Density stays behind intent.** A real tree carries twenty alternatives at nearly every position.
None is shown until a position is asked about.

## Writing

The surface offers the three acts and the two state edits, and nothing else. What each one is, is
`docs/CORE.md`; what it costs is here.

| operation | needs | can fail as |
| --- | --- | --- |
| `create` | a tokeniser | rejected — the round trip does not hold, or it adds no tokens |
| `generate` | a model | refused by the adapter, or failed mid-call, or rejected before the call |
| `realise` | neither | rejected — no such edge, or the node is not live |
| `delete` / `undelete` | neither | rejected — no such node |

**One write is in flight at a time, and while one is, no other may be requested.** There is no
queue. The surface is the tree's sole writer, so this is the whole of the concurrency it needs.

**Not every position can be generated from, and the surface asks rather than finds out.** A path
whose bytes end mid-character is a legal path that a backend may decline to evaluate, so at such a
position `generate` is offered as unavailable while `create` and `realise` — which call no model —
are not. `docs/ADAPTER.md` provides for exactly this: asking is not declining, it writes nothing,
and the real request still goes through `generate`. **The answer is advisory and is never
substituted for the outcome**: a request that goes anyway is refused by the adapter and recorded,
and the surface never suppresses a refusal it predicted.

**A request appears where its result will.** An inline placeholder at the position the act will
occupy, replaced by the nodes when they land. Not a spinner elsewhere on the page, and not
optimistic text: the act is the record, and the surface does not draw nodes that do not exist yet.

**A failure becomes a dismissable error in the placeholder's position**, and it says which kind it
was, because the record does.

- **A refusal is in the record.** The adapter declined, no model was called, and the act stands
  with the parameters and the seed it was asked for and terminator `refused`. The error names that
  act.
- **A rejection is not.** The core declined before writing anything and left no trace. The error
  says so.
- **A failure is in the record.** The call happened and nothing could be recorded from it.

**A retry is offered exactly where the same request could succeed.** That is `failed`, and
transport errors that never reached an act. A refusal and a rejection are both answers about the
request itself, so what they offer is an edit rather than a retry — repeating either unchanged
gets the same answer, and a button promising otherwise would be lying about a decision the backend
or the core already made.

**The tree is claimed when the surface opens it and held until it closes.** The surface is
therefore the only writer for as long as it runs, and the one thing that can fail is the opening: a
tree another process holds is refused at once, which the surface reports naming the tree rather
than starting and showing a page that never resolves.

**The tree is opened for writing once and verified once**, for the life of the process, rather
than per request. The claim is what makes that sound rather than merely economical — no other
writer can change the store while it is held — and it takes a whole-tree verification off every
interaction.

**Opening for writing can change the tree, and that is the surface's first write.** Claiming the
tree is what records abandoned generations as `aborted`, so a tree left in flight by a writer that
died — a killed command line, most likely — is swept the moment the surface opens it. That
terminator is therefore something the surface *finds*, never something its own request becomes:
the surface is the writer, and a request it loses it loses along with the process holding it.

## What the surface reads

**Three reads, and each is one descent.** Every bulk read in the core is N+1 as built — each node
walks its own ancestry or fetches its own children — and `docs/CORE.md` already says what the fix
is: *a descent from the root carries the answer down and costs nothing.* These are stated as what
must be answerable that way, not as an interface.

**1. A path.** From the root to a node: the segments in order, each carrying the node ids it
spells, and for each node its source, its logprob, whether it is live, and whether it is a fork.
One descent, carrying liveness down rather than asking per node.

**2. A ranking.** Every ranked edge at one node, in recorded order, each with the bytes its token
spells, its logprob, and **the child that realised it, if any**. Not the branchable set alone: a
reader looking at a position needs to see what was taken sitting at its own rank among the
alternatives, and the branchable set is then the rows with no child. **This read did not exist
before the band was built**, and it is the clearest case of the ordering this document was written
under: it fell out of laying out a panel, and no amount of reading the core would have produced it.

**3. A branch subtree.** Below one node: each divergence, the run of nodes from it, bounded by a
character budget, depth-first, with the nested divergences inside each run and the index each
parts at. The band is laid out from this and from measurement, and from nothing else.

Point reads — a node, a tree's roots, the act list — are already cheap and need nothing.

## Nothing written is only here

**No write may be surface-only**, and the surface satisfies this by construction. Everything it
writes is one of the five writes `docs/CORE.md` defines — the acts `create`, `generate` and
`realise`, and the state edits `delete` and `undelete` — and each has a verb of its own name,
`undelete` being `tokenloom delete --undo`. A long generation stopped by declining to issue the
next act is consecutive `tokenloom generate`, so it too is nothing new.

Everything else this document describes is a way of looking. The reading column, the band, a
ranking on demand, moving between forks, and whatever comparison across branches turns out to be
are the surface's own, record nothing, and are owed no counterpart.

## What is not decided here

**These are not gaps in the document. They are questions prose cannot close**, and answering one
from an armchair is how a one-line rejection decides something for a year. Each is decided against
a working surface, and each moves into this document when it is.

- **Keyboard.** The band's depth-first row order is already the natural arrow-key sequence, but
  what the whole reader does under a keyboard — moving between forks, into a ranking, back out
  without losing one's place — is unsettled. *Keyboard and mouse first* is the target and only
  half of it exists.
- **What a click means.** A fork opening a band and any other token opening a ranking are two
  meanings for one gesture. It works and it is not obviously right.
- **Whether a control token is marked.** The store can tell a control token from text spelling the
  same characters. Whether the reader should is a question about honesty against clutter.
- **Whether a hidden fork is announced.** A deleted sibling makes a fork vanish. Saying nothing is
  consistent; saying something may be truer.
- **Cadence.** Text arrives in whole acts. Whether the surface reveals a block at once or paces it
  out — which invents a timing the record does not hold — is a choice, and no measurement has been
  taken. Nothing is lost by waiting: chunk length *is* `length` in `params`, recorded per act, so
  the question stays answerable whenever it is asked.
- **Everything past the first gesture.** Comparison across branches, and what the instrument does
  that a reader could not get from reading one path at a time.

---

## Status

**The band is demonstrated, not proposed.** It was built against a real tree before this document
was written, which is the only reason Forks and the band states a design rather than a guess. Two
faults fell out of building it that no amount of prose would have produced: a newline inside a
one-line construct carries every row below it out of alignment, and the bound on the band's size
is load-bearing rather than theoretical — where a fork lands late in a line, the parent clips
before its own inner fork and the alternatives have nowhere to hang.

**Nothing else here is built.** There is no read layer, no API and no surface. What exists is the
core, the llama.cpp adapter, the command line, and a throwaway probe that reads a static
projection of a tree and cannot write.

**Superseded by this document:** `docs/surface-sketch/`, and all of `docs/surface-notes.md` but its
last section. Both are in history, and a note that outlives the document it fed is the second home
this project keeps paying for.

**Not superseded, and not yet in this document:** whether a first-pass generation should be greedy
rather than sampled, and what a surface shows of a distribution whose mass sits in three of twenty
recorded alternatives. `docs/surface-notes.md` holds the argument. It is taken up after the core
changes below land, and until it is settled **Rankings** describes how alternatives are presented
but not how many there are to present.
