/* The map: the tree under a root drawn as strands, beside the text.
 *
 * Along is tokens from the root. Across is local and is the ranking: at each fork one child
 * continues the row, the one on the reader's path where there is one and otherwise the
 * heaviest, and the others stand above it if the model ranked them higher and below it if
 * lower, the nearest rank nearest, each packed as close to its fork as the drawing allows.
 *
 * The plan is in those two: `x` along and `y` across, as the map drawn across the page has
 * them. Drawn down the page it is the same plan with the two swapped.
 *
 * Everything here is arithmetic over the strands `/map` answers and the measurements it is
 * handed. What turns the plan into marks on a page is the page's.
 */

export const GAP = 4;     // px kept clear between two strands on one row
export const REACH = 64;  // nodes past which a hair is drawn no longer

/** The cut's rungs, finest to coarsest. A child that does not continue its fork's row is drawn
 *  as a tick off the fork rather than given a row: a leaf where it is a stub and `stubs` is on
 *  or it is no longer than `under` nodes, and any other strand, with everything below it, where
 *  its subtree holds no more than `fold` tokens. */
export const LADDER = [
  { stubs: false, under: 0, fold: 0 },
  { stubs: true, under: 0, fold: 0 },
  { stubs: true, under: 4, fold: 0 },
  { stubs: true, under: 8, fold: 0 },
  { stubs: true, under: 16, fold: 0 },
  { stubs: true, under: 32, fold: 0 },
  { stubs: true, under: 64, fold: 0 },
  { stubs: true, under: 64, fold: 256 },
  { stubs: true, under: 64, fold: 1024 },
  { stubs: true, under: 64, fold: Infinity },
];

const rank = s => s.logprob ?? -Infinity;

/** The strands by head, each one's children in the order they came, and the root's; and by
 *  head, where the subtree under a strand ends in tokens from the root, and the deepest strand
 *  of its heaviest line. A strand comes before every strand below it, as `/map` sends them. */
export function index(strands) {
  const byHead = new Map(strands.map(s => [s.head, s]));
  const kids = new Map();
  let top = null;
  for (const s of strands) {
    if (s.up === null) { top = s; continue; }
    if (!kids.has(s.up)) kids.set(s.up, []);
    kids.get(s.up).push(s);
  }
  const ends = new Map(), lines = new Map();
  for (const s of [...strands].reverse()) {
    const mine = kids.get(s.head) ?? [];
    ends.set(s.head, mine.reduce((m, k) => Math.max(m, ends.get(k.head)), s.depth + s.length));
    const heaviest = continuing(mine, new Set());
    lines.set(s.head, heaviest === null ? s : lines.get(heaviest.head));
  }
  return { strands, byHead, kids, top, ends, lines };
}

/** The heads of the strands a path runs through, from its node ids. */
export function along(tree, nodes) {
  return new Set(nodes.filter(id => tree.byHead.has(id)));
}

/** The child that continues its fork's row: the one on the path, or the heaviest, ties to
 *  the first. */
export function continuing(kids, path) {
  let best = null;
  for (const k of kids) {
    if (path.has(k.head)) return k;
    if (best === null || k.weight > best.weight) best = k;
  }
  return best;
}

/** Which strands are drawn as ticks under `cut`, a rung of `LADDER` or a strand's rung from
 *  `zoned`: hair, which is a leaf, and folds, which are not. A fork's continuing child is never
 *  one. */
export function hair(tree, cut, path) {
  const out = new Set();
  const at = typeof cut === "function" ? cut : () => cut;
  for (const kids of tree.kids.values()) {
    const main = continuing(kids, path);
    for (const k of kids) {
      if (k === main) continue;
      const c = at(k);
      if (k.leaf ? (c.stubs && k.stub) || k.length <= c.under : k.weight <= (c.fold ?? 0))
        out.add(k.head);
    }
  }
  return out;
}

/** The strands with no row of their own under `hairs`: each tick and everything below it. */
export function undrawn(tree, hairs) {
  const out = new Set();
  for (const s of tree.strands) if (hairs.has(s.head) || out.has(s.up)) out.add(s.head);
  return out;
}

