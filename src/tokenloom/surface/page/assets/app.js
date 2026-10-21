/* The surface: a list of roots, a reading column, and the one composer both of them use.
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
 *
 * Nothing here is remembered between loads but the reader's waypoints, which `waypoint.js`
 * keeps. Reader state lives in the session, and what is live, what parts and what a ranking
 * holds are read from the store every time.
 */

import * as cursor from "./cursor.js";
import { along, draw, keep, panel, place, set, share } from "./draw.js";
import * as room from "./room.js";
import * as map from "./map.js";
import * as mark from "./mark.js";
import {
  panel as overlayPanel, read as overlays, rule as taken, wants, weighed,
} from "./overlay.js";
import * as ranking from "./ranking.js";
import * as stub from "./stub.js";
import * as wake from "./wake.js";
import * as waypoint from "./waypoint.js";

const $ = id => document.getElementById(id);

const { aside } = cursor;

/* Whether what has been set aside is drawn. A way of looking: it records nothing, the
 * continuation rule follows liveness either way, and what it reveals it never selects --
 * hidden nodes only ever carry the path on from where the live one ran out. */
let showHidden = false;

/* Whether the server writes, as `/tree` says. One started to read holds no claim, and the page
 * it serves offers no gesture that writes: no draw, no composer, no realise, no setting aside. */
let writable = true;

// ---- the wire -------------------------------------------------------------------------

class Fault extends Error {
  constructor(kind, message) { super(message); this.kind = kind; }
}

async function ask(path, body) {
  const answer = await fetch(path, body === undefined ? {} : {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
  });
  // A server that fell over before it could phrase an answer sends no JSON at all, and
  // reading it as JSON would report the parse rather than the fault.
  const shape = await answer.json().catch(() => null);
  // A fault says which kind it was because the record does: a refusal and a rejection are
  // answers about the request, and only a failure is worth repeating unchanged.
  if (!answer.ok) {
    throw new Fault(shape?.error || "error", shape?.message || answer.statusText);
  }
  if (shape === null) throw new Fault("error", "the server sent something that is not JSON");
  return shape;
}

/** Ask for a draw, and treat one that broke as the fault it is.
 *
 *  **A `generate` that failed is an act, and it comes back as one.** The record keeps it with
 *  terminator `failed` and no nodes, so the route answers it as made -- and a caller reading
 *  only that something was made would ask again, at the same place, for the same thing. Only
 *  a refusal is turned into a fault on the server, being an answer about the request; the rest
 *  of the ways a draw writes nothing are turned into one here. An `eos` with nothing before it
 *  is an answer and not a fault, and comes back as made.
 */
async function generated(body) {
  const act = await ask("/generate", body);
  if (["failed", "cancelled", "aborted"].includes(act.terminator)) {
    throw new Fault(act.terminator, `act ${act.id} wrote nothing: the draw ${act.terminator}`);
  }
  return act;
}

// ---- the list of roots ----------------------------------------------------------------

/** A label is one line and the column cuts it, so a newline is shown rather than obeyed. */
const oneLine = text => text.replace(/\n/g, "\\n");

function rootRow(root, current) {
  const li = document.createElement("li");
  li.append(oneLine(root.label));
  if (root.forked) {
    // It stopped where the tree parts rather than for room, and the two read the same in
    // the text. Part of the line, so it is clipped with it.
    const mark = document.createElement("span");
    mark.className = "fork";
    mark.textContent = " ⑂";
    mark.title = "the tree parts here";
    li.append(mark);
  }
  // Over the clipped text rather than in it, so it stops the click that would select the
  // root: the row and the control are two gestures in one place and only one is meant.
  const go = document.createElement("button");
  go.className = "flip";
  go.textContent = root.deleted ? "restore" : "hide";
  go.title = root.deleted ? "bring this root back" : "set this root aside";
  go.onclick = event => {
    event.stopPropagation();
    // Restoring lands on the root it brought back; hiding lands wherever there is
    // something to read, since a root has no parent to fall back to.
    flip(root.deleted, root.id, root.deleted ? root.id : null);
  };
  if (writable) li.append(go);
  if (root.deleted) li.classList.add("hidden");
  li.dataset.node = root.id;
  li.setAttribute("aria-current", String(root.id === current));
  li.onclick = () => show(root.id);
  return li;
}

// ---- waypoints ---------------------------------------------------------------------------

/* A waypoint stands under its root, and under the nearest waypoint above it, named by the
 * text either side of it with its own token picked out in the middle. Taking one is an
 * arrival: the path through it, the caret on it in the middle of the window, and the token
 * flashing there and in the nav so the eye finds where it landed. */

const storage = (() => { try { return localStorage; } catch { return null; } })();
let known = null;     // the last answer to `/tree`
let kept = [];        // { node, created }: the waypoints set in this tree, in the order set
let ways = new Map(); // root -> what the server said of the waypoints under it, nested

/** Ask what the kept waypoints are now: where each stands, whether it is live, and what
 *  leads up to it. Nothing is asked when there are none. */
async function named() {
  const rows = kept.length
    ? (await ask(`/waypoints?nodes=${kept.map(w => w.node).join(",")}`)).waypoints : [];
  ways = waypoint.nest(rows, kept);
}

function wayRows(item, depth) {
  const li = document.createElement("li");
  li.className = "waypoint";
  li.style.setProperty("--depth", depth);
  // The lead is clipped at its far end and the trail at its own, so the token holds the
  // middle of the row however wide the nav is.
  const lead = document.createElement("span");
  lead.className = "lead";
  lead.append(Object.assign(document.createElement("span"), { textContent: oneLine(item.lead) }));
  const token = Object.assign(document.createElement("b"), { textContent: oneLine(item.token) });
  const trail = Object.assign(document.createElement("span"), {
    className: "trail", textContent: oneLine(item.trail),
  });
  if (item.parts) {
    const mark = Object.assign(document.createElement("span"), {
      className: "fork", textContent: " ⑂", title: "the tree parts here",
    });
    trail.append(mark);
  }
  const go = document.createElement("button");
  go.className = "flip";
  go.textContent = "×";
  go.title = "clear this waypoint";
  go.onclick = event => { event.stopPropagation(); waymark(item.node); };
  li.append(lead, token, trail, go);
  // Set aside since it was set, which is shown whatever the toggle says: it is the reader's
  // mark, and dropping it would lose what they asked to keep.
  if (!item.live) li.classList.add("hidden");
  li.dataset.waypoint = item.node;
  li.onclick = () => reach(item.node, token);
  return [li, ...item.below.flatMap(under => wayRows(under, depth + 1))];
}

/** Arrive at `node` on the path through `through`, flashing it there and in `named` -- the
 *  token in the nav, for a waypoint -- where there is one. */
async function reach(node, named = null, through = node, hold = null) {
  await show(through, node);
  const seg = $("column").querySelector(".flow .seg.at");
  if (seg === null) return;
  // The page's own scroll, which is not the reader reading on: nothing is asked for and the
  // caret is not moved back into a band it is already in the middle of.
  carried = performance.now() + CARRY;
  if (hold === null) seg.scrollIntoView({ block: "center" });
  else window.scrollBy(0, seg.getBoundingClientRect().top - hold);
  for (const el of [seg, named]) {
    if (el === null) continue;
    el.classList.remove("beacon");
    void el.offsetWidth;  // a class taken off and put back in one frame does not restart
    el.classList.add("beacon");
    el.addEventListener("animationend", () => el.classList.remove("beacon"), { once: true });
  }
}

/** Set a waypoint at `node`, or clear the one there. */
async function waymark(node) {
  kept = waypoint.toggle(kept, node, Date.now());
  if (!waypoint.save(storage, known.created ?? known.path, kept))
    say("this browser is not keeping waypoints, so these go with the page", true);
  marked();
  await named();
  drawRoots(known, drawn[0]?.nodes[0].id);
  charted = null;
  charter();
}

/** Mark each segment holding a waypoint. */
function marked() {
  const at = new Set(kept.map(w => w.node));
  const segs = [...$("column").querySelectorAll(".flow .seg")];
  if (segs.length !== drawn.length) return;
  for (const [i, el] of segs.entries())
    el.classList.toggle("waypoint", drawn[i].nodes.some(n => at.has(n.id)));
}

/** Last in the list, which is the row the root it makes will occupy. */
function newRow() {
  const li = document.createElement("li");
  li.className = "new";
  const go = document.createElement("button");
  go.textContent = "+";
  go.title = "start something new";
  go.onclick = () => stage(null);
  li.append(go);
  return li;
}

function drawRoots(tree, current) {
  const rows = live(tree).flatMap(root => [
    rootRow(root, current), ...(ways.get(root.id) ?? []).flatMap(item => wayRows(item, 1)),
  ]);
  // An empty list and a list emptied by the toggle are different states, and a reader who
  // has set everything aside would otherwise be told the tree is new.
  if (!rows.length) rows.push(Object.assign(document.createElement("li"), {
    className: "none",
    textContent: tree.roots.length ? "Everything here is set aside." : "Nothing here yet.",
  }));
  $("roots").replaceChildren(...rows, ...(writable ? [newRow()] : []));
}

/** The roots the toggle admits. */
const live = tree => tree.roots.filter(root => showHidden || !root.deleted);

async function refresh(current) {
  // Every act lands through here, and an act is what makes a ranking read earlier wrong: the
  // rows only grow, but which of them a node now realises does not.
  ranking.forget();
  // An arm is what the tree holds on the top row, so an act can lengthen one or take it
  // off the top row entirely. Both make what is held wrong in the same way the rows are.
  stub.forget();
  drawnAt = null;  // the rows said what became of each row, and an act has changed that
  charted = null;  // and the strands, wherever it landed
  const tree = known = await ask("/tree");
  writable = tree.writable !== false;
  document.body.classList.toggle("read-only", !writable);
  // Keyed by the tree and not by the address, which names only the server.
  kept = waypoint.load(storage, tree.created ?? tree.path);
  walked = map.recall(storage, tree.created ?? tree.path);
  await named();
  drawRoots(tree, current);
  tally(tree);
  return tree;
}

/** What the tree is, in the status line. */
const tally = tree =>
  say(`${tree.path}  ${tree.vocabulary}  ` +
      `${tree.counts.nodes} nodes  ${tree.counts.edges} edges  ${tree.counts.acts} acts`);

/** The counts again, and nothing else.
 *
 *  A roll writes, so the figures move -- but `refresh` drops every arm and every ranking,
 *  which is right for an act the reader asked for out loud and wrong for one they are
 *  watching arrive. What a burst invalidates is bounded and the caller says what to do
 *  about it; this is only the part of `refresh` that is true after any write at all.
 */
const counted = async () => tally(await ask("/tree"));

// ---- the reading column ---------------------------------------------------------------

/** The mark a closure carries, wherever one is drawn. It is its own element because it is
 *  set in a face the words are not -- U+2298 is missing from some system UI faces and falls
 *  back to a tofu box, the same hazard the fork mark in the roots list hedges against. */
const shut = () => Object.assign(document.createElement("span"),
  { className: "shut", textContent: stub.SHUT });

/** Where the path leaves what is live, and the way back. One of these: what is hidden is a
 *  suffix, because the rule picks the live path first. */
function boundary(cell) {
  const mark = document.createElement("span");
  mark.className = "cut";
  const go = document.createElement("button");
  go.textContent = "restore";
  go.title = "bring this back into the live tree";
  go.onclick = () => restore(cell);
  mark.append(shut(), "set aside", ...(writable ? [go] : []));
  return mark;
}

