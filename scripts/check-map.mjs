/* Drive the map's arithmetic.  `node scripts/check-map.mjs`
 *
 * A packing that lets two strands overlap, or puts a branch the model liked better below the
 * row it left, draws a map that looks like a map and says the wrong thing. So the checks are
 * the layout's own promises, held over trees built at random as well as one built by hand.
 */

const m = await import(new URL("../src/tokenloom/surface/page/assets/map.js", import.meta.url));

let bad = 0;
const is = (what, got, want) => {
  const ok = JSON.stringify(got) === JSON.stringify(want);
  if (!ok) bad++;
  console.log(`${ok ? "ok  " : "FAIL"} ${what}: ${JSON.stringify(got)}` +
              (ok ? "" : ` != ${JSON.stringify(want)}`));
};

/** Strands as `/map` sends them, from `[head, up, length, logprob, stub?]` with depth,
 *  weight and leaf derived, so a tree can be written down by its shape alone. */
function strands(spec) {
  const out = spec.map(([head, up, length, logprob, stub = false]) =>
    ({ head, tail: head + length - 1, up, depth: 0, length, weight: length,
       logprob, leaf: true, stub, aside: null }));
  const by = new Map(out.map(s => [s.head, s]));
  for (const s of out) if (s.up !== null) {
    const up = by.get(s.up);
    s.depth = up.depth + up.length;
    up.leaf = false;
  }
  for (const s of [...out].reverse()) if (s.up !== null) by.get(s.up).weight += s.weight;
  return out;
}

// ---- by hand ------------------------------------------------------------------------------

//   1 (10) --+-- 20 (30, rank -0.5)  the heaviest, so it continues
//            +-- 60 (8, rank -0.1)   ranked higher: above
//            +-- 80 (5, rank -2.0)   ranked lower: below
//            +-- 90 (3, rank -0.2, stub)  hair
const hand = m.index(strands([[1, null, 10, null], [20, 1, 30, -0.5], [60, 1, 8, -0.1],
                              [80, 1, 5, -2.0], [90, 1, 3, -0.2, true]]));
const none = new Set();
const cut = { stubs: true, under: 2 };
const x = m.scale({ most: 40, width: 440, pad: 20 });

is("the heaviest continues where no path runs", m.continuing(hand.kids.get(1), none).head, 20);
is("  and the path's child where one does",
   m.continuing(hand.kids.get(1), m.along(hand, [1, 2, 80, 81])).head, 80);
const hairs = m.hair(hand, cut, none);
is("hair is a stub or a short leaf that is not continuing", [...hairs], [90]);
is("  and the path's child is never hair",
   [...m.hair(hand, { stubs: true, under: 99 }, m.along(hand, [1, 90]))].sort(), [20, 60, 80]);
is("what a cut does is said as strands kept and tokens set aside",
   m.effect(hand, hairs), { kept: 4, of: 5, share: 3 / 56 });
const rows = m.layout(hand, { x, hairs, path: none });
is("higher above, lower below, and the continuing child on the row",
   [1, 20, 60, 80].map(h => rows.get(h)), [0, 0, -1, 1]);
is("  and hair holds no row", rows.has(90), false);
const onPath = m.along(hand, [1, 2, 80]);
const turned = m.layout(hand, { x, hairs: m.hair(hand, cut, onPath), path: onPath });
is("the path is the straight row, and the rest are ranked against it",
   [1, 80, 20, 60].map(h => turned.get(h)), [0, 0, -1, -2]);

is("x runs from the pad to the width less it", [x(0), x(40)], [20, 420]);
is("  and inverts", x.invert(x(17)), 17);

const drawn = m.plan(hand, rows, { x, hairs, path: none, step: 10 });
is("a link from the fork's row to each strand off it",
   drawn.links.map(l => [l.head, l.y0, l.y1]), [[60, 10, 0], [80, 10, 20]]);
is("hair ticks off its fork on the side its rank puts it",
   drawn.hairs.map(h => [h.head, h.x0, h.y1 < h.y0]), [[90, x(10), true]]);
