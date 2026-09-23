/* The surface: a list of roots, a reading column, and the one composer both of them use.
 *
 * The reader's position is a single node and everything else is derived from it -- which
 * root is current, what path is drawn, where a write will land. Holding a root as well
 * would be two pieces of state that can disagree, and `/path/{node}` already answers from
 * a node what the surface needs.
 *
 * Nothing here is remembered between loads. Reader state lives in the session, and what is
 * live, what parts and what a ranking holds are read from the store every time.
 */

import { draw, panel } from "./draw.js";
import { asked as overlaid, panel as overlayPanel, read as overlays } from "./overlay.js";

const $ = id => document.getElementById(id);

/** The reader's position: a node, or nothing at all before there is a tree. */
let position = null;

/* Where a continuation hangs: the last node whose path has a string form, which is the leaf
 * unless the path ends mid-character. A segment cannot be split and nothing is addressed
 * inside one, so trailing bytes waiting for the rest of their character are not a position
 * the surface acts at -- and a draw that repeats them merges onto the same nodes. */
let addressable = null;

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
  const shape = await answer.json();
  // A fault says which kind it was because the record does: a refusal and a rejection are
  // answers about the request, and only a failure is worth repeating unchanged.
  if (!answer.ok) throw new Fault(shape.error || "error", shape.message || answer.statusText);
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
  const tree = await ask("/tree");
  drawRoots(tree, current);
  say(`${tree.path}  ${tree.vocabulary}  ` +
      `${tree.counts.nodes} nodes  ${tree.counts.edges} edges  ${tree.counts.acts} acts`);
  return tree;
}

// ---- the reading column ---------------------------------------------------------------

/** A segment is set aside if any of its nodes is. It is the addressable unit and cannot be
 *  split, so a character spelled across the boundary goes with the part that is hidden. */
const aside = cell => cell.nodes.some(n => !n.live);

/** Where the path leaves what is live, and the way back. One of these: what is hidden is a
 *  suffix, because the rule picks the live path first. */
function boundary(cell) {
  const mark = document.createElement("span");
  mark.className = "cut";
  const go = document.createElement("button");
  go.textContent = "restore";
  go.title = "bring this back into the live tree";
  go.onclick = () => restore(cell);
  mark.append("set aside", go);
  return mark;
}

/** `marks` is what the overlay made of each span, or null where none is drawn -- which is
 *  the column a reader has not asked anything of, and is why the mark is applied here rather
 *  than being something a span always carries. */
function spans(segments, marks) {
  const out = [];
  let cut = false;
  for (const [i, cell] of segments.entries()) {
    const hidden = aside(cell);
    if (hidden && !cut) { cut = true; out.push(boundary(cell)); }
    const el = document.createElement("span");
    el.className = `seg${cell.decodes ? "" : " raw"}${hidden ? " hidden" : ""}`;
    el.textContent = cell.text;
    el.dataset.node = cell.nodes[cell.nodes.length - 1].id;
    const mark = marks?.[i];
    if (mark) {
      el.classList.add(mark.cls);
      el.title = mark.title;
      // The scale hands over a place and the stylesheet owns the colour, so a palette stays
      // in one file and a theme changes nothing here.
      if (mark.t !== undefined) el.style.setProperty("--t", mark.t.toFixed(3));
    }
    // A plain click is spoken for -- `docs/SURFACE.md` has it opening a ranking -- so the
    // one gesture that changes the tree from here asks for a modifier and says so.
    el.onclick = event => {
      if (!event.altKey) return;
      if (hidden) restore(cell);
      else flip(false, cell.nodes[0].id, cell.nodes[0].parent);
    };
    out.push(el);
  }
  return out;
}

