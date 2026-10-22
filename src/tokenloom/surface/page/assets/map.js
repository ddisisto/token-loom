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
export const KNOT = { range: 4, cap: 16 };  // tokens from one fork to the next, and across a knot

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
// Whether `k` stands above the row `main` continues: ranked higher than what continued it where
// `k` left, which a knot carries as `against`.
const higher = (k, main) => rank(k) > (k.against ?? rank(main));

/** The strands by head, each one's children in the order they came, and the root's; by
 *  head, where the subtree under a strand ends in tokens from the root, and the deepest strand
 *  of its heaviest line; and the strands depth-first, a fork's children leaving earlier first,
 *  then ranked higher first and nothing ranked last. A strand comes before every strand below
 *  it, as `/map` sends them. */
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
  const order = [], next = top === null ? [] : [top];
  const first = (a, b) => a.depth - b.depth || (rank(a) > rank(b) ? -1 : rank(a) < rank(b) ? 1 : 0);
  while (next.length) {
    const s = next.pop();
    order.push(s);
    next.push(...[...(kids.get(s.head) ?? [])].sort(first).reverse());
  }
  return { strands, byHead, kids, top, ends, lines, order };
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

/** Forks along each row within `range` tokens of the last made one place, a knot spanning no
 *  more than `cap`: every branch leaving it leaves the strand above its first fork, carrying
 *  as `against` the rank of what continued the row where it really left. A fork whose branches
 *  are all hair under `hairs` is no part of one. Answers the tree indexed again, or `tree`
 *  itself where nothing is knotted; the knots as `{ head, from, to }`, the strand they leave
 *  and where along they start and end; and how many `places` the `forks` they count became. */
export function knot(tree, path, hairs, { range, cap }) {
  const moved = new Map(), knots = [];
  let forks = 0, places = 0;
  const rows = range > 0 && tree.top !== null ? [tree.top] : [];
  while (rows.length) {
    let open = null;
    for (let s = rows.pop(); ;) {
      const kids = tree.kids.get(s.head) ?? [];
      if (!kids.length) break;
      const main = continuing(kids, path);
      const others = kids.filter(k => k !== main);
      rows.push(...others);
      const at = s.depth + s.length;
      if (others.some(k => !hairs.has(k.head))) {
        forks++;
        if (open !== null && at - open.to <= range && at - open.from <= cap) {
          open.to = at;
          for (const k of others) moved.set(k.head, { up: open.head, against: rank(main) });
        } else {
          if (open !== null && open.to > open.from) knots.push(open);
          open = { head: s.head, from: at, to: at };
          places++;
        }
      }
      s = main;
    }
    if (open !== null && open.to > open.from) knots.push(open);
  }
  if (!moved.size) return { tree, knots, forks, places };
  return { tree: index(tree.strands.map(s => moved.has(s.head) ? { ...s, ...moved.get(s.head) } : s)),
           knots, forks, places };
}

/** Where the strand `head` leaves the path through `path`, in tokens from the root: the depth
 *  of the first strand above it that the path does not run through, or null if it runs through
 *  them all. */
export function parts(tree, head, path) {
  let off = null;
  for (let s = tree.byHead.get(head); s && !path.has(s.head); s = tree.byHead.get(s.up)) off = s;
  return off === null ? null : off.depth;
}

/** The leaf a scan steps to from the strand `head`, `by` 1 down the depth-first order or -1 up
 *  it: the nearest leaf with a row of its own under `hairs` that leaves the path through `head`
 *  at or above `until` and ends at or past `from`, or null past either end of the order. */
