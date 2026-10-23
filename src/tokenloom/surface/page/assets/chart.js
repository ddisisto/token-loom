/* The map: the tree under the current root, drawn as a shape in the margin, and what the hand
 * does on it. `map.js` has its arithmetic.
 *
 * The tree under the current root, drawn as a shape in the margin. Its strands are read once
 * per root, per toggle and per act; what moves with the reader -- the path and the caret -- is
 * drawn again from what is held, and costs no read. Pointing at a strand is an arrival, as
 * taking a waypoint is: the path through that point in the column, and the caret on it. */

import * as cursor from "./cursor.js";
import * as map from "./map.js";
import {
  carry, carrying, cells, drawn, pathEnd, pathIds, reach, showHidden,
} from "./reading.js";
import { known, marks, storage } from "./roots.js";
import { ask, say, wrong } from "./wire.js";
import { point } from "./column.js";

const SVG = "http://www.w3.org/2000/svg";
const LEAD = 100;          // ms the caret takes to where an arrival is going
const SHOWN = 700;         // ms the zones' edges stay drawn across the map after they last moved
const STRIDE = 400;        // ms it takes over a step of zoom
const OPEN = 2;            // steps of zoom a click on a reed takes in
const TOOTH = 14;          // px of each tooth lit from the box while its reed is pointed at
const SHAPE = ["x1", "y1", "x2", "y2", "cx", "cy", "r"];  // what a mark's geometry is
const STEPS = 4;           // paths back the trail is drawn for, each in a colour of its own

const $ = id => document.getElementById(id);
const chartEl = $("map");
const chartBar = $("chart-bar");
// The rung is `map.LADDER`'s, `byFork` puts a strand in the zone its fork is in, and `lens`
// gives the thumb more of the axis as the zoom goes in.
export const look = { on: true, down: true, rung: 4, byFork: false, lens: true, reed: 2 };
let charted = null;  // { root, hidden, tree, marks }: the last `/map`, indexed
let asking = null;   // which of those is in flight, so a late answer does not draw over a newer
let chart = null;    // what is drawn now, which a point is read against
let thumbed = null;  // the thumb in the hand: how far into it it was taken, in tokens
let dragged = false;  // a drag ended, and the click that follows it is not an arrival
let pointedAt = null; // the path's cell the pointer is over, from the column or the map
let gliding = 0;      // which move is running, so a newer drawing stops an older one
let lit = null;       // the strand the pointer is over on the map, traced to the root
let onReed = null;    // the reed the pointer is over on the map
let combing = null;   // the reeds of the tree drawn, combed once per tree and per setting
let glowing = [];     // the path's cells a reed pointed at spans, glowing
let walked = [];      // the trail: the paths the reader has been on in this tree, newest first
let zoomed = 0;       // steps of zoom in about the thumb
let wheeled = 0;      // px of a fine wheel not yet a step
let refocusing = false; // a check of the cut asked for this frame, so a scroll asks once
let scanned = 0;      // px of a fine wheel not yet a step across
let scanning = false; // an arrival across still on its way
let scanAt = null;    // where the last scan landed, the depth it kept, and the window it held
let led = null;       // where the caret has gone ahead of an arrival, until it is drawn
let rush = { until: 0, pace: map.GLIDE };  // the glide a run of steps across has hurried to
let cool = { t0: 0, until: 0 };        // from when until when the drawing catches the caret up
let swept = 1;   // which end of the caret its colour sweeps from: the side it came from
let scaled = null;    // where along the scale the hand holds the zoom, while it does
let shown = 0;        // the timer that takes the zones' edges off the map again
let heldTall = false; // the column kept at its height through steps across, until a scroll
let aiming = null;  // a run of steps across: where it lands, from where, and the branch it is going to

/** Forget the strands, which an act changes. */
export function forget() {
  charted = null;
}

/** Take up the trail kept for the tree keyed `key`. */
export function recall(key) {
  walked = map.recall(storage, key);
}

/** Read the strands again and draw them. */
export function rechart() {
  charted = null;
  charter();
}

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

