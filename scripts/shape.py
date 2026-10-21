#!/usr/bin/env python
"""What a tree looks like with its text taken away: strands, forks and how they nest.

**No server and no model.** It reads the store read-only and holds the whole parent column
in memory, which is a few megabytes at a hundred thousand nodes.

A **strand** is a maximal run of nodes each with exactly one child, opened at a root or at
a child of a fork and closed at a fork or a leaf. Collapsing to strands is what leaves the
shape: a tree grown by drawing is long runs with nothing on them, and the forks carry all of
its structure. It is `docs/MAP.md`'s word, and not `docs/SURFACE.md`'s *segment*, which means
the shortest run of nodes whose bytes decode.

A leaf strand is a **stub** when every act that wrote any node past its head drew at
temperature 0, which is `docs/SPINE.md`'s test for the reference arm. The head is left out
because a hover's stub opens on the row it was taken from, so a leaf of one node is not one.
It is the one cut through the acts taken here, because without it a fork count mixes forks
someone made with stubs a hover left.

    uv run scripts/shape.py data/daniel
    uv run scripts/shape.py data/daniel --json data/shape.json
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import statistics
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(slots=True)
class Strand:
    id: int
    head: int  #: first node
    tail: int  #: last node; a fork or a leaf
    length: int  #: nodes
    depth: int  #: tokens from the root to the head, exclusive
    parent: int | None  #: the strand whose tail this one hangs from
    root: int  #: the root node of the tree it is in
    stub: bool
    deleted: bool  #: any of its nodes is flagged
    kids: list[int] = field(default_factory=list)
    # Filled by `measure`.
    tokens: int = 0  #: nodes in the subtree from the head
    leaves: int = 0
    reach: int = 0  #: the longest path from the head to a leaf, in tokens
    strahler: int = 0


def load(db: Path) -> tuple[dict[int, int | None], dict[int, bool], dict[int, list[int]]]:
    conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    parent: dict[int, int | None] = {}
    deleted: dict[int, bool] = {}
    kids: dict[int, list[int]] = {}
    for nid, par, dele in conn.execute("SELECT id, parent, deleted FROM nodes ORDER BY id"):
        parent[nid] = par
        deleted[nid] = bool(dele)
        kids.setdefault(nid, [])
        if par is not None:
            kids.setdefault(par, []).append(nid)
    return parent, deleted, kids


def greedy_nodes(db: Path, parent: dict[int, int | None]) -> set[int]:
    """Nodes every writing act of which drew at temperature 0."""
    conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    temps = {pid: json.loads(body).get("temperature")
             for pid, body in conn.execute("SELECT id, json FROM params")}
    hot: set[int] = set()
    cold: set[int] = set()
    rows = conn.execute(
        "SELECT op, origin, tip, params FROM acts "
        "WHERE op IN ('create', 'generate', 'realise') AND tip IS NOT NULL"
    )
    for op, origin, tip, pid in rows:
        greedy = op == "generate" and temps.get(pid) == 0
        at: int | None = tip
        while at is not None and at != origin:
            (cold if greedy else hot).add(at)
            at = parent[at]
    return cold - hot


def strands(parent, deleted, kids, greedy: set[int]) -> list[Strand]:
    out: list[Strand] = []
    roots = [n for n, p in parent.items() if p is None]
    # (head, parent strand, depth, root)
    stack: list[tuple[int, int | None, int, int]] = [(r, None, 0, r) for r in reversed(roots)]
    while stack:
        head, up, depth, root = stack.pop()
        run = [head]
        while len(kids[run[-1]]) == 1:
            run.append(kids[run[-1]][0])
        s = Strand(
            id=len(out), head=head, tail=run[-1], length=len(run), depth=depth, parent=up,
            root=root,
            stub=not kids[run[-1]] and len(run) > 1 and all(n in greedy for n in run[1:]),
            deleted=any(deleted[n] for n in run),
        )
        out.append(s)
        if up is not None:
            out[up].kids.append(s.id)
        for k in reversed(kids[s.tail]):
            stack.append((k, s.id, depth + len(run), root))
    return out


def measure(ss: list[Strand]) -> None:
    """Subtree tokens, leaves, reach and Strahler order, children before parents."""
    for s in reversed(ss):  # a parent is always emitted before its children
        if not s.kids:
            s.tokens, s.leaves, s.reach, s.strahler = s.length, 1, s.length, 1
            continue
        below = [ss[k] for k in s.kids]
        s.tokens = s.length + sum(b.tokens for b in below)
        s.leaves = sum(b.leaves for b in below)
        s.reach = s.length + max(b.reach for b in below)
        top = max(b.strahler for b in below)
        s.strahler = top + 1 if sum(b.strahler == top for b in below) > 1 else top


def quantiles(xs: list[int], qs=(0.1, 0.25, 0.5, 0.75, 0.9, 0.99)) -> str:
    if not xs:
        return "-"
    xs = sorted(xs)
    pick = [xs[min(len(xs) - 1, int(q * len(xs)))] for q in qs]
    labels = " ".join(f"p{int(q * 100)}={v}" for q, v in zip(qs, pick, strict=True))
    return f"n={len(xs)} mean={statistics.fmean(xs):.1f} {labels} max={xs[-1]}"


def heavy_paths(ss: list[Strand], top: Strand) -> list[list[int]]:
    """Heavy-path decomposition by subtree tokens: each path follows the heaviest child."""
    paths: list[list[int]] = []
    stack = [top.id]
    while stack:
        at = ss[stack.pop()]
        path = [at.id]
        while at.kids:
            heavy = max(at.kids, key=lambda k: ss[k].tokens)
            stack.extend(k for k in at.kids if k != heavy)
            at = ss[heavy]
            path.append(at.id)
        paths.append(path)
    return paths


def report(ss: list[Strand]) -> None:
    by_root: dict[int, list[Strand]] = {}
    for s in ss:
        by_root.setdefault(s.root, []).append(s)
    total = sum(s.length for s in ss)
    forks = [s for s in ss if s.kids]
    leaves = [s for s in ss if not s.kids]
    print(f"{total} nodes  {len(by_root)} roots  {len(ss)} strands  "
          f"{len(forks)} forks  {len(leaves)} leaves")
    print(f"stubs {sum(s.stub for s in ss)}  "
          f"({sum(s.length for s in ss if s.stub)} nodes)  "
          f"strands holding a flagged node {sum(s.deleted for s in ss)}")

    print("\nper root (largest first)")
    print(f"  {'root':>7} {'tokens':>7} {'strands':>7} {'forks':>6} {'leaves':>6} "
          f"{'reach':>6} {'strahler':>8} {'trunk':>6} {'trunk%':>6} {'paths90':>7}")
    for root, group in sorted(by_root.items(), key=lambda kv: -kv[1][0].tokens):
        top = group[0]
        paths = heavy_paths(ss, top)
        trunk = sum(ss[i].length for i in paths[0])
        weights = sorted((sum(ss[i].length for i in p) for p in paths), reverse=True)
        acc, need = 0, 0
        for w in weights:
            acc += w
            need += 1
            if acc >= 0.9 * top.tokens:
                break
        print(f"  {root:>7} {top.tokens:>7} {len(group):>7} "
              f"{sum(1 for s in group if s.kids):>6} {top.leaves:>6} {top.reach:>6} "
              f"{top.strahler:>8} {trunk:>6} {100 * trunk / top.tokens:>5.0f}% {need:>7}")

    print("\nstrand length, tokens")
    print("  all          ", quantiles([s.length for s in ss]))
    print("  inner        ", quantiles([s.length for s in forks if s.parent is not None]))
    print("  leaf         ", quantiles([s.length for s in leaves]))
    print("  leaf stub    ", quantiles([s.length for s in leaves if s.stub]))
    print("  leaf other   ", quantiles([s.length for s in leaves if not s.stub]))

    print("\nfork arity")
    arity = Counter(len(s.kids) for s in forks)
    print("  " + "  ".join(f"{k}:{v}" for k, v in sorted(arity.items())))

    print("\nat a fork, how many children are leaves ending within 16 tokens")
    lateral = Counter()
    for s in forks:
        short = sum(1 for k in s.kids if not ss[k].kids and ss[k].length <= 16)
        lateral["all" if short == len(s.kids) else
                "all but one" if short == len(s.kids) - 1 else
                "fewer"] += 1
    print("  " + "  ".join(f"{k}: {v}" for k, v in lateral.items()))

    print("\nat a fork, the heaviest child's share of what is below")
    shares = [max(ss[k].tokens for k in s.kids) / (s.tokens - s.length) for s in forks]
    bins = Counter(min(9, int(x * 10)) for x in shares)
    print("  " + "  ".join(f"{b / 10:.1f}+:{bins[b]}" for b in range(10)))

    print("\nfork nesting, strands from the root to a leaf")
    nest = []
    for s in leaves:
        n, at = 0, s
        while at.parent is not None:
            n += 1
            at = ss[at.parent]
        nest.append(n)
    print("  ", quantiles(nest))

    print("\nwhere forks sit, tokens from the root (deciles of each root's reach)")
    rows = []
    for _root, group in by_root.items():
        reach = group[0].reach
        if reach < 50:
            continue
        rows.extend(min(9, int(10 * (s.depth + s.length) / reach)) for s in group if s.kids)
    hist = Counter(rows)
    print("  " + "  ".join(f"{d}0%:{hist[d]}" for d in range(10)))

    knots(ss, forks)
    hairs(ss, total)


def knots(ss: list[Strand], forks: list[Strand], gaps=(1, 4, 16)) -> None:
    """Forks joined by an inner strand no longer than `gap`, taken as one place."""
    print("\nknots: forks within `gap` tokens of the fork above them, joined")
    for gap in gaps:
        top: dict[int, int] = {}  # fork strand -> the fork strand opening its knot
        for s in forks:  # parents come first
            up = s.parent
            top[s.id] = top[up] if up is not None and s.length <= gap else s.id
        size = Counter(top.values())
        out = Counter()
        span: dict[int, tuple[int, int]] = {}
        for s in forks:
            k = top[s.id]
            out[k] += sum(1 for c in s.kids if c not in top or top[c] != k)
            lo, hi = span.get(k, (s.depth + s.length, s.depth + s.length))
            span[k] = (min(lo, s.depth + s.length), max(hi, s.depth + s.length))
        multi = [k for k, n in size.items() if n > 1]
        print(f"  gap<={gap:<3} {len(size)} knots ({len(multi)} of more than one fork)")
        print("    forks in a knot  ", quantiles(list(size.values())))
        print("    strands leaving  ", quantiles(list(out.values())))
        print("    tokens it spans  ", quantiles([hi - lo for lo, hi in span.values()]))


def hairs(ss: list[Strand], total: int, cuts=(16, 48, 128)) -> None:
    """Leaf strands no longer than `cut`, and the tree left once they are taken away.

    Cut by length alone, and then with every stub counted as hair whatever its length: a
    ranking whose rows were each rolled out is a fan of stubs, some of them hundreds long.
    """
    print("\nhairs: leaf strands of at most `cut` tokens, and the skeleton without them")
    for stubs_too in (False, True):
        for cut in cuts:
            skeleton(ss, hair(ss, cut, stubs_too), total,
                     f"{'stubs + ' if stubs_too else ''}cut<={cut}")


def hair(ss: list[Strand], cut: int, stubs: bool) -> set[int]:
    """Leaf strands of at most `cut` tokens, and every stub if `stubs`.

    **The heaviest child at a fork is never hair**, nor is a root, so the path a tree mostly
    is never cut out of it: a long greedy draw someone asked for passes the stub test as
    well as a hover's does, and one that carries its tree would otherwise vanish.
    """
    out: set[int] = set()
    for s in ss:
        if s.kids:
            continue
        if s.parent is None or max(ss[s.parent].kids, key=lambda k: ss[k].tokens) == s.id:
            continue
        if s.length <= cut or stubs and s.stub:
            out.add(s.id)
    return out


def skeleton(ss: list[Strand], hair: set[int], total: int, label: str) -> None:
    mass = sum(ss[i].length for i in hair)
    # A strand stays a fork of the skeleton when at least two children are not hair.
    kept = sum(1 for s in ss if sum(1 for k in s.kids if k not in hair) >= 2)
    bare = sum(1 for s in ss if s.id not in hair and s.kids and all(k in hair for k in s.kids))
    leaves = sum(1 for s in ss if not s.kids and s.id not in hair) + bare
    stubs = sum(1 for i in hair if ss[i].stub)
    print(f"  {label:<18} {len(hair)} hairs ({stubs} stubs), "
          f"{mass} tokens ({100 * mass / total:.0f}%)  "
          f"skeleton: {kept} forks, {leaves} leaves")


def dump(ss: list[Strand], out: Path) -> None:
    rows = [{k: getattr(s, k) for k in Strand.__slots__} for s in ss]
    out.write_text(json.dumps(rows))
    print(f"\nwrote {len(rows)} strands to {out}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="shape.py", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("tree", type=Path)
    parser.add_argument("--json", type=Path, help="write the strands here as well")
    args = parser.parse_args(argv)

    db = args.tree / "bulk.sqlite"
    parent, deleted, kids = load(db)
    ss = strands(parent, deleted, kids, greedy_nodes(db, parent))
    measure(ss)
    report(ss)
    if args.json:
        dump(ss, args.json)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
