/* What is being read: the path drawn, the rule and the toggle it was read under, and where the
 * window stands on it. Every other module reads these and changes them through what is here.
 *
 * The reader's position is a single node and everything else is derived from it -- which
 * root is current, what path is drawn, where a write will land. Holding a root as well
 * would be two pieces of state that can disagree, and `/path/{node}` already answers from
 * a node what the surface needs.
 *
 * That node is the caret, which `cursor.js` holds. It sits after a token and is what every
 * act at a position takes, so pointing at a segment and asking for a draw are one node apart
 * and not two states. Moving it along what is already drawn is a mark and never a read: a
 * path read re-chooses the continuation below the node it is given, so a read at the caret
 * would rearrange the text the reader is pointing into.
 */

import * as cursor from "./cursor.js";
import * as map from "./map.js";
import * as mark from "./mark.js";
import { read as overlays, rule as taken, wants } from "./overlay.js";
import { current, live, marked } from "./roots.js";
import { ask, wrong } from "./wire.js";
import { charter, hover } from "./chart.js";
import { frontier, laid, settled, stage, wakes } from "./app.js";

const $ = id => document.getElementById(id);

/* What is drawn, which is the view the caret is a position within. It is the last response
 * and not a second opinion about where the reader is -- the caret is only ever placed on a
 * node of it, so the two cannot disagree. What it is not is a prediction of the next read:
 * the rule chooses afresh on every arrival, and below the caret it may choose differently. */
export let drawn = [];
let cellsAt = null;   // the path's cells and where each starts in tokens, for the path drawn

/* Whether what has been set aside is drawn. A way of looking: it records nothing, the
 * continuation rule follows liveness either way, and what it reveals it never selects --
 * hidden nodes only ever carry the path on from where the live one ran out. */
export let showHidden = false;

let ruled = taken();  // the rule the path being read was laid out by

/* An act in flight: a draw, a realise, a composer's text, a setting aside. One at a time. */
export let working = false;

/* Where the window stood when the reader last moved it, so the next move can say whether it
 * went down and whether it arrived at the end. */
let wasAtEnd = false;
let wasAt = 0;
let carried = 0;  // until when a scroll is the page's own, and not the reader's
const CARRY = 150;

export const pathIds = () => drawn.flatMap(cell => cell.nodes.map(n => n.id));
export const pathEnd = () => drawn.at(-1)?.nodes.at(-1).id ?? null;

/** The path's cells as they stand on the page, and where each starts in tokens. */
export function cells() {
  const segs = [...$("column").querySelectorAll(".flow .seg")];
  if (segs.length !== drawn.length) return null;
  if (cellsAt?.drawn !== drawn)
    cellsAt = { drawn, at: map.offsets(drawn.map(c => c.nodes.length)) };
  return { segs, at: cellsAt.at };
}

export const atEnd = () =>
  window.scrollY + window.innerHeight >= document.documentElement.scrollHeight - 2;

/** The scrolls of the next moment are the page's own, which nothing reads as the reader's. */
export const carry = () => { carried = performance.now() + CARRY; };
export const carrying = () => performance.now() < carried;

/** Take where the window stands now as where the reader left it. */
export function rebase() {
  wasAtEnd = atEnd();
  wasAt = window.scrollY;
}

/** Take whether the window stands at the end now, and leave where it stood alone. */
export function ended() {
  wasAtEnd = atEnd();
}

/** A scroll the reader made: whether it went down and whether it arrived at the end, against
 *  where the window last stood, with `end` read before anything this scroll set off moved the
 *  page. Where it now stands is taken as where the reader left it. */
export function scrolled(end) {
  const was = { down: window.scrollY > wasAt, arrived: end && !wasAtEnd };
  wasAtEnd = end;
  wasAt = window.scrollY;
  return was;
}

export const busy = on => { working = on; };

export const seeHidden = on => { showHidden = on; };

/** Read a path and say what the toggle makes of it, or null where the reader is standing
 *  in text that is no longer drawn.
 *
 *  Separated from what is drawn because the two answer different questions: this one is about
 *  the record and the toggle, and `laid` is about the column.
 */