/** Read the strands if what is thumbed is not this root's, then draw. */
export async function charter() {
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
                            `&marks=${marks().join(",")}`);
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

/** The reeds of the tree drawn and the tree combed by them, combed again only when the tree,
 *  the cut or the dial changes. */
function combedOf(source) {
  if (combing?.charted === charted && combing.rung === look.rung && combing.reed === look.reed)
    return combing;
  const got = map.reeds(source, map.hair(source, map.LADDER[look.rung], new Set()),
                        map.combAt(map.reedSteps(map.most(source)), look.reed));
  combing = { charted, rung: look.rung, reed: look.reed, ...got, tree: map.comb(source, got.reeds) };
  return combing;
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
const placed = (along, across) => map.placed(look.down, along, across);
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
const lensed = (most, long, span) => map.scale({ most, width: long, pad: map.PAD,
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
  for (const r of plan.reeds)
    out.push([`r${r.head}`, "line", lineAt(r.x0, r.y0, r.x0, r.y1), "reed", null, {}]);
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
  chart.ruler.replaceChildren(...map.ticks(chart.x, chart.most).map(([v, major]) => {
    const a = chart.x(v), reach = major ? 6 : 3;
    return svg("line", lineAt(a, 1, a, 1 + reach), major ? "tick" : "tick minor");
  }));
  chartHandle();
}

/** The zoom as a mark on the scale: out at the tree's end and in at the root, or wherever the
 *  hand holding it is. */
function chartHandle() {
  const a0 = chart.x(0), a1 = chart.x(chart.most);
  const a = scaled ?? map.scaleAt(zoomed, a0, a1, zoomMost());
  assign(chart.handle, lineAt(a, 0, a, map.SCALE - 2));
}

/** Zoom to the step nearest where the hand holds the scale, `along` px down it. */
function scaleTo(along) {
  const { at, steps: to } = map.scaleTo(along, chart.x(0), chart.x(chart.most), zoomMost());
  scaled = at;
  if (to !== zoomed) {
    zoomed = to;
    sketch({ pace: STRIDE });
    foreshadow();
  }
  chartHandle();
}

/** Draw where the zones about the thumb part across the whole map, for a while. */
function foreshadow() {
  if (chart === null) return;
  const span = chart.span ?? chart.lensAt;
  const edges = zoomed > 0 && span
    ? map.bands(span, map.ZONES.focal * chart.most, chart.most).map(([from]) => from).filter(v => v > 0)
    : [];
  chart.bands.replaceChildren(...edges.map(v =>
    svg("line", lineAt(chart.x(v), 0, chart.x(v), chart.wide), "band")));
  chart.bands.classList.add("on");
  clearTimeout(shown);
  shown = setTimeout(() => chart?.bands.classList.remove("on"), SHOWN);
}

/** Draw the same strands again through the fisheye as it stands about the thumb now, moving
 *  each mark rather than making it anew. */
function restretch(span) {
  gliding++;
  chartEl.classList.remove("moving");
  const { tree } = chart;
  const x = lensed(chart.most, chart.long, span);
  const plan = map.plan(tree, chart.rows, { x, hairs: chart.hairs, path: chart.path,
                                            step: chart.step, top: chart.top });
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
export function sketch({ glides = true, pace = map.paced(performance.now(), rush) } = {}) {
  if (!look.on || charted === null) return;
  gliding++;
  chartEl.classList.remove("moving");
  chartEl.style.setProperty("--glide", `${pace}ms`);
  const { tree: source } = charted;
  const path = map.along(source, pathIds());
  const { most, span, hairs } = cutting(source, path);
  const { forks, places, tree } = combedOf(source);
  // The trail takes the path the reader is on, and is drawn from before and after it did.
  const earlier = chart === null ? null
    : { path: chart.path, back: map.steps(source, walked, chart.path, STEPS) };
  const now = map.remember(source, walked, path, [...path].at(-1) ?? null);
  if (now !== walked) map.keep(storage, known.created ?? known.path, now);
  walked = now;
  const back = map.steps(source, walked, path, STEPS);
  const box = chartEl.getBoundingClientRect();
  const [long, wide] = look.down ? [box.height, box.width] : [box.width, box.height];
  // Packed on the straight axis, so a fisheye moving with the thumb moves no strand across.
  const rows = map.layout(tree, { x: map.scale({ most, width: long, pad: map.PAD }), hairs, path });
  const all = [...rows.values()], lo = Math.min(...all);
  // The drawing holds the reed the window is at where it stood, so a step across moves what is
  // above it and not its teeth; too wide to fit, it is cut off at the edges and moves only to
  // keep the path's row where the window is in view.
  const mid = span ? (span[0] + span[1]) / 2 : null;
  const held = mid === null ? null : map.holds(tree, path, mid);
  const by = mid === null ? tree.top : map.anchor(tree, path, mid);
  const stood = chart !== null && chart.source === source && chart.wide === wide
    && chart.rows.has(by.head) && rows.has(by.head)
    ? chart.zero + (chart.rows.get(by.head) - rows.get(by.head)) * chart.step : null;
  const { step, top, cut } = map.fit(lo, Math.max(...all), wide, look.down,
    rows.get(held?.head) ?? 0, stood);
  const x = lensed(most, long, span);
  const plan = map.plan(tree, rows, { x, hairs, path, step, top });

  const out = [];
  const ruler = svg("g", {}, "scale");
  const bands = svg("g", {}, "bands");
  const handle = svg("line", {}, "handle");
  const thumb = svg("rect", {}, "thumb");
  out.push(bands, ruler, handle, thumb);
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
  const caret = svg("line", { "data-key": "caret" }, "caret");
  const sweep = svg("line", { "data-key": "sweep", pathLength: 1 }, "sweep");
  // An edge the drawing is cut off at says so.
  for (const [side, at] of [[cut[0], 0.5], [cut[1], wide - 0.5]])
    if (side) out.push(svg("line", lineAt(0, at, long, at), "cropped"));
  const pointed = svg("line", {}, "over");
  const teeth = svg("g", {}, "teeth");
  out.push(teeth, pointed, caret, sweep);
  // Shadows outlast a drawing, each carrying on its fade where it had got to.
  for (const el of chartEl.querySelectorAll(".shade")) {
    el.style.animationDelay = `${Number(el.dataset.t0) - performance.now()}ms`;
    out.push(el);
  }
  // The same tree drawn the same way and the same size is a packing that moved, which glides;
  // anything else is a new drawing, which does not.
  const same = glides && chart !== null && chart.source === source && chart.down === look.down
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
  const combed = look.reed ? { forks, places } : null;
  chart = { source, tree, combed, teeth, x, plan, path, hairs, rows, back, top, most,
            lensAt: span, caret, sweep, pointed, thumb, ruler, bands, handle, els, line: lineAt,
            step, byHead, down: look.down, long, wide, zero: top - lo * step,
            ys: new Map(plan.strands.map(s => [s.head, s.y])) };
  lit = null;
  onReed = null;
  for (const i of glowing) cellsGlow(i, false);
  glowing = [];
  // A run of steps still going on past this drawing keeps the caret where it is going.
  led = aiming !== null && aiming.to.head !== [...path].at(-1) ? ledAt(aiming.to.head, map.aimedAt(aiming)) : null;
  rule();
  chartCaret();
  cooling();
  chartOver();
  chartThumb();
  if (was !== null) glide(was, pace);
  chartSays(map.effect(tree, hairs),
            zoomed && span ? map.zoneCounts(tree, hairs, { span, most }) : null, combed);
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
 *  path's row. What is new fades in, the caret rides with its strand, and the pointer and the
 *  thumb wait until it lands. */
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
    else {
      chartEl.classList.remove("moving");
      // The last glide of a run of steps takes what is left of their shadows with it.
      if (now >= rush.until) for (const el of chartEl.querySelectorAll(".shade")) el.remove();
    }
  };
  frame(t0);
}

/** Where across the path stands `depth` tokens from the root: its row there, which a reed it
 *  goes through moves it off. */
function rowAt(depth) {
  const s = map.holds(chart.tree, chart.path, depth);
  return chart.ys.get(s?.head) ?? chart.ys.get(chart.tree.top.head);
}

/** Where the caret is on the path's row. */
export function chartCaret() {
  if (chart === null) return;
  if (led !== null) return caretAt(led);
  const at = pathIds().indexOf(cursor.node());
  if (at < 0) return caretAt(null);
  caretAt(chart.line(...map.upright(chart.x(at + 0.5), rowAt(at), chart.step)));
}

/** Draw the caret and the sweep over it at `attrs`, or neither with null. */
function caretAt(attrs) {
  for (const el of [chart.caret, chart.sweep]) {
    el.style.display = attrs === null ? "none" : "";
    if (attrs !== null) assign(el, attrs);
  }
}

/** Sweep the caret's colour along it over what is left of the time the drawing takes to catch
 *  it up, from where that has got to. */
function cooling() {
  const el = chart?.sweep;
  if (!el) return;
  const { left, offset } = map.cooled(performance.now(), cool, swept);
  el.style.transition = "none";
  el.style.strokeDashoffset = String(offset);
  if (left <= 0) return;
  void el.getBoundingClientRect();  // the offset lands before the transition from it starts
  el.style.transition = `stroke-dashoffset ${left}ms linear`;
  el.style.strokeDashoffset = "0";
}

/** Mark the path's cell `i` as what the pointer is over, in the column and on the map, or
 *  nothing with null. The two hold the same positions and a pointer is over one of them. */
export function hover(i) {
  if (i === null) tell(null);
  if (i === pointedAt) return;
  const segs = $("column").querySelectorAll(".flow .seg");
  segs[pointedAt]?.classList.remove("over");
  pointedAt = i;
  segs[pointedAt]?.classList.add("over");
  chartOver();
  const got = i === null ? null : cells();
  if (got === null) return tell(null);
  const depth = got.at[i + 1] - 1;
  tell(placeSays(chart && map.holds(chart.source, chart.path, depth)?.head, depth));
}

/** Say on the footer what the pointer is over, so a place can be named: a node, its depth, the
 *  strand holding it and the reed it is in, or a reed -- or nothing with null. */
function tell(text) {
  $("over").textContent = text ?? "";
}

/** A reed, as `map.where` has it. */
const reedSays = r => `reed ${r.head} · depth ${r.from}–${r.to} · ${r.forks} forks · ${r.teeth} teeth`;

/** The token `depth` from the root on the strand `head`, with its node where it is on the path. */
function placeSays(head, depth) {
  const ids = pathIds();
  const out = [];
  if (head == null || chart?.path.has(head)) out.push(`node ${ids[depth]}`);
  out.push(`depth ${depth}`);
  const w = chart === null || head == null ? null
    : map.where(chart.source, chart.tree, combing.reeds, head);
  if (w !== null) out.push(`strand ${w.strand.head}–${w.strand.tail}`);
  if (w?.reed) out.push(`${w.how === "tooth" ? `tooth ${w.slot} of` : `${w.how} of`} ${reedSays(w.reed)}`);
  return out.join(" · ");
}

/** Where the pointer is on the path's row, from whichever side it is on. */
function chartOver() {
  if (chart === null) return;
  const got = pointedAt === null ? null : cells();
  chart.pointed.style.display = got ? "" : "none";
  if (!got) return;
  const mid = (got.at[pointedAt] + got.at[pointedAt + 1]) / 2;
  assign(chart.pointed, chart.line(...map.upright(chart.x(mid), rowAt(mid), chart.step)));
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
  const half = chart.half = map.thumbHalf(chart.step);
  chart.thumbY = rowAt((span[0] + span[1]) / 2);
  assign(chart.thumb, { ...map.thumbBox(chart.x, span, chart.thumbY, half, look.down), rx: 2 });
}

/** The point an event is at, along and across the plan, or null off the map. */
function chartPoint(event) {
  if (chart === null) return null;
  const box = chartEl.getBoundingClientRect();
  return map.onPlan(event.clientX - box.left, event.clientY - box.top, box.width, box.height,
                    look.down);
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
  return map.inThumb(chartPoint(event), chart?.x, chart?.span, chart?.thumbY, chart?.half);
}

/** Scroll the column so the token `depth` tokens from the root stands at the top of the view. */
function scrollAt(depth) {
  const got = cells();
  if (got === null) return;
  const el = got.segs[map.holding(got.at, depth)];
  carry();
  window.scrollTo(0, window.scrollY + el.getBoundingClientRect().top - view()[0]);
}

/** Arrive where a click on the column's own ground points on the map, and say whether it did. */
export function charting(event) {
  if (dragged) { dragged = false; return true; }
  // A click while the drawing moves would land on where something is going, not where it is.
  if (chartEl.classList.contains("moving")) return true;
  // A click in the thumb puts the caret on the token under it, and the window stays.
  const into = onThumb(event);
  if (into !== null) {
    const got = cells();
    if (got !== null) point(map.holding(got.at, Math.floor(chart.span[0] + into)));
    return true;
  }
  // A click on a reed takes the reader to its input and zooms in about it.
  const p = chartPoint(event);
  const reed = p === null ? null : map.reedAt(chart.plan, p.along, p.across, 5);
  if (reed !== null) {
    const depth = reed.from - 1;
    lead(reed.head, depth);
    visit({ tail: chart.path.has(reed.head) ? pathEnd() : chart.tree.lines.get(reed.head).tail,
            depth })
      .then(() => zoomBy(OPEN)).catch(wrong).finally(unlead);
    return true;
  }
  const hit = chartHit(event);
  if (hit === null) return false;
  // A point on the path being read keeps it, and only the caret moves.
  const to = chart.path.has(hit.head) ? { tail: pathEnd(), depth: hit.depth } : hit;
  lead(hit.head, hit.depth);
  visit(to).catch(wrong)
    .finally(unlead);
  return true;
}

/** The path through a strand's tail, and the caret on the segment holding the node pointed at:
 *  centred in the window, or with the token `hold.depth` from the root at `hold.top` px. */
async function visit({ tail, depth }, hold = null) {
  const line = await ask(`/path/${tail}?rule=none&hidden=${showHidden ? 1 : 0}`);
  let seen = 0;
  for (const cell of line.segments) {
    seen += cell.nodes.length;
    if (seen > depth) return reach(cell.nodes.at(-1).id, null, tail, hold);
  }
  return reach(tail, null, tail, hold);
}

/** How far down the map's axis an event is, in px, whether or not it is over the map. */
function alongOf(event) {
  const box = chartEl.getBoundingClientRect();
  return look.down ? event.clientY - box.top : event.clientX - box.left;
}

/** Whether an event is on the scale, the strip along the map's inner edge. */
const onScale = event => map.onScale(chartPoint(event));

/** A press on the column's own ground: the scale taken, or the thumb. */
export function pressed(event) {
  if (event.target !== $("column") || event.button !== 0) return;
  // The scale is taken and dragged: the zoom follows to the nearest step, the mark to the hand.
  if (look.on && chart !== null && onScale(event)) {
    dragged = true;
    scaleTo(alongOf(event));
    $("column").setPointerCapture(event.pointerId);
    event.preventDefault();
    return;
  }
  const into = onThumb(event);
  if (into === null) return;
  thumbed = into;
  dragged = false;
  $("column").setPointerCapture(event.pointerId);
  event.preventDefault();
}

/** Let go of the scale or the thumb, and say whether it was the thumb, which moved the window. */
export function lifted(event) {
  if (scaled !== null) {
    scaled = null;
    $("column").releasePointerCapture(event.pointerId);
    if (chart !== null) chartHandle();
    return false;
  }
  if (thumbed === null) return false;
  thumbed = null;
  $("column").releasePointerCapture(event.pointerId);
  return true;
}

/** The pointer moving over the column: the scale or the thumb in the hand, or what on the map it
 *  is over. */
export function pointed(event) {
  if (scaled !== null) {
    if (chart !== null) scaleTo(alongOf(event));
    return;
  }
  if (thumbed !== null) {
    const p = chartPoint(event);
    if (p !== null) { dragged = true; scrollAt(chart.x.invert(p.along) - thumbed); }
    return;
  }
  // Over the text, the segment says what it is over itself.
  if (event.target !== $("column")) { pointReed(null); return; }
  const p = chartPoint(event);
  pointReed(p === null ? null : map.reedAt(chart.plan, p.along, p.across, 5));
  const hit = onReed !== null ? null : chartHit(event);
  const head = hit?.head ?? null;
  const got = hit !== null && chart.path.has(head) ? cells() : null;
  hover(got === null ? null : map.holding(got.at, hit.depth));
  if (onReed !== null)
    tell(reedSays(map.where(chart.source, chart.tree, combing.reeds, onReed.head).reed));
  else tell(hit === null ? null : placeSays(head, hit.depth));
  $("column").classList.toggle("charting", head !== null || onReed !== null);
  $("column").classList.toggle("thumbing", head === null && event.target === $("column")
                                           && onThumb(event) !== null);
  $("column").classList.toggle("scaling", look.on && onScale(event));
  if (head === lit) return;
  for (const el of chartEl.querySelectorAll(".lit")) el.classList.remove("lit");
  lit = head;
  // Traced back to the root, so where it leaves the path and the shape it would take are seen.
  if (head !== null)
    for (const h of map.lineage(chart.tree, head))
      for (const el of chart.byHead.get(h) ?? []) el.classList.add("lit");
}

/** Point at `reed` on the map, or at none with null: each tooth is lit where it leaves the box,
 *  and where the reed is on the path, the column glows across its span. */
function pointReed(reed) {
  if ((reed?.head ?? null) === (onReed?.head ?? null)) return;
  onReed = reed;
  for (const i of glowing) cellsGlow(i, false);
  glowing = [];
  chart.teeth.replaceChildren();
  for (const el of chartEl.querySelectorAll(".reed.lit")) el.classList.remove("lit");
  if (reed === null) return;
  chart.els.get(`r${reed.head}`)?.classList.add("lit");
  for (const t of reed.teeth)
    chart.teeth.append(svg("line", lineAt(t.x, t.y, t.x + TOOTH, t.y), "tooth"));
  const got = chart.path.has(reed.head) ? cells() : null;
  if (got === null) return;
  const last = map.holding(got.at, reed.to - 1);
  for (let i = map.holding(got.at, reed.from - 1); i <= last; i++) glowing.push(i);
  for (const i of glowing) cellsGlow(i, true);
}

/** The pointer left: no reed is pointed at. */
export function offReed() {
  if (chart !== null) pointReed(null);
}

/** Glow the path's cell `i` as pointed at, or stop. */
function cellsGlow(i, on) {
  $("column").querySelectorAll(".flow .seg")[i]?.classList.toggle("over", on || i === pointedAt);
}

/** A rung of the cut as the bar names it. */
const rungName = c =>
  c.fold === Infinity ? "fold all" : c.fold ? `fold ≤${c.fold}`
  : !c.stubs ? "uncut" : c.under ? `≤${c.under}` : "stubs";

/** The bar under the map: which way it is drawn, the cut, and what the cut does, and zoomed
 *  in, how many strands are drawn in each zone from the thumb out. */
function chartSays(effect, zones, combed = null) {
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
    ...reedDial(button),
    button("lens", "zoomed, give the thumb more of the axis; off, zoom cuts alone", look.lens,
           () => {
             look.lens = !look.lens;
             zoomed = Math.min(zoomed, zoomMost());
             sketch({ pace: STRIDE });
           }),
    Object.assign(document.createElement("span"), {
      className: "says",
      textContent: (zones ? `${zones.join(" · ")} near to far · ` : "")
        + `${effect.kept} of ${effect.of} strands · ${Math.round(effect.share * 100)}% cut`
        + (combed ? ` · ${combed.places} places of ${combed.forks} forks` : ""),
      title: zones ? "strands drawn in each zone, from the thumb out" : "",
    }),
  );
}

/** The dial that combs forks close together into reeds, as the bar shows it: less, how close,
 *  and more. */
function reedDial(button) {
  const steps = map.reedSteps(charted === null ? 1 : map.most(charted.tree));
  look.reed = Math.min(look.reed, steps.length - 1);
  const turn = by => () => {
    look.reed = Math.min(steps.length - 1, Math.max(0, look.reed + by));
    sketch({ pace: STRIDE });
  };
  const less = button("−", "comb less: more forks drawn where they are", false, turn(-1));
  const more = button("+", "comb more: forks further apart drawn as one reed", false, turn(1));
  less.disabled = look.reed === 0;
  more.disabled = look.reed === steps.length - 1;
  return [less, Object.assign(document.createElement("span"), {
    className: "rung",
    textContent: !look.reed ? "uncombed" : look.reed === steps.length - 1 ? "reed all"
      : `reed ≤${steps[look.reed]}`,
    title: "how close forks are, in tokens, to be combed into one reed",
  }), more];
}

/** Draw the map, or take it away. */
export function mapped(on) {
  look.on = on;
  document.body.classList.toggle("unmapped", !look.on);
}

/** Whether a map is drawn to take a gesture. */
export const live = () => look.on && chart !== null;

/** The window moved: the thumb follows it, and zoomed in, so does the cut. */
export function followed() {
  chartThumb();
  refocus();
}

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
    const jumped = carrying() || chartEl.classList.contains("moving");
    const bent = look.lens && span
      && (span[0] !== chart.lensAt?.[0] || span[1] !== chart.lensAt?.[1]);
    if (!map.same(hairs, chart.hairs) || (jumped && bent)) {
      sketch(jumped ? {} : { glides: false });
      foreshadow();
      return;
    }
    if (!span) return;
    if (bent) { restretch(span); foreshadow(); }
    chartSays(map.effect(tree, hairs), map.zoneCounts(tree, hairs, { span, most }), chart.combed);
  });
}

