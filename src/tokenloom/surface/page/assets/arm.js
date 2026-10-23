/* The reference arm, read by pointing at a row and bought by resting on it.
 *
 * `docs/SPINE.md` has a stub asked for by hovering the row it belongs to. **What the record
 * already holds arrives at once and unpaced**: a greedy rollout merges onto what an earlier
 * one wrote, so reading the top-row descent is reading what asking again would produce, and
 * a wait before it would be charging the reader for looking.
 *
 * **The arm belongs to the row and the price belongs to the pointer**, and that is the whole
 * division here. An arm is drawn wherever its row is -- on arrival, on a list rebuilt later,
 * whether or not the hand stayed -- because what it says is a fact about the position. The
 * pulse is drawn only under the pointer, because what it says is what the next thing would
 * cost the reader. So hovering only ever means *there is more here*, and a row the tree has
 * no arm for shows nothing at all.
 *
 * **Resting on a price is what buys.** The free read and the paid roll are the same gesture
 * held for different lengths of time, which is what keeps the reader from having to decide
 * what a row is before looking at it: they point, they read what is there, and if what is
 * there runs out under a pulse they can stay. `roll` is where that is paid for.
 *
 * **A row nothing realised is bought the same way, and the fork comes first.** It is two
 * acts rather than one, and the `realise` is free -- so what rests on a row the record has
 * never been down makes the node and then rolls from it, which is one gesture because it
 * is one question: *what does the model say here*. The row changes kind under the pointer
 * rather than the list being rebuilt around it.
 */

import { reveal } from "./column.js";
import { keep } from "./draw.js";
import * as ranking from "./ranking.js";
import { showHidden, working } from "./reading.js";
import { counted, writable } from "./roots.js";
import { arriving } from "./rows.js";
import * as stub from "./stub.js";
import { ask, generated, wrong } from "./wire.js";

const $ = id => document.getElementById(id);

let armed = null;    // the node whose row the pointer is on, or null
let resting = null;  // the row the pointer is on, which has a node only once realised
let restingOn = null;  // where that row is drawn and the payload it came from

/* Milliseconds a pointer rests on a priced row before anything is bought. **It is a
 * different threshold from `rows.js`'s `SEEN` because it guards a different thing**: that one
 * keeps a pointer crossing the page from asking a question, and this one keeps it from spending.
 * A reader sweeping a list passes over priced rows on the way to the one they want, and
 * the pulse is already there to be read before the dwell elapses -- so what is bought is
 * what was looked at. */
const DWELL = 500;

export let buying = null;  // the node being rolled, or null -- one roll at a time
let dwelling = null;  // the timer a rested pointer is counting down

/** The row a node's arm belongs to, in whichever list is the live one.
 *
 *  **An arm belongs to the row and not to the pointer**, so it is drawn where its row is
 *  rather than where the hand is. And the row that asked is not always the row that
 *  answers: leaving the column rebuilds the list at the caret, so a read begun on one
 *  element can land after that element has been replaced by an equal one. The node is what
 *  survives that; the element is not.
 */
const seat = node =>
  $("column").querySelector(`.rows:not(.leaving) li[data-node="${node}"]`);

/** The pulse at the tail of a row. **It is a price and not a progress bar**: it says that
 *  reaching further from here would cost inference, so a row without one is free to look at
 *  and a reader scanning the list can land on those without spending. It follows the pointer
 *  rather than the reading, which is why it is set on arrival and not when an answer comes
 *  back. */
function pulse(where, on) {
  const had = where.querySelector(".more");
  if (!on) return had?.remove();
  if (had) return;
  where.append(Object.assign(document.createElement("span"),
    { className: "more", textContent: "\u2026" }));
}

/** Whether a row carries the price: there is more to buy below it, and a server to buy it from. */
const priced = node => writable && stub.costly(node);

/** Hang an arm in the row it belongs to. What it is drawn as is `stub.draw`; this is where
 *  it goes, what it replaces, and what its closure mark does when taken. */
function paint(where, out) {
  const arm = stub.draw(out);
  const had = where.querySelector(".arm");
  if (arm === null) had?.remove();
  else if (had) had.replaceWith(arm);
  else where.append(arm);
  const mark = arm?.querySelector(".shut");
  if (mark) mark.onclick = event => { event.stopPropagation(); reveal(); };
}