async function reading(node) {
  // Each half of what the read can carry is asked for, and a read not asked for one carries
  // none of it. The rule is a parameter of the read and never of the page: what is drawn is
  // the path the server derived, so the page holds no opinion about where it went.
  const want = wants();
  // The mark is not an overlay and reads the same ranking one of them would, so what is
  // asked for is the union of what is on rather than what the panel alone chose.
  const ranked = want.overlays || mark.wants();
  const read = await ask(`/path/${node}?hidden=${showHidden ? 1 : 0}&rule=${taken()}`
    + `&overlays=${ranked ? 1 : 0}&beneath=${want.beneath ? 1 : 0}`);
  let cells = read.segments;
  // Whether the text stops where it does because something was set aside. Either the read's
  // own leaf has nothing live below it, or the cut below happened first -- a path *through*
  // a hidden node ends at the hidden part rather than at the leaf, and both are the reader
  // having closed something rather than the model not having been asked.
  let closed = read.why === "closed";
  if (!showHidden) {
    // The read carries a hidden ancestry whatever the toggle says, since a path through a
    // node that was set aside still reaches it. With the toggle off none of that is drawn,
    // and a reader left standing in it falls back to where the live tree ends.
    const stop = cells.findIndex(cursor.aside);
    if (stop === 0) return null;
    if (stop > 0) { cells = cells.slice(0, stop); closed = true; }
  } else {
    closed = false;  // what was set aside is drawn, so `boundary` is already saying it
  }
  return { read, cells, closed };
}

/** Draw the path through a node, and leave the caret at `where` -- or at the end of what is
 *  drawn, which is where a reader who has not pointed at anything is.
 *
 *  So a draw at the end carries the caret along with it, by as much as it drew. That is the
 *  batch discipline `docs/INTERFERENCE.md` names rather than a convenience of the code:
 *  asking for the next batch is a deliberate act taken after reading the last, so it carries
 *  acceptance of everything above it -- or at least a wish to see past it -- and the caret
 *  standing at the new end is what that looks like. A reader who did not accept it moves the
 *  caret back, which is the same gesture as pointing at anything else.
 */
export async function show(node, where) {
  const got = await reading(node);
  if (got === null) return land(null);
  drawn = got.cells;
  // Where the reader has not pointed, the caret rests at the end of what is drawn -- so the
  // gesture that asks for more of a path and the gesture that asks for a draw at a position
  // are the same act at the same node, which is the ordinary case and not a coincidence.
  cursor.place(where === undefined ? cursor.resting(got.cells) : where);
  hover(null);
  $("column").replaceChildren(laid(got));
  frontier();
  marked();
  wakes();
  settled();
  charter();
  current(got.cells[0].nodes[0].id);
}

/** Nothing drawn and the caret nowhere, which is what a composer in place of the column is. */
export function blank() {
  drawn = [];
  cursor.place(null);
}

/** Where to look once what was being read is no longer drawn. */
export async function land(prefer) {
  if (prefer !== null) return show(prefer);
  const rows = live(await ask("/tree"));
  if (rows.length) return show(rows[0].id);
  stage(null);  // everything is set aside, and the only thing to do is the thing offered
}

/** Arrive at `node` on the path through `through`, flashing it there and in `named` -- the
 *  token in the nav, for a waypoint -- where there is one. */
export async function reach(node, named = null, through = node, hold = null) {
  await show(through, node);
  const seg = $("column").querySelector(".flow .seg.at");
  if (seg === null) return;
  // The page's own scroll, which is not the reader reading on: nothing is asked for and the
  // caret is not moved back into a band it is already in the middle of.
  carry();
  if (hold === null) seg.scrollIntoView({ block: "center" });
  else {
    const got = cells();
    const el = got?.segs[map.holding(got.at, Math.min(hold.depth, got.at.at(-1) - 1))];
    if (el) window.scrollBy(0, el.getBoundingClientRect().top - hold.top);
  }
  for (const el of [seg, named]) {
    if (el === null) continue;
    el.classList.remove("beacon");
    void el.offsetWidth;  // a class taken off and put back in one frame does not restart
    el.classList.add("beacon");
    el.addEventListener("animationend", () => el.classList.remove("beacon"), { once: true });
  }
}

/* The overlay, the continuation rule and what is set aside are all ways of looking, and they
 * share a panel because they are one question asked three times: what of the record is in
 * front of me. Moving any of them re-reads rather than repainting what is already drawn --
 * turning a measure on asks the server for what the last read did not carry, and changing the
 * rule asks for a different path entirely. One path costs milliseconds either way. */

/** Read again after the panel changed: the path held, unless the rule it was laid out by
 *  changed, and then the path the new rule takes through the caret. */
export async function relaid() {
  try {
    const here = cursor.node();
    const through = taken() === ruled ? pathEnd() : here;
    ruled = taken();
    await (here === null ? overlays([], {}) : show(through, here));
  } catch (why) {
    wrong(why);
  }
}
