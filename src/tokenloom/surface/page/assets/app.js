/* The surface: a list of roots, a reading column, and the one composer both of them use.
 *
 * The reader's position is a single node and everything else is derived from it -- which
 * root is current, what path is drawn, where a write will land. Holding a root as well
 * would be two pieces of state that can disagree, and `/path/{node}` already answers from
 * a node what the surface needs.
 *
 * That node is the caret, which `cursor.js` holds. It sits after a token and is what every
 * act at a position takes, so pointing at a segment and asking for a draw are one node apart
 * and not two states. A path is drawn *through* it in both directions, so moving it along
 * what is already drawn returns the same text -- which is why it costs a read and needs no
 * second way of redrawing.
 *
 * Nothing here is remembered between loads. Reader state lives in the session, and what is
 * live, what parts and what a ranking holds are read from the store every time.
 */

import * as cursor from "./cursor.js";
import { draw, keep, panel } from "./draw.js";
import * as mark from "./mark.js";
import {
  panel as overlayPanel, read as overlays, rule as taken, wants, weighed,
} from "./overlay.js";
import * as ranking from "./ranking.js";
import * as stub from "./stub.js";

const $ = id => document.getElementById(id);

const { aside } = cursor;

/* Whether what has been set aside is drawn. A way of looking: it records nothing, the
 * continuation rule follows liveness either way, and what it reveals it never selects --
 * hidden nodes only ever carry the path on from where the live one ran out. */
let showHidden = false;

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
  li.append(go);
  if (root.deleted) li.classList.add("hidden");
  li.dataset.node = root.id;
  li.setAttribute("aria-current", String(root.id === current));
  li.onclick = () => show(root.id);
  return li;
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
  const rows = live(tree).map(root => rootRow(root, current));
  // An empty list and a list emptied by the toggle are different states, and a reader who
  // has set everything aside would otherwise be told the tree is new.
  if (!rows.length) rows.push(Object.assign(document.createElement("li"), {
    className: "none",
    textContent: tree.roots.length ? "Everything here is set aside." : "Nothing here yet.",
  }));
  $("roots").replaceChildren(...rows, newRow());
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
  const tree = await ask("/tree");
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
  mark.append(shut(), "set aside", go);
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
      if (!event.altKey) return point(i);
      if (hidden) restore(cell);
      else flip(false, cell.nodes[0].id, cell.nodes[0].parent);
    };
    el.onmouseenter = () => peek(i, el);
    // The caret is drawn *on* the segment it follows and never between segments. An element
    // in the flow moves the text around it, and text that shifts as the reader points at it
    // is friction in the one thing this page is for. A rule on an inside edge costs no
    // layout at all, which is the same reason the hover mark is one.
    out.push(el);
  }
  return out;
}

/** Say where the caret stands, over what is already drawn.
 *
 *  Its own pass and not something a span is built with, because the caret moves without the
 *  text doing: a path through any node of the path already drawn is that same path, so
 *  putting the caret somewhere else along it is a mark to move and never a read.
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
}

/** Point at a segment, which moves the caret before it. It re-reads rather than redrawing
 *  what is in front of the reader: the path through the node the caret lands on is the path
 *  already drawn, so what comes back is the same text, and one path costs milliseconds. */
function point(i) {
  const to = cursor.chosen(drawn, i);
  if (to === null) return;
  show(to, to).catch(why => say(`${why.kind || "unreachable"}: ${why.message}`, true));
}

/* What is drawn, kept so that pointing at a segment knows which one was chosen. It is the
 * last response and not a second opinion about the tree: nothing is decided from it that the
 * next read would decide differently. */
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

/** Draw the rows at a node beside `anchor`, which is the span they are about. */
async function opened(node, anchor, pace = SCAN) {
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
  const after = drawn.flatMap(cell => cell.nodes).find(mark => mark.parent === node);
  // The measure is read at the moment of drawing rather than being sent with the read: the
  // response carries every downward measure, so changing which one the rows are sized by
  // costs a redraw and never a request.
  // Already answering for this node. Replacing it with a copy of itself would take the row
  // out from under the reader's hand and strand whatever that row had asked for.
  if (drawnAt === node && $("column").querySelector(".rows:not(.leaving)")) return;
  const box = ranking.list(payload, after ? after.id : null, took, weighed(), rolls);
  // Before it goes up, so a list arrives carrying what the reader already read from it
  // rather than filling in once it has landed.
  prefill(box);
  // Placed against the column rather than the window, so it scrolls with the text it is
  // about and nothing here listens for a scroll.
  const frame = $("column").getBoundingClientRect();
  box.style.top = `${anchor.getBoundingClientRect().top - frame.top}px`;
  drawnAt = node;
  swap(box, pace);
}

