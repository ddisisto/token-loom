/* The reference arm as the page holds it: what has been read for each position, whether
 * there is more to be had, and whether having it would cost inference.
 *
 * `docs/SPINE.md` has the stub as the model left alone from a position, and the gesture that
 * asks for one is a hover. **What the record already holds is not paced.** A greedy rollout
 * merges onto what an earlier one wrote, so the descent that never leaves the top row is what
 * asking again would produce -- it costs nothing, it is one read, and making the reader wait
 * for it would be charging them for looking. The pacing is for what has to be bought, and it
 * arrives with the buying; `docs/SPINE.md` has the timings it will be built from.
 *
 * **Lengths and not increments.** `/stub` answers with a prefix of the arm, so growing one is
 * asking for a longer prefix and never for a continuation of what is held. That is what lets
 * a read be restarted from anywhere, survive an answer arriving after a longer one, and read
 * the record and the model through one path -- the page does not know which of the two
 * answered, and nothing here should.
 */

/** Tokens an arm is read to. `docs/SPINE.md` has a flat length as enough to start and what
 *  would settle a better one; this is that flat length. */
export const CAP = 40;

/* What is held, by the node an arm descends from. An arm only grows, and a longer one
 * supersedes a shorter one entirely rather than being appended to -- so this keeps across
 * hovers and is dropped only when the record changes under it. */
const held = new Map();

export const recall = node => held.get(node);
export const forget = () => held.clear();

const blank = () => ({ cells: [], grown: 0, why: null, asking: false });

/** The four `surface/reads.py` names, kept in step with it. **Only `ENDS` is a price.** An
 *  arm that stopped is not an arm the model has no more of: a closed one continues under a
 *  flag the reader set and a declining one has no single top row to follow, and a roll at
 *  either merges onto what is already there and writes nothing. */
export const FULL = "full";
export const ENDS = "ends";
export const CLOSED = "closed";
export const DECLINES = "declines";

/** Whether the record has no more of this arm, whichever of the three reasons it is. It is
 *  what stops the reading and says nothing about whether anything can be bought. */
const done = have => have.why !== null && have.why !== FULL;

/** How long an arm to ask for, or null when there is nothing to ask.
 *
 *  One read and not a sequence, because the record answers in full or not at all: an arm
 *  that came back short came back short because the tree ends there, and asking again
 *  returns the same thing. What is held is therefore final until something writes.
 */
export function reach(node, { cap = CAP } = {}) {
  const have = held.get(node);
  if (have === undefined) return cap;
  if (have.asking || done(have) || have.grown >= cap) return null;
  return cap;
}

/** Mark an arm as having a read in flight, so a second hover does not start another. */
export function asking(node, yes) {
  const have = held.get(node) ?? blank();
  have.asking = yes;
  held.set(node, have);
}

/** Where in `cells` the part that was not there before begins.
 *
 *  Counted in nodes and not in cells, because a cell is a character and the boundary can
 *  fall inside one -- a half-character held from the last answer is completed by this one,
 *  and the completed cell is not new. It draws as settled rather than as arriving, which is
 *  the quieter of the two mistakes available.
 */
export function freshFrom(cells, had) {
  let seen = 0;
  for (const [i, cell] of cells.entries()) {
    if (seen >= had) return i;
    seen += cell.nodes.length;
  }
  return cells.length;
}

/** Take what a read returned, and say what of it is new.
 *
 *  A shorter answer than what is held is dropped rather than applied: an arm only grows, so
 *  a short one is a stale read landing after a long one and applying it would make the text
 *  retreat. The `why` it carries is still taken, since that is a fact about the record and
 *  not about this answer's length.
 */
export function landed(node, payload) {
  const have = held.get(node) ?? blank();
  const cells = payload.segments ?? [];
  const grown = cells.reduce((sum, cell) => sum + cell.nodes.length, 0);
  have.asking = false;
  have.why = payload.why ?? ENDS;
  if (grown < have.grown) {
    held.set(node, have);
    return { cells: have.cells, fresh: have.cells.length, why: have.why };
  }
  const fresh = freshFrom(cells, have.grown);
  have.cells = cells;
  have.grown = grown;
  held.set(node, have);
  return { cells, fresh, why: have.why };
}

