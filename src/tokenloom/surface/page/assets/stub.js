/* The reference arm as the page grows it: what is held for each position, how long an arm
 * to ask for next, and when to stop asking.
 *
 * `docs/SPINE.md` has the stub as the model left alone from a position, and the gesture that
 * asks for one is a hover -- so the shape of the thing is a loop rather than a request. The
 * pointer rests, a length is asked for, what comes back is longer than what was there, and
 * if the pointer has not moved it asks again. It stops at a cap, or where there is nothing
 * left to ask for.
 *
 * **Lengths and not increments.** `/stub` answers with a prefix of the arm, so growing one is
 * asking for a longer prefix and never for a continuation of what is held. That is what lets
 * the loop be restarted from anywhere, survive a response arriving out of order, and read the
 * record and the model through one path -- the page does not know which of the two answered,
 * and nothing here should.
 *
 * **The burst is a measurement and not a taste.** A full arm is one request's worth of
 * generation at about a second, which is far too long to read as an arrival; a tenth of it
 * lands in roughly a quarter second, which is the eyeblink the gesture is built around. So
 * the loop is what gives the page streaming without the adapter learning to stream.
 */

/** Tokens a hovered arm grows to before it stops asking. The reader can still ask for more
 *  by other means; what this bounds is what pointing at something spends. */
export const CAP = 40;

/** Tokens per ask. ~265 ms of generation against the measured 38 tok/s, which is what makes
 *  each landing read as an arrival rather than as a wait. `docs/SPINE.md`'s *Evidence in
 *  hand* has the timings this comes from. */
export const BURST = 10;

/** Milliseconds of rest before each ask, and a ceiling rather than a target: it is the
 *  longest the reader should have to hold still, and the pace is then set by what the model
 *  actually returns. Resting before the *first* ask is what keeps crossing the page from
 *  being a request; resting before each one after is what makes the growth a thing the
 *  reader can stop by moving. */
export const DWELL = 500;

/* What is held, by the node an arm descends from. An arm only grows, and a longer one
 * supersedes a shorter one entirely rather than being appended to -- so this keeps across
 * hovers and is dropped only when the record changes under it. */
const held = new Map();

export const recall = node => held.get(node);
export const forget = () => held.clear();

/** How long an arm to ask for next, or null when there is nothing left to ask.
 *
 *  Three ways to be finished and they are not the same. **Full** is the cap reached, and the
 *  arm is as long as pointing at something buys. **Spent** is the record having no more of
 *  it, which is where a rollout would have to be paid for -- so it stops the loop here and
 *  is the hook whatever spends will take. **Asking** is one in flight, because a second
 *  request for the same arm would race the first and the later answer is not the longer one.
 */
export function reach(node, { cap = CAP, burst = BURST } = {}) {
  const have = held.get(node);
  if (have === undefined) return Math.min(burst, cap);
  if (have.asking || have.spent || have.grown >= cap) return null;
  return Math.min(have.grown + burst, cap);
}

/** Mark an arm as having a request in flight, so the loop does not start a second. */
export function asking(node, yes) {
  const have = held.get(node) ?? blank();
  have.asking = yes;
  held.set(node, have);
}

const blank = () => ({ cells: [], grown: 0, spent: false, asking: false });

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
 *  a short one is a stale request landing after a long one and applying it would make the
 *  text retreat. The `spent` it carries is still taken, since that is a fact about the
 *  record and not about this answer's length.
 */
export function landed(node, payload) {
  const have = held.get(node) ?? blank();
  const cells = payload.segments ?? [];
  const grown = cells.reduce((sum, cell) => sum + cell.nodes.length, 0);
  have.asking = false;
  have.spent = payload.spent === true;
  if (grown < have.grown) {
    held.set(node, have);
    return { cells: have.cells, fresh: have.cells.length };
  }
  const fresh = freshFrom(cells, have.grown);
  have.cells = cells;
  have.grown = grown;
  held.set(node, have);
  return { cells, fresh };
}

/** Whether an arm is as long as it will get, which is what stops the pulse. An arm that is
 *  spent and one that is full both stop, and a reader is owed the difference: one has
 *  nothing more to show and the other has more to sell. */
export const full = (node, { cap = CAP } = {}) => (held.get(node)?.grown ?? 0) >= cap;
export const spent = node => held.get(node)?.spent === true;

/** An arm as an element, with what has just arrived marked apart from what was already
 *  there.
 *
 *  Built here and attached by the caller, the way a list of rows is: what a cell is drawn as
 *  is a decision about the record -- which part is new, which part spells nothing -- and
 *  where it hangs is a decision about the page.
 *
 *  **Only the new part is animated.** The reader is watching the tail, so motion over text
 *  they have already read would say *this changed* about something that did not.
 */
export function draw(out) {
  // Nothing is drawn for an arm with nothing in it. The record has no continuation on the
  // top row here, which is a position to spend at rather than a thing to read, and an empty
  // box would say the model had been asked and had nothing to say.
  if (!out.cells.length) return null;
  const arm = document.createElement("span");
  arm.className = "arm";
  for (const [i, cell] of out.cells.entries()) {
    const span = document.createElement("span");
    if (i >= out.fresh) span.classList.add("lands");
    // A cell that spells no character is marked rather than hidden: an arm that ends inside
    // one is a real ending and the reader is owed the sight of it.
    if (cell.decodes === false) span.classList.add("raw");
    span.textContent = cell.text;
    arm.append(span);
  }
  return arm;
}