function clear() {
  drawnAt = null;
  for (const box of $("column").querySelectorAll(".rows")) box.remove();
}

/** Taking a row. Two of the three kinds cost nothing: the one the path took is where the
 *  reader already is, and one realised elsewhere is a selection -- which is the way back to
 *  an arm a draw parted from. The third is an act. */
function took(row, payload) {
  if (row.child === null) return realise(row, payload);
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
  if (working) return;
  working = true;
  try {
    const act = await ask("/realise", {
      at: payload.node, source: payload.sources[String(row.source)], token: row.token,
    });
    await refresh();
    await show(act.tip, act.tip);
    cursor.arm();
    frontier();  // placed by `show` and armed after it, so the mark is remade and not patched
    say("realised \u00b7 scroll down to draw from here");
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
 */

let armed = null;  // the node whose row the pointer is on, or null

/* Milliseconds a pointer rests on a priced row before anything is bought. **It is a
 * different threshold from `SEEN` because it guards a different thing**: that one keeps a
 * pointer crossing the page from asking a question, and this one keeps it from spending.
 * A reader sweeping a list passes over priced rows on the way to the one they want, and
 * the pulse is already there to be read before the dwell elapses -- so what is bought is
 * what was looked at. The number is a first one and is settled by use. */
const DWELL = 420;

let buying = null;    // the node being rolled, or null -- one roll at a time
let dwelling = null;  // the timer a rested pointer is counting down

/** The last node of what the column is showing, which is where a purchase may extend it. */
const tail = () => drawn.at(-1)?.nodes.at(-1)?.id ?? null;

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
    if (armed === node) pulse(li, stub.costly(node));
  } catch {
    // A failed read is not reported: nothing was asked for out loud, and an error where a
    // reader only moved a pointer is noise about something they did not do.
    stub.asking(node, false);
  }
}

/** Pay to roll the arm below a node, for as long as the pointer stays on its row.
 *
 *  **Hovering is the gesture and dwelling is the payment.** A reader scanning a list reads
 *  the pulse, which says that reaching further here would cost inference; resting on it is
 *  the asking, and moving on is the stopping. So what is spent is proportional to what was
 *  looked at, and nothing is bought by crossing a row on the way somewhere else.
 *
 *  **It arrives in parts and each part is an act.** `stub.BURST` has why the record would
 *  rather have one act of forty, and why the reader would rather have ten of four. What
 *  the page does between them is read `/stub` again -- the free read, the same one a hover
 *  makes -- so the arm is drawn from the record whether the record or the model last
 *  answered, and there is no second path through which a bought token reaches the page.
 *
 *  **Where the purchase hangs decides whether the column moves**, and `stub.lengthens` is
 *  that decision. The text the reader is reading is not rearranged by their looking.
 */
async function roll(node) {
  // One at a time, against one writer and one cache slot. A second roll would not only
  // queue behind this one, it would truncate the prompt cache this one is warm in --
  // `docs/SPINE.md` measures that at 28 ms against 7.4 s.
  if (buying !== null || working) return;
  buying = node;
  // Taken before anything is bought, because the first burst is what moves the tip: after
  // it the arm hangs off its own new tokens and would never read as the end of the column.
  const grows = stub.lengthens(stub.tip(node), tail());
  let last = null;
  try {
    while (armed === node) {
      const want = stub.burst(node);
      if (want === null) break;
      // The length and the heat are the rollout's own and the rest is the reader's, which
      // is the cut `keep` is named for. Naming no sampler is what makes the act greedy in
      // its own `params` rather than greedy by argument.
      const act = await ask("/generate", {
        at: stub.tip(node), params: { ...keep(), length: want, temperature: 0 },
      });
      last = act.tip;
      const out = stub.landed(node, await ask(
        `/stub/${node}?length=${stub.CAP}&hidden=${showHidden ? 1 : 0}`));
      const li = seat(node);
      if (li === null) continue;  // the list was rebuilt; the arm is the node's, so carry on
      paint(li, out);
      // The price follows the pointer and not the reading, the same as everywhere else --
      // and it is what goes out when the arm reaches the cap, which is the roll ending by
      // having finished rather than by being left.
      if (armed === node) pulse(li, stub.costly(node));
    }
  } catch (why) {
    // Said out loud, unlike a failed free read: the reader rested on a price and nothing
    // came of it, which is a thing they did and are owed an answer about.
    say(`${why.kind || "unreachable"}: ${why.message}`, true);
  } finally {
    buying = null;
  }
  if (last === null) return;
  // What a burst wrote is below the arm's old tip, so no ranking on screen is stale -- but
  // that tip now realises a child it did not, and the next reader of its list would be
  // told otherwise. Dropping them costs a read apiece and only where one is opened again.
  ranking.forget();
  await counted();
  if (!grows) return;
  await show(last);
  // The text is longer than it was, so where the reader stands in it has moved under them.
  // Left stale, a reader who was at the end before the roll is recorded as still being
  // there, and the scroll that walks down to the new end reads as no gesture at all.
  wasAtEnd = atEnd();
  wasAt = window.scrollY;
}