/** Draw the path through a node and make it the position. */
async function show(node) {
  // An overlay is asked for, and a read not asked for one carries none of it.
  const read = await ask(
    `/path/${node}?hidden=${showHidden ? 1 : 0}&overlays=${overlaid() ? 1 : 0}`);
  let cells = read.segments;
  if (!showHidden) {
    // The read carries a hidden ancestry whatever the toggle says, since a path through a
    // node that was set aside still reaches it. With the toggle off none of that is drawn,
    // and a reader left standing in it falls back to where the live tree ends.
    const stop = cells.findIndex(aside);
    if (stop === 0) return land(null);
    if (stop > 0) cells = cells.slice(0, stop);
  }
  position = node;
  const closed = cells.filter(cell => cell.decodes && !aside(cell));
  addressable = closed.length ? closed[closed.length - 1].nodes.at(-1).id : null;
  const flow = document.createElement("div");
  flow.className = "flow";
  // Read over what is drawn and not over what came back, so a path-relative scale takes its
  // range from the text in front of the reader.
  flow.append(...spans(cells, overlays(cells, read.sources)));
  $("column").replaceChildren(flow);
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
  position = addressable = null;
  $("column").replaceChildren(compose(at));
  $("column").querySelector("textarea").focus();
}

// ---- continuing ------------------------------------------------------------------------

/* The gesture is the scroll: reaching the end of what there is to read asks for more of it,
 * at the end of the path, where the reader is already looking.
 *
 * A downward move *at* the end counts as well as an arrival there. Under about a thousand
 * characters the column sits at its minimum height, so text that lands does not make the
 * page any taller -- the room above it shrinks instead -- and a reader who stayed at the end
 * would have nowhere left to scroll and no way to ask again.
 */

const SETTLE = 140;  // ms of quiet before a scroll counts, so momentum is not a request
const REST = 450;    // ms after one lands, so a held key is one request and not twenty

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

/** Ask for more of the path. One at a time: there is no queue, and the server says so too. */
async function more() {
  if (working || addressable === null) return;
  working = true;
  waiting();
  try {
    // Ending mid-character is not the only reason a backend may decline a path, so the
    // predicate is asked at the position the act would use. Asking writes nothing, and the
    // answer is advisory -- what it saves is a refusal nobody needed to see.
    if (!(await ask(`/evaluable?node=${addressable}`)).evaluable) {
      pending(Object.assign(document.createElement("span"), {
        textContent: "The model will not continue from this position.",
      }));
      return;
    }
    // Asked for at the moment of the act, so what the panel holds now is what is sent and
    // what the record keeps. Nothing here caches it.
    const act = await ask("/generate", { at: addressable, params: draw() });
    await refresh();
    await show(act.tip);
  } catch (why) {
    failed(why);
  } finally {
    working = false;
    quiet = Date.now() + REST;
    wasAtEnd = atEnd();  // what landed moved the end; an arrival at it is a fresh one
  }
}

/** Reached the end, and stayed there long enough to have meant it. */
function asked() {
  if (working || Date.now() < quiet) return;
  clearTimeout(timer);
  timer = setTimeout(() => { if (atEnd()) more(); }, SETTLE);
}

let wasAtEnd = false;
addEventListener("scroll", () => {
  const now = atEnd();
  if (now && !wasAtEnd) asked();
  wasAtEnd = now;
}, { passive: true });

// Already at the end, and still going down. Every way of moving the page is one of these.
addEventListener("wheel", event => { if (event.deltaY > 0 && atEnd()) asked(); },
                { passive: true });
addEventListener("keydown", event => {
  if (event.target.closest("textarea, input")) return;
  if (["ArrowDown", "PageDown", "End", " "].includes(event.key) && atEnd()) asked();
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

/* The overlay and what is set aside are both ways of looking, and they share a panel because
 * they are the same question asked twice: what of the record is in front of me. Moving either
 * re-reads rather than repainting what is already drawn -- turning a measure on asks the
 * server for what the last read did not carry, and one path costs milliseconds. */
$("read").append(overlayPanel(async () => {
  try {
    await (position === null ? overlays([], {}) : show(position));
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
    if (position !== null) await show(position);
  } catch (why) {
    say(`${why.kind || "unreachable"}: ${why.message}`, true);
  }
};

$("fold").onclick = () => {
  const folded = document.body.classList.toggle("folded");
  $("fold").setAttribute("aria-pressed", String(folded));
};

try {
  // A reload restores a checkbox in some browsers, and nothing here is remembered between
  // loads -- so what the box says is what the page believes, rather than the other way.
  showHidden = $("hidden").checked;
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
      await show(position);
    }
  }
  wasAtEnd = atEnd();
} catch (why) {
  say(`${why.kind || "unreachable"}: ${why.message}`, true);
}
