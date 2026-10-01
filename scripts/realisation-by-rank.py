#!/usr/bin/env -S uv run python
"""How often a ranked row acquired a node, by the rank it sat at.

    uv run python scripts/realisation-by-rank.py data/3 data/logozoa data/continuations

`docs/SPINE.md` leaves open *whether a well-sampled tree is its own reference arm*: the greedy
child is the likeliest to be drawn, so it should be the first row at each position to acquire
a node, and a tree visited enough would hold the model's preference as readable text rather
than as a number in a ranking. This is the measurement that document asks for, and **it has to
be taken before anything rolls a stub out on hover** -- a pointer that generates from the top
row drives that row's realisation to one and leaves the curve measuring the pointer.

**Stubs are excluded by liveness and not by archaeology.** `docs/SURFACE.md` has a stub born
set aside, so a node under a `delete` is a rollout the reader asked for and never a draw the
sampler made. Nothing rolls stubs yet, which is the point: the numbers here are what a tree
grown without them looks like, and the same script over a later tree says what the hover did
to it.

Three readings, and they answer different halves:

* **By rank** -- the curve the open question names. The share of rows at each rank with a live
  child, over every position the model ranked at.
* **By how often the position was visited** -- the hypothesis is about *well-sampled* trees, so
  a top row realised at thinly-visited positions and at heavily-visited ones separately is what
  says whether visiting is what does it.
* **Against the aggregate** -- *any rule that argmaxes an aggregate over the subtree converges
  on the greedy choice* is the claim the question turns on. Where two or more rows at one
  position have children, this asks whether the biggest subtree is the top row's. Where it is
  not, the reader steered and kept going.
"""

from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path

from tokenloom.core import Store

# Two logprobs within this are one row, as everywhere else: backends do not present near-ties
# in a reproducible order, so ranking them against each other reads noise as preference.
TIE = 1e-9

#: How many ranks to print. Past this the rows are the tail of a distribution and the
#: question is about the head.
DEPTH = 8

#: Visit buckets, as (ceiling, label). A position's visits are the rows at it that acquired a
#: live child, which is what the record can say -- a merge leaves no count behind.
VISITS = ((1, "1"), (2, "2"), (4, "3-4"), (8, "5-8"), (10**9, "9+"))


def set_aside(conn) -> set[int]:
    """Every node at or under a `delete`. This is the stub exclusion, and it is the whole of
    it: a stub is born set aside and its continuation inherits that."""
    return {
        row[0]
        for row in conn.execute("""
            WITH RECURSIVE dead(id) AS (
                SELECT id FROM nodes WHERE deleted = 1
                UNION
                SELECT n.id FROM nodes n JOIN dead d ON n.parent = d.id
            )
            SELECT id FROM dead
        """)
    }


def subtree_sizes(conn, dead: set[int]) -> dict[int, int]:
    """Nodes below each node, counting itself and skipping what is set aside.

    Iterative and not recursive: these trees run to six thousand deep on one path and the
    interpreter's stack is shallower than that.
    """
    kids: dict[int | None, list[int]] = defaultdict(list)
    for node, parent in conn.execute("SELECT id, parent FROM nodes ORDER BY id"):
        if node not in dead:
            kids[parent].append(node)
    size: dict[int, int] = {}
    for root in kids[None]:
        order, stack = [], [root]
        while stack:
            at = stack.pop()
            order.append(at)
            stack.extend(kids[at])
        for at in reversed(order):
            size[at] = 1 + sum(size[k] for k in kids[at])
    return size


def rows(conn, dead: set[int]):
    """Every ranked row at a live position, as (position, rank, child or None).

    Ranked by value within its own source, which is the only ordering a ranking has -- the
    table stores a set. Ties share the better rank, so a flat head does not hand one row a
    place the model did not give it.
    """
    at: dict[tuple[int, int], list] = defaultdict(list)
    for node, source, token, logprob in conn.execute(
        "SELECT node, source, token_id, logprob FROM edges"
    ):
        if node not in dead and logprob is not None:
            at[(node, source)].append((logprob, token))
    # `deleted` is nullable and a live node carries NULL rather than 0, so `deleted = 0`
    # matches nothing and reads every row as unrealised without saying so.
    children = {
        (parent, source, token): node
        for node, parent, token, source in conn.execute(
            "SELECT id, parent, token_id, source FROM nodes WHERE deleted IS NULL"
        )
        if node not in dead
    }
    for (node, source), ranked in at.items():
        ranked.sort(key=lambda r: (-r[0], r[1]))
        rank, previous = 0, None
        for index, (logprob, token) in enumerate(ranked, start=1):
            if previous is None or logprob < previous - TIE:
                rank, previous = index, logprob
            yield node, rank, children.get((node, source, token))


def survey(where: Path) -> None:
    with Store.open(where, verify=False) as store:
        conn = store.reader()
        dead = set_aside(conn)
        size = subtree_sizes(conn, dead)

        seen: dict[int, list[int]] = defaultdict(lambda: [0, 0])
        taken: dict[int, list[tuple[int, int]]] = defaultdict(list)
        for node, rank, child in rows(conn, dead):
            seen[rank][0] += 1
            if child is not None:
                seen[rank][1] += 1
                taken[node].append((rank, child))

        print(f"\n=== {where}")
        print(f"  {len(seen) and sum(c for c, _ in seen.values()):,} ranked rows at "
              f"{len(set(taken)) :,} positions that took one, "
              f"{len(dead):,} nodes set aside")

        print("\n  by rank")
        for rank in range(1, DEPTH + 1):
            if rank not in seen:
                continue
            count, hits = seen[rank]
            print(f"    rank {rank:>2}  {hits:>7,} of {count:>8,}   {100 * hits / count:5.1f}%")
        tail = [(c, h) for r, (c, h) in seen.items() if r > DEPTH]
        if tail:
            count = sum(c for c, _ in tail)
            hits = sum(h for _, h in tail)
            print(f"    past {DEPTH} {hits:>7,} of {count:>8,}   {100 * hits / count:5.1f}%")

        print("\n  the top row, by how often the position was visited")
        buckets: dict[str, list[int]] = defaultdict(lambda: [0, 0])
        for got in taken.values():
            label = next(name for ceiling, name in VISITS if len(got) <= ceiling)
            buckets[label][0] += 1
            buckets[label][1] += any(rank == 1 for rank, _ in got)
        for _, label in VISITS:
            if label not in buckets:
                continue
            count, hits = buckets[label]
            print(f"    {label:>4} rows taken  {hits:>7,} of {count:>8,}"
                  f"   {100 * hits / count:5.1f}%")

        print("\n  where two or more rows were taken, is the biggest subtree the top row's")
        agrees = total = 0
        for got in taken.values():
            if len(got) < 2:
                continue
            total += 1
            best = max(got, key=lambda g: (size.get(g[1], 0), -g[1]))
            agrees += best[0] == 1
        if total:
            print(f"    {agrees:,} of {total:,}   {100 * agrees / total:5.1f}%")
        else:
            print("    no position took two rows")


if __name__ == "__main__":
    for arg in sys.argv[1:] or ["data/3"]:
        survey(Path(arg))