/** The pointer arriving at a row or leaving it.
 *
 *  **Only the price moves with it.** What is drawn in the row was put there by `prefill` or
 *  by a read landing, and it stays -- so hovering says *there is more here* and never *here
 *  is what there is*.
 */
function rolls(row, where, on) {
  // A list still coming into place is not somewhere to point at. The row under the hand is
  // about to be somewhere else, and reading from it would be answering a question the
  // reader has not finished asking. `swap` asks again once it has stopped.
  if (on && performance.now() < settled_at) return;
  // Whichever way the pointer moved, it is no longer resting where it was. A roll already
  // under way is not cancelled here -- it reads `armed` after each part and stops itself,
  // so the burst in flight is paid for and finishes, which is what was asked for.
  clearTimeout(dwelling);
  if (!on) {
    // Only if this row is still the one being read. A pointer crossing from one row to the
    // next produces a leave and an enter, and nothing guarantees which the page sees first
    // -- clearing unconditionally lets the row being left cancel the read its neighbour
    // just started, which shows up as a hover that does nothing every other time.
    if (armed === row.child) armed = null;
    // The price goes with the pointer. It is about where the reader is looking and not about
    // the row, so a list left behind holding half a dozen of them would be saying that six
    // places are about to cost something.
    return pulse(where, false);
  }
  armed = row.child;
  // Set before anything is read, because the pulse follows the pointer and not the answer.
  // A row with no node under it is certainly costly and needs no read to say so.
  pulse(where, stub.costly(row.child));
  // A row nothing realised has nothing to descend from. Making one is a `realise` and then
  // a rollout -- two acts, the first of which is the one that makes a fork real, so it is
  // not something a pointer does. The pulse still says what reaching here would cost.
  if (row.child === null) return;
  // The dwell is counted from the answer and not from the arrival: until the free read has
  // landed there is no price to have rested on, and `burst` would decline anyway. An arm
  // already held resolves at once, so returning to a row starts the clock immediately.
  grow(row.child).then(() => {
    if (armed !== row.child) return;
    clearTimeout(dwelling);
    dwelling = setTimeout(() => {
      if (armed === row.child) roll(row.child).catch(() => {});
    }, DWELL);
  }).catch(() => {});
}

/** Show the rows the caret is at, which is where they sit when nothing is hovered. */
function settled() {
  showing = cursor.node();
  const mark = $("column").querySelector(".seg.at");
  if (!ranking.asked() || mark === null) return clear();
  opened(showing, mark, SETTLE_IN).catch(() => clear());
}