export function scan(tree, hairs, head, by, { from, until }) {
  const gone = undrawn(tree, hairs);
  const path = new Set(lineage(tree, head));
  const at = tree.order.findIndex(s => s.head === head);
  if (at < 0) return null;
  for (let i = at + by; i >= 0 && i < tree.order.length; i += by) {
    const s = tree.order[i];
    if (s.leaf && !gone.has(s.head) && s.depth + s.length >= from
        && (parts(tree, s.head, path) ?? Infinity) <= until) return s;
  }
  return null;
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

/** Each kept strand's row, the root's at 0 and the path's on it. Up is negative. A strand that
 *  left a knot stands in the knot's order: by where it left, then by rank.
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
    const others = mine.filter(k => k !== main);
    const above = others.filter(k => higher(k, main))
      .sort((a, b) => a.depth - b.depth || rank(a) - rank(b));
    const below = others.filter(k => !higher(k, main))
      .sort((a, b) => a.depth - b.depth || rank(b) - rank(a));
    for (const [side, group] of [[-1, above], [1, below]]) {
      for (const k of group) {
        const xf = x0(k);
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
 *  a strand that left it, hair as ticks off the fork they leave, a fan wherever three or more
 *  strands leave one fork, and each of `knots` as a bar along its span and across the rows of
 *  what leaves it, which stands in for those strands' links. `step` is the px between rows; `top` is the y of the
 *  highest row. */
export function plan(tree, rows, { x, hairs, path, step, top = 0, knots = [] }) {
  let lo = Infinity, hi = -Infinity;
  for (const r of rows.values()) { lo = Math.min(lo, r); hi = Math.max(hi, r); }
  const y = head => top + (rows.get(head) - lo) * step;
  const out = { strands: [], links: [], hairs: [], fans: [], knots: [],
                height: rows.size ? (hi - lo) * step : 0 };
  // A knot is one bar, across every row a strand leaving it stands on, in place of their links.
  const tying = new Set();
  for (const k of knots) {
    if (!rows.has(k.head)) continue;
    const ys = [k.head, ...(tree.kids.get(k.head) ?? []).map(c => c.head)]
      .filter(h => rows.has(h)).map(y);
    out.knots.push({ head: k.head, from: k.from, to: k.to, x0: x(k.from), x1: x(k.to),
                     y0: Math.min(...ys), y1: Math.max(...ys) });
    tying.add(k.head);
  }
  for (const s of tree.strands) {
    if (!rows.has(s.head)) continue;
    const a = x(s.depth), b = x(s.depth + s.length);
    out.strands.push({ head: s.head, x0: a, x1: b, y: y(s.head), path: path.has(s.head),
                       aside: s.aside === null ? null : x(s.depth + s.aside) });
    if (s.up !== null && rows.get(s.up) !== rows.get(s.head) && !tying.has(s.up))
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
      const above = main === null || higher(k, main);
      const from = x(k.depth);
      const reach = x(k.depth + (k.leaf ? Math.min(span, REACH) : span));
      out.hairs.push({ head: k.head, x0: from, x1: Math.max(from + 1, reach),
                       y0: y(up), y1: y(up) + (above ? -lift : lift),
                       stub: k.stub, aside: k.aside !== null,
                       fold: !k.leaf, weight: k.weight });
    }
  }
  return out;
}

