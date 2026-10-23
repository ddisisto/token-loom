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

is("depth-first, a fork's children ranked higher first",
   limb.order.map(s => s.head), [1, 60, 62, 61, 20]);
const unranked = m.index(strands([[1, null, 5, null], [10, 1, 5, null], [20, 1, 5, -3],
                                  [30, 1, 5, null]]));
is("  and nothing ranked last, in the order it came", unranked.order.map(s => s.head),
   [1, 20, 10, 30]);
const scanFrom = (head, by, hairs = none, from = 0, until = Infinity) =>
  m.scan(limb, hairs, head, by, { from, until })?.head ?? null;
is("a strand leaves a path where the first strand above it off the path starts",
   [m.parts(limb, 61, new Set([1, 60, 62])), m.parts(limb, 61, new Set([1, 20])),
    m.parts(limb, 60, new Set([1, 60]))], [18, 10, null]);
is("a scan steps to the next leaf over, either way",
   [scanFrom(62, 1), scanFrom(61, 1), scanFrom(61, -1)], [61, 20, 62]);
is("  and stops past either end", [scanFrom(20, 1), scanFrom(62, -1)], [null, null]);
is("  from a strand that is not a leaf, to the leaves either side of where it stands",
   [scanFrom(60, 1), scanFrom(60, -1)], [62, null]);
is("  passing a leaf that ends short of the focus", scanFrom(62, 1, none, 60), 20);
is("  and one with no row of its own", scanFrom(62, 1, new Set([61])), 20);
is("  and one leaving the path below the window, which reads the same in it",
   [scanFrom(62, 1, none, 0, 17), scanFrom(62, 1, none, 0, 18)], [20, 61]);

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

// On the rung that folds 60 unzoomed, a step leaves it drawn near the thumb and folded far off.
const folds60 = (span, byFork) => m.hair(limb, m.zoned(limb,
  { base: 7, steps: 1, span, most: 110, byFork }), none).has(60);
is("zoomed in, a subtree far from the thumb folds, and near it is drawn",
   [folds60([100, 110]), folds60([20, 30])], [true, false]);
is("  near by its nearest point, and by its fork behind the switch",
   [folds60([50, 58], false), folds60([50, 58], true)], [false, true]);
is("unzoomed, every strand is on the base",
   m.zoned(limb, { base: 3, steps: 0, span: [0, 5], most: 110 })(limb.byHead.get(60)), m.LADDER[3]);
const counted = m.zoneCounts(limb, folded, { span: [100, 110], most: 110 });
is("each strand drawn is counted in the zone it stands in, and only those",
   [counted, counted.reduce((a, b) => a + b)], [[1, 0, 1], m.effect(limb, folded).kept]);
// The fisheye.
let unbanded = 0, misbanded = 0;
for (let t = 0; t < 200; t++) {
  const most = 50 + rand() * 1000, a = rand() * most, b = Math.min(most, a + rand() * 60);
  const f = 1 + rand() * 40, runs = m.bands([a, b], f, most);
  if (runs[0][0] !== 0 || runs.at(-1)[1] !== most) unbanded++;
  for (let j = 1; j < runs.length; j++) if (runs[j][0] !== runs[j - 1][1]) unbanded++;
  for (const [from, to, i] of runs) {
    const mid = (from + to) / 2;
    if (m.zone([mid, mid], [a, b], f) !== i) misbanded++;
  }
}
is("the zones' runs cover the axis end to end with nothing between them", unbanded, 0);
is("  and each is the zone its tokens stand in", misbanded, 0);
const flat = m.fisheye({ span: [40, 60], most: 200, steps: 0 });
is("unzoomed, the fisheye is the straight share", [flat(0), flat(50), flat(200)], [0, 0.25, 1]);
let falling = 0, unread = 0, unmagnified = 0, ungiven = 0;
for (let t = 0; t < 200; t++) {
  const most = 100 + rand() * 2000, a = rand() * most * 0.9, b = Math.min(most, a + 1 + rand() * 40);
  const steps = 1 + Math.floor(rand() * 6), lens = m.fisheye({ span: [a, b], most, steps });
  let was = -1;
  for (let i = 0; i <= 200; i++) {
    const v = most * i / 200, u = lens(v);
    if (u < was - 1e-12) falling++;
    was = u;
    if (Math.abs(lens.invert(u) - v) > 1e-6 * most) unread++;
  }
  if (lens(b) - lens(a) <= (b - a) / most) unmagnified++;
  // The same thumb against the root's wall has more of the axis than it has well clear of it.
  const w = b - a, mid = m.fisheye({ span: [most / 2, most / 2 + w], most, steps });
  const wall = m.fisheye({ span: [0, w], most, steps });
  if (wall(w) - wall(0) <= mid(most / 2 + w) - mid(most / 2)) ungiven++;
}
is("the fisheye only rises", falling, 0);
is("  reads back what it was given", unread, 0);
is("  gives the thumb more of the axis than its tokens' share", unmagnified, 0);
is("  and against a wall, more again", ungiven, 0);
const lx2 = m.scale({ most: 200, width: 440, pad: 20,
                      lens: m.fisheye({ span: [40, 60], most: 200, steps: 2 }) });
