/* What else was live: the rows at the caret, or at the token the pointer is on.
 *
 * A ranking is content about one position and the toggle that asks for it is a way of
 * looking, so the two are in different places: the switch sits with what is set aside, and
 * the rows stand in the half the reading column leaves empty, at the line they are about.
 *
 * Hovering is a caret that has not been committed. It shows what pointing somewhere would
 * give, by the same rule -- the ranking at the node before the segment under the pointer --
 * and the click that was already there is what commits it. So nothing new is named, and a
 * reader sweeping the column reads the alternatives along it without changing where they are.
 */

import { prefill, rolls } from "./arm.js";
import { hover } from "./chart.js";
import { frontier } from "./column.js";
import { composing } from "./compose.js";
import * as cursor from "./cursor.js";
import { parked, stir } from "./edge.js";
import { weighed } from "./overlay.js";
import * as ranking from "./ranking.js";
import { busy, drawn, rebase, show, showHidden, working } from "./reading.js";
import { refresh, writable } from "./roots.js";
import { ask, say, wrong } from "./wire.js";

const $ = id => document.getElementById(id);

const SEEN = 90;  // ms of quiet before a hover counts, so crossing the page is not a request

/* How long a list takes to replace the one before it, and the two are different gestures.
 * **Scanning is quick because the reader is not reading it yet** -- the pointer is sweeping
 * the text and the panel is keeping up, so what the movement has to do is say that the
 * answer changed, not hold anyone's eye. **A settled arrival is slower** because the reader
 * stopped, and a list that snapped into place under a resting pointer would be a list they
 * have to re-find. */
const SCAN = 130;   // ms, the panel following a pointer across the column
const SETTLE_IN = 280;  // ms, the panel arriving where the reader came to rest

let peeking = null;
let unpeeking = null;  // a token let go of, whose peek goes once nothing else is pointed at
let showing = null;

/* The node the list on screen belongs to, and when it stops moving. A list is left alone
 * while it still answers for the node it was built for -- rebuilding an identical one under
 * the pointer replaces every row with a copy of itself, which costs the reader's hand its
 * place and costs anything in flight the element it was going to land in. */
let drawnAt = null;
let settled_at = 0;

/** Whether the list on screen is still coming into place. */
export const arriving = () => performance.now() < settled_at;

/** Put a list up in place of the one before it, moving in the direction the reader is.
 *
 *  Both are in the document while it happens, and the one leaving stops taking the pointer
 *  so that *what is hovered* keeps meaning the live list. A transition that never runs --
 *  a hidden tab, a reader who asked for no motion -- still has to end, so the removal is
 *  also on a timer and not only on the event.
 */
function swap(box, pace) {
  const column = $("column");
  const old = column.querySelector(".rows:not(.leaving)");
  const down = old === null
    || parseFloat(box.style.top) >= parseFloat(old.style.top || "0");
  box.style.setProperty("--pace", `${pace}ms`);
  box.style.setProperty("--from", down ? "1" : "-1");
  box.classList.add("arriving");
  column.append(box);
  if (old) {
    old.style.setProperty("--pace", `${pace}ms`);
    old.style.setProperty("--from", down ? "-1" : "1");
    old.classList.add("leaving");
    old.addEventListener("transitionend", () => old.remove(), { once: true });
    setTimeout(() => old.remove(), pace + 200);
  }
  // Two frames, because a class set in the same frame as the append is the state the
  // element is first painted in and there is nothing to transition from.
  requestAnimationFrame(() => requestAnimationFrame(() => box.classList.remove("arriving")));
  settled_at = performance.now() + pace;
  setTimeout(() => {
    // A row the pointer is already on was never entered, so the list asks who is under it
    // once it has stopped moving. This is also the earliest a hover may spend anything.
    box.querySelector("li:hover")?.onpointerenter?.();
  }, pace);
}

/* Which gesture the rows are up by, and it is the only thing about them that is provisional.
 * **The caret's list is reachable and a peek's is not**: leaving the token takes the rows with
 * it, so a reader moving towards them commits first -- a click on the token they were peeking
 * from, which is the gesture that was already there. Saying which is which is what makes that
 * a step rather than a list that went away on the approach. */
const CARET = "caret";
const PEEK = "peek";

