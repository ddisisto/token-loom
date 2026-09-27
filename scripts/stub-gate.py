"""What a stub would be spawned at, and how much room it would get.

`docs/SPINE.md` selects stubs by the gap between a ranking's top two rows rather than by the
deviation, and sets a stub's depth from the distance to the next one. Both numbers under *Evidence
in hand* come from here, and both are provisional: they were measured over a tree almost
nothing steered, so the divergences in them are the sampler's and not a reader's. Re-run this
against a document the loop actually produced and expect the gate to move.

    uv run python scripts/stub-gate.py data/continuations/bulk.sqlite

Positions are counted only inside generated runs, walked origin-to-tip through parents, and a
position is judged against the ranking at its parent for its own source -- so an authored token
contributes nothing, having no ranking to disagree with.
"""

from __future__ import annotations

import json
import sqlite3
import statistics as st
import sys
from collections import defaultdict

# Tokens of a 400-token screen, at the reading column's current measure: about 24 lines of
# about 17 tokens. It scales the densities into something a reader can picture and is not
# load-bearing -- every rate below is per position underneath.
SCREEN = 400

# Where the temperature bands are cut, as (ceiling, label). Greedy is its own band because it
# cannot diverge at all, which is the finding rather than an artefact of the cut.
BANDS = [(0.001, "0.0 greedy"), (0.35, "0.05-0.35"), (0.8, "0.4-0.8"), (9.9, "0.9+")]


def read(db):
    """Every generated run, as a list of (deviation, gap) in path order.

    A censored position -- the draw fell past what was recorded -- carries a deviation we know
    only a bound for, so it is given one larger than any real value. That is honest for a gate,
    which only ever asks whether a threshold was passed.
    """
    conn = sqlite3.connect(db)
    parent, token, source = {}, {}, {}
    for i, p, t, s in conn.execute("select id,parent,token_id,source from nodes"):
        parent[i], token[i], source[i] = p, t, s
    ranking = defaultdict(dict)
    for node, src, tok, logprob in conn.execute(
        "select node,source,token_id,logprob from edges"
    ):
        ranking[(node, src)][tok] = logprob

    runs = []
    for origin, tip, params in conn.execute(
        "select a.origin,a.tip,p.json from acts a left join params p on p.id=a.params"
        " where a.op='generate' and a.tip is not null"
    ):
        heat = (json.loads(params) or {}).get("temperature") if params else None
        chain, node = [], tip
        while node is not None and node != origin:
            chain.append(node)
            node = parent[node]
        out = []
        for node in reversed(chain):
            rows = ranking.get((parent[node], source[node]))
            if not rows:
                continue
            ordered = sorted(rows.values(), reverse=True)
            gap = ordered[0] - ordered[1] if len(ordered) > 1 else float("inf")
            taken = rows.get(token[node])
            deviation = float("inf") if taken is None else ordered[0] - taken
            out.append((deviation, gap))
        if out:
            runs.append((heat, out))
    return runs


def band(heat):
    if heat is None:
        return None
    return next((name for ceiling, name in BANDS if heat <= ceiling), None)


def spacing(runs, hit):
    """Spawns, and the run of unselected positions before each -- a stub's display depth."""
    gaps, spawns, total = [], 0, 0
    for _, run in runs:
        since = 0
        for deviation, gap in run:
            total += 1
            if hit(deviation, gap):
                gaps.append(since)
                since = 0
                spawns += 1
            else:
                since += 1
    return gaps, spawns, total


def show(name, runs, hit):
    gaps, spawns, total = spacing(runs, hit)
    if not spawns:
        return print(f"{name:<32} {0:>8}")
    deep = 100 * sum(1 for g in gaps if g >= 8) / len(gaps)
    print(f"{name:<32} {spawns:>8} {SCREEN * spawns / total:>10.0f} "
          f"{st.median(gaps):>11.0f} {deep:>13.0f}%")


def main(db):
    runs = read(db)
    print("--- how often the draw leaves the argmax, by what it was asked for ---")
    print(f"{'draw':>12} {'positions':>10} {'diverged':>9} {'rate':>7}")
    by = defaultdict(lambda: [0, 0])
    for heat, run in runs:
        name = band(heat)
        if name is None:
            continue
        for deviation, _ in run:
            by[name][0] += 1
            by[name][1] += deviation > 0
    for _, name in BANDS:
        seen, diverged = by.get(name, [0, 0])
        if seen:
            print(f"{name:>12} {seen:>10} {diverged:>9} {100 * diverged / seen:>6.1f}%")

    print(f"\n--- what a gate admits, and the room it leaves (screen = {SCREEN} tokens) ---")
    print(f"{'gate':<32} {'spawns':>8} {'per screen':>10} {'median room':>11} {'room >= 8':>14}")
    show("every divergence", runs, lambda f, g: f > 0)
    for t in (1.0, 2.0, 3.0):
        show(f"deviation > {t}", runs, lambda f, g, t=t: f > t)
    for t in (0.5, 1.0, 2.0):
        show(f"gap > {t}", runs, lambda f, g, t=t: f > 0 and g > t)
    # Deviation adds nothing until its threshold passes the gap's, since a draw that left the
    # argmax took something at or below the second row. These lines are the demonstration.
    for g, f in ((1.0, 1.0), (2.0, 2.0)):
        show(f"gap > {g} and deviation > {f}", runs, lambda x, y, g=g, f=f: x > f and y > g)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "data/continuations/bulk.sqlite")