function peek(i, el) {
  if (!ranking.asked()) return;
  clearTimeout(peeking);
  const to = cursor.chosen(drawn, i);
  if (to === null || to === showing) return;
  peeking = setTimeout(() => { showing = to; opened(to, el).catch(() => clear()); }, SEEN);
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
async function show(node, where) {
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
    if (stop === 0) return land(null);
    if (stop > 0) { cells = cells.slice(0, stop); closed = true; }
  } else {
    closed = false;  // what was set aside is drawn, so `boundary` is already saying it
  }
  drawn = cells;
  // Where the reader has not pointed, the caret rests at the end of what is drawn -- so the
  // gesture that asks for more of a path and the gesture that asks for a draw at a position
  // are the same act at the same node, which is the ordinary case and not a coincidence.
  cursor.place(where === undefined ? cursor.resting(cells) : where);
  const flow = document.createElement("div");
  flow.className = "flow";
  // Leaving the text puts the rows back where the reader is, so a peek never outlives the
  // pointer and what stands beside the column is the caret's again.
  flow.onmouseleave = () => { clearTimeout(peeking); settled(); };
  // Read over what is drawn and not over what came back, so a path-relative scale takes its
  // range from the text in front of the reader.
  flow.append(...spans(cells, overlays(cells, read.sources), mark.read(cells, read.kinds)));
  if (closed) flow.append(closure());
  $("column").replaceChildren(flow);
  frontier();
  settled();
  // Which root is current is derived from the path rather than held beside the position,
  // so the two cannot disagree about where the reader is.
  const root = cells[0].nodes[0].id;
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
  $("column").replaceChildren(compose(at));
  $("column").querySelector("textarea").focus();
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

function waiting() {
  pending(Object.assign(document.createElement("span"), {
    className: "wait", textContent: "\u2026",
  }));
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
 *  -- the tokens either merge onto what already follows or part from it. */
async function more(where = cursor.node()) {
  // A roll in flight is the other writer there is, and it holds a warm prompt cache a draw
  // from somewhere else would truncate -- `docs/SPINE.md` measures that at 28 ms against
  // 7.4 s. A scroll during one is dropped rather than queued, the same as during a draw.
  if (working || buying !== null || where === null || where === undefined) return;
  working = true;
  waiting();
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
    const act = await ask("/generate", { at: where, params: draw() });
    await refresh();
    await show(act.tip);
  } catch (why) {
    failed(why);
  } finally {
    working = false;
    quiet = Date.now() + REST;
    // What landed moved the end and may have moved the window: an arrival at the end is a
    // fresh one, and where the page now stands is not somewhere the reader scrolled to.
    wasAtEnd = atEnd();
    wasAt = window.scrollY;
  }
}

/** Whether a downward move counts as a request: at the end of the page, or anywhere at all
 *  once the caret has been armed. */
const ready = () => cursor.armed() || atEnd();

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
 *  It costs no read. A path through any node of the path already drawn is that same path, so
 *  this is a mark that moves over text that does not.
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
addEventListener("scroll", () => {
  const now = atEnd();
  // Downward and not merely different. At the end of the page there is nowhere below to go,
  // so an arrival there is the gesture; an armed caret has no such place, so the direction is
  // all there is -- and what lands after an act can shorten the page and move the window on
  // its own, which would otherwise read as a reader asking for the next one.
  const asks = (cursor.armed() && window.scrollY > wasAt) || (now && !wasAtEnd);
  wasAtEnd = now;
  wasAt = window.scrollY;
  // Every scroll settles, because the caret follows the window whichever way it went. Only
  // some of them ask for anything.
  moved(asks);
}, { passive: true });

// Already somewhere that counts, and still going down. Every way of moving the page is one
// of these.
addEventListener("wheel", event => { moved(event.deltaY > 0 && ready()); }, { passive: true });
addEventListener("keydown", event => {
  if (event.target.closest("textarea, input")) return;
  if (!["ArrowDown", "PageDown", "End", " ", "ArrowUp", "PageUp", "Home"].includes(event.key))
    return;
  moved(["ArrowDown", "PageDown", "End", " "].includes(event.key) && ready());
});

/** An act with no terminator is a generation in flight, so a reload draws it rather than
 *  losing it. One writer means there is at most one. */
async function resume() {
  const { acts } = await ask("/acts?in_flight=1");
  if (!acts.length) return false;
  working = true;
  waiting();
  while ((await ask("/acts?in_flight=1")).acts.length)
    await new Promise(again => setTimeout(again, 700));
  working = false;
  return true;
}

// ---- the page -------------------------------------------------------------------------

function say(text, bad) {
  $("status").textContent = text;
  $("status").className = bad ? "fault" : "";
}

$("draw").replaceChildren(panel());

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

$("rows").onchange = () => {
  ranking.want($("rows").checked);
  settled();
};

$("fold").onclick = () => {
  const folded = document.body.classList.toggle("folded");
  $("fold").setAttribute("aria-pressed", String(folded));
};

try {
  // A reload restores a checkbox in some browsers, and nothing here is remembered between
  // loads -- so what the box says is what the page believes, rather than the other way.
  showHidden = $("hidden").checked;
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
