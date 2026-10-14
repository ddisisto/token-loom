#!/usr/bin/env python
"""Draw a tree's shape as SVG, with `shape.py`'s strands as the unit and no text at all.

**A sketch to look at, not the page's drawing.** Each option is one candidate answer to what
visual language the structure takes, drawn the same way across the tree.

**x is a quantity summed from the root**, on one scale for everything drawn:

- `tokens`: one per node.
- `entropy`: bits in the ranking each node was drawn from. Depth-bound in `docs/LAYERS.md`'s
  sense: the recorded rows count exactly and the unrecorded mass as one lump, so it is a lower
  bound and positions recorded to different depths are not like for like.
- `surprisal`: bits of the row each node took.

A position with no ranking, or whose row was not recorded, adds nothing to either measure;
the header says how many there were. `--log` draws the axis as log(1 + x).

**Modes.** `full` gives every leaf strand a place; `skeleton` takes hair out (`shape.hair`
with stubs, and other leaves of at most `--cut` tokens) and draws it as ticks off the fork it
leaves, grey for a stub and amber otherwise, capped at `REACH` nodes; `icicle` gives each
strand a band as tall as the tokens below it, stubs pale.

**Layouts**, for `full` and `skeleton`. At each fork one child continues the parent's row:
the one on the path to `--at` where there is one, and otherwise the heaviest.

- `stack`: every other child opens a row below everything placed so far.
- `near`: every other child goes below, packed as close to its fork as the drawing allows.
- `slots`: the fork's children keep the ranking's order. A child the model ranked above the
  continuing one goes above it, a lower one below, nearest rank nearest, packed as in `near`.
  A child whose row was not recorded ranks below all that were. Hair ticks go up or down by
  the same rule.

A fork with three or more strands leaving is a dot sized by how many.

    uv run scripts/shape-sketch.py data/daniel out.svg --root 1 --layout slots
    uv run scripts/shape-sketch.py data/daniel out.svg --at 4096 --axis entropy
    uv run scripts/shape-sketch.py data/daniel forest.svg --mode icicle --log
"""

from __future__ import annotations

import argparse
import bisect
import math
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import shape  # noqa: E402

INK = "#1d2330"
STUB = "#b9bfca"
OTHER = "#d98a1c"
FLAG = "#c0392b"
PATH = "#1f6fd1"
ROW = 7  #: px between rows
PAD = 24
GAP = 4.0  #: px kept clear between two strands on one row
REACH = 64  #: nodes past which a hair is drawn no longer

Profile = dict[int, list[tuple[float, float]]]


# ---- the record ---------------------------------------------------------------------------


class Record:
    """Per node: token, source, and what the axis and the ranking order need."""

    def __init__(self, db: Path, kids: dict[int, list[int]]) -> None:
        conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        self.token: dict[int, int] = {}
        self.source: dict[int, int] = {}
        self.parent: dict[int, int | None] = {}
        for nid, par, tok, src in conn.execute(
            "SELECT id, parent, token_id, source FROM nodes ORDER BY id"
        ):
            self.token[nid], self.source[nid], self.parent[nid] = tok, src, par
        wanted = {n: {self.token[k] for k in ks} for n, ks in kids.items() if ks}
        #: bits of the ranking at a node, by source
        self.entropy: dict[int, dict[int, float]] = {}
        #: logprob of a child's token in the ranking at its parent, best over sources
        self.logprob: dict[tuple[int, int], float] = {}
        rows = conn.execute(
            "SELECT node, source, token_id, logprob FROM edges ORDER BY node, source"
        )
        key, ps = None, []
        for node, src, tok, lp in rows:
            if (node, src) != key:
                self._close(key, ps)
                key, ps = (node, src), []
            ps.append(lp)
            if tok in wanted.get(node, ()):
                k = (node, tok)
                self.logprob[k] = max(lp, self.logprob.get(k, -math.inf))
        self._close(key, ps)

    def _close(self, key: tuple[int, int] | None, lps: list[float]) -> None:
        if key is None:
            return
        ps = [math.exp(lp) for lp in lps]
        rest = max(0.0, 1.0 - sum(ps))
        bits = -sum(p * math.log2(p) for p in ps if p > 0)
        if rest > 1e-12:
            bits -= rest * math.log2(rest)
        self.entropy.setdefault(key[0], {})[key[1]] = bits

    def rank(self, node: int) -> float:
        """The logprob `node`'s token had at its parent, or -inf where it was not recorded."""
        par = self.parent[node]
        if par is None:
            return -math.inf
        return self.logprob.get((par, self.token[node]), -math.inf)

    def step(self, node: int, axis: str) -> float | None:
        """What `node` adds to the axis, or None where the record has no value for it."""
        if axis == "tokens":
            return 1.0
        par = self.parent[node]
        if par is None:
            return None
        if axis == "entropy":
            by = self.entropy.get(par)
            if not by:
                return None
            return by.get(self.source[node], by[min(by)])
        lp = self.logprob.get((par, self.token[node]))
        return None if lp is None else -lp / math.log(2)