is("a scale through the fisheye still runs from pad to pad", [lx2(0), lx2(200)], [20, 420]);
is("  and inverts", Math.round(lx2.invert(lx2(57)) * 1e9) / 1e9, 57);
const sx = m.scale({ most: 1000, width: 440, pad: 20 });
const straight = m.ticks(sx, 1000), majors = straight.filter(([, big]) => big).map(([v]) => v);
is("ticks start at the root, a round step apart, as far as the tree",
   [majors[0], majors[1] - majors[0], majors.at(-1)], [0, 100, 1000]);
is("  given their room on a straight axis", sx(majors[1]) - sx(majors[0]) >= 24, true);
const lensed = m.ticks(lx2, 200);
const bigAt = lensed.filter(([, big]) => big).map(([v]) => v);
const fineAt = lensed.filter(([, big]) => !big).map(([v]) => v);
const major = bigAt[1] - bigAt[0], minor = fineAt[0] % major;
const under = v => Math.floor(v / major) * major;  // the major tick a fine one follows
is("  and finer ones only where the fisheye spreads them a third of the room apart",
   [fineAt.length > 0, fineAt.every(v => lx2(under(v) + minor) - lx2(under(v)) >= 8),
    new Set(fineAt.map(under)).size < bigAt.length], [true, true, true]);
is("the same strands are the same cut", [m.same(new Set([1, 2]), new Set([2, 1])),
   m.same(new Set([1]), new Set([1, 2]))], [true, false]);

// A row with forks at 10, 12 and 14 and then not until 34.
//   1 (10) -+- 2 (2, -0.3) -+- 3 (2, -0.5) -+- 4 (20, -0.2) -+- 5 (10)
//           +- 50 (5, -1)   +- 60 (5, -0.1)  +- 70 (5, -3)    +- 80 (5, -1)
const row = m.index(strands([[1, null, 10, null], [2, 1, 2, -0.3], [50, 1, 5, -1],
                             [3, 2, 2, -0.5], [60, 2, 5, -0.1], [4, 3, 20, -0.2], [70, 3, 5, -3],
                             [5, 4, 10, -0.1], [80, 4, 5, -1]]));
const combed = m.reeds(row, none, { range: 4, cap: 16 });
const reeded = m.comb(row, combed.reeds);
is("forks within range of the last along a row are one reed, and one further off is not",
   combed.reeds.map(({ head, from, to }) => [head, from, to]), [[1, 10, 14]]);
is("  and four forks are two places", [combed.forks, combed.places], [4, 2]);
is("what runs between its forks is passage",
   [2, 3, 4].map(h => !!reeded.byHead.get(h).passage), [true, true, false]);
is("every way out of it is a tooth of its top's", [50, 60, 4, 70].map(h => reeded.byHead.get(h).up),
   [1, 1, 1, 1]);
is("  the row's own going straight on, and the rest out from it by rank against the row where each left",
   [60, 4, 50, 70].map(h => reeded.byHead.get(h).slot), [-1, 0, 1, 2]);
