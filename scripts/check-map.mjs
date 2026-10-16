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
const x = m.scale({ log: false, most: 40, width: 440, pad: 20 });

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
const lx = m.scale({ log: true, most: 40, width: 440, pad: 20 });
is("  and on log too", [lx(0), Math.round(lx(40))], [20, 420]);
is("  and inverts", [x.invert(x(17)), Math.round(lx.invert(lx(17)) * 1e9) / 1e9], [17, 17]);

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

// ---- at random ----------------------------------------------------------------------------

let seed = 7;
const rand = () => (seed = (seed * 1103515245 + 12345) % 2 ** 31) / 2 ** 31;

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
  const hairs = m.hair(tree, { stubs: true, under: 4 }, path);
  const log = t % 2 === 0;
  const x = m.scale({ log, most: m.most(tree, hairs), width: 600, pad: 10 });
  const rows = m.layout(tree, { x, hairs, path });
  for (const s of tree.strands) if (rows.has(s.head) === hairs.has(s.head)) unplaced++;
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
is("every kept strand is placed and no hair is", unplaced, 0);
is("the path holds row 0 throughout", offPath, 0);
is("above is ranked higher than what continues, and below lower", misranked, 0);
is("the nearest rank stands nearest", misordered, 0);
is("every strand off its fork's row is linked to it", unlinked, 0);

process.exit(bad ? 1 : 0);
