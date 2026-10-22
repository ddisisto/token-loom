/* The tree as the nav has it: its roots, the waypoints under them, and the counts.
 *
 * A waypoint stands under its root, and under the nearest waypoint above it, named by the
 * text either side of it with its own token picked out in the middle. Taking one is an
 * arrival: the path through it, the caret on it in the middle of the window, and the token
 * flashing there and in the nav so the eye finds where it landed.
 */

import * as ranking from "./ranking.js";
import * as stub from "./stub.js";
import * as waypoint from "./waypoint.js";
import { ask, say } from "./wire.js";
import { drawn, reach, show, showHidden } from "./reading.js";
import { flip, rechart, retrace, stage, stale } from "./app.js";

const $ = id => document.getElementById(id);

export const storage = (() => { try { return localStorage; } catch { return null; } })();
export let known = null;     // the last answer to `/tree`
let kept = [];        // { node, created }: the waypoints set in this tree, in the order set
let ways = new Map(); // root -> what the server said of the waypoints under it, nested

/* Whether the server writes, as `/tree` says. One started to read holds no claim, and the page
 * it serves offers no gesture that writes: no draw, no composer, no realise, no setting aside. */
export let writable = true;

/** The nodes the kept waypoints stand on. */
export const marks = () => kept.map(w => w.node);

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

/** Ask what the kept waypoints are now: where each stands, whether it is live, and what
 *  leads up to it. Nothing is asked when there are none. */
async function named() {
  const rows = kept.length
    ? (await ask(`/waypoints?nodes=${marks().join(",")}`)).waypoints : [];
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

/** Set a waypoint at `node`, or clear the one there. */
export async function waymark(node) {
  kept = waypoint.toggle(kept, node, Date.now());
  if (!waypoint.save(storage, known.created ?? known.path, kept))
    say("this browser is not keeping waypoints, so these go with the page", true);
  marked();
  await named();
  drawRoots(known, drawn[0]?.nodes[0].id);
  rechart();
}

/** Mark each segment holding a waypoint. */
export function marked() {
  const at = new Set(marks());
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

/** Say which root is current, which is derived from the path rather than held beside the
 *  position, so the two cannot disagree about where the reader is. */
export function current(root) {
  for (const li of $("roots").querySelectorAll("li[data-node]"))
    li.setAttribute("aria-current", String(Number(li.dataset.node) === root));
}

/** The roots the toggle admits. */
export const live = tree => tree.roots.filter(root => showHidden || !root.deleted);

export async function refresh(at) {
  // Every act lands through here, and an act is what makes a ranking read earlier wrong: the
  // rows only grow, but which of them a node now realises does not.
  ranking.forget();
  // An arm is what the tree holds on the top row, so an act can lengthen one or take it
  // off the top row entirely. Both make what is held wrong in the same way the rows are.
  stub.forget();
  // The rows said what became of each row and the strands where every act landed, and an act
  // has changed both.
  stale();
  const tree = known = await ask("/tree");
  writable = tree.writable !== false;
  document.body.classList.toggle("read-only", !writable);
  // Keyed by the tree and not by the address, which names only the server.
  kept = waypoint.load(storage, tree.created ?? tree.path);
  retrace(tree.created ?? tree.path);
  await named();
  drawRoots(tree, at);
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
export const counted = async () => tally(await ask("/tree"));