const leaving = m.along(row, [1, 2, 60]), through = m.along(row, [1, 2, 3, 4, 5]);
const viaSixty = m.layout(reeded, { x, hairs: none, path: leaving });
const viaFour = m.layout(reeded, { x, hairs: none, path: through });
is("  each on its own row in slot order",
   [60, 4, 50, 70].map(h => viaFour.get(h)), [-1, 0, 1, 2]);
is("  and with the path through another, that one straight on and the rest moved with it",
   [60, 4, 50, 70].map(h => viaSixty.get(h)), [0, 1, 2, 3]);
is("  and a scan walks them in that order",
   reeded.order.filter(s => s.leaf).map(s => s.head), [60, 5, 80, 50, 70]);
is("the drawing is held by the reed at the window, by its tooth in slot 0",
   [m.anchor(reeded, through, 20).head, m.anchor(reeded, leaving, 20).head, m.anchor(reeded, through, 5).head],
   [4, 4, 1]);
{
  // Held by that tooth across a step from 4 to 60, every tooth stands where it stood.
  const fitOf = (rows, zero) => {
    const all = [...rows.values()];
    return { ...m.fit(Math.min(...all), Math.max(...all), 300, true, 0, zero), lo: Math.min(...all) };
  };
  const before = fitOf(viaFour, null), zero = before.top - before.lo * before.step;
  const after = fitOf(viaSixty, zero + (viaFour.get(4) - viaSixty.get(4)) * before.step);
  const zeroAfter = after.top - after.lo * after.step;
  is("  so a step across leaves every tooth where it stood, and moves what is above",
     [[60, 4, 50, 70].map(h => zero + viaFour.get(h) * before.step),
      zeroAfter + viaSixty.get(1) * after.step !== zero + viaFour.get(1) * before.step],
     [[60, 4, 50, 70].map(h => zeroAfter + viaSixty.get(h) * after.step), true]);
}
const reededPlan = m.plan(reeded, viaFour, { x, hairs: none, path: through, step: 10 });
const reedBox = reededPlan.reeds[0];
const yOf = h => reededPlan.strands.find(s => s.head === h).y;
is("it is drawn as a rail at its top, across its teeth's rows, read along its span",
   [reedBox.x0, reedBox.x1, reedBox.y0, reedBox.y1], [x(10), x(14), yOf(60), yOf(70)]);
is("  its teeth each drawn from it as the whole route",
   [50, 60, 4, 70].map(h => reededPlan.strands.find(s => s.head === h).x0), [x(10), x(10), x(10), x(10)]);
is("  with no links", reededPlan.links.filter(l => reeded.byHead.get(l.head).up === 1), []);
is("  and a point on the rail is the reed", m.reedAt(reededPlan, x(10) + 2, (reedBox.y0 + reedBox.y1) / 2, 3)?.head, 1);
is("  and one along a tooth is not", m.reedAt(reededPlan, x(13), reedBox.y0, 3), null);
is("the path stands on its tooth from the reed's top on, and on the strand above it before",
   [9, 11, 16].map(d => m.holds(reeded, leaving, d).head), [1, 60, 60]);
is("  and a point on a tooth before it really left is a token on its route",
   m.hit(reeded, reededPlan, x, x(11.5), yOf(60), 2), { head: 60, tail: 64, depth: 11 });
const widest = m.reedSteps(m.most(row));
is("the dial runs doubling from nothing to the whole tree", widest, [0, 2, 4, 8, 16, 32, 44]);
const all = m.reeds(row, none, m.combAt(widest, widest.length - 1));
is("  and at its widest a root is one reed, every leaf a tooth",
   [all.reeds.length, all.places, m.comb(row, all.reeds).kids.get(1).filter(k => k.leaf).length],
   [1, 1, row.strands.filter(s => s.leaf).length]);
is("a cap parts a ladder", m.reeds(row, none, { range: 4, cap: 3 }).reeds
   .map(({ head, from, to }) => [head, from, to]), [[1, 10, 12]]);
is("no range combs nothing, and the tree is the one given",
   m.comb(row, m.reeds(row, none, { range: 0 }).reeds) === row, true);