/** Say which of the two a list is, whether it is being built or is already up.
 *
 *  **It is a word to the stylesheet and never one to the reader.** What a hovered list is and
 *  what would keep it are both said in how it is drawn, because a line of instruction in a
 *  list is read on every list and wanted on none of them after the first.
 *
 *  Already up is the case this is for: a click on the token a peek was taken from asks for the
 *  same rows at the same node, and rebuilding them would take the list out from under the hand
 *  that was reaching for it. So nothing about the rows changes and the claim over them does,
 *  which is exactly what the click changed.
 */
function labelled(box, why) {
  box.classList.remove(CARET, PEEK);
  box.classList.add(why);
}

/** Mark the token the rows are alternatives to, and the caret's own while a peek is up.
 *
 *  **The caret and the pointer each already say where they are, and neither says what the
 *  list is about.** A position sits before a token and the rows are rivals to the one after
 *  it, which is a segment nothing marked -- so a reader could read a list without knowing
 *  which token in front of them it was offering to replace. It is the same segment the row
 *  marked `took` is, said at the other end.
 *
 *  **The caret's mark stays while a peek shows somewhere else**, drawn back rather than taken
 *  away. The caret is the one boundary on the page a reader has to be able to return to, and
 *  a mark around the segment after it says where it stands more exactly than a rule on an
 *  edge does -- so a peek that put it out would take the better of the two sightings of it
 *  away at the moment the reader is furthest from it.
 *
 *  `null` is no list up, and then nothing is marked.
 */
function about(found, why) {
  const seat = at => (at === null ? null : String(drawn[at.cell].nodes.at(-1).id));
  // Read from the caret and not from the list, because that is the rule: the caret's token is
  // marked whenever a list is up, whichever position the list is answering for.
  const held = why === null ? null : seat(ranking.subject(drawn, cursor.node()));
  const peeked = why === PEEK ? seat(found) : null;
  for (const el of $("column").querySelectorAll(".flow .seg")) {
    el.classList.toggle("about", held !== null && el.dataset.node === held);
    el.classList.toggle("peeked", peeked !== null && el.dataset.node === peeked);
  }
  $("column").classList.toggle("peeking", why === PEEK);
}

/** Draw the rows at a node beside `anchor`, which is the span they are about.
 *
 *  `why` is the gesture they are up by, which the list says and the column's mark is drawn in.
 *  It is passed and not read off `pace`: the pace is how fast a list moves, and a caret's list
 *  drawn at a scan's pace is something a later gesture may want.
 */
async function opened(node, anchor, pace, why) {
  if (!ranking.asked() || node === null || anchor === null) return clear();
  let payload = ranking.recall(node);
  if (payload === undefined) {
    // What lies below each row is always asked for, because it is one of the list's two axes
    // and not a way of looking at it. The descent it costs is the one below this node, which
    // is bounded by the subtree the rows partition -- unlike the path's, which is anchored
    // at a root. It takes the toggle with it, so what is cached is cached per toggle: an act
    // drops the lot and so does flipping it, both through `refresh`.
    payload = await ask(`/ranking/${node}?beneath=1&hidden=${showHidden ? 1 : 0}`);
    ranking.remember(node, payload);
  }
  if (showing !== node) return;  // the pointer moved on while this was in the air
  // What the rows are rival to. One derivation feeding both ends, so the row marked as taken
  // and the segment marked in the column cannot come apart.
  const found = ranking.subject(drawn, node);
  about(found, why);
  // The measure is read at the moment of drawing rather than being sent with the read: the
  // response carries every downward measure, so changing which one the rows are sized by
  // costs a redraw and never a request.
  // Already answering for this node. Replacing it with a copy of itself would take the row
  // out from under the reader's hand and strand whatever that row had asked for. Only the
  // label is remade, which is the one thing a click on a peeked token actually changed.
  const up = $("column").querySelector(".rows:not(.leaving)");
  if (drawnAt === node && up !== null) return labelled(up, why);
  const box = ranking.list(payload, found === null ? null : found.node, took, weighed(), rolls);
  // Before it goes up, so a list arrives carrying what the reader already read from it
  // rather than filling in once it has landed.
  prefill(box);
  // The label is the box's own and not the column's state, because both lists are in the
  // document while one replaces the other -- read from the column, the one leaving would
  // claim to be the gesture that displaced it on the way out.
  labelled(box, why);
  // Placed against the column rather than the window, so it scrolls with the text it is
  // about and nothing here listens for a scroll.
  const frame = $("column").getBoundingClientRect();
  box.style.top = `${anchor.getBoundingClientRect().top - frame.top}px`;
  drawnAt = node;
  swap(box, pace);
}