/** The knot whose bar in `drawn` a point is on, within `slack` px, or null. */
export function knotAt(drawn, px, py, slack) {
  return drawn.knots.find(k => px >= k.x0 - slack && px <= k.x1 + slack
                               && py >= k.y0 - slack && py <= k.y1 + slack) ?? null;
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

// ---- on the page ----------------------------------------------------------------------

/* What the page measures the map by, and what it makes of a pointer, a wheel and a run of steps
 * across. Every measurement is an argument: what is on screen is the page's to read. */

export const PAD = 10;          // px inside the map on every side
export const STEP = [1.5, 20];  // px between rows, at the least and the most
export const MARK = 9;          // px of a row's step the caret, the pointer and the thumb grow to
export const GLIDE = 1200;      // ms the drawing takes to move from one packing to the next
export const RUSH = 0.6;        // what a step across taken while the drawing moves leaves of its glide
export const BRISK = 240;       // ms a glide is never hurried below
export const BAND = 3;          // rows from the thumb past which a moving caret takes no step across
export const SCALE = 8;         // px in from the map's inner edge that are the scale, to drag the zoom by
export const NOTCH = 40;        // px of a fine wheel that make one step of zoom

/** Along and across the plan as the page has them: down the page the two are swapped. */
export const placed = (down, along, across) =>
  down ? { x: across, y: along } : { x: along, y: across };

/** A point `px` and `py` into a box `width` by `height`, along and across the plan, or null off
 *  the box. */
export function onPlan(px, py, width, height, down) {
  if (px < 0 || py < 0 || px > width || py > height) return null;
  return down ? { along: py, across: px } : { along: px, across: py };
}

/** How rows `lo` to `hi` stand across a map `wide` px: the step between two, and where row 0 is.
 *  Where they fit, from the margin's edge down the page and centred across it; where they do
 *  not, row 0 in the middle. */
export function fit(lo, hi, wide, down) {
  const step = Math.max(STEP[0], Math.min(STEP[1], (wide - 2 * PAD) / Math.max(1, hi - lo)));
  const fits = (hi - lo) * step <= wide - 2 * PAD;
  const top = !fits ? wide / 2 + lo * step : down ? PAD : (wide - (hi - lo) * step) / 2;
  return { step, top };
}

/** A mark standing across the row at `across`, `along` the plan, as tall as rows `step` apart
 *  allow: `[along, from, along, to]`. */
export function upright(along, across, step) {
  const h = Math.max(4, Math.min(MARK, step));
  return [along, across - h, along, across + h];
}

/** Half the thumb's breadth across its row, for rows `step` apart. */
export const thumbHalf = step => Math.max(5, Math.min(MARK, step) * 1.5);

/** The thumb over `span` on the row at `y0`, as a box on the page through `x`. */
export function thumbBox(x, span, y0, half, down) {
  const p = placed(down, x(span[0]), y0 - half);
  const q = placed(down, x(span[1]), y0 + half);
  return { x: p.x, y: p.y, width: Math.max(1, q.x - p.x), height: Math.max(1, q.y - p.y) };
}

/** How far into the thumb over `span` a point on the plan is, in tokens, or null off it. */
export function inThumb(p, x, span, y0, half) {
  if (p === null || !span || Math.abs(p.across - y0) > half + 2) return null;
  const t = x.invert(p.along);
  return t >= span[0] - 0.5 && t <= span[1] + 0.5 ? t - span[0] : null;
}

/** Whether a point on the plan is on the scale, the strip along the map's inner edge. */
export const onScale = p => p !== null && p.across <= SCALE;

/** Where the zoom stands on a scale running from `a0` at the root to `a1` at the tree's end,
 *  `steps` in of the `most` there are. */
export const scaleAt = (steps, a0, a1, most) => a1 - (a1 - a0) * steps / (most || 1);

/** A hand `along` the scale: where it holds it, kept on the scale, and the step nearest. */
export function scaleTo(along, a0, a1, most) {
  const at = Math.min(a1, Math.max(a0, along));
  return { at, steps: Math.round((a1 - at) / (a1 - a0) * most) };
}

/** How long a drawing at `now` glides: as a run of steps across hurried it, while it does. */
export const paced = (now, rush) => (now < rush.until ? rush.pace : GLIDE);

/** The glide a step across taken at `now` hurries to: faster than the last while that one
 *  still moves, never below `BRISK`, and the usual from rest. */
export function hurried(now, rush) {
  const pace = now < rush.until ? Math.max(BRISK, rush.pace * RUSH) : GLIDE;
  return { until: now + pace, pace };
}

/** What is left at `now` of the caret's colour sweeping over `cool`, in ms, and as the share of
 *  the caret still to sweep, signed by the side it sweeps from. */
export function cooled(now, cool, side) {
  const left = cool.until - now;
  return { left, offset: left > 0 ? side * left / (cool.until - cool.t0) : 0 };
}

/** The side a caret moved from `from` to `to` sweeps its colour from, or `was` where it did not
 *  move across. */
export function side(from, to, down, was) {
  const across = at => (down ? at.x1 + at.x2 : at.y1 + at.y2);
  return across(to) !== across(from) ? Math.sign(across(to) - across(from)) : was;
}

/** Whether a caret `across` the plan is further from the thumb's row at `y0` than a step across
 *  may take it, for rows `step` apart. */
export const far = (across, y0, step) => Math.abs(across - y0) > Math.max(MARK * 2, BAND * step);

/** A wheel's movement `d` gathered onto `acc`: the steps it makes, and what is left over. A
 *  coarse wheel, or a movement of a notch or more, is one step its way. */
export function notch(acc, d, coarse) {
  const sum = coarse || Math.abs(d) >= NOTCH ? Math.sign(d) * NOTCH : acc + d;
  const n = Math.trunc(sum / NOTCH);
  return { n, acc: sum - n * NOTCH };
}

/** Where a run of steps across lands on the branch it is going to: the depth it keeps, or the
 *  branch's end where that is short of it. */
export const aimedAt = run => Math.min(run.depth, run.to.depth + run.to.length - 1);

/** A run of steps across, begun from a path `ends` tokens long with `span` in view and the
 *  caret `caret` tokens in, or -1 off it. `kept` is where the last run landed, if the caret is
 *  still where it put it, and `y` where the window stands. The depth kept is the one the reader
 *  last put the caret at; the window holds the stretch of the path it held, which a run carried
 *  on with keeps, and `edge(depth)` is where the token `depth` in stands on the page now. */
export function aim({ ends, span, caret, kept, y, edge }) {
  const depth = kept ? kept.depth
    : caret >= 0 ? caret : span ? Math.floor((span[0] + span[1]) / 2) : ends - 1;
  if (kept && Math.abs(kept.y - y) < 2) return { ...kept.run, depth, to: null };
  const top = span ? Math.floor(span[0]) : Math.min(depth, ends - 1);
  return {
    depth, from: top + 1, until: span ? span[1] : depth,
    hold: { depth: top, top: edge(top) }, to: null,
  };
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