// 70 leaves the reed at 14 and forks again at 16, within range: the same reed.
const below = m.index(strands([[1, null, 10, null], [2, 1, 2, -0.3], [50, 1, 5, -1],
                               [3, 2, 2, -0.5], [60, 2, 5, -0.1], [4, 3, 20, -0.2], [70, 3, 2, -3],
                               [71, 70, 9, -0.1], [72, 70, 5, -2]]));
const absorbed = m.reeds(below, none, { range: 4, cap: 16 });
is("a branch forking again close below a reed is the same reed",
   absorbed.reeds.map(({ head, from, to }) => [head, from, to]), [[1, 10, 16]]);
is("  and what leaves it there is a tooth of its top's",
   [71, 72].map(h => m.comb(below, absorbed.reeds).byHead.get(h).up), [1, 1]);

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
let overspun = 0, unmoved = 0, uncounted = 0, overboxed = 0, unslotted = 0, unedged = 0;
for (let t = 0; t < 80; t++) {
  const source = grown(5 + Math.floor(rand() * 120));
  const tip = source.strands[Math.floor(rand() * source.strands.length)];
  const nodes = [];
  for (let s = tip; s; s = source.byHead.get(s.up)) nodes.push(s.head);
  const path = m.along(source, nodes);
  // Half of them zoomed about a thumb somewhere on the path.
  const steps = t % 2 ? 1 + Math.floor(rand() * 5) : 0;
  const end = tip.depth + tip.length;
  const most = m.most(source);
  const from = rand() * end, span = [from, Math.min(end, from + 1 + rand() * 40)];
  const base = t % m.LADDER.length;
  const hairs = m.hair(source, m.zoned(source, { base, steps, span, most }), path);
  // Every other tree combed, and the layout's promises held over that as well.
  const dial = t % 4 < 2 ? { range: 0 } : { range: 1 + Math.floor(rand() * 8), cap: 2 + Math.floor(rand() * 30) };
  const { reeds, forks, places } = m.reeds(source, hairs, dial);
  const tree = m.comb(source, reeds);
  for (const r of reeds) if (r.to - r.from > dial.cap || r.to <= r.from) overspun++;
  for (const s of tree.strands) {
    const was = source.byHead.get(s.head);
    if (s.up !== was.up && (s.depth !== was.depth || !m.lineage(source, was.up).includes(s.up)
                            || s.against === undefined)) unmoved++;
  }
  if (dial.range === 0 ? tree !== source || forks !== 0
      : places !== forks - reeds.reduce((n, r) => n + r.at.size, 0)) uncounted++;
  const gone = m.undrawn(tree, hairs);
  const x = m.scale({ most, width: 200 + 20 * t, pad: 10 });
  const rows = m.layout(tree, { x, hairs, path });
  // What runs between a reed's forks is the reed, and has no row.
  for (const s of tree.strands) if (rows.has(s.head) === (gone.has(s.head) || !!s.passage)) unplaced++;
  for (const h of path) if (!tree.byHead.get(h).passage && rows.get(h) !== 0) offPath++;
  // A reed's teeth stand in slot order, whichever of them the path takes.
  for (const [up, kids] of tree.kids) {
    if (!tree.byHead.get(up).reed) continue;
    const placed = kids.filter(k => rows.has(k.head)).sort((a, b) => rows.get(a.head) - rows.get(b.head));
    for (let i = 1; i < placed.length; i++) if (placed[i - 1].slot >= placed[i].slot) unslotted++;
  }
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
    const kids = all.filter(k => !hairs.has(k.head) && !k.passage);
    // A reed's teeth stand in slot order, which is checked on its own below.
    if (tree.byHead.get(up).reed) continue;
    const main = m.continuing(kids, path);
    if (main === null) continue;
    const r = s => s.logprob ?? -Infinity;
    // A tooth is ranked against what continued the row where it left.
    const vs = k => k.against ?? r(main);
    if (rows.get(main.head) !== rows.get(up)) misranked++;
    for (const k of kids) if (k !== main &&
        (r(k) > vs(k)) !== (rows.get(k.head) < rows.get(up))) misranked++;
    // Nearest rank nearest: on one side, among those leaving at one place, a rank strictly
    // nearer the continuing child's stands strictly nearer its row. Ties, and ranks nothing
    // recorded, are either way.
    const off = k => Math.abs(rows.get(k.head) - rows.get(up));
    for (const a of kids) for (const b of kids) {
      if (a === main || b === main || a.depth !== b.depth || a.against !== undefined
          || b.against !== undefined || (r(a) > r(main)) !== (r(b) > r(main))) continue;
      if (Math.abs(r(a) - r(main)) < Math.abs(r(b) - r(main)) && off(a) >= off(b)) misordered++;
    }
  }
  const drawn = m.plan(tree, rows, { x, hairs, path, step: 5 });
  for (const a of drawn.reeds) for (const b of drawn.reeds)
    if (a !== b && a.x0 <= b.x1 && b.x0 <= a.x1 && a.y0 <= b.y1 && b.y0 <= a.y1) overboxed++;
  for (const r of drawn.reeds) for (const t of r.teeth) if (t.x !== r.x0) unedged++;
  // A reed's box stands in for the links of its teeth.
  const linked = new Set([...drawn.links.map(l => l.head),
                          ...tree.strands.filter(s => drawn.reeds.some(r => r.head === s.up)).map(s => s.head)]);
  for (const s of tree.strands)
    if (rows.has(s.head) && s.up !== null && rows.get(s.head) !== rows.get(s.up) && !linked.has(s.head))
      unlinked++;
}
is("no two strands on one row come within the gap", overlaps, 0);
is("no reed spans more than its cap, nor nothing", overspun, 0);
is("a tooth is a tooth of an ancestor's, where it really left", unmoved, 0);
is("  and the places reeds make are the forks less those they took in", uncounted, 0);
is("no reed's box overlaps another's", overboxed, 0);
is("a reed's teeth stand in slot order", unslotted, 0);
is("  and are drawn from its top", unedged, 0);