is("a fan where three or more leave one fork", drawn.fans.map(k => [k.head, k.n]), [[1, 4]]);
is("a point on a strand is the node under it, from the root",
   m.hit(hand, drawn, x, x(25.5), 11, 4), { head: 20, tail: 49, depth: 25 });
is("  clamped to the strand's own nodes",
   m.hit(hand, drawn, x, x(0) - 2, 10, 4), { head: 1, tail: 10, depth: 0 });
is("  and a point near nothing is nothing", m.hit(hand, drawn, x, x(30), 35, 4), null);

// A limb: 60 leaves the root's fork and forks again, its heaviest line through 62.
//   1 (10) --+-- 20 (100, rank -0.5)
//            +-- 60 (8, rank -0.1) --+-- 61 (5, rank -1.0)
//                                    +-- 62 (40, rank -0.2)
const limb = m.index(strands([[1, null, 10, null], [20, 1, 100, -0.5], [60, 1, 8, -0.1],
                              [61, 60, 5, -1.0], [62, 60, 40, -0.2]]));
is("a subtree ends where its deepest strand does", m.most(limb), 110);
is("  and its heaviest line runs down the heaviest child", limb.lines.get(60).head, 62);
const foldAt = cut => [...m.hair(limb, { stubs: true, under: 4, fold: cut }, none)];
is("a strand that is not a leaf folds where it holds no more than the rung says",
   [foldAt(52), foldAt(53)], [[], [60]]);
const folded = m.hair(limb, { stubs: true, under: 4, fold: 256 }, none);
is("  and everything below a fold is undrawn with it", [...m.undrawn(limb, folded)], [60, 61, 62]);
is("  which is what the cut is said in", m.effect(limb, folded), { kept: 2, of: 5, share: 53 / 163 });
is("  and the path is never folded",
   [...m.hair(limb, { stubs: true, under: 64, fold: Infinity }, m.along(limb, [1, 60, 61]))], [62]);
const lx = m.scale({ most: m.most(limb), width: 240, pad: 20 });
const limbRows = m.layout(limb, { x: lx, hairs: folded, path: none });
is("a fold holds no row, nor does anything below it", [...limbRows.keys()].sort(), [1, 20]);
const limbDrawn = m.plan(limb, limbRows, { x: lx, hairs: folded, path: none, step: 10 });
is("a fold ticks off its fork as far as what it holds reaches",
   limbDrawn.hairs.map(h => [h.head, h.fold, h.x0, h.x1, h.weight]), [[60, true, lx(10), lx(58), 53]]);
const tick = limbDrawn.hairs[0];
is("a point on a fold goes down its heaviest line",
   m.hit(limb, limbDrawn, lx, lx(30.5), tick.y0 + (tick.y1 - tick.y0) * (20.5 / 48), 3),
   { head: 60, tail: 101, depth: 30 });
is("a fold is drawn heavier the more it holds",
   [m.heft(0), m.heft(256) < m.heft(1024), m.heft(1e9)], [1, true, 5]);
is("the ladder runs from nothing cut to everything folded",
   [m.LADDER[0], m.LADDER.at(-1).fold === Infinity], [{ stubs: false, under: 0, fold: 0 }, true]);

let seed = 7;
const rand = () => (seed = (seed * 1103515245 + 12345) % 2 ** 31) / 2 ** 31;

// ---- zoom --------------------------------------------------------------------------------

is("a strand over the focus or within the focal distance of it is in the first zone",
   [m.zone([105, 106], [100, 110], 10), m.zone([111, 120], [100, 110], 10)], [0, 0]);
is("  one ring further is in the second, and past them all in the last",
   [m.zone([140, 150], [100, 110], 10), m.zone([0, 1], [100, 110], 10)], [1, 2]);
is("no step leaves every zone on the base", [0, 1, 2].map(i => m.rungAt(4, 0, i)), [4, 4, 4]);
is("  a step takes the focus finer and the far zone coarser",
   [0, 1, 2].map(i => m.rungAt(4, 1, i)), [3, 4, 5]);