/** Hang what is already held on each row of a list that is about to go up.
 *
 *  **An arm that has been read stays read**, and a list the reader comes back to is the list
 *  they left. What is held is a fact about the position and not about where the pointer has
 *  been, so returning to a row shows what was there instead of asking for it again -- and
 *  the comparison `docs/SPINE.md` wants, several stubs at one position read against each
 *  other, is a thing the reader can look away from and still have.
 *
 *  Nothing animates. It did not just arrive, and saying it had would be the page claiming
 *  something about the record that the reader can see is not so.
 */
export function prefill(box) {
  for (const li of box.querySelectorAll("li[data-node]")) {
    const have = stub.recall(Number(li.dataset.node));
    if (have === undefined) continue;
    paint(li, { cells: have.cells, fresh: have.cells.length, why: have.why });
  }
}

/** Read the arm below a node and draw it, if there is one left to read.
 *
 *  **No wait before it and no parts to it.** The record answers in full, so a reader who
 *  pointed at a row gets what is there at once -- a pause would be charging them for looking
 *  at what has already been paid for. `roll` is the other half, and it is paced because
 *  what it reads has to be made first.
 *
 *  What comes back is drawn whether or not the pointer stayed. The arm is the row's and the
 *  reader asked for it; dropping it because they moved on would leave the record holding
 *  something the page had decided not to show. The price is the other way round -- it is
 *  about where they are looking -- so that is the one thing `armed` still gates.
 */
async function grow(node) {
  const want = stub.reach(node);
  if (want === null) return;
  stub.asking(node, true);
  try {
    const got = await ask(`/stub/${node}?length=${want}&hidden=${showHidden ? 1 : 0}`);
    const out = stub.landed(node, got);
    const li = seat(node);
    if (li === null) return;
    paint(li, out);
    if (armed === node) pulse(li, priced(node));
  } catch {
    // A failed read is not reported: nothing was asked for out loud, and an error where a
    // reader only moved a pointer is noise about something they did not do.
    stub.asking(node, false);
  }
}

/** Make the node a row names if it has none, then roll its arm for as long as the pointer
 *  stays on the row.
 *
 *  **Hovering is the gesture and dwelling is the payment.** A reader scanning a list reads
 *  the pulse, which says that reaching further here would cost inference; resting on it is
 *  the asking, and moving on is the stopping. So what is spent is proportional to what was
 *  looked at, and nothing is bought by crossing a row on the way somewhere else.
 *
 *  **The `realise` is part of the gesture and not a step before it.** It writes one node,
 *  calls no model and merges, so what it costs is a selection -- and a reader comparing
 *  several continuations at one position wants the fork made by looking at the row, not by
 *  committing to it first. What makes the arm worth having is that it is the model's
 *  answer at a place the record has never been, which is exactly the row that has no node.
 *
 *  **It arrives in parts and each part is an act.** `stub.BURST` has why the record would
 *  rather have one act of forty, and why the reader would rather have ten of four. What
 *  the page does between them is read `/stub` again -- the free read, the same one a hover
 *  makes -- so the arm is drawn from the record whether the record or the model last
 *  answered, and there is no second path through which a bought token reaches the page.
 *
 *  **It never moves the column, whichever row it is.** What is bought reaches the page as the
 *  arm in its row and by no other route, so looking leaves the text alone and the rows at a
 *  position are read against each other on equal terms. `docs/SURFACE.md` has why.
 */