/** Zoom by `n` steps, in where it is positive, gliding to the cut that makes. */
function zoomBy(n) {
  const to = Math.min(zoomMost(), Math.max(0, zoomed + n));
  if (to === zoomed) return;
  zoomed = to;
  sketch({ pace: STRIDE });
  foreshadow();
}

/** Where the caret stands `depth` tokens from the root on the strand `head` as it is drawn now,
 *  or null where that strand has no row. */
function ledAt(head, depth) {
  const s = chart?.plan.strands.find(s => s.head === head);
  if (!s) return null;
  return chart.line(...map.upright(chart.x(depth + 0.5), s.y, chart.step));
}

/** Send the caret at once to the node `depth` tokens from the root on the strand `head`, as
 *  it is drawn now, so it leads the drawing there, leaving a shadow where it was. */
export function lead(head, depth) {
  const to = ledAt(head, depth);
  if (to === null) return;
  if (chart.caret.style.display !== "none" && chart.caret.hasAttribute("x1")) shade();
  led = to;
  const els = [chart.caret, chart.sweep], from = {};
  for (const k of Object.keys(to))
    from[k] = els[0].hasAttribute(k) ? Number(els[0].getAttribute(k)) : to[k];
  swept = map.side(from, to, look.down, swept);
  for (const el of els) el.style.display = "";
  const t0 = performance.now();
  const frame = now => {
    if (led !== to || !els[0].isConnected) return;
    const e = map.ease(Math.min(1, (now - t0) / LEAD));
    for (const el of els)
      for (const k of Object.keys(to)) el.setAttribute(k, from[k] + (to[k] - from[k]) * e);
    if (e < 1) requestAnimationFrame(frame);
  };
  requestAnimationFrame(frame);
}