/** The same boundary with nothing drawn after it: the path stops here because what carries
 *  it on was set aside.
 *
 *  **It is the one thing the column could not say.** A path that has not been continued and
 *  a path the reader closed both end with the text simply stopping, and the difference is
 *  the difference between somewhere to spend and somewhere to reopen. Taking it shows the
 *  tail, which puts `boundary` above it and the `undelete` with it -- so this is the same
 *  component in the state where the text it would precede is not drawn.
 */
function closure() {
  const mark = document.createElement("span");
  mark.className = "cut";
  const go = document.createElement("button");
  go.textContent = "show";
  go.title = "draw what was set aside below this";
  go.onclick = reveal;
  mark.append(shut(), "set aside", go);
  return mark;
}

/** `marks` is what the overlay made of each span and `takers` what the mark made of it,
 *  either being null where that one is not drawn -- which is the column a reader has not
 *  asked anything of, and is why both are applied here rather than being something a span
 *  always carries. The two have the same shape and share nothing else: each names a class, a
 *  place on its own scale and what it says, and neither knows the other ran. */
function spans(segments, marks, takers) {
  const out = [];
  let cut = false;
  for (const [i, cell] of segments.entries()) {
    const hidden = aside(cell);
    if (hidden && !cut) { cut = true; out.push(boundary(cell)); }
    const el = document.createElement("span");
    el.className = `seg${cell.decodes ? "" : " raw"}${hidden ? " hidden" : ""}`;
    el.textContent = cell.text;
    el.dataset.node = cell.nodes[cell.nodes.length - 1].id;
    // Who took the token is its own class and never the overlay's: the two axes are
    // independent, so a segment whose value cannot be trusted still says whose it is. Each
    // hands over a place on its own scale, under its own property, and the stylesheet owns
    // both colours -- so a palette stays in one file and a theme changes nothing here.
    const said = [];
    const taker = takers?.[i];
    if (taker) {
      el.classList.add(taker.cls);
      // A line whose value was never priced says so in the style it is drawn in, which is
      // the same appearance every other unreadable value gets.
      if (taker.odd) el.classList.add("odd");
      el.style.setProperty("--m", taker.t.toFixed(3));
      said.push(taker.title);
    }
    const mark = marks?.[i];
    if (mark) {
      el.classList.add(mark.cls);
      if (mark.t !== undefined) el.style.setProperty("--t", mark.t.toFixed(3));
      said.push(mark.title);
    }
    // Both axes are on one span and both have something to say about it, so the title holds
    // whichever are drawn rather than whichever was applied last.
    if (said.length) el.title = said.join("\n");
    // A plain click points at this token, which puts the caret where an alternative to it
    // would stand. `docs/SURFACE.md` has that same gesture opening a ranking, and it is the
    // same selection: the rows it would show are the rows at the node the caret lands on.
    // The one gesture that changes the tree from here asks for a modifier and says so.
    el.onclick = event => {
      // An open composer is aimed at the position it was opened at, so the caret may not leave
      // it: the two would then say different things about where the text is going, and only
      // one of them is on screen. The status line has the way out of it.
      if (composing()) return;
      if (!event.altKey || !writable) return point(i);
      if (hidden) restore(cell);
      else flip(false, cell.nodes[0].id, cell.nodes[0].parent);
    };
    el.onmouseenter = () => { clearTimeout(unpeeking); hover(i); peek(i, el); };
    el.onmouseleave = () => { clearTimeout(unpeeking); unpeeking = setTimeout(unpeek, SEEN); };
    // The caret is drawn *on* the segment it follows and never between segments. An element
    // in the flow moves the text around it, and text that shifts as the reader points at it
    // is friction in the one thing this page is for. A rule on an inside edge costs no
    // layout at all, which is the same reason the hover mark is a glow.
    out.push(el);
  }
  return out;
}

/** Say where the caret stands, over what is already drawn.
 *
 *  Its own pass and not something a span is built with, because the caret moves without the
 *  text doing -- so putting it somewhere else along what is drawn is a mark to move, and the
 *  text it is a mark on is never read again to place it.
 *
 *  Everything after it is drawn because the rule reaches it and not because the reader
 *  accepted it -- the caret is the frontier of what they have, and what lies past it is
 *  derived and never remembered. So it is subdued, which says so without hiding it.
 */
function frontier() {
  let past = false;
  for (const el of $("column").querySelectorAll(".flow .seg")) {
    const here = Number(el.dataset.node) === cursor.node();
    el.classList.toggle("past", past);
    el.classList.toggle("at", here);
    el.classList.toggle("armed", here && cursor.armed());
    if (here) past = true;
  }
  chartCaret();
}

/** Point at a segment, which moves the caret before it over text that does not move.
 *
 *  **It takes no read, and it may not take one.** A path read is an ancestry and a fresh
 *  continuation below it, so reading at the caret re-chooses everything under the reader's
 *  finger -- and where an arm has been rolled, what the rule picks there is the arm.
 *  `docs/SURFACE.md`'s *Pointing is not arriving* has it. The node `chosen` lands on is the
 *  last node of the segment before it and is already drawn, so the mark is all there is to
 *  move.
 */
function point(i) {
  const to = cursor.chosen(drawn, i);
  if (to === null) return;
  cursor.place(to);
  frontier();
  settled();
}

/** Put the caret back at the tip of what is drawn, which is where a reader who has pointed at
 *  nothing stands.
 *
 *  **Pointing has no other way out.** Every segment is somewhere to point and the tip is a
 *  segment like the rest, so without this the resting position is reachable only by reloading
 *  -- and since nothing arms away from the tip, a reader who pointed somewhere would have no
 *  way back to the scroll gesture at all. It takes no read, for the reason `point` gives.
 */
function release() {
  if (composing()) return;
  const to = cursor.resting(drawn);
  if (to === null || to === cursor.node()) return;
  cursor.place(to);
  frontier();
  settled();
}

/* What is drawn, which is the view the caret is a position within. It is the last response
 * and not a second opinion about where the reader is -- the caret is only ever placed on a
 * node of it, so the two cannot disagree. What it is not is a prediction of the next read:
 * the rule chooses afresh on every arrival, and below the caret it may choose differently. */
let drawn = [];

// ---- what else was live -----------------------------------------------------------------

/* A ranking is content about one position and the toggle that asks for it is a way of
 * looking, so the two are in different places: the switch sits with what is set aside, and
 * the rows stand in the half the reading column leaves empty, at the line they are about.
 *
 * Hovering is a caret that has not been committed. It shows what pointing somewhere would
 * give, by the same rule -- the ranking at the node before the segment under the pointer --
 * and the click that was already there is what commits it. So nothing new is named, and a
 * reader sweeping the column reads the alternatives along it without changing where they are.
 */

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
  show(row.child, row.child).catch(
    why => say(`${why.kind || "unreachable"}: ${why.message}`, true));
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
  working = true;
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
    say(`${why.kind || "unreachable"}: ${why.message}`, true);
  } finally {
    working = false;
    wasAtEnd = atEnd();
    wasAt = window.scrollY;
  }
}

/* ---- the reference arm, read by pointing at something ----
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

let armed = null;    // the node whose row the pointer is on, or null
let resting = null;  // the row the pointer is on, which has a node only once realised
let restingOn = null;  // where that row is drawn and the payload it came from

/* Milliseconds a pointer rests on a priced row before anything is bought. **It is a
 * different threshold from `SEEN` because it guards a different thing**: that one keeps a
 * pointer crossing the page from asking a question, and this one keeps it from spending.
 * A reader sweeping a list passes over priced rows on the way to the one they want, and
 * the pulse is already there to be read before the dwell elapses -- so what is bought is
 * what was looked at. The number is a first one and is settled by use. */
const DWELL = 420;

let buying = null;    // the node being rolled, or null -- one roll at a time
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

/** What a closure mark does when it is taken: show what is set aside, wherever it is.
 *
 *  **It reveals and it does not revive.** Turning the toggle on brings the hidden tail back
 *  into the column with `.cut` standing at its head, and that boundary is where `undelete`
 *  already lives -- so the reader sees what they closed before deciding to reopen it, and
 *  nothing the surface does on a click puts a node back that they put away. It is also why
 *  the mark can sit in a hover panel at all: it costs a view and never an act.
 */
