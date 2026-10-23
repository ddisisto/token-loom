# Alternation

**A fork can be shown in space or in time.** Laid out in space, its branches stand side by side,
which needs room the page mostly does not have. Shown in time, they take turns in one place, so
a fork costs no room at all. *Arms* is the first answer and this is the second. They do not
compete: a fork can be laid out where there is room and alternated where there is not.

**What is shown when the reader acts is what they get.** A click, an arrival or a scroll onto
alternating text takes whichever branch was showing. The choice is the reader's timing, and not
a rule's verdict made before they looked.

---

## What it replaces

**A rule picks one future by something that has nothing to do with reading.** Under `ranked`,
the path below the caret is whichever continuation the model ranked highest at each fork, and
under `longest` whichever is tallest. An arrival can land on a stub nobody chose, because buying
one made it the highest ranked or rolling one made it the tallest. Under alternation no branch
is favoured for good, and nothing is chosen until the reader acts.

**It is a continuation rule, of a kind that varies over time.** `docs/SURFACE.md` names a family
of rules and settles none. A rule here gives each branch at a fork a weight rather than picking
one, and the page shows each branch for a share of the time in proportion to its weight.
`ranked` and `longest` are the case where all the weight is on one branch, so they stay members
of the family and are not replaced by this.

## The weight

Several are candidates, and which ones read well is settled by trying them side by side:

- **The model's preference**: the probability of the first token after the fork. Every later
  token is conditioned on that one, so this already weights early tokens over late ones.
- **What lies below**: the size of each branch's subtree, which `beneath` already computes.
- **Recency**: newer draws shown more often.
- **The reader's own marks**: a branch carrying a waypoint, or one visited, shown more often.

They are a list to choose from, as `RULES` is, and the choice is a control.

## How it moves

**Few branches alternate slowly and distinctly, and many alternate faster and dimmer.** The
frenzy of a wide fork is itself the reading: it says how open the position is.

**Only what differs moves.** Branches share everything before their fork, so the shared run
stays still and only the tails take turns. With forks below forks, one frame is one whole path,
picked among the leaves by weight.

**Under reduced motion nothing alternates**, and the heaviest branch stands still.

## What is in flux, and what is fixed

**Everything below the furthest point the reader has reached is in flux, and everything above it
is fixed.** A fresh session has fixed nothing below the root. Moving the caret down past a point
fixes what it passed. Arriving at a waypoint fixes everything before it. Placing the caret back
up, casually, unfixes nothing, so what is below stays as it was read.

**A gesture at the caret puts what is below it back in flux.** It is the way to ask *what else is
down here* without leaving the position.

## Holding one still

**Hovering freezes the alternation, and stepping moves through the branches while frozen.** A
click at the instant of a change would take the branch after the one meant, since reaction is
slower than a turn. Freezing on hover makes the click take what is held still. That makes hover
the moment a branch is picked out, which is what it already means on the page.

**For a single line, the wheel steps.** In the nav and in a hovered arm, the wheel has nothing
else to do. In the column the wheel scrolls the page, so stepping there needs another gesture,
which is open.

## The order it is built in

1. **The nav's trails.** A waypoint's trail stops at the first fork below it. Alternating there
   is peripheral, small and cheap, so it is where the weights and the rates are tried first.
2. **The hovered arm in the panel**, which is already a provisional line.
3. **The column below the fixed point**, as a member of `RULES` with a switch, on by default.

**The server owes it little.** `branches` in `surface/reads.py` already returns a node's
branches as a subtree with where each one parts. A weight on each is the addition.

## Open

- **Which weights read well.** *Settled by trying several side by side.*
- **The rates and the dimming.** *Settled by looking.*
- **How stepping works in the column**, where the wheel already scrolls. *Settled once the column
  alternates and there is something to step through.*
- **Whether a wide fork in the nav is too much motion beside the text.** If it is, it alternates
  only while the reader is idle, or only for a row being pointed at. *Settled by use.*