function clear() {
  drawnAt = null;
  about(null, null);  // the mark belongs to the list and goes when it does
  for (const box of $("column").querySelectorAll(".rows")) box.remove();
}

/** Taking a row. Two of the three kinds cost nothing: the one the path took is where the
 *  reader already is, and one realised elsewhere is a selection -- which is the way back to
 *  an arm a draw parted from. The third is an act. */
function took(row, payload) {
  if (composing()) return;  // the same reason a click on a token does nothing
  if (row.child === null) return writable ? realise(row, payload) : undefined;
  show(row.child, row.child).catch(wrong);
}

/** Make the node a row names, and stand the caret on it armed.
 *
 *  `realise` writes one node and calls no model, so what it leaves is a position with nothing
 *  under it -- the alternative made real and not yet followed. Asking for the continuation is
 *  the separate act it already was, and the caret being armed is what makes the next scroll
 *  down that ask, wherever the page is standing. So the reader takes an alternative and keeps
 *  reading, and the act that costs inference is still one gesture of their own.
 *
 *  The source is sent rather than inferred: a token alone names nothing at a node two models
 *  have ranked. The row carries the id the wire keys sources by and the act wants the name,
 *  which the payload the row came from already holds -- as it holds the node these are the
 *  alternatives at. That node and not the caret: with the rows shown, the pointer moves them
 *  ahead of the caret, and clicking one is the click that commits that move.
 */
async function realise(row, payload) {
  if (working || !writable) return;
  busy(true);
  try {
    const act = await ask("/realise", {
      at: payload.node, source: payload.sources[String(row.source)], token: row.token,
    });
    await refresh();
    await show(act.tip, act.tip);
    cursor.arm(drawn);  // placed by `show` above, so the tip is the one just drawn
    frontier();  // placed by `show` and armed after it, so the mark is remade and not patched
    stir();
    say(parked ? "realised \u00b7 the page is parked, enter draws from here"
               : "realised \u00b7 scroll down to draw from here");
  } catch (why) {
    wrong(why);
  } finally {
    busy(false);
    rebase();
  }
}

/** Forget what the rows said became of each row, which an act changes. */
export function stale() {
  drawnAt = null;
}

/** No list answers for anywhere, which is what a composer in place of the column is. */
export function unshown() {
  showing = null;
}

/** The rows open over the map where they are on, and their own ground covers it there. */
export function margin() {
  ranking.want($("rows").checked);
  settled();
}

/** Show the rows the caret is at, which is where they sit when nothing is hovered. */
export function settled() {
  showing = cursor.node();
  const mark = $("column").querySelector(".seg.at");
  if (!ranking.asked() || mark === null) return clear();
  opened(showing, mark, SETTLE_IN, CARET).catch(() => clear());
}

/** Put the rows back where the reader is, and what the pointer is over with them. */
function unpeek() {
  clearTimeout(peeking);
  hover(null);
  settled();
}

function peek(i, el) {
  if (!ranking.asked()) return;
  clearTimeout(peeking);
  const to = cursor.chosen(drawn, i);
  if (to === null || to === showing) return;
  peeking = setTimeout(
    () => { showing = to; opened(to, el, SCAN, PEEK).catch(() => clear()); }, SEEN);
}

/** The pointer arriving on the column's `i`th segment, `el`. */
export function entered(i, el) {
  clearTimeout(unpeeking);
  hover(i);
  peek(i, el);
}

/** The pointer leaving a segment: its peek goes once nothing else is pointed at. */
export function left() {
  clearTimeout(unpeeking);
  unpeeking = setTimeout(unpeek, SEEN);
}

/** The pointer leaving the text, which puts the rows back where the reader is at once, as
 *  leaving a token does after a beat, so a peek never outlives the pointer on its token. */
export function unpeeked() {
  clearTimeout(unpeeking);
  unpeek();
}