def positions(rec: Record, axis: str) -> tuple[dict[int, float], int]:
    """Each node's summed axis value, itself included, and how many steps had no value."""
    pos: dict[int, float] = {}
    missing = 0
    for nid in rec.token:  # ids ascend from parent to child
        step = rec.step(nid, axis)
        if step is None:
            missing += 1
            step = 0.0
        par = rec.parent[nid]
        pos[nid] = step + (pos[par] if par is not None else 0.0)
    return pos, missing


# ---- layout -------------------------------------------------------------------------------


class Frame:
    """Where a strand sits on x, which child continues a row, and which side the rest go."""

    def __init__(self, ss, kids, rec, pos, log, scale, hair, on_path) -> None:
        self.ss, self.kids, self.rec, self.hair, self.on_path = ss, kids, rec, hair, on_path
        self.pos, self.log, self.scale = pos, log, scale

    def x(self, v: float) -> float:
        return PAD + (math.log1p(v) if self.log else v) * self.scale

    def x0(self, s: shape.Strand) -> float:
        par = self.rec.parent[s.head]
        return self.x(self.pos[par] if par is not None else 0.0)

    def x1(self, s: shape.Strand) -> float:
        return self.x(self.pos[s.tail])

    def node_at(self, s: shape.Strand, n: int) -> int:
        """The `n`th node of a strand, or its tail if it is shorter."""
        at = s.head
        for _ in range(min(n, s.length) - 1):
            at = self.kids[at][0]
        return at

    def kept(self, s: shape.Strand) -> list[shape.Strand]:
        return [self.ss[k] for k in s.kids if k not in self.hair]

    def main(self, kept: list[shape.Strand]) -> shape.Strand | None:
        for k in kept:
            if k.id in self.on_path:
                return k
        return max(kept, key=lambda k: k.tokens) if kept else None

    def rank(self, s: shape.Strand) -> float:
        return self.rec.rank(s.head)


def stack(f: Frame, top: shape.Strand) -> dict[int, int]:
    rows: dict[int, int] = {}
    last = [0]

    def walk(start: shape.Strand, row: int) -> None:
        at: shape.Strand | None = start
        while at is not None:
            rows[at.id] = row
            kept = f.kept(at)
            main = f.main(kept)
            for light in sorted((k for k in kept if k is not main), key=lambda s: -s.tokens):
                last[0] += 1
                walk(light, last[0])
            at = main

    walk(top, 0)
    return rows


class Row:
    """What one row holds on x: disjoint intervals, sorted, touching ones merged."""

    __slots__ = ("starts", "ends")

    def __init__(self) -> None:
        self.starts: list[float] = []
        self.ends: list[float] = []

    def add(self, a0: float, a1: float) -> None:
        i = bisect.bisect_left(self.ends, a0)  # first that ends at or after a0
        j = bisect.bisect_right(self.starts, a1)  # past the last that starts by a1
        if i < j:
            a0, a1 = min(a0, self.starts[i]), max(a1, self.ends[j - 1])
        self.starts[i:j] = [a0]
        self.ends[i:j] = [a1]

    def clashes(self, a0: float, a1: float) -> bool:
        """Whether anything here comes within `GAP` of the interval."""
        i = bisect.bisect_left(self.starts, a1 + GAP) - 1
        return i >= 0 and self.ends[i] + GAP > a0


def _fits(profile: dict[int, Row], sub: Profile, d: int) -> bool:
    """Whether `sub` shifted by `d` rows clears everything in `profile`.

    The connector from the fork is not checked: the nearest row that fits is short of any
    strand across the fork's column whenever such a row exists, and past one a crossing is
    forced. Connectors placed earlier are in the profile, so later strands keep off them.
    """
    for r, ivs in sub.items():
        have = profile.get(r + d)
        if have is not None and any(have.clashes(a0, a1) for a0, a1 in ivs):
            return False
    return True


def _put(profile: dict[int, Row], r: int, a0: float, a1: float) -> None:
    row = profile.get(r)
    if row is None:
        row = profile[r] = Row()
    row.add(a0, a1)