async function roll(row, where, payload) {
  // One at a time, against one writer and one cache slot. A second roll would not only
  // queue behind this one, it would truncate the prompt cache this one is warm in --
  // `docs/SPINE.md` measures that at 28 ms against 7.4 s.
  if (buying !== null || working || !writable) return;
  buying = row;
  let last = null;
  try {
    if (row.child === null) {
      // The source is named rather than inferred: a token alone names nothing at a node
      // two models ranked, and the payload the row came from carries the names.
      const act = await ask("/realise", {
        at: payload.node, source: payload.sources[String(row.source)], token: row.token,
      });
      ranking.realised(where, row, act.tip);
      // The row has a node now, and the price follows it only if the pointer is still there.
      if (resting === row) armed = act.tip;
      last = act.tip;
    }
    const node = row.child;
    // The free read first, even where the fork was just made: an arm is read from the
    // record whatever put the record there, and until it has been there is no price.
    await grow(node);
    while (resting === row) {
      const want = stub.burst(node);
      if (want === null) break;
      // The length and the heat are the rollout's own and the rest is the reader's, which
      // is the cut `keep` is named for. Naming no sampler is what makes the act greedy in
      // its own `params` rather than greedy by argument.
      // A greedy draw that failed fails the same way every time it is asked, so one is the end
      // of the roll and is said, which `generated` sees to.
      const act = await generated({
        at: stub.tip(node), params: { ...keep(), length: want, temperature: 0 },
      });
      last = act.tip ?? last;
      const had = stub.recall(node)?.grown ?? 0;
      const out = stub.landed(node, await ask(
        `/stub/${node}?length=${stub.CAP}&hidden=${showHidden ? 1 : 0}`));
      const li = seat(node);
      if (li !== null) {
        paint(li, out);
        // The price follows the pointer and not the reading, the same as everywhere else
        // -- and it is what goes out when the arm reaches the cap, which is the roll
        // ending by having finished rather than by being left.
        if (armed === node) pulse(li, priced(node));
      }
      // And a burst that brought nothing ends it too, whatever the reason: asking again from
      // the same tip under the same settings is asking the same question.
      if ((stub.recall(node)?.grown ?? 0) <= had) break;
    }
  } catch (why) {
    // Said out loud, unlike a failed free read: the reader rested on a price and nothing
    // came of it, which is a thing they did and are owed an answer about.
    wrong(why);
  } finally {
    buying = null;
    // A row the pointer moved on to while this one was buying had its dwell run out against
    // a roll in flight, and nothing would ask for it again until the pointer left and came
    // back. Its clock starts now instead.
    if (resting !== null && resting !== row) dwell(resting, restingOn.where, restingOn.payload);
  }
  if (last === null) return;
  // A `realise` changes what the rows at this position say became of one of them, and a
  // burst gives the arm's old tip a child it did not have. The list on screen was told
  // about the first as it happened and nothing on screen is about the second, so what is
  // dropped is only what would be read again -- a read apiece, where one is opened again.
  ranking.forget();
  await counted();
}

/** The pointer arriving at a row or leaving it.
 *
 *  **Only the price moves with it.** What is drawn in the row was put there by `prefill` or
 *  by a read landing, and it stays -- so hovering says *there is more here* and never *here
 *  is what there is*.
 */
export function rolls(row, where, on, payload) {
  // A list still coming into place is not somewhere to point at. The row under the hand is
  // about to be somewhere else, and reading from it would be answering a question the
  // reader has not finished asking. `swap` asks again once it has stopped.
  if (on && arriving()) return;
  if (!on) {
    // Only if this row is still the one being rested on. A pointer crossing from one row
    // to the next produces a leave and an enter, and nothing guarantees which the page
    // sees first -- clearing unconditionally lets the row being left cancel what its
    // neighbour just started, which shows up as a hover that does nothing every other
    // time. **The row and not its node**, because two rows nothing realised both have
    // none and would answer to each other's departure.
    if (resting === row) {
      clearTimeout(dwelling);
      resting = null;
      restingOn = null;
      armed = null;
    }
    // The price goes with the pointer. It is about where the reader is looking and not about
    // the row, so a list left behind holding half a dozen of them would be saying that six
    // places are about to cost something. A roll already under way is not stopped here --
    // it reads `resting` after each part and stops itself, so the part in flight is paid
    // for and finishes, which is what was asked for.
    return pulse(where, false);
  }
  clearTimeout(dwelling);  // this row supersedes whatever else was counting down
  resting = row;
  restingOn = { where, payload };
  armed = row.child;
  // Set before anything is read, because the pulse follows the pointer and not the answer.
  // A row with no node under it is certainly costly and needs no read to say so.
  pulse(where, priced(row.child));
  // The dwell is counted from the free read, where there is one to make: until it has
  // landed there is no price to have rested on, and `burst` would decline anyway. An arm
  // already held resolves at once, so returning to a row starts the clock immediately --
  // and a row with no node has nothing to read, so its clock starts on arrival.
  dwell(row, where, payload);
}

/** Count the dwell down on a row, from its free read where it has one, and roll it if the
 *  pointer is still there when it runs out. */
function dwell(row, where, payload) {
  const read = row.child === null ? Promise.resolve() : grow(row.child);
  read.then(() => {
    if (resting !== row || !writable) return;
    clearTimeout(dwelling);
    dwelling = setTimeout(() => {
      if (resting === row) roll(row, where, payload).catch(() => {});
    }, DWELL);
  }).catch(() => {});
}