/** What a cut does to the drawing, which is what it is stated in: strands kept of all of
 *  them, and the share of the tokens drawn as ticks. */
export function effect(tree, hairs) {
  const gone = undrawn(tree, hairs);
  let tokens = 0, cut = 0;
  for (const s of tree.strands) {
    tokens += s.length;
    if (gone.has(s.head)) cut += s.length;
  }
  return { kept: tree.strands.length - gone.size, of: tree.strands.length,
           share: tokens ? cut / tokens : 0 };
}

/** x for a count of tokens from the root, over `[pad, width - pad]` for `[0, most]`, and
 *  back again: straight, or through a `lens` from `fisheye`. */
export function scale({ most, width, pad, lens = null }) {
  if (lens !== null) {
    const k = width - 2 * pad;
    const x = v => pad + lens(v) * k;
    x.invert = px => lens.invert(Math.min(1, Math.max(0, (px - pad) / k)));
    return x;
  }
  const k = (width - 2 * pad) / Math.max(most, 1e-9);
  const x = v => pad + v * k;
  x.invert = px => Math.max(0, px - pad) / k;
  return x;
}

/** How far the tree reaches on x, in tokens, whatever is cut. */
export const most = tree => tree.top === null ? 1 : Math.max(1, tree.ends.get(tree.top.head));

/** How wide a fold's tick is drawn, in px, for the tokens it holds. */
export const heft = weight => Math.min(5, 1 + Math.log2(1 + weight / 256));

// ---- packing ------------------------------------------------------------------------------

const lower = (xs, v) => {  // the first index whose value is at or above v
  let lo = 0, hi = xs.length;
  while (lo < hi) { const mid = (lo + hi) >> 1; if (xs[mid] < v) lo = mid + 1; else hi = mid; }
  return lo;
};
const upper = (xs, v) => {  // past the last index whose value is at or below v
  let lo = 0, hi = xs.length;
  while (lo < hi) { const mid = (lo + hi) >> 1; if (xs[mid] <= v) lo = mid + 1; else hi = mid; }
  return lo;
};

/** What one row holds on x: disjoint intervals, sorted, touching ones merged. */
class Row {
  starts = [];
  ends = [];

  add(a0, a1) {
    const i = lower(this.ends, a0), j = upper(this.starts, a1);
    if (i < j) { a0 = Math.min(a0, this.starts[i]); a1 = Math.max(a1, this.ends[j - 1]); }
    this.starts.splice(i, j - i, a0);
    this.ends.splice(i, j - i, a1);
  }

  /** Whether anything here comes within `GAP` of the interval. */
  clashes(a0, a1) {
    const i = lower(this.starts, a1 + GAP) - 1;
    return i >= 0 && this.ends[i] + GAP > a0;
  }
}

const put = (profile, r, a0, a1) => {
  if (!profile.has(r)) profile.set(r, new Row());
  profile.get(r).add(a0, a1);
};

/** Whether `sub`, as `[row, [[a0, a1], ...]]` pairs shifted by `d` rows, clears `profile`.
 *
 *  The connector from the fork is not checked: the nearest row that fits is short of any
 *  strand across the fork's column whenever such a row exists, and connectors placed
 *  earlier are in the profile, so later strands keep off them. */
const fits = (profile, sub, d) =>
  sub.every(([r, ivs]) => {
    const have = profile.get(r + d);
    return have === undefined || !ivs.some(([a0, a1]) => have.clashes(a0, a1));
  });

/** Each kept strand's row, the root's at 0 and the path's on it. Up is negative.
 *
 *  A subtree is packed against what its continuing child's already holds, built in place
 *  on that child's profile so nothing is copied along a long trunk; each other child's is
 *  packed on its own and placed at the nearest row on its side that clears it. */