def packed(f: Frame, top: shape.Strand, two_sided: bool) -> dict[int, int]:
    """Rows relative to `top`, each subtree packed against what is already placed.

    A subtree's profile is built in place on its continuing child's, so nothing is copied on
    the way up a long trunk; a branch's profile is read as intervals once, to be placed.
    """

    def flat(profile: dict[int, Row]) -> Profile:
        return {r: list(zip(row.starts, row.ends, strict=True)) for r, row in profile.items()}

    def pack(s: shape.Strand) -> tuple[dict[int, Row], dict[int, int]]:
        kept = f.kept(s)
        main = f.main(kept)
        if main is None:
            profile: dict[int, Row] = {}
            _put(profile, 0, f.x0(s), f.x1(s))
            return profile, {s.id: 0}
        profile, rows = pack(main)
        _put(profile, 0, f.x0(s), f.x1(s))
        rows[s.id] = 0
        others = [k for k in kept if k is not main]
        pivot = f.rank(main)
        if two_sided:
            above = sorted((k for k in others if f.rank(k) > pivot), key=f.rank)
            below = sorted((k for k in others if f.rank(k) <= pivot), key=lambda k: -f.rank(k))
        else:
            above, below = [], sorted(others, key=lambda k: -f.rank(k))
        xf = f.x1(s)
        for side, group in ((-1, above), (1, below)):
            for k in group:
                built, where = pack(k)
                sub = flat(built)
                d = side
                while not _fits(profile, sub, d):
                    d += side
                for r, ivs in sub.items():
                    for a0, a1 in ivs:
                        _put(profile, r + d, a0, a1)
                for r in range(side, d, side):
                    _put(profile, r, xf, xf)
                rows.update({sid: r + d for sid, r in where.items()})
        return profile, rows

    return pack(top)[1]


# ---- drawing ------------------------------------------------------------------------------


def draw(f: Frame, top: shape.Strand, rows: dict[int, int], two_sided: bool, y0: float,
         out: list[str]) -> float:
    """Draw one tree from `y0`, and say how tall it was."""
    ss = f.ss
    lo = min(rows.values())

    def y(sid: int) -> float:
        return y0 + (rows[sid] - lo) * ROW

    for sid in rows:
        s = ss[sid]
        x0, x1 = f.x0(s), f.x1(s)
        colour = PATH if sid in f.on_path else FLAG if s.deleted else INK
        width = 2.0 if sid in f.on_path else 1.2
        if s.parent is not None and rows[s.parent] != rows[sid]:
            out.append(f'<path d="M{x0:.1f},{y(s.parent):.1f} V{y(sid):.1f}" stroke="{INK}" '
                       f'stroke-opacity="0.35" stroke-width="0.6" fill="none"/>')
        out.append(f'<line x1="{x0:.1f}" y1="{y(sid):.1f}" x2="{max(x1, x0 + 0.8):.1f}" '
                   f'y2="{y(sid):.1f}" stroke="{colour}" stroke-width="{width}"/>')
    for sid in f.hair:
        s = ss[sid]
        if s.parent not in rows:
            continue
        up = ss[s.parent]
        x0 = f.x0(s)
        x1 = max(x0 + 1.0, f.x(f.pos[f.node_at(s, REACH)]))
        lift = 1.5 + 3.0 * (1 - min(1.0, s.length / REACH))
        if two_sided:
            main = f.main(f.kept(up))
            if main is not None and f.rank(s) <= f.rank(main):
                lift = -lift
        colour = FLAG if s.deleted else STUB if s.stub else OTHER
        out.append(f'<line x1="{x0:.1f}" y1="{y(up.id):.1f}" x2="{x1:.1f}" '
                   f'y2="{y(up.id) - lift:.1f}" stroke="{colour}" stroke-width="0.7"/>')
    for sid in rows:
        s = ss[sid]
        if len(s.kids) >= 3:
            rad = 0.8 + 0.6 * math.sqrt(len(s.kids))
            out.append(f'<circle cx="{f.x1(s):.1f}" cy="{y(sid):.1f}" r="{rad:.1f}" '
                       f'fill="{INK}" fill-opacity="0.7"/>')
    return (max(rows.values()) - lo + 1) * ROW