// A scan from the root down, and from the last leaf up, meets every leaf that has a row and
// reaches the focus, once each and in the order's own order; and bounded below, a step there
// and back returns to what reads the same in the window, which is the same leaf or one leaving
// its path only below it.
let unbroken = 0, missed = 0, unreversed = 0, unreturned = 0;
for (let t = 0; t < 80; t++) {
  // Every other tree combed, which a scan walks as one place.
  const grew = grown(5 + Math.floor(rand() * 120));
  const tree = t % 2 ? grew : m.comb(grew, m.reeds(grew, new Set(),
    { range: 1 + Math.floor(rand() * 8), cap: 2 + Math.floor(rand() * 30) }).reeds);
  const at = new Map(tree.order.map((s, i) => [s.head, i]));
  for (const s of tree.order) {
    const under = tree.strands.filter(o => m.lineage(tree, o.head).includes(s.head)).length;
    for (const o of tree.order.slice(at.get(s.head), at.get(s.head) + under))
      if (!m.lineage(tree, o.head).includes(s.head)) unbroken++;
  }
  const hairs = m.hair(tree, m.LADDER[t % m.LADDER.length], new Set());
  const gone = m.undrawn(tree, hairs);
  const from = rand() * m.most(tree);
  const want = tree.order.filter(s => s.leaf && !s.passage && !gone.has(s.head) && s.depth + s.length >= from)
    .map(s => s.head);
  const reach = { from, until: Infinity };
  const walk = (head, by) => {
    const out = [];
    for (let s = m.scan(tree, hairs, head, by, reach); s; s = m.scan(tree, hairs, s.head, by, reach))
      out.push(s.head);
    return out;
  };
  const until = from + rand() * 100;
  for (const s of tree.order) for (const by of [1, -1]) {
    const there = m.scan(tree, hairs, s.head, by, { from, until });
    if (there !== null && s.leaf && !s.passage && !gone.has(s.head) && s.depth + s.length >= from
        && (m.parts(tree, m.scan(tree, hairs, there.head, -by, { from, until })?.head ?? s.head,
                    new Set(m.lineage(tree, s.head))) ?? Infinity) <= until) unreturned++;
  }
  if (JSON.stringify(walk(tree.top.head, 1)) !== JSON.stringify(want.filter(h => h !== tree.top.head)))
    missed++;
  const last = tree.order.at(-1).head;
  const back = [...walk(last, -1)].reverse();
  if (JSON.stringify(back) !== JSON.stringify(want.filter(h => h !== last))) unreversed++;
}
is("depth-first keeps every subtree together", unbroken, 0);
is("a scan down meets every leaf in reach, once each", missed, 0);
is("  and a scan up meets the same, reversed", unreversed, 0);
is("bounded below, a step across and back returns to what reads the same", unreturned, 0);
is("every kept strand is placed and nothing cut is", unplaced, 0);
is("the path holds row 0 throughout, through reeds as well", offPath, 0);
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