export function layout(tree, { x, hairs, path }) {
  const x0 = s => x(s.depth), x1 = s => x(s.depth + s.length);
  const kept = s => (tree.kids.get(s.head) ?? []).filter(k => !hairs.has(k.head));

  function pack(s) {
    const mine = kept(s);
    const main = continuing(mine, path);
    let profile, rows;
    if (main === null) {
      profile = new Map();
      rows = new Map();
    } else {
      ({ profile, rows } = pack(main));
    }
    put(profile, 0, x0(s), x1(s));
    rows.set(s.head, 0);
    if (main === null) return { profile, rows };
    const pivot = rank(main);
    const others = mine.filter(k => k !== main);
    const above = others.filter(k => rank(k) > pivot).sort((a, b) => rank(a) - rank(b));
    const below = others.filter(k => rank(k) <= pivot).sort((a, b) => rank(b) - rank(a));
    const xf = x1(s);
    for (const [side, group] of [[-1, above], [1, below]]) {
      for (const k of group) {
        const built = pack(k);
        const sub = [...built.profile].map(([r, row]) =>
          [r, row.starts.map((a0, i) => [a0, row.ends[i]])]);
        let d = side;
        while (!fits(profile, sub, d)) d += side;
        for (const [r, ivs] of sub) for (const [a0, a1] of ivs) put(profile, r + d, a0, a1);
        for (let r = side; r !== d; r += side) put(profile, r, xf, xf);
        for (const [head, r] of built.rows) rows.set(head, r + d);
      }
    }
    return { profile, rows };
  }

  return tree.top === null ? new Map() : pack(tree.top).rows;
}

// ---- the plan -----------------------------------------------------------------------------

/** What is drawn, in px: strands as runs along their rows, links from a fork down or up to
 *  a strand that left it, hair as ticks off the fork they leave, and a fan wherever three
 *  or more strands leave one fork. `step` is the px between rows; `top` is the y of the
 *  highest row. */
export function plan(tree, rows, { x, hairs, path, step, top = 0 }) {
  let lo = Infinity, hi = -Infinity;
  for (const r of rows.values()) { lo = Math.min(lo, r); hi = Math.max(hi, r); }
  const y = head => top + (rows.get(head) - lo) * step;
  const out = { strands: [], links: [], hairs: [], fans: [],
                height: rows.size ? (hi - lo) * step : 0 };
  for (const s of tree.strands) {
    if (!rows.has(s.head)) continue;
    const a = x(s.depth), b = x(s.depth + s.length);
    out.strands.push({ head: s.head, x0: a, x1: b, y: y(s.head), path: path.has(s.head),
                       aside: s.aside === null ? null : x(s.depth + s.aside) });
    if (s.up !== null && rows.get(s.up) !== rows.get(s.head))
      out.links.push({ head: s.head, x: a, y0: y(s.up), y1: y(s.head) });
  }
  for (const [up, kids] of tree.kids) {
    if (!rows.has(up)) continue;
    const parent = tree.byHead.get(up);
    const at = x(parent.depth + parent.length);
    if (kids.length >= 3) out.fans.push({ head: up, x: at, y: y(up), n: kids.length });
    const main = continuing(kids.filter(k => !hairs.has(k.head)), path);
    for (const k of kids) {
      if (!hairs.has(k.head)) continue;
      // Shorter hair stands further off its row, so a fringe of them reads as a fringe. A fold
      // reaches as far as what it holds does.
      const span = tree.ends.get(k.head) - k.depth;
      const lift = step * (0.25 + 0.5 * (1 - Math.min(1, span / REACH)));
      const higher = main === null || rank(k) > rank(main);
      const reach = x(k.depth + (k.leaf ? Math.min(span, REACH) : span));
      out.hairs.push({ head: k.head, x0: at, x1: Math.max(at + 1, reach),
                       y0: y(up), y1: y(up) + (higher ? -lift : lift),
                       stub: k.stub, aside: k.aside !== null,
                       fold: !k.leaf, weight: k.weight });
    }
  }
  return out;
}

/** The strand or tick nearest a point within `slack` px, and which of its nodes the point is
 *  over, counted from the root -- or null. A fold is its heaviest line. */