is("  and none goes off the ladder",
   [m.rungAt(0, 3, 0), m.rungAt(8, 3, 2)], [0, m.LADDER.length - 1]);
let unmirrored = 0, nearer = 0;
for (let t = 0; t < 400; t++) {
  const a = rand() * 500, b = a + rand() * 100, w = rand() * 50, f = 1 + rand() * 30;
  const g = rand() * 200, h = g + rand() * 200;
  if (m.zone([a - g - w, a - g], [a, b], f) !== m.zone([b + g, b + g + w], [a, b], f)) unmirrored++;
  if (m.zone([b + h, b + h + w], [a, b], f) < m.zone([b + g, b + g + w], [a, b], f)) nearer++;
}
is("zones are mirrored either side of the focus", unmirrored, 0);
is("  and further is never in a nearer one", nearer, 0);
let pastDeepest = 0;
for (let base = 0; base < m.LADDER.length; base++) {
  const d = m.deepest(base);
  for (let i = 0; i < m.ZONES.n; i++) if (m.rungAt(base, d + 1, i) !== m.rungAt(base, d, i))
    pastDeepest++;
}
is("past the deepest step nothing changes", pastDeepest, 0);

is("the axis is the whole tree unzoomed", m.axis(limb, 0, 30), 110);
is("  and zoomed, ends where the path does", m.axis(limb, 1, 30), 30);
// On the rung that folds 60 unzoomed, a step leaves it drawn near the thumb and folded far off.
const folds60 = (span, byFork) => m.hair(limb, m.zoned(limb,
  { base: 7, steps: 1, span, most: 110, byFork }), none).has(60);
is("zoomed in, a subtree far from the thumb folds, and near it is drawn",
   [folds60([100, 110]), folds60([20, 30])], [true, false]);
is("  near by its nearest point, and by its fork behind the switch",
   [folds60([50, 58], false), folds60([50, 58], true)], [false, true]);
is("unzoomed, every strand is on the base",
   m.zoned(limb, { base: 3, steps: 0, span: [0, 5], most: 110 })(limb.byHead.get(60)), m.LADDER[3]);
const walled = m.hair(limb, m.LADDER[0], none, 15);
is("past the wall every strand is cut", [...walled].sort(), [61, 62]);
const wx = m.scale({ most: 15, width: 240, pad: 20 });
const wallDrawn = m.plan(limb, m.layout(limb, { x: wx, hairs: walled, path: none }),
                         { x: wx, hairs: walled, path: none, step: 10 });
is("  a strand running past it is clipped at the edge and says so",
   wallDrawn.strands.map(s => [s.head, s.x1, s.clipped]),
   [[1, wx(10), false], [20, wx(15), true], [60, wx(15), true]]);
is("  and nothing past it is drawn", wallDrawn.hairs.length, 0);
const counted = m.zoneCounts(limb, folded, { span: [100, 110], most: 110 });
is("each strand drawn is counted in the zone it stands in, and only those",
   [counted, counted.reduce((a, b) => a + b)], [[1, 0, 1], m.effect(limb, folded).kept]);
is("the same strands are the same cut", [m.same(new Set([1, 2]), new Set([2, 1])),
   m.same(new Set([1]), new Set([1, 2]))], [true, false]);

// ---- at random ----------------------------------------------------------------------------

function grown(n) {
  const spec = [[1, null, 1 + Math.floor(rand() * 20), null]];
  let head = 1000;
  for (let i = 1; i < n; i++) {
    const up = spec[Math.floor(rand() * spec.length)][0];
    const length = 1 + Math.floor(rand() ** 3 * 80);
    spec.push([head, up, length, rand() < 0.1 ? null : -rand() * 6, rand() < 0.3]);
    head += 1000;
  }
  return m.index(strands(spec));
}