// ---- on the page ----------------------------------------------------------------------------

// A point read off the page and drawn back again lands where it was, whichever way it runs.
const frame = { w: 300, h: 900 };
const back = [true, false].map(down => [[0, 0], [12.5, 40], [frame.w, frame.h]].every(([px, py]) => {
  const p = m.onPlan(px, py, frame.w, frame.h, down);
  const q = m.placed(down, p.along, p.across);
  return q.x === px && q.y === py;
}));
is("a point read onto the plan and placed back is the point, down the page or across it",
   back, [true, true]);
is("  and a point off the frame is off the plan",
   [m.onPlan(-1, 5, frame.w, frame.h, true), m.onPlan(5, frame.h + 1, frame.w, frame.h, false)],
   [null, null]);

// The scale: every step of zoom stands somewhere on it, and taking the scale there asks for that
// step again. The ends of the scale are the ends of the zoom, and a hand past them holds an end.
const [a0, a1] = [20, 620];
for (const most of [1, 6, 9]) {
  const steps = Array.from({ length: most + 1 }, (_, z) => z);
  is(`a step of zoom placed on the scale and taken there is that step (${most} steps)`,
     steps.map(z => m.scaleTo(m.scaleAt(z, a0, a1, most), a0, a1, most).steps), steps);
}
is("  out at the tree's end and in at the root",
   [m.scaleAt(0, a0, a1, 6), m.scaleAt(6, a0, a1, 6)], [a1, a0]);
is("  and a hand past either end holds that end",
   [m.scaleTo(a0 - 50, a0, a1, 6), m.scaleTo(a1 + 50, a0, a1, 6)],
   [{ at: a0, steps: 6 }, { at: a1, steps: 0 }]);

// The thumb: its middle, read back through the scale, is the middle of the span it covers, and
// its edges are its edges.
const xs = m.scale({ most: 400, width: 900, pad: m.PAD });
const span = [120, 180], y0 = 50, half = m.thumbHalf(6);
for (const down of [true, false]) {
  const t = m.thumbBox(xs, span, y0, half, down);
  const mid = m.onPlan(t.x + t.width / 2, t.y + t.height / 2, 1e6, 1e6, down);
  is(`the thumb's middle is ${(span[1] - span[0]) / 2} tokens into it (${down ? "down" : "across"})`,
     Math.round(m.inThumb(mid, xs, span, y0, half) * 1e9) / 1e9, (span[1] - span[0]) / 2);
}
is("  a point above or below it is off it",
   [m.inThumb({ along: xs(150), across: y0 - half - 3 }, xs, span, y0, half),
    m.inThumb({ along: xs(150), across: y0 + half + 3 }, xs, span, y0, half)], [null, null]);
is("  and so is one past either end of the span by more than half a token",
   [m.inThumb({ along: xs(span[0] - 0.6), across: y0 }, xs, span, y0, half),
    m.inThumb({ along: xs(span[1] + 0.6), across: y0 }, xs, span, y0, half)], [null, null]);
is("  and with nothing in view there is no thumb", m.inThumb({ along: 0, across: y0 }, xs, null, y0, half),
   null);
is("the scale is the strip at the inner edge",
   [m.onScale({ along: 5, across: m.SCALE }), m.onScale({ along: 5, across: m.SCALE + 1 }),
    m.onScale(null)], [true, false, false]);