export function hit(tree, drawn, x, px, py, slack) {
  let best = null, far = slack, folded = false;
  const consider = (head, x0, x1, y0, y1, fold) => {
    if (px < x0 - slack || px > x1 + slack) return;
    const t = x1 > x0 ? Math.min(1, Math.max(0, (px - x0) / (x1 - x0))) : 0;
    const d = Math.abs(py - (y0 + (y1 - y0) * t));
    if (d <= far) { far = d; best = head; folded = fold; }
  };
  for (const s of drawn.strands) consider(s.head, s.x0, s.x1, s.y, s.y, false);
  for (const h of drawn.hairs) consider(h.head, h.x0, h.x1, h.y0, h.y1, h.fold);
  if (best === null) return null;
  const s = tree.byHead.get(best);
  const to = folded ? tree.lines.get(best) : s;
  const at = Math.floor(x.invert(px));
  const depth = Math.min(to.depth + to.length - 1, Math.max(s.depth, at));
  return { head: best, tail: to.tail, depth };
}


// ---- the window ---------------------------------------------------------------------------

/** Where each of a path's cells starts, in tokens from the root, and where the last ends. */
export function offsets(counts) {
  const out = [0];
  for (const n of counts) out.push(out.at(-1) + n);
  return out;
}

/** The tokens of a path in view, as `[from, to)` -- or null with none. `edge(i)` is cell i's
 *  `{ top, bottom }` and the cells stand in order down the page; `[lo, hi]` is what is in
 *  view, on the same measure. */
export function seen(at, edge, lo, hi) {
  const n = at.length - 1;
  let a = 0, b = n;
  while (a < b) { const mid = (a + b) >> 1; if (edge(mid).bottom <= lo) a = mid + 1; else b = mid; }
  const first = a;
  a = first; b = n;
  while (a < b) { const mid = (a + b) >> 1; if (edge(mid).top < hi) a = mid + 1; else b = mid; }
  const last = a - 1;
  return first > last ? null : [at[first], at[last + 1]];
}

/** The cell holding the token `depth` tokens from the root, the last where it is past them. */
export function holding(at, depth) {
  let a = 0, b = at.length - 2;
  while (a < b) { const mid = (a + b + 1) >> 1; if (at[mid] <= depth) a = mid; else b = mid - 1; }
  return Math.max(0, a);
}

// ---- zoom --------------------------------------------------------------------------------

/* Zoomed in, the cut varies with distance from the thumb: the axis is split into zones about
 * it, mirrored either side, and each zone is cut at a rung of its own. A step moves the focus a
 * rung finer and each zone further out `scaling` rungs coarser than the one inside it. */

/** The focal distance as a share of the axis, how much wider each ring is than the last, how
 *  many zones there are, and the rungs a step moves a zone by against the one inside it. */
export const ZONES = { focal: 0.05, ratio: 3, n: 3, scaling: 1 };

const clamp = (v, lo, hi) => Math.min(hi, Math.max(lo, v));

/** Which zone `[s, e)` stands in about the focus `[a, b)`: 0 within `focal` tokens of it, each
 *  ring after that wider than the last by the ratio, and the last zone everything past them. */
export function zone([s, e], [a, b], focal, { ratio, n } = ZONES) {
  const gap = Math.max(0, a - e, s - b);
  let edge = focal, width = focal;
  for (let i = 0; i < n - 1; i++) {
    if (gap <= edge) return i;
    width *= ratio;
    edge += width;
  }
  return n - 1;
}

/** The rung zone `i` is on, `steps` in from `base`. */
export const rungAt = (base, steps, i, scaling = ZONES.scaling) =>
  clamp(base + Math.round(steps * (i * scaling - 1)), 0, LADDER.length - 1);

/** How far in a zoom can go from `base` and still change something. */
export function deepest(base, { n, scaling } = ZONES) {
  const far = (n - 1) * scaling - 1;  // rungs a step moves the furthest zone by
  return Math.max(base, far > 0 ? Math.ceil((LADDER.length - 1 - base) / far) : 0);
}

