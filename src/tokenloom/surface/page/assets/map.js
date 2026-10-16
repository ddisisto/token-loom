/* The map: the tree under a root drawn as strands, beside the text.
 *
 * x is a quantity summed from the root and says which -- tokens, on a linear or a log scale.
 * y is local and is the ranking: at each fork one child continues the row, the one on the
 * reader's path where there is one and otherwise the heaviest, and the others stand above it
 * if the model ranked them higher and below it if lower, the nearest rank nearest, each packed
 * as close to its fork as the drawing allows.
 *
 * Everything here is arithmetic over the strands `/map` answers and the measurements it is
 * handed. What turns the plan into marks on a page is the page's.
 */

export const GAP = 4;     // px kept clear between two strands on one row
export const REACH = 64;  // nodes past which a hair is drawn no longer

const rank = s => s.logprob ?? -Infinity;

/** The strands by head, each one's children in the order they came, and the root's. */
export function index(strands) {
  const byHead = new Map(strands.map(s => [s.head, s]));
  const kids = new Map();
  let top = null;
  for (const s of strands) {
    if (s.up === null) { top = s; continue; }
    if (!kids.has(s.up)) kids.set(s.up, []);
    kids.get(s.up).push(s);
  }
  return { strands, byHead, kids, top };
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

/** Which strands are hair under `cut`: leaves that are not their fork's continuing child,
 *  and are a stub where `cut.stubs` is on or no longer than `cut.under` nodes. */
export function hair(tree, cut, path) {
  const out = new Set();
  for (const kids of tree.kids.values()) {
    const main = continuing(kids, path);
    for (const k of kids)
      if (k !== main && k.leaf && ((cut.stubs && k.stub) || k.length <= cut.under))
        out.add(k.head);
  }
  return out;
}

/** What a cut does to the drawing, which is what it is stated in: strands kept of all of
 *  them, and the share of the tokens set aside as hair. */
export function effect(tree, hairs) {
  let tokens = 0, cut = 0;
  for (const s of tree.strands) {
    tokens += s.length;
    if (hairs.has(s.head)) cut += s.length;
  }
  return { kept: tree.strands.length - hairs.size, of: tree.strands.length,
           share: tokens ? cut / tokens : 0 };
}

/** x for a count of tokens from the root, over `[pad, width - pad]` for `[0, most]`, and
 *  back again. */
export function scale({ log, most, width, pad }) {
  const f = log ? Math.log1p : v => v;
  const g = log ? Math.expm1 : v => v;
  const k = (width - 2 * pad) / Math.max(f(most), 1e-9);
  const x = v => pad + f(v) * k;
  x.invert = px => g(Math.max(0, px - pad) / k);
  return x;
}

/** How far the drawing reaches on x, in tokens: the furthest kept strand's end. */
export const most = (tree, hairs) =>
  tree.strands.reduce((m, s) => hairs.has(s.head) ? m : Math.max(m, s.depth + s.length), 1);

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
      // Shorter hair stands further off its row, so a fringe of them reads as a fringe.
      const lift = step * (0.25 + 0.5 * (1 - Math.min(1, k.length / REACH)));
      const higher = main === null || rank(k) > rank(main);
      const reach = x(k.depth + Math.min(k.length, REACH));
      out.hairs.push({ head: k.head, x0: at, x1: Math.max(at + 1, reach),
                       y0: y(up), y1: y(up) + (higher ? -lift : lift),
                       stub: k.stub, aside: k.aside !== null });
    }
  }
  return out;
}

/** The strand or hair nearest a point within `slack` px, and which of its nodes the point is
 *  over, counted from the root -- or null. */
export function hit(tree, drawn, x, px, py, slack) {
  let best = null, far = slack;
  const consider = (head, x0, x1, y0, y1) => {
    if (px < x0 - slack || px > x1 + slack) return;
    const t = x1 > x0 ? Math.min(1, Math.max(0, (px - x0) / (x1 - x0))) : 0;
    const d = Math.abs(py - (y0 + (y1 - y0) * t));
    if (d <= far) { far = d; best = head; }
  };
  for (const s of drawn.strands) consider(s.head, s.x0, s.x1, s.y, s.y);
  for (const h of drawn.hairs) consider(h.head, h.x0, h.x1, h.y0, h.y1);
  if (best === null) return null;
  const s = tree.byHead.get(best);
  const at = Math.floor(x.invert(px));
  const depth = Math.min(s.depth + s.length - 1, Math.max(s.depth, at));
  return { head: best, tail: s.tail, depth };
}
