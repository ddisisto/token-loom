/* The reading column: the text laid as segments, the caret's mark on it, and setting aside and
 * bringing back from it. */

import * as cursor from "./cursor.js";
import * as mark from "./mark.js";
import { read as overlays } from "./overlay.js";
import { busy, carry, drawn, land, rebase, showHidden, working } from "./reading.js";
import { refresh, writable } from "./roots.js";
import { entered, left, settled, unpeeked } from "./rows.js";
import * as stub from "./stub.js";
import { ask, say, wrong } from "./wire.js";
import { chartCaret } from "./chart.js";
import { composing } from "./compose.js";

const $ = id => document.getElementById(id);

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
    const hidden = cursor.aside(cell);
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
    el.onmouseenter = () => entered(i, el);
    el.onmouseleave = left;
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
export function frontier() {
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
export function point(i) {
  put(cursor.chosen(drawn, i));
}

/** Put the caret after the node `to`, over text that does not move. */
function put(to) {
  if (to === null) return;
  cursor.place(to);
  frontier();
  settled();
}

/** Step the caret `by` segments along the path, scrolling only as far as keeps it in view. */
export function step(by) {
  const to = cursor.stepped(drawn, cursor.node(), by);
  if (to === null) return;
  put(to);
  const seg = $("column").querySelector(".flow .seg.at");
  if (seg === null) return;
  carry();
  seg.scrollIntoView({ block: "nearest" });
}

/** Put the caret back at the tip of what is drawn, which is where a reader who has pointed at
 *  nothing stands.
 *
 *  **Pointing has no other way out.** Every segment is somewhere to point and the tip is a
 *  segment like the rest, so without this the resting position is reachable only by reloading
 *  -- and since nothing arms away from the tip, a reader who pointed somewhere would have no
 *  way back to the scroll gesture at all. It takes no read, for the reason `point` gives.
 */
export function release() {
  if (composing()) return;
  const to = cursor.resting(drawn);
  if (to === null || to === cursor.node()) return;
  cursor.place(to);
  frontier();
  settled();
}

/** What a closure mark does when it is taken: show what is set aside, wherever it is.
 *
 *  **It reveals and it does not revive.** Turning the toggle on brings the hidden tail back
 *  into the column with `.cut` standing at its head, and that boundary is where `undelete`
 *  already lives -- so the reader sees what they closed before deciding to reopen it, and
 *  nothing the surface does on a click puts a node back that they put away. It is also why
 *  the mark can sit in a hover panel at all: it costs a view and never an act.
 */
export function reveal() {
  if (showHidden) return;
  $("hidden").checked = true;
  $("hidden").onchange();
}

/** The text itself, as an element, built apart from being hung. */
export function laid({ read, cells, closed }) {
  const flow = document.createElement("div");
  flow.className = "flow";
  // Leaving the text puts the rows back where the reader is at once, as leaving a token does
  // after a beat, so a peek never outlives the pointer on its token.
  flow.onmouseleave = unpeeked;
  // Read over what is drawn and not over what came back, so a path-relative scale takes its
  // range from the text in front of the reader.
  flow.append(...spans(cells, overlays(cells, read.sources), mark.read(cells, read.kinds)));
  if (closed) flow.append(closure());
  return flow;
}

// ---- setting aside, and bringing back ---------------------------------------------------

/* `delete` sets a flag on one node and `undelete` clears it. Nothing leaves the store, so
 * both are ordinary acts under their own verbs and the page reads the record again after
 * either -- what changed is liveness, which is derived and never held here.
 */

export async function flip(undo, node, then) {
  if (working) return;
  busy(true);
  try {
    await ask(undo ? "/undelete" : "/delete", { node });
    await refresh();
    await land(then);
  } catch (why) {
    wrong(why);
  } finally {
    busy(false);
    rebase();  // the path just got shorter or longer; an arrival is a fresh one
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