/** A shadow of the caret where it stands, which dims and goes, and goes with the drawing. */
function shade() {
  const el = svg("line", { "data-t0": performance.now() }, "shade");
  for (const k of ["x1", "y1", "x2", "y2"]) el.setAttribute(k, chart.caret.getAttribute(k));
  chartEl.append(el);
  el.addEventListener("animationend", () => el.remove(), { once: true });
}

/** Whether the drawing is still moving with the caret further out from the thumb's row than a
 *  step across may take it. */
function stretched() {
  if (!chartEl.classList.contains("moving")) return false;
  const [a, b] = look.down ? ["x1", "x2"] : ["y1", "y2"];
  const across = (Number(chart.caret.getAttribute(a)) + Number(chart.caret.getAttribute(b))) / 2;
  return map.far(across, chart.thumbY, chart.step);
}

/** A step across taken while the drawing still moves glides faster than the last, and one
 *  taken from rest at the usual pace. */
function hurry() {
  const now = performance.now();
  rush = map.hurried(now, rush);
  cool = { t0: now, until: rush.until };
  cooling();
}

/** Let the caret go back to the path, where an arrival ended without drawing it there. */
export function unlead() {
  if (led === null) return;
  led = null;
  chartCaret();
}

/** Step to the branch next over, `by` 1 down the depth-first order or -1 up it, at the depth the
 *  reader last put the caret at, with the window holding the stretch of the path it held. A
 *  step taken before the last has landed steps on from where that was going, so a run of them
 *  is counted and lands once, on the last. `paced` drops a step while one is on its way and the
 *  caret is far out from the thumb, which is what keeps a spun wheel from running away. */