let overlaps = 0, misranked = 0, misordered = 0, unplaced = 0, offPath = 0, unlinked = 0;
for (let t = 0; t < 40; t++) {
  const tree = grown(5 + Math.floor(rand() * 120));
  const tip = tree.strands[Math.floor(rand() * tree.strands.length)];
  const nodes = [];
  for (let s = tip; s; s = tree.byHead.get(s.up)) nodes.push(s.head);
  const path = m.along(tree, nodes);
  // Half of them zoomed about a thumb somewhere on the path, against the wall at its end.
  const steps = t % 2 ? 1 + Math.floor(rand() * 5) : 0;
  const end = tip.depth + tip.length;
  const most = m.axis(tree, steps, end);
  const from = rand() * end, span = [from, Math.min(end, from + 1 + rand() * 40)];
  const base = t % m.LADDER.length;
  const hairs = m.hair(tree, m.zoned(tree, { base, steps, span, most }), path,
                       steps ? most : Infinity);
  const gone = m.undrawn(tree, hairs);
  const x = m.scale({ most, width: 200 + 20 * t, pad: 10 });
  const rows = m.layout(tree, { x, hairs, path });
  for (const s of tree.strands) if (rows.has(s.head) === gone.has(s.head)) unplaced++;
  for (const h of path) if (rows.get(h) !== 0) offPath++;
  const byRow = new Map();
  for (const s of tree.strands) if (rows.has(s.head)) {
    const r = rows.get(s.head);
    if (!byRow.has(r)) byRow.set(r, []);
    byRow.get(r).push([x(s.depth), x(s.depth + s.length), s.head, s.up]);
  }
  // A strand continuing its parent's row touches it by being the row going on.
  for (const ivs of byRow.values()) {
    ivs.sort((a, b) => a[0] - b[0]);
    for (let i = 1; i < ivs.length; i++)
      if (ivs[i][3] !== ivs[i - 1][2] && ivs[i][0] < ivs[i - 1][1] + m.GAP - 1e-9) overlaps++;
  }
  for (const [up, all] of tree.kids) {
    if (!rows.has(up)) continue;
    const kids = all.filter(k => !hairs.has(k.head));
    const main = m.continuing(kids, path);
    if (main === null) continue;
    const r = s => s.logprob ?? -Infinity;
    if (rows.get(main.head) !== rows.get(up)) misranked++;
    for (const k of kids) if (k !== main &&
        (r(k) > r(main)) !== (rows.get(k.head) < rows.get(up))) misranked++;
    // Nearest rank nearest: on one side, a rank strictly nearer the continuing child's
    // stands strictly nearer its row. Ties, and ranks nothing recorded, are either way.
    const off = k => Math.abs(rows.get(k.head) - rows.get(up));
    for (const a of kids) for (const b of kids) {
      if (a === main || b === main || (r(a) > r(main)) !== (r(b) > r(main))) continue;
      if (Math.abs(r(a) - r(main)) < Math.abs(r(b) - r(main)) && off(a) >= off(b)) misordered++;
    }
  }
  const drawn = m.plan(tree, rows, { x, hairs, path, step: 5 });
  const linked = new Set(drawn.links.map(l => l.head));
  for (const s of tree.strands)
    if (rows.has(s.head) && s.up !== null && rows.get(s.head) !== rows.get(s.up) && !linked.has(s.head))
      unlinked++;
}
is("no two strands on one row come within the gap", overlaps, 0);
is("every kept strand is placed and nothing cut is", unplaced, 0);
is("the path holds row 0 throughout", offPath, 0);
is("above is ranked higher than what continues, and below lower", misranked, 0);
is("the nearest rank stands nearest", misordered, 0);
is("every strand off its fork's row is linked to it", unlinked, 0);