// A mark across the row stands on it, centred, and never shorter or taller than its bounds.
const marks = [0.5, 3, 6, 20].map(step => m.upright(10, 40, step));
is("a mark across a row is centred on it", marks.every(([, c0, , c1]) => c0 + c1 === 80), true);
is("  as tall as the rows allow, within its bounds",
   marks.map(([, c0, , c1]) => (c1 - c0) / 2), [4, 4, 6, m.MARK]);

// Rows that fit stand inside the margin; rows that do not keep row 0 in the middle.
for (const [lo, hi, wide, down] of [[-3, 2, 300, true], [-3, 2, 300, false], [0, 0, 120, true],
                                    [-200, 150, 300, true]]) {
  const { step, top } = m.fit(lo, hi, wide, down);
  const inside = top - lo * step >= m.PAD - 1e-9 && top + (hi - lo) * step <= wide - m.PAD + 1e-9;
  const fits = (hi - lo) * step <= wide - 2 * m.PAD;
  is(`rows ${lo}..${hi} across ${wide}px: a step within its bounds, and ${fits ? "inside the margin" : "row 0 in the middle"}`,
     [step >= m.STEP[0] && step <= m.STEP[1], fits ? inside : top - lo * step === wide / 2],
     [true, true]);
}

// Rows that do not fit stay where the last drawing had them, cut off at the edges, and move only
// to keep the path's row in from either edge.
{
  const [lo, hi, wide] = [-200, 150, 300], keep = wide * m.HOLD;
  const zeroOf = f => f.top - lo * f.step;
  const at = (f, r) => zeroOf(f) + r * f.step;
  const first = m.fit(lo, hi, wide, true, 0);
  is("rows that do not fit, cut off at both edges", first.cut, [true, true]);
  const held = m.fit(lo, hi, wide, true, 10, zeroOf(first));
  is("  and drawn again with the path's row still in view, stand where they stood",
     zeroOf(held), zeroOf(first));
  const far = 200 / first.step;  // a row 200px past row 0, out past the edge's keep
  const moved = m.fit(lo, hi, wide, true, far, zeroOf(first));
  is("  and with it out of view, move just far enough to keep it in",
     Math.abs(at(moved, far) - (wide - keep)) < 1e-9, true);
  const back = m.fit(lo, hi, wide, true, -far, zeroOf(first));
  is("  from either side", Math.abs(at(back, -far) - keep) < 1e-9, true);
  is("  and rows that fit are cut off nowhere", m.fit(-3, 2, 300, true).cut, [false, false]);
}

// A run of steps across hurries each glide by `RUSH` while the last is still moving, down to
// `BRISK`, and one taken from rest goes at the usual pace.
let rush = { until: 0, pace: m.GLIDE }, now = 1000;
const paces = [];
for (let i = 0; i < 8; i++) {
  rush = m.hurried(now, rush);
  paces.push(rush.pace);
  now += 10;
}
const want = [m.GLIDE];
while (want.length < 8) want.push(Math.max(m.BRISK, want.at(-1) * m.RUSH));
is("steps across in quick succession each glide faster, never below the floor", paces, want);
is("  and a drawing glides at the pace the run reached, while it does",
   [m.paced(now, rush), m.paced(rush.until, rush)], [rush.pace, m.GLIDE]);
is("  and a step from rest glides at the usual pace", m.hurried(rush.until + 1, rush).pace, m.GLIDE);
const cool = { t0: 0, until: 400 };
is("the caret's colour sweeps from its side to nothing over the glide",
   [0, 100, 400, 500].map(t => m.cooled(t, cool, -1).offset), [-1, -0.75, 0, 0]);
is("  and sweeps from the side the caret came from, or the side it last did",
   [m.side({ x1: 0, x2: 0 }, { x1: 4, x2: 4 }, true, -1),
    m.side({ y1: 9, y2: 9 }, { y1: 1, y2: 1 }, false, 1),
    m.side({ x1: 3, x2: 3, y1: 0, y2: 0 }, { x1: 3, x2: 3, y1: 7, y2: 7 }, true, -1)], [1, -1, -1]);