export function scanBy(by, { paced = false } = {}) {
  if (!look.on || chart === null) return;
  if (paced && (scanning || stretched())) return;
  let run = aiming;
  if (run === null) {
    const got = cells();
    if (got === null) return;
    run = map.aim({
      ends: got.at.at(-1),
      span: chart.span,
      caret: pathIds().indexOf(cursor.node()),
      kept: scanAt?.node === cursor.node() ? scanAt : null,
      y: window.scrollY,
      edge: depth => got.segs[map.holding(got.at, depth)].getBoundingClientRect().top,
    });
  }
  const to = map.scan(chart.tree, chart.hairs, run.to?.head ?? [...chart.path].at(-1), by, run);
  if (to === null) { say(by > 0 ? "no branch further over" : "no branch further back"); return; }
  aiming = { ...run, to };
  holdTall();
  lead(to.head, map.aimedAt(aiming));
  hurry();
  if (!scanning) goAcross().catch(wrong);
}

/** Keep the column at the height it has, so a shorter branch stepped onto does not shorten the
 *  page under the window holding its place. */
function holdTall() {
  if (heldTall) return;
  heldTall = true;
  $("column").style.minHeight = getComputedStyle($("column")).height;
}

/** Let the column take its own height again. The text stands at its foot, so what that takes
 *  off comes off the top, and the window moves up by as much to stay on the same text. */