function reveal() {
  if (showHidden) return;
  $("hidden").checked = true;
  $("hidden").onchange();
}

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
function prefill(box) {
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
    say(`${why.kind || "unreachable"}: ${why.message}`, true);
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
function rolls(row, where, on, payload) {
  // A list still coming into place is not somewhere to point at. The row under the hand is
  // about to be somewhere else, and reading from it would be answering a question the
  // reader has not finished asking. `swap` asks again once it has stopped.
  if (on && performance.now() < settled_at) return;
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

/** Show the rows the caret is at, which is where they sit when nothing is hovered. */
function settled() {
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
    const stop = cells.findIndex(aside);
    if (stop === 0) return null;
    if (stop > 0) { cells = cells.slice(0, stop); closed = true; }
  } else {
    closed = false;  // what was set aside is drawn, so `boundary` is already saying it
  }
  return { read, cells, closed };
}

/** The text itself, as an element, built apart from being hung. */
function laid({ read, cells, closed }) {
  const flow = document.createElement("div");
  flow.className = "flow";
  // Leaving the text puts the rows back where the reader is at once, as leaving a token does
  // after a beat, so a peek never outlives the pointer on its token.
  flow.onmouseleave = () => { clearTimeout(unpeeking); unpeek(); };
  // Read over what is drawn and not over what came back, so a path-relative scale takes its
  // range from the text in front of the reader.
  flow.append(...spans(cells, overlays(cells, read.sources), mark.read(cells, read.kinds)));
  if (closed) flow.append(closure());
  return flow;
}

async function show(node, where) {
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
  // Which root is current is derived from the path rather than held beside the position,
  // so the two cannot disagree about where the reader is.
  const root = got.cells[0].nodes[0].id;
  for (const li of $("roots").querySelectorAll("li[data-node]"))
    li.setAttribute("aria-current", String(Number(li.dataset.node) === root));
}

// ---- setting aside, and bringing back ---------------------------------------------------

/* `delete` sets a flag on one node and `undelete` clears it. Nothing leaves the store, so
 * both are ordinary acts under their own verbs and the page reads the record again after
 * either -- what changed is liveness, which is derived and never held here.
 */

/** Where to look once what was being read is no longer drawn. */
async function land(prefer) {
  if (prefer !== null) return show(prefer);
  const rows = live(await ask("/tree"));
  if (rows.length) return show(rows[0].id);
  stage(null);  // everything is set aside, and the only thing to do is the thing offered
}

async function flip(undo, node, then) {
  if (working) return;
  working = true;
  try {
    await ask(undo ? "/undelete" : "/delete", { node });
    await refresh();
    await land(then);
  } catch (why) {
    say(`${why.kind || "unreachable"}: ${why.message}`, true);
  } finally {
    working = false;
    wasAtEnd = atEnd();  // the path just got shorter or longer; an arrival is a fresh one
    wasAt = window.scrollY;
  }
}

/** The node to bring back is the one that carries the flag, which is not always the first
 *  of the segment: below the boundary a node is out of the live tree on its ancestor's
 *  account, and clearing its own flag would change nothing and say it had. */
function restore(cell) {
  const back = cell.nodes.find(n => n.deleted);
  if (!back) return say("nothing here carries the flag; what hides it is further up");
  flip(true, back.id, back.id);
}

// ---- the composer ---------------------------------------------------------------------

/* One component. What changes between starting something and continuing or branching from
 * a position is `at`, which is the node the text hangs under and is null for a root.
 *
 * Staging it writes nothing. The act is the submit, which is what keeps the gesture that
 * offers a place to write separate from the write.
 */
function compose(at) {
  const box = document.createElement("div");
  box.className = "compose";
  const area = document.createElement("textarea");
  area.placeholder = at === null
    ? "Something to start from. It is tokenised as written."
    : "Text to hang under this position.";
  const fault = document.createElement("span");
  fault.className = "fault";
  const go = document.createElement("button");
  go.textContent = "create";

  const submit = async () => {
    const text = area.value;
    if (!text) return;
    fault.textContent = "";
    go.disabled = area.disabled = true;
    try {
      const act = await ask("/create", { at, text });
      await refresh();
      await show(act.tip);
    } catch (why) {
      // A rejection left no trace in the record, so what it offers is an edit.
      fault.textContent = `${why.kind}: ${why.message}`;
      go.disabled = area.disabled = false;
      area.focus();
    }
  };

  go.onclick = submit;
  area.onkeydown = event => {
    if (event.key === "Enter" && (event.metaKey || event.ctrlKey)) submit();
  };

  const foot = document.createElement("div");
  foot.className = "foot";
  foot.append(Object.assign(document.createElement("span"), {
    className: "grow", textContent: "⌘⏎ / ctrl⏎",
  }), fault, go);
  box.append(area, foot);
  return box;
}

function stage(at) {
  drawn = [];
  cursor.place(null);
  showing = null;
  if (!writable) return $("column").replaceChildren();
  $("column").replaceChildren(compose(at));
  $("column").querySelector("textarea").focus();
}

/* **A token the model never ranked is one the surface cannot reach, and nothing past it is
 * reachable either.** The rows are what the record ranked, so a word the model did not
 * consider is a branch no gesture arrives at -- and the reader who wants to steer through one
 * has no way to say so. The act for it is already here: `create` takes the position it hangs
 * under, `/create` forwards it, and `compose` has been written for both cases from the start.
 * What was missing is a place to type that is not the whole column.
 *
 * So this is that component's other half rather than a second composer. A root replaces the
 * column because there is nothing to read yet; this one stands *in* the text at the caret, and
 * what is below it stays. **A draw at the caret takes that text down and this does not**, which
 * looks like the same gesture wanting two answers and is not: a draw replaces what is below with
 * something the reader has not seen, and the old text standing under it would be read as part of
 * the new one. Here the reader is writing the replacement themselves, and what they are replacing
 * is the thing they want in front of them while they do.
 */

/** Whether a composer is open in the column. It holds the gestures that write, because they
 *  all land at the caret and the caret is where the typing is going. */
const composing = () => $("column").querySelector(".author") !== null;

/** Take an open composer away, from wherever the reader is when they ask.
 *
 *  **The key that leaves it is the page's and not the box's.** A reader who clicked somewhere
 *  else has a composer that is still open and no longer has the focus, and the way out of it
 *  cannot be a key only the thing they just left would hear.
 */
function unauthor() {
  $("column").querySelector(".author")?.remove();
  say("");
}

/** Open a composer at the caret, carrying the token it would stand instead of.
 *
 *  **Pre-filled and selected, so the first keystroke is the replacement.** The token after the
 *  caret is the one being reconsidered -- the one the rows are alternatives to and the one the
 *  column outlines -- so it is read with the same derivation that marks it, and the box starts
 *  on exactly what is marked. At the tip there is no such token and the box starts empty, which
 *  is the same gesture with nothing to say about it.
 *
 *  **What it writes is a sibling and never a change.** The text hangs under the caret, so the
 *  token that stood there still stands, on its own branch, with everything below it: authoring
 *  takes nothing away and the act is as reversible as any other. What is drawn afterwards is
 *  the path through what was made, which is `show` doing what it does for every act.
 */
function author() {
  if (working || composing() || !writable) return;
  const flow = $("column").querySelector(".flow");
  const at = cursor.node();
  if (flow === null || at === null) return;
  const standing = ranking.subject(drawn, at);

  const box = document.createElement("span");
  box.className = "author";
  box.spellcheck = false;
  // `plaintext-only` is what keeps a paste from bringing markup in with it, and setting it
  // where it is not understood throws rather than being ignored. Falling back leaves the box
  // editable and loses nothing that matters: what is sent is `textContent` either way.
  const editable = yes => {
    const want = yes ? "plaintext-only" : "false";
    try { box.contentEditable = want; } catch { box.contentEditable = yes ? "true" : "false"; }
  };
  editable(true);
  box.textContent = standing === null ? "" : drawn[standing.cell].text;

  let sending = false;

  const send = async () => {
    const text = box.textContent;
    if (sending || !text) return;
    sending = true;
    working = true;
    editable(false);
    try {
      const act = await ask("/create", { at, text });
      await refresh();
      // Which replaces the column, and the composer with it.
      await show(act.tip);
      say(`${act.nodes.length} token${act.nodes.length === 1 ? "" : "s"} authored`);
    } catch (why) {
      // A rejection left no trace in the record, so what it offers is an edit and not a
      // dismissal -- the same answer the root composer gives, in the one place there is.
      say(`${why.kind || "unreachable"}: ${why.message}`, true);
      editable(true);
      box.focus();
      sending = false;
    } finally {
      working = false;
      wasAtEnd = atEnd();
      wasAt = window.scrollY;
    }
  };

  box.onkeydown = event => {
    if (event.key === "Escape") { event.preventDefault(); unauthor(); return; }
    if (event.key === "Enter" && (event.ctrlKey || event.metaKey)) {
      event.preventDefault();
      send().catch(() => {});
    }
  };

  // In the text at the caret, and not instead of it. **What stands below is what the reader is
  // writing an alternative to**, so it is theirs to look at while they do -- taking it down
  // would hide the one thing the new text is being measured against. It moves along and down to
  // make room, which is what text does for text.
  const mark = flow.querySelector(".seg.at");
  if (mark === null) flow.append(box); else mark.insertAdjacentElement("afterend", box);
  box.focus();
  // The whole of it, so typing replaces rather than appends. A caret left at one end would
  // make the pre-fill something to delete, which is the opposite of what putting it there
  // was for.
  const all = document.createRange();
  all.selectNodeContents(box);
  const where = window.getSelection();
  where.removeAllRanges();
  where.addRange(all);
  say("typing replaces it \u00b7 ctrl\u23ce writes it, esc leaves");
}

// ---- continuing ------------------------------------------------------------------------

/* The gesture is the scroll: reaching the end of what there is to read asks for more of it,
 * at the caret -- which is where the reader is already looking, because left alone it follows
 * the end of the path. Pointing somewhere moves it, and then the same gesture asks there
 * instead: one anchor for every act at a position, and not a second rule for this one.
 *
 * A downward move *at* the end counts as well as an arrival there. Under about a thousand
 * characters the column sits at its minimum height, so text that lands does not make the
 * page any taller -- the room above it shrinks instead -- and a reader who stayed at the end
 * would have nowhere left to scroll and no way to ask again.
 *
 * An armed caret drops the end of the page from the gesture. Arriving at the end is what
 * makes an ordinary scroll deliberate; a caret armed by `realise` was placed by a click on a
 * row drawn in front of the reader, which is the same deliberateness spent earlier -- so the
 * next scroll down asks wherever the page is standing, and asking once disarms it.
 */

const SETTLE = 140;  // ms of quiet before a scroll counts, so momentum is not a request
const REST = 450;    // ms after one lands, so a held key is one request and not twenty
const AIR = 1.5;     // lines of context the caret keeps between itself and either edge

let working = false;
let quiet = 0;
let timer = null;

const atEnd = () =>
  window.scrollY + window.innerHeight >= document.documentElement.scrollHeight - 2;

function pending(...what) {
  const box = document.createElement("div");
  box.className = "pending";
  box.append(...what);
  const had = $("column").querySelector(".pending");
  if (had) had.replaceWith(box); else $("column").append(box);
  return box;
}

/* What a draw leaves behind it, which `wake.js` times. While it is asked for, a row of
 * placeholders stands straight after the caret, one for each token it may bring, and glows;
 * once it lands, what it brought takes them over segment by segment, and the run it makes
 * keeps the glow a while and then lets it go. So the mark answers *what just landed*, and
 * draws in quick succession leave a trail. The row is where the length line's pulse hands
 * over to -- that one stops as the draw is asked, which is when this one starts.
 *
 * A run is one element around its segments, so its glow is one box broken only where the line
 * breaks: a tunnel the text runs through, with no edge between one token and the next. */
let landing = null;  // a draw that has landed and is not drawn yet: { ids, length }
let traces = [];     // { ids, length, born, count, hold }: what each draw brought, while it shows
let revealing = [];  // { trace, segs, sizes, run }: what is still taking its placeholders over,
                     // and the last run of it, where what is left of the row stands

const column = $("column");
column.style.setProperty("--rise", `${wake.RISE}ms`);
column.style.setProperty("--decay", `${wake.DECAY}ms`);
column.style.setProperty("--wink-for", `${wake.WINK}ms`);
column.style.setProperty("--dimmed",
                         `color-mix(in srgb, var(--accent) ${wake.DIM * 100}%, transparent)`);

const slots = n => Array.from({ length: n }, () => [
  Object.assign(document.createElement("span"), { className: "slot" }), " ",
]).flat();

/** A run around `els`, which stand next to each other in the flow. */
function enclose(els) {
  const run = document.createElement("span");
  run.className = "run";
  els[0].before(run);
  run.append(...els);
  return run;
}

/** Mark what is drawn with whatever is still under way, resumed where it had got to: the
 *  column is rebuilt by every read, and a rebuild is not the draw landing again. */
function wakes() {
  const now = performance.now();
  const brought = (ids, cell) => cell.nodes.some(n => ids.has(n.id));
  if (landing !== null) {
    const { ids, length } = landing;
    const count = drawn.filter(cell => brought(ids, cell)).length;
    traces.push({ ids, length, born: now, count, hold: wake.hold(count, still.matches) });
    landing = null;
  }
  traces = wake.trail(traces, now);
  revealing = [];
  const segs = [...column.querySelectorAll(".flow .seg")];
  if (segs.length !== drawn.length) return;
  for (const trace of traces) {
    // The newest claims a segment first, since a variation that merged brings nodes an older
    // draw did.
    const at = drawn.flatMap((cell, i) =>
      traces.findLast(t => brought(t.ids, cell)) === trace ? [i] : []);
    if (!at.length) continue;
    const mine = at.map(i => segs[i]);
    // One run for each stretch that stands together, so wrapping never reorders the text.
    const stretches = at.reduce((out, i, k) => {
      if (k > 0 && i === at[k - 1] + 1) out.at(-1).push(segs[i]); else out.push([segs[i]]);
      return out;
    }, []);
    let run = null;
    for (const stretch of stretches) {
      run = enclose(stretch);
      run.style.setProperty("--hold", `${wake.delay(trace, now)}ms`);
      run.style.setProperty("--wink", `${wake.delay(trace, now) + wake.DECAY}ms`);
      const done = run;
      done.onanimationend = event => {
        if (event.target !== done || event.animationName !== "wink") return;
        // Moved, a segment still marked as arriving would arrive again.
        for (const el of done.querySelectorAll(".arrives")) el.classList.remove("arrives");
        done.replaceWith(...done.childNodes);
      };
    }
    // Under reduced motion it is simply there.
    if (!still.matches && now - trace.born < wake.arrived(trace.count)) {
      for (const el of mine) el.classList.add("due");
      revealing.push({ trace, segs: mine, sizes: at.map(i => drawn[i].nodes.length), run });
    }
  }
  if (revealing.length) requestAnimationFrame(unveil);
}

/** One frame of the runs taking their placeholders over: each segment due by now comes in,
 *  and what is left of the row stands after it, until the last is in and the row goes. */
function unveil(now) {
  for (const r of revealing) {
    const n = wake.shown(now - r.trace.born, r.trace.count);
    let tokens = 0;
    for (const [k, el] of r.segs.entries()) {
      if (k >= n) break;
      tokens += r.sizes[k];
      if (el.classList.contains("due")) el.classList.replace("due", "arrives");
    }
    const want = n >= r.trace.count ? 0 : wake.tail(r.trace.length, tokens);
    const have = r.run.querySelectorAll(".slot");
    if (have.length > want) {
      for (const slot of [...have].slice(want)) { slot.nextSibling?.remove(); slot.remove(); }
    } else if (have.length < want) {
      r.run.append(...slots(want - have.length));
    }
  }
  revealing = revealing.filter(r =>
    r.segs.some(el => el.classList.contains("due")) || r.run.querySelector(".slot") !== null);
  if (revealing.length) requestAnimationFrame(unveil);
}

/** The row of placeholders, straight after the caret, which is where what is asked for will
 *  start. A caret that ends a run still glowing stands the row after the run; one inside a run
 *  takes the run apart, since what follows it there is about to be replaced. */
function waiting(length = draw().length) {
  const at = column.querySelector(".flow .seg.at");
  const row = Object.assign(document.createElement("span"), { className: "run waiting" });
  row.append(...slots(length));
  if (at === null) return pending(row);
  const run = at.closest(".run");
  if (run === null) at.after(row);
  else if ([...run.querySelectorAll(".seg")].at(-1) === at) run.after(row);
  else {
    run.replaceWith(...run.childNodes);
    at.after(row);
  }
}

/** Take the text below the caret down while a variation is drawn at it, and put it back.
 *
 *  What stands below is what the draw is about to replace, and leaving it there shows the
 *  reader one continuation and then exchanges it for another. Hidden and not re-read: the
 *  segments below are part of what the text above is measured against, so a column rebuilt
 *  short would move the wash on lines this act is not about. The caret's own mark is what the
 *  stylesheet finds them by, every one of them being a sibling after it or after its run.
 */
function parting() {
  const flow = column.querySelector(".flow");
  if (flow === null) return waiting();
  flow.classList.add("parting");
  waiting();
}

function rejoin() {
  const flow = column.querySelector(".flow");
  if (flow === null) return;
  flow.classList.remove("parting");
}

/** What a variation left, said once it has landed.
 *
 *  **A draw that samples what was already below the caret merges onto it and moves nothing.**
 *  The tokens reach existing nodes through `(parent, token_id, source)` and the act records
 *  them like any others, so nothing in the response distinguishes the case -- and at
 *  temperature zero it is the ordinary one, the path below a node being a greedy descent
 *  already. It is the one outcome the reader cannot see, so it is the one that is said.
 *
 *  Whether the text moved is a node that is on the screen and was not, which is the question
 *  asked rather than a count of what the act wrote: an act writes the same nodes whether they
 *  were there before or not.
 */
function parted(act, was) {
  const moved = drawn.flatMap(cell => cell.nodes).some(n => !was.has(n.id));
  const drew = `${act.nodes.length} token${act.nodes.length === 1 ? "" : "s"} drawn`;
  say(moved
    ? `${drew} \u00b7 enter again for another variation`
    : `${drew} onto what was already here \u00b7 the text has not moved`);
}

/** A failure is dismissable and says which kind it was, because the record does. */
function failed(why) {
  const box = pending(Object.assign(document.createElement("span"), {
    className: "grow", textContent: `${why.kind}: ${why.message}`,
  }));
  box.classList.add("fault");
  const go = document.createElement("button");
  go.textContent = "dismiss";
  go.onclick = () => box.remove();
  box.append(go);
}

/** Ask for more of the path, at a node. The scroll gesture passes the end of what is being
 *  read; the caret passes wherever the reader put it, and a draw there is what makes a fork
 *  -- the tokens either merge onto what already follows or part from it.
 *
 *  **`pin` keeps the caret where it is, which makes the act repeatable without aiming it
 *  again.** The ordinary draw carries the caret to the tip, which is the batch discipline
 *  `docs/SURFACE.md` names: asking for the next batch carries acceptance of the last. A
 *  variation at a fixed position is the other thing a draw can be -- several continuations
 *  from one node, read against each other -- and there the caret is the position being asked
 *  about rather than the frontier of what has been read. The path drawn is the one that
 *  landed and not the one the rule would pick, because the read is through the act's own tip.
 */
async function more(where = cursor.node(), { pin = false } = {}) {
  // A roll in flight is the other writer there is, and it holds a warm prompt cache a draw
  // from somewhere else would truncate -- `docs/SPINE.md` measures that at 28 ms against
  // 7.4 s. A scroll during one is dropped rather than queued, the same as during a draw.
  //
  // An open composer holds it too. The reader is writing the continuation at this position by
  // hand, and a draw landing under them would answer the question they are in the middle of.
  if (working || composing() || buying !== null || !writable) return;
  if (where === null || where === undefined) return;
  working = true;
  // Taken before the act, because what is drawn is replaced by it and the comparison is what
  // says whether the draw parted from anything.
  const was = pin ? new Set(drawn.flatMap(cell => cell.nodes).map(n => n.id)) : null;
  if (pin) parting(); else waiting();
  try {
    // Ending mid-character is not the only reason a backend may decline a path, so the
    // predicate is asked at the position the act would use. Asking writes nothing, and the
    // answer is advisory -- what it saves is a refusal nobody needed to see.
    if (!(await ask(`/evaluable?node=${where}`)).evaluable) {
      pending(Object.assign(document.createElement("span"), {
        textContent: "The model will not continue from this position.",
      }));
      return;
    }
    // Asked for at the moment of the act, so what the panel holds now is what is sent and
    // what the record keeps. Nothing here caches it.
    const params = draw();
    const act = await generated({ at: where, params });
    landing = { ids: new Set(act.nodes.map(n => n.id)), length: params.length };
    await refresh();
    // An `eos` before anything was drawn names no tip, and the path is where it was.
    await show(act.tip ?? where, pin ? where : undefined);
    if (pin) parted(act, was);
  } catch (why) {
    failed(why);
  } finally {
    // Every way out of here, including the refusal that returns without drawing. A path that
    // landed has replaced the flow this was set on, so there is nothing left to put back.
    if (pin) rejoin();
    // A draw that failed leaves the flow it was asked in, placeholders and all.
    column.querySelector(".flow .waiting")?.remove();
    landing = null;
    working = false;
    quiet = Date.now() + REST;
    // What landed moved the end and may have moved the window: an arrival at the end is a
    // fresh one, and where the page now stands is not somewhere the reader scrolled to.
    wasAtEnd = atEnd();
    wasAt = window.scrollY;
    stir();  // a draw disarms the caret and moves the end
  }
}

/** Whether a downward move counts as a request: at the end of the page, or anywhere at all
 *  once the caret has been armed -- and never while the room is parked, which is what parking
 *  is for. */
const ready = () => !parked && (cursor.armed() || atEnd());

/** Put the caret back in the window, if scrolling has carried it out.
 *
 *  The gesture that asks for a draw is the scroll and the draw lands at the caret, so a caret
 *  off the screen aims an act at a position nobody is looking at. Following the window is
 *  what keeps *the draw lands where you are looking* true rather than usually true -- and it
 *  is what makes the end of the page and the caret agree again, since a reader who pointed
 *  somewhere and then scrolled to the foot was drawing thousands of tokens above it.
 *
 *  **An armed caret does not move.** It is the one the reader chose, on a row drawn in front
 *  of them, and the next downward scroll is the draw -- so there is no reading to keep up
 *  with, and drifting off it would both aim the act elsewhere and disarm it on the way.
 *
 *  It costs no read, and `point` has why it may not take one: this is a mark that moves over
 *  text that does not.
 */
function dodge() {
  if (working || cursor.armed() || cursor.node() === null) return;
  const segs = $("column").querySelectorAll(".flow .seg");
  if (segs.length !== drawn.length) return;  // the composer, or a read in flight
  // A caret hard against an edge is one the reader has to hunt for, and the line it marks is
  // half a line of context in either direction. The band is reckoned in lines and not in
  // pixels, so it holds whatever the column is set in.
  const line = parseFloat(getComputedStyle($("column")).lineHeight) || 24;
  const air = line * AIR;
  const room = window.innerHeight;
  const to = cursor.seated(drawn, cursor.node(), i => {
    const box = segs[i].getBoundingClientRect();
    if (box.top < air) return -1;
    if (box.bottom > room - air) return 1;
    return 0;
  });
  if (to === null || to === cursor.node()) return;
  cursor.place(to);
  frontier();
  settled();
}

/* One settle for both, because they are one gesture read twice and the order between them
 * matters: the caret goes back in the window first, and what is asked for is asked at where
 * it ended up. Two timers would race, and the losing order draws at a position that was about
 * to move. */
let wanted = false;

function moved(counts) {
  wanted = wanted || counts;
  clearTimeout(timer);
  timer = setTimeout(() => {
    const ask = wanted;
    wanted = false;
    dodge();
    if (ask && !working && Date.now() >= quiet && ready()) more();
  }, SETTLE);
}

let wasAtEnd = false;
let wasAt = 0;
let carried = 0;  // until when a scroll is the page's own, and not the reader's
const CARRY = 150;
addEventListener("scroll", () => {
  const now = atEnd();
  if (performance.now() < carried) {
    wasAtEnd = now;
    wasAt = window.scrollY;
    return;
  }
  // Downward and not merely different. At the end of the page there is nowhere below to go,
  // so an arrival there is the gesture; an armed caret has no such place, so the direction is
  // all there is -- and what lands after an act can shorten the page and move the window on
  // its own, which would otherwise read as a reader asking for the next one.
  stir(true);
  // A room being moved shifts the end of the page under a reader who has not scrolled.
  const asks = !shifting
    && ((cursor.armed() && window.scrollY > wasAt) || (now && !wasAtEnd));
  wasAtEnd = now;
  wasAt = window.scrollY;
  // Every scroll settles, because the caret follows the window whichever way it went. Only
  // some of them ask for anything.
  moved(asks);
}, { passive: true });

// Already somewhere that counts, and still going down. Every way of moving the page is one
// of these.
addEventListener("wheel", event => {
  if (event.shiftKey && look.on) return;  // the map's zoom
  // The drawer scrolls itself, and a wheel there is not the page being read further.
  if (event.target instanceof Element && event.target.closest("footer")) return;
  stir(true);
  moved(event.deltaY > 0 && ready());
}, { passive: true });
addEventListener("keydown", event => {
  // A composer is an editable that is not a form control, so this is wider than the two tags.
  if (event.target.closest("textarea, input, [contenteditable]")) return;
  // Typing at the caret. **A modifier on the draw key and not a key of its own**: both write
  // at the caret, and the pair reads as *draw here* and *write here* rather than as two
  // unrelated keys. It is also what the composer sends with, so the gesture that opens one is
  // the gesture that finishes it.
  if (event.key === "Enter" && (event.ctrlKey || event.metaKey)
      && !event.altKey && !event.shiftKey) {
    if (event.repeat) return;
    event.preventDefault();
    author();
    return;
  }
  // A variation at the caret, which is the draw that does not move the reader. **It is a key
  // and not a scroll because it has no place to be arrived at.** What makes the scroll
  // deliberate is the end of the page, and what makes an armed caret deliberate is the click
  // that armed it; a draw at a position in the middle of the text has neither, so the gesture
  // itself is what has to be unmistakable. A modifier on it is some other gesture rather than
  // a quieter version of this one, and a held key is one request because `quiet` says so.
  if (event.key === "Enter") {
    if (event.repeat || event.ctrlKey || event.metaKey || event.altKey || event.shiftKey) return;
    if (event.target.closest("button, a")) return;  // Enter there is that control's own
    event.preventDefault();
    if (Date.now() < quiet) return;
    more(cursor.node(), { pin: true }).catch(() => {});
    return;
  }
  // The way back to the tip, which is what makes the scroll gesture reachable again. It writes
  // nothing and arms nothing: a reader standing at the tip has the foot of the page for that.
  //
  // An open composer takes it first, and this is where that has to be heard: a reader who
  // clicked away from the box still has one open, and the key that leaves it cannot be one only
  // the box hears. The caret has not moved while it was open, so the release that would have
  // happened here is still there on the next press.
  if (event.key === "Escape") {
    if (composing()) unauthor(); else release();
    stir();
    return;
  }
  // A waypoint at the caret, or the one there cleared.
  if (event.key === "w" && !event.ctrlKey && !event.metaKey && !event.altKey) {
    if (event.repeat || cursor.node() === null || known === null) return;
    event.preventDefault();
    waymark(cursor.node()).catch(why => say(`${why.kind || "unreachable"}: ${why.message}`, true));
    return;
  }
  // Across the map to the next branch over: left and right where it runs down the page, up and
  // down where it runs across.
  if (event.ctrlKey && !event.metaKey && !event.altKey && !event.shiftKey && look.on) {
    const by = (look.down ? { ArrowLeft: -1, ArrowRight: 1 } : { ArrowUp: -1, ArrowDown: 1 })[event.key];
    if (by !== undefined) {
      event.preventDefault();
      scanBy(by).catch(scanFails);
      return;
    }
  }
  if (!["ArrowDown", "PageDown", "End", " ", "ArrowUp", "PageUp", "Home"].includes(event.key))
    return;
  moved(["ArrowDown", "PageDown", "End", " "].includes(event.key) && ready());
});

/** An act with no terminator is a generation in flight, so a reload draws it rather than
 *  losing it. One writer means there is at most one.
 *
 *  On a server that only reads, the act is another writer's, and it is said rather than waited
 *  on or called abandoned. */
async function resume() {
  const { acts } = await ask("/acts?in_flight=1");
  if (!acts.length) return false;
  if (!writable) {
    say(`act ${acts[0].id} is a draw in flight: the writer holding this tree is drawing it, `
        + "or is gone and the next writer will record it aborted \u00b7 reload to see it land");
    return false;
  }
  working = true;
  // As long as the act asked for, which the record holds and the page's setting may not.
  waiting(acts[0].params?.length);
  while ((await ask("/acts?in_flight=1")).acts.length)
    await new Promise(again => setTimeout(again, 700));
  working = false;
  return true;
}

// ---- the map --------------------------------------------------------------------------

/* The tree under the current root, drawn as a shape in the margin. Its strands are read once
 * per root, per toggle and per act; what moves with the reader -- the path and the caret -- is
 * drawn again from what is held, and costs no read. Pointing at a strand is an arrival, as
 * taking a waypoint is: the path through that point in the column, and the caret on it. */

const SVG = "http://www.w3.org/2000/svg";
const PAD = 10;            // px inside the map on every side
const STEP = [1.5, 20];    // px between rows, at the least and the most
const MARK = 9;            // px of a row's step the caret, the pointer and the thumb grow to
const GLIDE = 1200;        // ms the drawing takes to move from one packing to the next
const STRIDE = 400;        // ms it takes over a step of zoom
const NOTCH = 40;          // px of a fine wheel that make one step of zoom
const SHAPE = ["x1", "y1", "x2", "y2", "cx", "cy", "r"];  // what a mark's geometry is
const STEPS = 4;           // paths back the trail is drawn for, each in a colour of its own

const chartEl = $("map");
const chartBar = $("chart-bar");
// The rung is `map.LADDER`'s, `byFork` puts a strand in the zone its fork is in, and `lens`
// gives the thumb more of the axis as the zoom goes in.
const look = { on: true, down: true, rung: 4, byFork: false, lens: true };
let charted = null;  // { root, hidden, tree, marks }: the last `/map`, indexed
let asking = null;   // which of those is in flight, so a late answer does not draw over a newer
let chart = null;    // what is drawn now, which a point is read against
let thumbed = null;  // the thumb in the hand: how far into it it was taken, in tokens
let dragged = false;  // a drag ended, and the click that follows it is not an arrival
let pointedAt = null; // the path's cell the pointer is over, from the column or the map
let gliding = 0;      // which move is running, so a newer drawing stops an older one
let lit = null;       // the strand the pointer is over on the map, traced to the root
let walked = [];      // the trail: the paths the reader has been on in this tree, newest first
let zoomed = 0;       // steps of zoom in about the thumb
let wheeled = 0;      // px of a fine wheel not yet a step
let refocusing = false; // a check of the cut asked for this frame, so a scroll asks once
let scanned = 0;      // px of a fine wheel not yet a step across
let scanning = false; // an arrival across still on its way
let cellsAt = null;   // the path's cells and where each starts in tokens, for the path drawn

/** A strand's colour: the path's, how many paths back it was on one, or none. */
const tone = (path, back, head) =>
  path.has(head) ? "var(--accent)"
  : back.has(head) ? `var(--trail-${back.get(head)})` : "var(--dim)";

const svg = (name, attrs, cls) => {
  const el = document.createElementNS(SVG, name);
  for (const [k, v] of Object.entries(attrs)) el.setAttribute(k, v);
  if (cls) el.setAttribute("class", cls);
  return el;
};
const pathIds = () => drawn.flatMap(cell => cell.nodes.map(n => n.id));

/** The rows open over the map where they are on, and their own ground covers it there. */
function margin() {
  ranking.want($("rows").checked);
  settled();
}

/** Read the strands if what is thumbed is not this root's, then draw. */
async function charter() {
  const root = drawn[0]?.nodes[0].id;
  if (!look.on || root === undefined) {
    chartEl.replaceChildren();
    chart = null;
    return;
  }
  if (charted?.root !== root || charted.hidden !== showHidden) {
    const want = { root, hidden: showHidden };
    asking = want;
    try {
      const got = await ask(`/map/${root}?hidden=${showHidden ? 1 : 0}` +
                            `&marks=${kept.map(w => w.node).join(",")}`);
      if (asking !== want) return;
      if (charted?.root !== root) zoomed = 0;
      charted = { ...want, tree: map.index(got.strands), marks: got.marks };
    } catch (why) {
      if (asking === want) say(`map: ${why.kind || "unreachable"}: ${why.message}`, true);
      return;
    }
  }
  sketch();
}

/** What is cut on the path drawn, zoomed as far as it is about the thumb, and the axis it is
 *  cut on. */
function cutting(tree, path) {
  const most = map.most(tree);
  const span = thumbSpan();
  const cut = map.zoned(tree, { base: look.rung, steps: zoomed, span, most, byFork: look.byFork });
  return { most, span, hairs: map.hair(tree, cut, path) };
}

/** Along and across the plan, as the page has them: down the page the two are swapped. */
const placed = (along, across) => look.down ? { x: across, y: along } : { x: along, y: across };
const lineAt = (a0, c0, a1, c1) => {
  const p = placed(a0, c0), q = placed(a1, c1);
  return { x1: p.x, y1: p.y, x2: q.x, y2: q.y };
};
const dotAt = (along, across, r) => {
  const p = placed(along, across);
  return { cx: p.x, cy: p.y, r };
};

/** The scale the map is drawn on: straight, or zoomed in with the lens on, through the fisheye
 *  about the thumb. */
const lensed = (most, long, span) => map.scale({ most, width: long, pad: PAD,
  lens: look.lens && zoomed > 0 && span ? map.fisheye({ span, most, steps: zoomed }) : null });

/** Every mark a plan draws, keyed by what it draws, as `[key, name, attrs, cls, head, style]`.
 *  A waypoint folded away marks the fold that holds it. */
function marksOf(tree, plan, x, back) {
  const out = [];
  const ys = new Map(plan.strands.map(s => [s.head, s.y]));
  const folds = new Set(plan.hairs.filter(h => h.fold).map(h => h.head));
  const marked = new Set(), spots = [];
  for (const w of charted.marks) {
    if (w.head === null) continue;
    if (ys.has(w.head)) { spots.push(w); continue; }
    const fold = map.lineage(tree, w.head).find(h => folds.has(h));
    if (fold !== undefined) marked.add(fold);
  }
  for (const l of plan.links)
    out.push([`l${l.head}`, "line", lineAt(l.x, l.y0, l.x, l.y1), "link", l.head, {}]);
  for (const h of plan.hairs)
    out.push([`h${h.head}`, "line", lineAt(h.x0, h.y0, h.x1, h.y1),
              `hair${h.fold ? " fold" : h.stub ? " stub" : ""}${h.aside ? " aside" : ""}`
              + (marked.has(h.head) ? " marked" : ""),
              h.head, h.fold ? { "--heft": map.heft(h.weight) } : {}]);
  for (const s of plan.strands) {
    const end = s.aside ?? s.x1;
    out.push([`s${s.head}`, "line", lineAt(s.x0, s.y, Math.max(end, s.x0 + 0.8), s.y),
              `strand${s.path ? " path" : back.has(s.head) ? " behind" : ""}`, s.head, {}]);
    if (s.aside !== null)
      out.push([`a${s.head}`, "line", lineAt(s.aside, s.y, Math.max(s.x1, s.aside + 0.8), s.y),
                "strand aside", s.head, {}]);
  }
  for (const k of plan.fans)
    out.push([`f${k.head}`, "circle", dotAt(k.x, k.y, 0.8 + 0.6 * Math.sqrt(k.n)), "fan", null, {}]);
  for (const w of spots)
    out.push([`w${w.node}`, "circle", dotAt(x(w.depth + 0.5), ys.get(w.head), 3), "waypoint",
              null, {}]);
  return out;
}

/** The ticks along the map's outer edge, while the fisheye is bending the axis. */
function rule() {
  const ticks = look.lens && zoomed > 0 ? map.ticks(chart.x, chart.most) : [];
  const edge = chart.wide - 2;
  chart.ruler.replaceChildren(...ticks.map(([v, major]) => {
    const a = chart.x(v), reach = major ? 5 : 2.5;
    return svg("line", lineAt(a, edge - reach, a, edge), major ? "tick" : "tick minor");
  }));
}

/** Draw the same strands again through the fisheye as it stands about the thumb now, moving
 *  each mark rather than making it anew. */
function restretch(span) {
  gliding++;
  chartEl.classList.remove("moving");
  const { tree } = charted;
  const x = lensed(chart.most, chart.long, span);
  const plan = map.plan(tree, chart.rows,
                        { x, hairs: chart.hairs, path: chart.path, step: chart.step, top: chart.top });
  for (const [key, , attrs] of marksOf(tree, plan, x, chart.back)) {
    const el = chart.els.get(key);
    if (el === undefined) continue;
    assign(el, attrs);
    el.style.opacity = "";  // a glide cut short leaves what it was fading in part way
  }
  Object.assign(chart, { x, plan, lensAt: span });
  rule();
  chartCaret();
  chartOver();
  chartThumb();
}

/** How far in a zoom goes: as far as the cut changes, and with the lens on, as far as it does. */
const zoomMost = () => Math.max(map.deepest(look.rung), look.lens ? map.LENS.steps : 0);

/** Draw what is thumbed around the path that is drawn: across the margin, or down it with the
 *  window in view as the thumb on the path. A drawing that glides takes `pace` ms. */
function sketch({ glides = true, pace = GLIDE } = {}) {
  if (!look.on || charted === null) return;
  gliding++;
  chartEl.classList.remove("moving");
  chartEl.style.setProperty("--glide", `${pace}ms`);
  const { tree } = charted;
  const path = map.along(tree, pathIds());
  const { most, span, hairs } = cutting(tree, path);
  // The trail takes the path the reader is on, and is drawn from before and after it did.
  const earlier = chart === null ? null
    : { path: chart.path, back: map.steps(tree, walked, chart.path, STEPS) };
  const now = map.remember(tree, walked, path, [...path].at(-1) ?? null);
  if (now !== walked) map.keep(storage, known.created ?? known.path, now);
  walked = now;
  const back = map.steps(tree, walked, path, STEPS);
  const box = chartEl.getBoundingClientRect();
  const [long, wide] = look.down ? [box.height, box.width] : [box.width, box.height];
  // Packed on the straight axis, so a fisheye moving with the thumb moves no strand across.
  const rows = map.layout(tree, { x: map.scale({ most, width: long, pad: PAD }), hairs, path });
  const all = [...rows.values()];
  const lo = Math.min(...all), hi = Math.max(...all);
  const step = Math.max(STEP[0], Math.min(STEP[1], (wide - 2 * PAD) / Math.max(1, hi - lo)));
  // Where it fits, from the margin's edge down the page and centred across it; where it does
  // not, the path's row in the middle.
  const fits = (hi - lo) * step <= wide - 2 * PAD;
  const top = !fits ? wide / 2 + lo * step : look.down ? PAD : (wide - (hi - lo) * step) / 2;
  const x = lensed(most, long, span);
  const plan = map.plan(tree, rows, { x, hairs, path, step, top });

  const out = [];
  const ruler = svg("g", {}, "scale");
  const thumb = svg("rect", {}, "thumb");
  out.push(ruler, thumb);
  // Every mark keyed by what it draws, so the next drawing can say where each one was.
  const byHead = new Map(), els = new Map();
  for (const [key, name, attrs, cls, head, style] of marksOf(tree, plan, x, back)) {
    const el = svg(name, { ...attrs, "data-key": key }, cls);
    for (const [k, v] of Object.entries(style)) el.style.setProperty(k, v);
    if (head !== null) {
      el.dataset.head = head;
      if (!byHead.has(head)) byHead.set(head, []);
      byHead.get(head).push(el);
    }
    els.set(key, el);
    out.push(el);
  }
  const caret = svg("line", {}, "caret");
  const pointed = svg("line", {}, "over");
  out.push(pointed, caret);
  // The same tree drawn the same way and the same size is a packing that moved, which glides;
  // anything else is a new drawing, which does not.
  const same = glides && chart !== null && chart.tree === tree && chart.down === look.down
    && chart.long === long && chart.wide === wide;
  const was = same ? shape() : null;
  // Each strand's colour, and where it changed, the change eased over the same glide.
  for (const s of plan.strands) {
    const el = els.get(`s${s.head}`);
    const to = tone(path, back, s.head);
    el.style.setProperty("--to", to);
    const from = same && earlier !== null ? tone(earlier.path, earlier.back, s.head) : to;
    if (from !== to) {
      el.style.setProperty("--from", from);
      el.classList.add("stain");
    }
  }
  chartEl.replaceChildren(...out);
  chart = { tree, x, plan, path, hairs, rows, back, top, most, lensAt: span, caret, pointed,
            thumb, ruler, els, at: placed, line: lineAt, step, byHead, down: look.down, long,
            wide, y0: plan.strands.find(s => s.head === tree.top.head).y };
  lit = null;
  if (was !== null) glide(was, pace);
  rule();
  chartCaret();
  chartOver();
  chartThumb();
  chartSays(map.effect(tree, hairs),
            zoomed && span ? map.zoneCounts(tree, hairs, { span, most }) : null);
}

const assign = (el, attrs) => {
  for (const [k, v] of Object.entries(attrs)) el.setAttribute(k, v);
};

/** Each keyed mark's geometry, as numbers. */
function shape() {
  const out = new Map();
  for (const el of chartEl.querySelectorAll("[data-key]")) {
    const at = {};
    for (const k of SHAPE) if (el.hasAttribute(k)) at[k] = Number(el.getAttribute(k));
    out.set(el.dataset.key, at);
  }
  return out;
}

/** Move what is drawn from where it was, so a branch taken is seen straightening onto the
 *  path's row. What is new fades in, and what moves with the reader -- the caret, the pointer
 *  and the thumb -- waits until it lands. */
function glide(was, pace) {
  const { moved, fresh } = map.shift(was, shape());
  if (!moved.length && !fresh.length) return;
  const els = new Map([...chartEl.querySelectorAll("[data-key]")].map(el => [el.dataset.key, el]));
  const id = gliding;
  const t0 = performance.now();
  chartEl.classList.add("moving");
  const frame = now => {
    if (id !== gliding) return;
    const t = Math.min(1, (now - t0) / pace), e = map.ease(t);
    for (const [key, pairs] of moved)
      for (const [k, a, b] of pairs) els.get(key).setAttribute(k, a + (b - a) * e);
    for (const key of fresh) els.get(key).style.opacity = t < 1 ? e : "";
    if (t < 1) requestAnimationFrame(frame);
    else chartEl.classList.remove("moving");
  };
  frame(t0);
}

/** Where the caret is on the path's row. */
function chartCaret() {
  if (chart === null) return;
  const at = pathIds().indexOf(cursor.node());
  chart.caret.style.display = at < 0 ? "none" : "";
  if (at < 0) return;
  const a = chart.x(at + 0.5), h = Math.max(4, Math.min(MARK, chart.step));
  assign(chart.caret, chart.line(a, chart.y0 - h, a, chart.y0 + h));
}

/** Mark the path's cell `i` as what the pointer is over, in the column and on the map, or
 *  nothing with null. The two hold the same positions and a pointer is over one of them. */
function hover(i) {
  if (i === pointedAt) return;
  const segs = $("column").querySelectorAll(".flow .seg");
  segs[pointedAt]?.classList.remove("over");
  pointedAt = i;
  segs[pointedAt]?.classList.add("over");
  chartOver();
}

/** Where the pointer is on the path's row, from whichever side it is on. */
function chartOver() {
  if (chart === null) return;
  const got = pointedAt === null ? null : cells();
  chart.pointed.style.display = got ? "" : "none";
  if (!got) return;
  const mid = (got.at[pointedAt] + got.at[pointedAt + 1]) / 2;
  const a = chart.x(mid), h = Math.max(4, Math.min(MARK, chart.step));
  assign(chart.pointed, chart.line(a, chart.y0 - h, a, chart.y0 + h));
}

/** The path's cells as they stand on the page, and where each starts in tokens. */
function cells() {
  const segs = [...$("column").querySelectorAll(".flow .seg")];
  if (segs.length !== drawn.length) return null;
  if (cellsAt?.drawn !== drawn)
    cellsAt = { drawn, at: map.offsets(drawn.map(c => c.nodes.length)) };
  return { segs, at: cellsAt.at };
}

/** What is above the footer, which is the window the column is read in. */
const view = () => [0, document.querySelector("footer").getBoundingClientRect().top];

/** The tokens in view on the path, as `[from, to)`, or null. */
function thumbSpan() {
  const got = cells();
  const [lo, hi] = view();
  return got && map.seen(got.at, i => got.segs[i].getBoundingClientRect(), lo, hi);
}

/** The tokens in view, drawn as the thumb over the path's row. */
function chartThumb() {
  if (chart === null) return;
  const span = thumbSpan();
  chart.thumb.style.display = span ? "" : "none";
  chart.span = span;
  if (!span) return;
  const half = chart.half = Math.max(5, Math.min(MARK, chart.step) * 1.5);
  const p = chart.at(chart.x(span[0]), chart.y0 - half);
  const q = chart.at(chart.x(span[1]), chart.y0 + half);
  assign(chart.thumb, { x: p.x, y: p.y, rx: 2,
                        width: Math.max(1, q.x - p.x), height: Math.max(1, q.y - p.y) });
}

/** The point an event is at, along and across the plan, or null off the map. */
function chartPoint(event) {
  if (chart === null) return null;
  const box = chartEl.getBoundingClientRect();
  const px = event.clientX - box.left, py = event.clientY - box.top;
  if (px < 0 || py < 0 || px > box.width || py > box.height) return null;
  return look.down ? { along: py, across: px } : { along: px, across: py };
}

/** The point an event is at, as a strand and a node on it, or null. */
function chartHit(event) {
  const p = chartPoint(event);
  if (p === null) return null;
  return map.hit(chart.tree, chart.plan, chart.x, p.along, p.across,
                 Math.max(4, chart.step / 2 + 1));
}

/** Whether an event is on the thumb, and how far into it in tokens. */
function onThumb(event) {
  const p = chartPoint(event);
  if (p === null || !chart.span || Math.abs(p.across - chart.y0) > chart.half + 2) return null;
  const t = chart.x.invert(p.along);
  return t >= chart.span[0] - 0.5 && t <= chart.span[1] + 0.5 ? t - chart.span[0] : null;
}

/** Scroll the column so the token `depth` tokens from the root stands at the top of the view. */
function scrollAt(depth) {
  const got = cells();
  if (got === null) return;
  const el = got.segs[map.holding(got.at, depth)];
  carried = performance.now() + CARRY;
  window.scrollTo(0, window.scrollY + el.getBoundingClientRect().top - view()[0]);
}

/** Arrive where a click on the column's own ground points on the map, and say whether it did. */
function charting(event) {
  if (dragged) { dragged = false; return true; }
  // A click while the drawing moves would land on where something is going, not where it is.
  if (chartEl.classList.contains("moving")) return true;
  const hit = chartHit(event);
  if (hit === null) return false;
  visit(hit).catch(why => say(`${why.kind || "unreachable"}: ${why.message}`, true));
  return true;
}

/** The path through a strand's tail, and the caret on the segment holding the node pointed at:
 *  centred in the window, or with its top at `hold` px. */
async function visit({ tail, depth }, hold = null) {
  const line = await ask(`/path/${tail}?rule=none&hidden=${showHidden ? 1 : 0}`);
  let seen = 0;
  for (const cell of line.segments) {
    seen += cell.nodes.length;
    if (seen > depth) return reach(cell.nodes.at(-1).id, null, tail, hold);
  }
  return reach(tail, null, tail, hold);
}

$("column").addEventListener("pointerdown", event => {
  if (event.target !== $("column") || event.button !== 0) return;
  const into = onThumb(event);
  if (into === null) return;
  thumbed = into;
  dragged = false;
  $("column").setPointerCapture(event.pointerId);
  event.preventDefault();
});
$("column").addEventListener("pointerup", event => {
  if (thumbed === null) return;
  thumbed = null;
  $("column").releasePointerCapture(event.pointerId);
  // The caret follows the window, as it does after any scroll, and nothing is asked for.
  moved(false);
});

$("column").addEventListener("pointerleave", () => hover(null));
$("column").addEventListener("pointermove", event => {
  if (thumbed !== null) {
    const p = chartPoint(event);
    if (p !== null) { dragged = true; scrollAt(chart.x.invert(p.along) - thumbed); }
    return;
  }
  // Over the text, the segment says what it is over itself.
  if (event.target !== $("column")) return;
  const hit = chartHit(event);
  const head = hit?.head ?? null;
  const got = hit !== null && chart.path.has(head) ? cells() : null;
  hover(got === null ? null : map.holding(got.at, hit.depth));
  $("column").classList.toggle("charting", head !== null);
  $("column").classList.toggle("thumbing", head === null && event.target === $("column")
                                           && onThumb(event) !== null);
  if (head === lit) return;
  for (const el of chartEl.querySelectorAll(".lit")) el.classList.remove("lit");
  lit = head;
  // Traced back to the root, so where it leaves the path and the shape it would take are seen.
  if (head !== null)
    for (const h of map.lineage(chart.tree, head))
      for (const el of chart.byHead.get(h) ?? []) el.classList.add("lit");
});

/** A rung of the cut as the bar names it. */
const rungName = c =>
  c.fold === Infinity ? "fold all" : c.fold ? `fold ≤${c.fold}`
  : !c.stubs ? "uncut" : c.under ? `≤${c.under}` : "stubs";

/** The bar under the map: which way it is drawn, the cut, and what the cut does, and zoomed
 *  in, how many strands are drawn in each zone from the thumb out. */
function chartSays(effect, zones) {
  const button = (text, title, pressed, onclick) => {
    const b = Object.assign(document.createElement("button"),
                            { textContent: text, title, onclick });
    b.setAttribute("aria-pressed", String(pressed));
    return b;
  };
  const rung = by => () => {
    look.rung = Math.min(map.LADDER.length - 1, Math.max(0, look.rung + by));
    zoomed = Math.min(zoomed, zoomMost());
    sketch();
  };
  const finer = button("−", "cut less: draw more of the tree", false, rung(-1));
  const coarser = button("+", "cut more: draw less of the tree", false, rung(1));
  finer.disabled = look.rung === 0;
  coarser.disabled = look.rung === map.LADDER.length - 1;
  chartBar.replaceChildren(
    button("down", "draw the map down the page, as a scrollbar; off, across it", look.down,
           () => { look.down = !look.down; sketch(); }),
    finer,
    Object.assign(document.createElement("span"), {
      className: "rung",
      textContent: rungName(map.LADDER[look.rung]) + (zoomed ? ` · ${zoomed} in` : ""),
      title: "what is drawn as a tick off its fork rather than given a row;"
        + " shift and the wheel zoom in about the thumb",
    }),
    coarser,
    button("fork", "zoomed, put a strand in the zone its fork is in;"
           + " off, in the zone of its nearest point", look.byFork,
           () => { look.byFork = !look.byFork; sketch({ pace: STRIDE }); }),
    button("lens", "zoomed, give the thumb more of the axis; off, zoom cuts alone", look.lens,
           () => {
             look.lens = !look.lens;
             zoomed = Math.min(zoomed, zoomMost());
             sketch({ pace: STRIDE });
           }),
    Object.assign(document.createElement("span"), {
      className: "says",
      textContent: (zones ? `${zones.join(" · ")} near to far · ` : "")
        + `${effect.kept} of ${effect.of} strands · ${Math.round(effect.share * 100)}% cut`,
      title: zones ? "strands drawn in each zone, from the thumb out" : "",
    }),
  );
}

$("charted").onchange = () => {
  look.on = $("charted").checked;
  document.body.classList.toggle("unmapped", !look.on);
  margin();
  charter();
};
addEventListener("resize", () => sketch());
addEventListener("scroll", () => { chartThumb(); refocus(); }, { passive: true });

/** Zoomed in, draw again once this frame if the thumb moving changed what is cut, and move
 *  what is drawn if it bent the axis. */
function refocus() {
  if (zoomed === 0 || chart === null || refocusing) return;
  refocusing = true;
  requestAnimationFrame(() => {
    refocusing = false;
    if (chart === null || charted === null) return;
    const { tree } = charted;
    const { most, span, hairs } = cutting(tree, chart.path);
    // A scroll the reader makes is followed as it goes; one the page makes, or one that lands
    // while the drawing is still moving, glides there from wherever the marks now stand.
    const jumped = performance.now() < carried || chartEl.classList.contains("moving");
    const bent = look.lens && span
      && (span[0] !== chart.lensAt?.[0] || span[1] !== chart.lensAt?.[1]);
    if (!map.same(hairs, chart.hairs) || (jumped && bent)) {
      sketch(jumped ? {} : { glides: false });
      return;
    }
    if (!span) return;
    if (bent) restretch(span);
    chartSays(map.effect(tree, hairs), map.zoneCounts(tree, hairs, { span, most }));
  });
}

/** Zoom by `n` steps, in where it is positive, gliding to the cut that makes. */
function zoomBy(n) {
  const to = Math.min(zoomMost(), Math.max(0, zoomed + n));
  if (to === zoomed) return;
  zoomed = to;
  sketch({ pace: STRIDE });
}

/** Arrive on the branch next over from the path, `by` 1 down the depth-first order or -1 up it,
 *  at the caret's depth or that branch's end where it is short of it, with the token at that
 *  depth held where it stands in the window. */
async function scanBy(by) {
  if (!look.on || chart === null || scanning) return;
  const got = cells();
  if (got === null) return;
  const { tree, span, most } = chart;
  const caret = pathIds().indexOf(cursor.node());
  const depth = caret >= 0 ? caret : span ? Math.floor((span[0] + span[1]) / 2) : got.at.at(-1) - 1;
  const from = span ? span[0] - map.ZONES.focal * most : depth;
  const until = span ? span[1] : depth;
  const to = map.scan(tree, chart.hairs, [...chart.path].at(-1), by, { from, until });
  if (to === null) { say(by > 0 ? "no branch further over" : "no branch further back"); return; }
  const hold = got.segs[map.holding(got.at, depth)].getBoundingClientRect().top;
  scanning = true;
  try {
    await visit({ tail: to.tail, depth: Math.min(depth, to.depth + to.length - 1) }, hold);
  } finally {
    scanning = false;
  }
}

const scanFails = why => say(`${why.kind || "unreachable"}: ${why.message}`, true);

// Shift and the wheel zoom the map, wherever the pointer is, and do nothing else: not the
// draw a wheel at the end of the column asks for, nor the sideways scroll some browsers make
// of it, nor the browser's own zoom with Ctrl, which scans across instead. A notch is a step,
// and a fine wheel's movement adds up to one.
addEventListener("wheel", event => {
  if (!event.shiftKey || !look.on || chart === null) return;
  event.preventDefault();
  const d = event.deltaY || event.deltaX;
  if (event.ctrlKey) {
    if (event.deltaMode !== 0 || Math.abs(d) >= NOTCH) scanned = Math.sign(d) * NOTCH;
    else scanned += d;
    const n = Math.trunc(scanned / NOTCH);
    if (n === 0) return;
    scanned -= n * NOTCH;
    scanBy(Math.sign(n)).catch(scanFails);
    return;
  }
  if (event.deltaMode !== 0 || Math.abs(d) >= NOTCH) wheeled = Math.sign(d) * NOTCH;
  else wheeled += d;
  const n = Math.trunc(wheeled / NOTCH);
  if (n === 0) return;
  wheeled -= n * NOTCH;
  zoomBy(-n);
}, { passive: false });

// ---- the page -------------------------------------------------------------------------

function say(text, bad) {
  $("status").textContent = text;
  $("status").className = bad ? "fault" : "";
}

$("drawer").append(panel());

/* The length of a draw is set at the page's edge, as the room below the last line, and
 * `room.js` has what each position means. Room is a share of the height above the footer, so
 * a drawer held up shortens the edge and keeps every position where it was learned. Parked, a scroll draws nothing and the length is
 * left where it was, so the key that draws at the caret still has one. */

let parked = false;
let shifting = false;  // the point in the hand

const edge = Object.assign(document.createElement("div"), { id: "edge" });
const says = Object.assign(document.createElement("span"), { className: "says" });
const handle = Object.assign(document.createElement("div"), { className: "point" });
const counter = Object.assign(document.createElement("div"), { className: "counter" });
edge.append(counter, handle,
            Object.assign(document.createElement("div"), { className: "across" }), says);
// In `main`, so the measure it is placed by is read against what the column is.
document.querySelector("main").append(edge);

function stand(asked) {
  const at = room.place(asked);
  parked = at.length === null;
  if (!parked) set("length", at.length);
  $("column").style.setProperty("--space", `calc((100vh - var(--foot)) * ${at.room / 100})`);
  edge.style.setProperty("--room", `${at.room}%`);
  edge.classList.toggle("parked", parked);
  says.textContent = parked ? "parked" : `${at.length} tokens`;
  stir();
}

/* The cue: how near the next scroll is to drawing, drawn as a counter-point at the last
 * line's height that pulses against the point and meets it at the mark. `room.cue` decides what
 * is shown; this only paints it, and runs a frame loop only while something is moving. */

let stirred = -Infinity;  // when the page last moved
let hovering = false;
let phase = 0;
let frame = null;
let then = 0;
const still = matchMedia("(prefers-reduced-motion: reduce)");

/** How far below the mark the last line stands, in the room's units: what is left to scroll. */
const gap = () => Math.max(0,
  (document.documentElement.scrollHeight - window.scrollY - window.innerHeight)
  / Math.max(1, window.innerHeight - foot.offsetHeight) * 100);

function beat(now) {
  const c = room.cue({ gap: gap(), since: now - stirred, hover: hovering,
                       armed: cursor.armed(), parked });
  edge.classList.toggle("cued", c !== null && (c.near || hovering));
  edge.classList.toggle("close", c !== null && c.close);
  if (c === null) {
    counter.style.opacity = "0";
    handle.style.opacity = "";
    return false;
  }
  phase = (phase + c.rate * (now - then) / 1000) % 1;
  // Solid while a draw is in flight: the gesture has been made and there is nothing to warn of.
  const depth = still.matches || working ? 0 : c.pulse;
  // The two in opposite phase, so one is brightest where the other is faintest.
  const wave = 0.5 - 0.5 * Math.cos(2 * Math.PI * phase);
  edge.style.setProperty("--gap", `${c.gap}%`);
  handle.style.opacity = String(1 - 0.65 * depth * wave);
  counter.style.opacity = String(1 - 0.65 * depth * (1 - wave));
  // A frame is wanted while there is a pulse to run or a fade still under way.
  return depth > 0 || hovering || now - stirred < room.FADE;
}

function tick(now) {
  const going = beat(now);
  then = now;
  frame = going ? requestAnimationFrame(tick) : null;
}

/** Something moved: start the loop if it is not running. */
function stir(moving = false) {
  if (moving) stirred = performance.now();
  if (frame === null) {
    then = performance.now();
    frame = requestAnimationFrame(tick);
  }
}

edge.addEventListener("pointerenter", () => { hovering = true; stir(); });
edge.addEventListener("pointerleave", () => { hovering = false; stir(); });

// A share of the edge's own height, above its foot, which is the footer's top.
const asked = event => {
  const box = edge.getBoundingClientRect();
  return (box.bottom - event.clientY) / box.height * 100;
};

edge.addEventListener("pointerdown", event => {
  if (event.button !== 0) return;
  event.preventDefault();
  edge.setPointerCapture(event.pointerId);
  shifting = true;
  edge.classList.add("moving");
  stand(asked(event));
});
edge.addEventListener("pointermove", event => { if (shifting) stand(asked(event)); });
function letGo() {
  if (!shifting) return;
  shifting = false;
  edge.classList.remove("moving");
  // Where the page's end went is not somewhere the reader scrolled to, so it is taken as the
  // place to start from once the scroll the move caused has been heard.
  requestAnimationFrame(() => { wasAtEnd = atEnd(); wasAt = window.scrollY; });
}
edge.addEventListener("pointerup", letGo);
edge.addEventListener("pointercancel", letGo);

stand(room.roomFor(draw().length));

/* The footer, and the drawer in it. Hovering it lifts the drawer over the text after a beat,
 * and leaving lets it fall after another, so passing over it does neither; the heat rides its
 * top edge, and a pointer on it keeps the drawer up without lifting it. Dragged up by the heat,
 * the drawer is held at whatever height it was let go and takes that room from the text, which
 * is `--foot`; how high the footer reaches either way is `--lid`. `room.js` has where it rests.
 */
const foot = document.querySelector("footer");
const drawer = $("drawer");
const LIFT = 120, FALL = 300;  // ms
const NEAR = 32;  // px either side of the drawer's panel a pointer on the footer lifts it from
let over = 0;   // how many of the footer and the heat the pointer is on
let lifting = null;
let rising = null;  // a lift waiting on the pointer staying near the drawer
let held = 0;   // px the drawer is held open at; 0 is shut

/** How tall the drawer is with everything in it showing, held to most of the screen. */
const full = () => Math.min(drawer.scrollHeight, window.innerHeight * 0.6);

function measure() {
  const root = document.documentElement.style;
  root.setProperty("--foot", `${foot.offsetHeight}px`);
  const floating = foot.classList.contains("peek") && held === 0;
  root.setProperty("--lid", `${foot.offsetHeight + (floating ? drawer.offsetHeight : 0)}px`);
}
new ResizeObserver(measure).observe(foot);
new ResizeObserver(measure).observe(drawer);

function hold(px) {
  held = Math.round(px);
  foot.classList.toggle("held", held > 0);
  if (held > 0) foot.classList.remove("peek");
  foot.style.setProperty("--held", `${held}px`);
  measure();
}

function lift(up) {
  clearTimeout(lifting);
  // A line in the hand keeps it up, wherever the pointer has wandered while holding it.
  if (!up && drawer.querySelector(".moving")) {
    lifting = setTimeout(() => lift(false), FALL);
    return;
  }
  foot.classList.toggle("peek", up && held === 0);
  measure();
}

/** The pointer arrived on something that keeps the drawer up. */
function arrive() {
  over++;
  clearTimeout(lifting);
}
function depart() {
  over = Math.max(0, over - 1);
  clearTimeout(lifting);
  if (over === 0 && foot.classList.contains("peek")) lifting = setTimeout(() => lift(false), FALL);
}
/** Lift the drawer after a beat while the pointer on the footer is across from its panel, and
 *  not while it is anywhere else along the footer. */
function aim(event) {
  const panel = drawer.querySelector(".panel")?.getBoundingClientRect();
  const near = panel && event.clientX >= panel.left - NEAR && event.clientX <= panel.right + NEAR;
  if (!near || held > 0 || foot.classList.contains("peek")) {
    clearTimeout(rising);
    rising = null;
    return;
  }
  if (rising === null) rising = setTimeout(() => { rising = null; lift(true); }, LIFT);
}
foot.addEventListener("pointerenter", event => { arrive(); aim(event); });
foot.addEventListener("pointermove", aim);
foot.addEventListener("pointerleave", () => {
  clearTimeout(rising);
  rising = null;
  depart();
});

/* The heat of a draw, set along a line across the column at the footer's top. Its range and
 * steps are the draw panel's, read through `along` and `share`. */
const heat = Object.assign(document.createElement("div"), { id: "heat" });
const track = Object.assign(document.createElement("div"), { className: "track" });
const warmth = Object.assign(document.createElement("div"), { className: "point" });
const heatSays = Object.assign(document.createElement("span"), { className: "says" });
const gripper = Object.assign(document.createElement("div"), {
  className: "grip", title: "drag up for the rest of the draw, or click" });
track.append(warmth, heatSays);
heat.append(track, gripper);
document.querySelector("main").append(heat);

/** Where along the heat each of the stylesheet's colours stands. */
const GLOW = [[0, "--heat-0"], [1, "--heat-1"], [2, "--heat-2"], [along("temperature", 1), "--heat-3"]];

/** The colour a heat is drawn in: mixed between the two stops either side of it. */
function glow(t) {
  const i = Math.max(0, GLOW.findLastIndex(([at]) => at <= t));
  const [a, from] = GLOW[Math.min(i, GLOW.length - 2)];
  const [b, to] = GLOW[Math.min(i + 1, GLOW.length - 1)];
  const p = Math.min(1, Math.max(0, (t - a) / (b - a)));
  return `color-mix(in oklab, var(${from}), var(${to}) ${(p * 100).toFixed(1)}%)`;
}
heat.style.setProperty("--scale", `linear-gradient(to right, ${GLOW.map(([t, c]) =>
  `var(${c}) ${(t / GLOW.at(-1)[0] * 100).toFixed(1)}%`).join(", ")})`);

function heated() {
  heat.style.setProperty("--x", String(share("temperature")));
  const { temperature } = draw();
  heat.style.setProperty("--glow", glow(temperature));
  heatSays.textContent = temperature === 0 ? "greedy" : `heat ${temperature.toFixed(2)}`;
}

/* A drag on the heat sets the heat, until it has gone far enough up or down to be the
 * drawer's -- and then the heat goes back to where the drag found it, since a hand reaching
 * for the drawer was not setting it. A drag from the grip is only ever the drawer's, and a
 * grip let go without moving it opens the drawer, or shuts one that is open. */
let grip = null;  // { y, from, heat, drawer, bare }
const toward = event => {
  const box = track.getBoundingClientRect();
  place("temperature", (event.clientX - box.left) / box.width);
  heated();
};
heat.addEventListener("pointerdown", event => {
  if (event.button !== 0) return;
  event.preventDefault();
  heat.setPointerCapture(event.pointerId);
  // A drawer lifted by hovering is the height it shows, so a drag starts from there.
  const from = held > 0 ? held : foot.classList.contains("peek") ? drawer.offsetHeight : 0;
  const bare = event.target === gripper;
  grip = { y: event.clientY, from, heat: draw().temperature, drawer: false, bare };
  heat.classList.add(bare ? "lifting" : "moving");
  if (!bare) toward(event);
});
heat.addEventListener("pointermove", event => {
  if (grip === null) return;
  const to = room.pulled(grip.from, grip.y - event.clientY, full());
  if (to === null && !grip.drawer) return grip.bare ? undefined : toward(event);
  if (!grip.drawer) {
    grip.drawer = true;
    set("temperature", grip.heat);
    heated();
  }
  hold(to ?? grip.from);
});
heat.addEventListener("pointerenter", () => arrive());
heat.addEventListener("pointerleave", depart);
for (const end of ["pointerup", "pointercancel"]) {
  heat.addEventListener(end, () => {
    if (grip?.drawer) hold(room.rests(held, full()));
    else if (grip?.bare) hold(held > 0 ? 0 : full());
    grip = null;
    heat.classList.remove("moving", "lifting");
  });
}
heated();

/* The overlay, the continuation rule and what is set aside are all ways of looking, and they
 * share a panel because they are one question asked three times: what of the record is in
 * front of me. Moving any of them re-reads rather than repainting what is already drawn --
 * turning a measure on asks the server for what the last read did not carry, and changing the
 * rule asks for a different path entirely. One path costs milliseconds either way. */
$("read").append(overlayPanel(async () => {
  try {
    const here = cursor.node();
    await (here === null ? overlays([], {}) : show(here, here));
  } catch (why) {
    say(`${why.kind || "unreachable"}: ${why.message}`, true);
  }
}));

/* One state for the whole page, so the roots and the column always say the same thing about
 * what has been set aside. Flipping it re-reads rather than filtering what is already drawn:
 * the column's hidden tail is not in the response until it is asked for. */
$("hidden").onchange = async () => {
  showHidden = $("hidden").checked;
  try {
    await refresh();
    if (cursor.node() !== null) await show(cursor.node());
  } catch (why) {
    say(`${why.kind || "unreachable"}: ${why.message}`, true);
  }
};

/* Whether what else was live is shown. A way of looking, like what is set aside: it records
 * nothing, and it asks for nothing until it is on -- a position can run to dozens of rows,
 * and `docs/SURFACE.md` has density staying behind intent. */
/* Whether who took each token is marked. Default on, and a way of looking like the two
 * above: it records nothing and changes no text. Flipping it re-reads, because the sampler's
 * half of the mark needs the ranking and a read made without it did not carry one. */
$("taker").onchange = async () => {
  mark.want($("taker").checked);
  const here = cursor.node();
  try {
    if (here !== null) await show(here, here);
  } catch (why) {
    say(`${why.kind || "unreachable"}: ${why.message}`, true);
  }
};

/* The same release, spelled where the reader's hand already is. **Two boxes and not a rule about
 * what to ignore**: the column's own and the text's, which are where there is nothing. Everything
 * else in here -- a segment, a row, a boundary's control, the composer -- is a click that already
 * means something, and naming those instead would be a list that goes stale as they are added. */
$("column").onclick = event => {
  const on = event.target;
  if (on === $("column") && charting(event)) return;
  if (on === $("column") || on.classList?.contains("flow")) release();
};

$("rows").onchange = () => margin();

$("fold").onclick = () => {
  const folded = document.body.classList.toggle("folded");
  $("fold").setAttribute("aria-pressed", String(folded));
};

try {
  // A reload restores a checkbox in some browsers, and nothing here is remembered between
  // loads -- so what the box says is what the page believes, rather than the other way.
  showHidden = $("hidden").checked;
  look.on = $("charted").checked;
  document.body.classList.toggle("unmapped", !look.on);
  ranking.want($("rows").checked);
  const tree = await refresh();
  // With nothing yet chosen the first root is what is read; with no roots at all the page
  // is never a bare one, because the only thing to do here is the only thing offered.
  const rows = live(tree);
  if (!rows.length) stage(null);
  else {
    await show(rows[0].id);
    // Something another page started, or this one was reloaded out from under.
    if (await resume()) {
      await refresh();
      await show(cursor.node());
    }
  }
  wasAtEnd = atEnd();
} catch (why) {
  say(`${why.kind || "unreachable"}: ${why.message}`, true);
}