/** Each strand's rung zoomed `steps` in about the thumb's `span`, on an axis `most` tokens long:
 *  that of the zone it stands in, by its nearest point or, `byFork`, by where it leaves its
 *  fork. Not zoomed, or with no thumb, every strand is on `base`. */
export function zoned(tree, { base, steps, span, most, byFork = false, zones = ZONES }) {
  if (steps === 0 || span === null) return () => LADDER[base];
  const focal = zones.focal * most;
  return k => LADDER[rungAt(base, steps, zone(
    byFork ? [k.depth, k.depth] : [k.depth, tree.ends.get(k.head)], span, focal, zones),
    zones.scaling)];
}

/** How much a step of zoom magnifies the focus, and how many steps of it there are. */
export const LENS = { gain: 2, steps: 6 };

/** The zones about the focus `[a, b)` on `[0, most]`, in order along the axis, as
 *  `[from, to, zone]` runs. A zone past a wall spans nothing and is left out. */
export function bands([a, b], focal, most, { ratio, n } = ZONES) {
  const edges = [];  // how far from the focus each zone but the last reaches
  for (let i = 0, edge = 0, width = focal; i < n - 1; i++, width *= ratio) edges.push(edge += width);
  const starts = [[-Infinity, n - 1]];
  for (let i = n - 2; i >= 0; i--) starts.push([a - edges[i], i]);
  for (let i = 0; i < n - 1; i++) starts.push([b + edges[i], i + 1]);
  const out = [];
  for (let j = 0; j < starts.length; j++) {
    const from = clamp(starts[j][0], 0, most);
    const to = clamp(j + 1 < starts.length ? starts[j + 1][0] : Infinity, 0, most);
    if (to > from) out.push([from, to, starts[j][1]]);
  }
  return out;
}

/** The share of the axis a count of tokens stands at, zoomed `steps` in about the thumb's
 *  `span`: each zone's tokens weighted by the gain, the focus up and the far zone down as their
 *  rungs go, and straight within a zone. Not zoomed, or with no thumb, it is straight.
 *  `share.invert` reads a share back as tokens. */
export function fisheye({ span, most, steps, zones = ZONES, lens = LENS }) {
  const runs = steps === 0 || span === null ? [[0, most, 0, 1]]
    : bands(span, zones.focal * most, most, zones).map(([from, to, i]) =>
        [from, to, i, lens.gain ** (-steps * (i * zones.scaling - 1))]);
  const at = [];  // the weighted tokens before each run
  let total = 0;
  for (const [from, to, , w] of runs) { at.push(total); total += (to - from) * w; }
  const which = v => { let j = 0; while (j < runs.length - 1 && v >= runs[j][1]) j++; return j; };
  const share = v => {
    const j = which(v), [from, to, , w] = runs[j];
    return (at[j] + (clamp(v, from, to) - from) * w) / total;
  };
  share.invert = u => {
    const t = u * total;
    let j = 0;
    while (j < runs.length - 1 && t >= at[j + 1]) j++;
    const [from, to, , w] = runs[j];
    return clamp(from + (t - at[j]) / w, from, to);
  };
  return share;
}

/** The round count at or above `v`: one, two or five of a power of ten. */
const nice = v => {
  const k = 10 ** Math.floor(Math.log10(v));
  return [1, 2, 5, 10].map(m => m * k).find(m => m >= v - 1e-9);
};

/** Round counts of tokens to mark the axis at, as `[v, major]`: a step that gives the straight
 *  axis `room` px or more between them, and finer ones between those wherever `x` spreads them
 *  a third of that apart. */
export function ticks(x, most, room = 24) {
  const step = nice(Math.max(1, most * room / Math.max(1, x(most) - x(0))));
  const lead = Math.round(step / 10 ** Math.floor(Math.log10(step)));
  const fine = lead === 2 ? step / 2 : step / 5;
  const out = [];
  for (let v = 0; v <= most; v += step) {
    out.push([v, true]);
    if (fine >= 1 && x(Math.min(most, v + fine)) - x(v) >= room / 3)
      for (let f = v + fine; f < v + step && f <= most; f += fine) out.push([f, false]);
  }
  return out;
}