export const full = (node, { cap = CAP } = {}) => (held.get(node)?.grown ?? 0) >= cap;

/** Which of the four ended this arm, or null where nothing has been read for it. */
export const why = node => held.get(node)?.why ?? null;

/** Whether reaching further from here would have to be paid for.
 *
 *  **This is what the pulse means, and it is a price rather than a progress bar.** A reader
 *  scanning rows is deciding where to spend attention before deciding where to spend
 *  inference, so what they need at a glance is which of these are free to look at. An arm
 *  the record carries to the cap is free and says so by showing nothing.
 *
 *  A row with no node under it is the certain case and needs no read to know: nothing was
 *  ever grown there, so every token of an arm from it would have to be made. A row with one
 *  is costly only once the record has been seen to run out, which is why an unread arm is
 *  not costly -- saying so before looking would mark every row in the list.
 *
 *  **And only where it ran out with more to say.** An arm the reader closed continues under
 *  a flag and one that declines has no top row to follow; a roll at either merges onto what
 *  is already there and writes nothing, so a price on them would be charging for a thing
 *  that cannot be delivered. What those two want is a mark of their own and not this one.
 */
export function costly(node) {
  if (node === null || node === undefined) return true;
  const have = held.get(node);
  if (have === undefined) return false;
  return have.why === ENDS && have.grown < CAP;
}

/** The mark a closed continuation ends with, in the arm and in the column alike. One
 *  character, because in a row it has to sit on a line that may not grow. */
export const SHUT = "\u2298";

/* A newline is shown and not obeyed, the way a row's own spelling is: an arm is one line by
 * construction here, and a real break would move every row below it -- `docs/NEXT.md` has
 * the panel holding still as what this stage is for. Where an arm gets the room to run down
 * the page, the newline comes back with it. */
const oneLine = text => text.replace(/\n/g, "\\n");

/** An arm as an element, with what has just arrived marked apart from what was already
 *  there.
 *
 *  Built here and attached by the caller, the way a list of rows is: what a cell is drawn as
 *  is a decision about the record -- which part is new, which part spells nothing -- and
 *  where it hangs is a decision about the page.
 *
 *  **An arm read whole unfurls, and an arm added to animates only its tail.** The first is
 *  one gesture because the reader asked one question and it was answered at once; the second
 *  is the shape the spending will have, where the tail is the only part that was waited for.
 */
export function draw(out) {
  // Nothing is drawn for an arm with nothing in it. The record has no continuation on the
  // top row here, which is a position to spend at rather than a thing to read, and an empty
  // box would say the model had been asked and had nothing to say. **Unless it was closed**
  // -- then there is something to say and nothing to show it with, which is the one case
  // the reader cannot work out for themselves.
  const closed = out.why === CLOSED;
  if (!out.cells.length && !closed) return null;
  const arm = document.createElement("span");
  arm.className = "arm";
  if (out.fresh === 0) arm.classList.add("unfurl");
  for (const [i, cell] of out.cells.entries()) {
    const span = document.createElement("span");
    if (out.fresh > 0 && i >= out.fresh) span.classList.add("lands");
    // A cell that spells no character is marked rather than hidden: an arm that ends inside
    // one is a real ending and the reader is owed the sight of it.
    if (cell.decodes === false) span.classList.add("raw");
    span.textContent = oneLine(cell.text);
    arm.append(span);
  }
  // **An arm that was closed is terminated where it closed.** It ran out short of the cap
  // and nothing else in the row says why, so without this a stub cut at eight tokens reads
  // as one that broke at eight tokens. The caller hangs what it does on it: the mark is
  // what the record says and the gesture is the page's.
  if (closed) arm.append(Object.assign(document.createElement("span"),
    { className: "shut", textContent: SHUT, title: "the rest of this was set aside" }));
  return arm;
}