// The window: cells set as text sets them, several to a line and some across several, and
// what is in view read against every cell's box one at a time.
is("a path's offsets start at 0 and sum its cells", m.offsets([2, 1, 3]), [0, 2, 3, 6]);
let unseen = 0, misheld = 0;
for (let t = 0; t < 40; t++) {
  const counts = [], boxes = [];
  let line = 0;
  for (let i = 0, n = 1 + Math.floor(rand() * 60); i < n; i++) {
    counts.push(1 + Math.floor(rand() * 4));
    const lines = rand() < 0.1 ? 2 + Math.floor(rand() * 3) : 1;
    boxes.push({ top: line * 20, bottom: (line + lines) * 20 });
    line += lines - 1 + (rand() < 0.3 ? 1 : 0);
  }
  const at = m.offsets(counts);
  const lo = rand() * line * 20, hi = lo + rand() * 200;
  const inView = boxes.map((b, i) => [b, i]).filter(([b]) => b.bottom > lo && b.top < hi);
  const want = inView.length ? [at[inView[0][1]], at[inView.at(-1)[1] + 1]] : null;
  if (JSON.stringify(m.seen(at, i => boxes[i], lo, hi)) !== JSON.stringify(want)) unseen++;
  for (let d = 0; d <= at.at(-1) + 2; d++) {
    const i = m.holding(at, d);
    const ok = d >= at.at(-1) ? i === counts.length - 1 : at[i] <= d && d < at[i + 1];
    if (!ok) misheld++;
  }
}
is("the tokens in view are those of the cells the window crosses", unseen, 0);
is("each token is held by the cell it falls in, and past the end by the last", misheld, 0);

// Moving between two drawings.
is("a strand's lineage runs up to the root", m.lineage(hand, 20), [20, 1]);
is("  and the root's is itself", m.lineage(hand, 1), [1]);
const eased = Array.from({ length: 101 }, (_, i) => m.ease(i / 100));
is("easing starts at 0 and ends at 1", [eased[0], eased[100]], [0, 1]);
is("  never goes back", eased.every((v, i) => i === 0 || v >= eased[i - 1]), true);
is("  and is half way at half time, either side mirroring the other",
   eased.every((v, i) => Math.abs(v + eased[100 - i] - 1) < 1e-12), true);
// The trail, on a tree whose strands 20, 60 and 80 each hang from the root's.
const on = (...heads) => new Set(heads);
let walked = m.remember(hand, [], on(1, 20), 20);
is("the first path read starts the trail", walked, [{ head: 20 }]);
is("  and reading it again changes nothing", m.remember(hand, walked, on(1, 20), 20), walked);
walked = m.remember(hand, walked, on(1, 60), 60);
walked = m.remember(hand, walked, on(1, 80), 80);
is("each path taken goes on top", walked.map(e => e.head), [80, 60, 20]);
is("  and one taken again comes off where it stood",
   m.remember(hand, walked, on(1, 20), 20).map(e => e.head), [20, 80, 60]);
is("a path that only grew takes the place of the one it grew from",
   m.remember(hand, [{ head: 1 }], on(1, 20), 20), [{ head: 20 }]);
is("  and the trail stops at what it keeps",
   m.remember(hand, walked, on(1, 20), 20, 2).map(e => e.head), [20, 80]);
is("a strand off the path is as many paths back as it was last on one, the root never",
   [...m.steps(hand, walked, on(1, 80), 4)], [[60, 1], [20, 2]]);
is("  and only so many are counted", [...m.steps(hand, walked, on(1, 80), 1)], [[60, 1]]);
is("  and a path under another root counts for nothing",
   [...m.steps(hand, [{ head: 80 }, { head: 999 }, { head: 60 }], on(1, 80), 1)], [[60, 1]]);
const box = new Map();
const store = { getItem: k => box.get(k) ?? null, setItem: (k, v) => box.set(k, v) };
m.keep(store, "t", walked);
is("a trail kept is the trail recalled", m.recall(store, "t"), walked);
is("  and with no storage there is none, and nothing fails",
   [m.recall(null, "t"), m.keep(null, "t", walked)], [[], false]);
is("what moved is what is in both and differs, and what is new is said apart",
   m.shift(new Map([["a", { x: 1, y: 2 }], ["b", { x: 0 }], ["gone", { x: 9 }]]),
           new Map([["a", { x: 1, y: 5 }], ["b", { x: 0 }], ["c", { x: 3 }]])),
   { moved: [["a", [["y", 2, 5]]]], fresh: ["c"] });

process.exit(bad ? 1 : 0);