export function unheld() {
  if (!heldTall) return;
  heldTall = false;
  const was = $("column").offsetHeight;
  $("column").style.minHeight = "";
  const less = was - $("column").offsetHeight;
  if (less <= 0) return;
  carry();
  window.scrollBy(0, -less);
}

/** Arrive where a run of steps across is going, and again wherever it went on to meanwhile. */
async function goAcross() {
  scanning = true;
  try {
    while (aiming !== null && aiming.to.head !== [...chart.path].at(-1)) {
      const run = aiming;
      await visit({ tail: run.to.tail, depth: map.aimedAt(run) }, run.hold);
      const { from, until, hold } = run;
      scanAt = { node: cursor.node(), depth: run.depth, y: window.scrollY,
                 run: { from, until, hold } };
    }
  } finally {
    scanning = false;
    aiming = null;
    unlead();
  }
}

/** Shift and the wheel: zoom the map, or with Ctrl, scan across it. A notch is a step, and a
 *  fine wheel's movement adds up to one. */
export function wheel(event) {
  const d = event.deltaY || event.deltaX;
  const coarse = event.deltaMode !== 0;
  if (event.ctrlKey) {
    const got = map.notch(scanned, d, coarse);
    scanned = got.acc;
    if (got.n !== 0) scanBy(Math.sign(got.n), { paced: true });
    return;
  }
  const got = map.notch(wheeled, d, coarse);
  wheeled = got.acc;
  if (got.n !== 0) zoomBy(-got.n);
}