def icicle(f: Frame, top: shape.Strand, y0: float, height: float, out: list[str]) -> None:
    ss = f.ss
    stack_ = [(top, y0, y0 + height)]
    while stack_:
        s, a, b = stack_.pop()
        colour = PATH if s.id in f.on_path else FLAG if s.deleted else STUB if s.stub else INK
        x0, x1 = f.x0(s), f.x1(s)
        out.append(f'<rect x="{x0:.2f}" y="{a:.2f}" width="{max(0.5, x1 - x0):.2f}" '
                   f'height="{max(0.3, b - a - 0.15):.2f}" fill="{colour}" '
                   f'fill-opacity="{0.35 if s.stub else 0.8}"/>')
        at = a
        rest = s.tokens - s.length
        for k in sorted(s.kids, key=lambda k: -ss[k].tokens):
            share = (b - a) * ss[k].tokens / rest
            stack_.append((ss[k], at, at + share))
            at += share


# ---- main ---------------------------------------------------------------------------------


def path_strands(ss: list[shape.Strand], parent: dict[int, int | None], at: int) -> set[int]:
    nodes = set()
    n: int | None = at
    while n is not None:
        nodes.add(n)
        n = parent[n]
    return {s.id for s in ss if s.head in nodes}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="shape-sketch.py", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("tree", type=Path)
    parser.add_argument("out", type=Path)
    parser.add_argument("--root", type=int, help="draw only the tree from this root node")
    parser.add_argument("--at", type=int, help="keep the path to this node straight, and mark it")
    parser.add_argument("--mode", choices=("full", "skeleton", "icicle"), default="skeleton")
    parser.add_argument("--layout", choices=("stack", "near", "slots"), default="slots")
    parser.add_argument("--axis", choices=("tokens", "entropy", "surprisal"), default="tokens")
    parser.add_argument("--log", action="store_true", help="draw the axis as log(1 + x)")
    parser.add_argument("--cut", type=int, default=16,
                        help="longest leaf strand other than a stub that is hair")
    parser.add_argument("--width", type=int, default=1600)
    args = parser.parse_args(argv)
    sys.setrecursionlimit(20_000)

    db = args.tree / "bulk.sqlite"
    parent, deleted, kids = shape.load(db)
    ss = shape.strands(parent, deleted, kids, shape.greedy_nodes(db, parent))
    shape.measure(ss)
    rec = Record(db, kids)
    pos, missing = positions(rec, args.axis)

    on_path: set[int] = set()
    root = args.root
    if args.at is not None:
        if args.at not in parent:
            raise SystemExit(f"no node {args.at}")
        on_path = path_strands(ss, parent, args.at)
        root = next(ss[i].root for i in on_path)
    tops = [s for s in ss if s.parent is None and (root is None or s.head == root)]
    if not tops:
        raise SystemExit(f"no root {root}")
    tops.sort(key=lambda s: -s.tokens)

    hair = shape.hair(ss, args.cut, stubs=True) if args.mode == "skeleton" else set()
    hair -= on_path
    drawn = {t.head for t in tops}
    far = max(pos[s.tail] for s in ss if s.root in drawn)
    scale = (args.width - 2 * PAD) / ((math.log1p(far) if args.log else far) or 1.0)
    frame = Frame(ss, kids, rec, pos, args.log, scale, hair, on_path)

    body: list[str] = []
    y0 = PAD + 14
    axis = f"{'log ' if args.log else ''}{args.axis}"
    body.append(f'<text x="{PAD}" y="{PAD}" font-family="sans-serif" font-size="12" '
                f'fill="{INK}">x: {axis}, 0 to {far:.0f} · {args.mode} · {args.layout}'
                f'{f" · {missing} steps with no value" if args.axis != "tokens" else ""}</text>')
    for top in tops:
        y0 += 2 * PAD
        body.append(f'<text x="{PAD}" y="{y0 - 10}" font-family="sans-serif" font-size="11" '
                    f'fill="{INK}">root {top.head} · {top.tokens} tokens · {top.leaves} leaves '
                    f'· reach {top.reach}</text>')
        if args.mode == "icicle":
            band = max(24.0, 1400 * top.tokens / tops[0].tokens)
            icicle(frame, top, y0, band, body)
            y0 += band
            continue
        mine = {s.id for s in ss if s.root == top.head}
        frame.hair = hair & mine
        if args.layout == "stack":
            rows = stack(frame, top)
        else:
            rows = packed(frame, top, two_sided=args.layout == "slots")
        y0 += draw(frame, top, rows, args.layout == "slots", y0, body)

    height = int(y0 + PAD)
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{args.width}" height="{height}" '
           f'viewBox="0 0 {args.width} {height}"><rect width="100%" height="100%" fill="#fff"/>'
           + "".join(body) + "</svg>")
    args.out.write_text(svg)
    print(f"wrote {args.out}  {args.width}x{height}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