is("a caret is far out once past the band, or past twice the mark where the rows are close",
   [m.far(50 + 3 * 10, 50, 10), m.far(50 + 3 * 10 + 0.1, 50, 10),
    m.far(50 + 2 * m.MARK + 0.1, 50, 1)], [false, true, true]);

// A wheel: a fine one adds up, and what it scrolled is the steps it made and what is left over;
// a coarse one, or a movement of a notch or more, is one step its way and leaves nothing.
const fine = [7, 13, -4, 30, 25, 3, -39, -9, 38, 2];  // each under a notch
let acc = 0, made = 0;
for (const d of fine) { const got = m.notch(acc, d, false); acc = got.acc; made += got.n; }
is("a fine wheel's movement is the steps it made and what is left over",
   made * m.NOTCH + acc, fine.reduce((a, b) => a + b, 0));
is("  and what is left over is under a step", Math.abs(acc) < m.NOTCH, true);
is("  and a coarse wheel or a long movement is one step its way, whatever had gathered",
   [m.notch(30, 3, true), m.notch(-30, -120, false), m.notch(30, 5, false)],
   [{ n: 1, acc: 0 }, { n: -1, acc: 0 }, { n: 0, acc: 35 }]);

// A run of steps across lands at the depth it keeps, or the end of a branch short of it.
const ran = [[30, { depth: 10, length: 50 }], [30, { depth: 10, length: 5 }]]
  .map(([depth, to]) => m.aimedAt({ depth, to }));
is("a run lands at the depth it keeps, or the end of a branch short of it", ran, [30, 14]);
is("  never past the branch's own end",
   [5, 20, 80].every(d => m.aimedAt({ depth: d, to: { depth: 10, length: 20 } }) <= 10 + 20 - 1), true);

// Where a run begins: from the caret's depth, the window holding the stretch in view.
const edge = d => d * 2;
const fresh = m.aim({ ends: 100, span: [40, 60], caret: 52, kept: null, y: 0, edge });
is("a run from the caret keeps the caret's depth and holds the stretch in view",
   fresh, { depth: 52, from: 41, until: 60, hold: { depth: 40, top: 80 }, to: null });
is("  off the path, the middle of what is in view, and with nothing in view, the end",
   [m.aim({ ends: 100, span: [40, 60], caret: -1, kept: null, y: 0, edge }).depth,
    m.aim({ ends: 100, span: null, caret: -1, kept: null, y: 0, edge }).depth], [50, 99]);
const kept = { depth: 70, y: 300, run: { from: 41, until: 60, hold: { depth: 40, top: 80 } } };
is("  where the last run landed and the window has not moved, its depth and window go on",
   m.aim({ ends: 30, span: [10, 20], caret: 29, kept, y: 301, edge }),
   { from: 41, until: 60, hold: { depth: 40, top: 80 }, depth: 70, to: null });
is("  and where the window has moved since, the depth goes on and the window is taken afresh",
   m.aim({ ends: 30, span: [10, 20], caret: 29, kept, y: 320, edge }),
   { depth: 70, from: 11, until: 20, hold: { depth: 10, top: 20 }, to: null });

// A step across and back from where the last run landed comes back to the same branch, with
// the same depth and the same window, so the two read the same.
const at = 62, run0 = m.aim({ ends: 40, span: [5, 25], caret: 20, kept: null, y: 0, edge });
const over = m.scan(limb, none, at, 1, run0);
const across = { ...run0, to: over };
const landed = { depth: run0.depth, y: 0, run: { from: run0.from, until: run0.until, hold: run0.hold } };
const run1 = m.aim({ ends: over.depth + over.length, span: [5, 25], caret: m.aimedAt(across), kept: landed, y: 0, edge });
const home = m.scan(limb, none, over.head, -1, run1);
is("a step across and back comes home, at the depth and in the window it left",
   [home.head, run1.depth, run1.from, run1.until, run1.hold], [at, run0.depth, run0.from, run0.until, run0.hold]);

process.exit(bad ? 1 : 0);