/** How many strands are drawn in each zone, nearest first, by where each one stands. */
export function zoneCounts(tree, hairs, { span, most, zones = ZONES }) {
  const out = Array(zones.n).fill(0);
  const gone = undrawn(tree, hairs);
  for (const s of tree.strands)
    if (!gone.has(s.head))
      out[zone([s.depth, s.depth + s.length], span, zones.focal * most, zones)]++;
  return out;
}

/** Whether two cuts are the same strands. */
export const same = (a, b) => a.size === b.size && [...a].every(h => b.has(h));

// ---- moving ------------------------------------------------------------------------------

/** The heads of a strand and of every strand it hangs from, up to the root's. */
export function lineage(tree, head) {
  const out = [];
  for (let s = tree.byHead.get(head); s; s = tree.byHead.get(s.up)) out.push(s.head);
  return out;
}

/** Eased progress at `t` of the way, slow out and slow in. */
export const ease = t => (t < 0.5 ? 4 * t ** 3 : 1 - (-2 * t + 2) ** 3 / 2);

/** What moves from one drawing to the next, each mark keyed and its geometry as numbers:
 *  `moved` is every mark in both whose numbers differ, as `[key, [[name, from, to], ...]]`,
 *  and `fresh` the keys only in the next. */
export function shift(was, now) {
  const moved = [], fresh = [];
  for (const [key, to] of now) {
    const from = was.get(key);
    if (from === undefined) { fresh.push(key); continue; }
    const pairs = Object.keys(to).filter(k => k in from && from[k] !== to[k])
      .map(k => [k, from[k], to[k]]);
    if (pairs.length) moved.push([key, pairs]);
  }
  return { moved, fresh };
}

// ---- the trail --------------------------------------------------------------------------

/* Where the reader has been: the paths they were on, newest first, each kept as its deepest
 * strand since a strand's lineage is its path. Kept in the browser and keyed by the tree, as
 * waypoints are, and missing storage is simply no trail. */

const TRAIL = "tokenloom:trail:";
export const KEEP = 20;  // paths remembered

/** The trail kept for `tree`. */
export function recall(storage, tree) {
  try {
    const list = JSON.parse(storage?.getItem(TRAIL + tree) ?? "[]");
    return Array.isArray(list) ? list.filter(e => Number.isInteger(e?.head)) : [];
  } catch {
    return [];
  }
}

/** Keep `trail` for `tree`, and say whether it was kept. */
export function keep(storage, tree, trail) {
  try {
    storage.setItem(TRAIL + tree, JSON.stringify(trail));
    return true;
  } catch {
    return false;
  }
}

/** The trail once the reader is on `path`, whose deepest strand is `deepest`. A path that only
 *  grew past the last one is that one further on and takes its place; any other is put on top,
 *  coming off wherever it stood lower down. The same trail is handed back where nothing
 *  changed. */
export function remember(tree, trail, path, deepest, most = KEEP) {
  if (deepest === null || trail[0]?.head === deepest) return trail;
  const top = trail[0];
  const grew = top !== undefined && tree.byHead.has(top.head)
    && lineage(tree, top.head).every(h => path.has(h));
  const rest = (grew ? trail.slice(1) : trail).filter(e => e.head !== deepest);
  return [{ head: deepest }, ...rest].slice(0, most);
}

/** How many paths back each strand off `path` was last on one, from 1 to `n`, counting only
 *  paths under this tree. */
export function steps(tree, trail, path, n) {
  const out = new Map();
  let k = 0;
  for (const e of trail) {
    if (!tree.byHead.has(e.head) || path.has(e.head)) continue;
    if (++k > n) break;
    for (const h of lineage(tree, e.head)) if (!path.has(h) && !out.has(h)) out.set(h, k);
  }
  return out;
}
