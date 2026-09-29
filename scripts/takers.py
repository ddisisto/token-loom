"""Where each taker of a divergence lands, banded by the gap it paid and by the rows it had.

`docs/SPINE.md` reports two things from here. **Recorded depth bounds what a divergence can
say**, and since the recording rule spends rows on flat positions, depth falls as the gap rises
-- so banding the takers by gap reads the rule back out, and banding by depth is the correction.
And **neither taker chooses by how long the list is**, which the ceiling being raised from ten
rows to fifty partway through `data/logozoa` is what makes readable.

It also carries a negative result, kept so it can be re-run. A deviation splits as
`deviation = gap + excess`, where `gap = top1 - top2` is the toll for leaving the argmax at all
and `excess = top2 - taken` is how far past the best alternative the taker went. That split was
proposed as what tells a deliberate divergence from a hot draw. It does not: the two populations
sit in nearly the same place on it.

    uv run python scripts/takers.py data/logozoa/bulk.sqlite data/continuations/bulk.sqlite

A position is judged against the ranking at its parent for its own source, so an authored token
contributes nothing. An uncovered position -- the taken token absent from the recorded rows --
has no excess to read and is left out of both populations, and carries the span to the lowest
row into the window sums so that a sum is over every position. **These are what an older tree
discarded**: under `token-loom/3` a draw is valued whatever the rows reached, so a tree written
since should show none of them where a source drew.
"""

from __future__ import annotations

import json
import sqlite3
import statistics as st
import sys
from collections import defaultdict
from typing import NamedTuple

# Two rows within this of each other are one row for the purpose of asking whether the draw
# took the second. Backends do not present near-ties in a reproducible order and `docs/CORE.md`
# does not enforce descending logprob, so exact equality would count the wrong thing.
TIE = 1e-9

# Where the temperature bands are cut, as (ceiling, label), matching `scripts/stub-gate.py`.
BANDS = [(0.001, "0.0 greedy"), (0.35, "0.05-0.35"), (0.8, "0.4-0.8"), (9.9, "0.9+")]

# Gap bands the two populations are compared inside. The reader works where the model was torn
# and an automatic gate fires where it was sure, so an unmatched comparison compares regions.
GAP_BANDS = [(0.5, "0.0-0.5"), (1.0, "0.5-1.0"), (2.0, "1.0-2.0"), (4.0, "2.0-4.0"),
             (float("inf"), "4.0+")]

# A window short enough that a 200-token run carries several of them. Longer windows left
# `data/continuations` with no run long enough to rank its own windows against each other,
# which is what the comparison below needs.
WINDOW = 25


def load(db):
    """Parents, tokens, sources, and every ranking, keyed as the record keys them."""
    conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    node = {}
    for i, p, t, s in conn.execute("select id,parent,token_id,source from nodes"):
        node[i] = (p, t, s)
    ranking = defaultdict(dict)
    for n, src, tok, logprob in conn.execute(
        "select node,source,token_id,logprob from edges"
    ):
        ranking[(n, src)][tok] = logprob
    return conn, node, ranking


class Position(NamedTuple):
    """What one position on a path says, read against the ranking it stood in."""

    kind: str          # 'ranked' | 'uncovered'
    gap: float         # top1 - top2
    deviation: float   # top1 - taken, or the span to the lowest row where uncovered
    depth: int         # rows recorded here, which is the choice the taker actually had
    rank: int          # computed here: the taken row's place in logprob order


def split(rows, token):
    """A Position, or None where the ranking holds fewer than two rows.

    A token the ranking does not carry has no deviation to read. **A tree written under
    `token-loom/3` should have none of these where the source drew**, since what was drawn is
    valued -- so the count is a count of what an older tree discarded at record time, and the
    span to the lowest row is put in the deviation's place only so a sum has something. It is
    marked apart so anything needing a value can drop it.
    """
    if len(rows) < 2:
        return None
    ordered = sorted(rows.values(), reverse=True)
    gap = ordered[0] - ordered[1]
    taken = rows.get(token)
    if taken is None:
        return Position("uncovered", gap, ordered[0] - ordered[-1], len(rows), len(rows))
    by_logprob = sorted(rows, key=lambda t: -rows[t])
    return Position("ranked", gap, ordered[0] - taken, len(rows), by_logprob.index(token))


def runs(conn, node, ranking):
    """Every generated run, as (temperature, [Position]) in path order."""
    out = []
    for origin, tip, params in conn.execute(
        "select a.origin,a.tip,p.json from acts a left join params p on p.id=a.params"
        " where a.op='generate' and a.tip is not null"
    ):
        heat = (json.loads(params) or {}).get("temperature") if params else None
        chain, cursor = [], tip
        while cursor is not None and cursor != origin:
            chain.append(cursor)
            cursor = node[cursor][0]
        path = []
        for child in reversed(chain):
            parent, token, source = node[child]
            got = split(ranking.get((parent, source), {}), token)
            if got is not None:
                path.append(got)
        if path:
            out.append((heat, path))
    return out


def reader(conn, node, ranking):
    """Every `realise` as a Position, with the top-row count beside it.

    The edge an act took is read off the node it made -- `origin`, the tip's source and the
    tip's token -- because that is the whole of what the act stores.
    """
    out, unranked, argmax = [], 0, 0
    for origin, tip in conn.execute(
        "select origin,tip from acts where op='realise' and tip is not null"
    ):
        token, source = node[tip][1], node[tip][2]
        rows = ranking.get((origin, source), {})
        got = split(rows, token)
        if got is None:
            unranked += 1
            continue
        if got.deviation <= TIE:
            argmax += 1
            continue
        out.append(got)
    return out, unranked, argmax


def gap_band(gap):
    return next(name for ceiling, name in GAP_BANDS if gap < ceiling)


def on_line(excesses):
    return 100 * sum(1 for e in excesses if e <= TIE) / len(excesses)


def by_gap(name, positions):
    """A population's excess, banded by the gap it was paid against.

    `depth` is beside it because it is what bounds the excess: a position recorded to two rows
    offers no row past the second, so taking the second there is the only divergence available
    and says nothing about what was wanted.
    """
    print(f"\n{name}")
    print(f"{'gap band':>10} {'n':>7} {'med gap':>8} {'med excess':>11} {'took row 2':>11} "
          f"{'excess > 1':>11} {'med depth':>10} {'depth 2':>8}")
    banded = defaultdict(list)
    for p in positions:
        banded[gap_band(p.gap)].append(p)
    for _, label in GAP_BANDS:
        here = banded.get(label)
        if not here:
            continue
        excess = [p.deviation - p.gap for p in here]
        far = 100 * sum(1 for e in excess if e > 1) / len(excess)
        shallow = 100 * sum(1 for p in here if p.depth == 2) / len(here)
        print(f"{label:>10} {len(here):>7} {st.median([p.gap for p in here]):>8.2f} "
              f"{st.median(excess):>11.2f} {on_line(excess):>10.0f}% {far:>10.0f}% "
              f"{st.median([p.depth for p in here]):>10.0f} {shallow:>7.0f}%")


# Depth buckets, as (ceiling, label). The top three exist because the recording ceiling was
# raised mid-tree, which is what lets the taken rank be read against how many rows were there.
DEPTH_BANDS = [(2, "2"), (3, "3"), (4, "4"), (9, "5-9"), (19, "10-19"), (49, "20-49"),
               (10 ** 9, "50+")]


def by_depth(name, positions):
    """The same population, banded by how many rows it actually had to choose among.

    `rank / depth` is the column the others are here to be read against: a taker choosing
    without regard to the rows would hold it near a half whatever the depth, and one choosing
    among the rows would not.
    """
    print(f"\n{name}")
    print(f"{'depth':>10} {'n':>7} {'med gap':>8} {'med excess':>11} {'took row 2':>11} "
          f"{'med rank':>9} {'rank/depth':>11}")
    banded = defaultdict(list)
    for p in positions:
        banded[next(label for ceiling, label in DEPTH_BANDS if p.depth <= ceiling)].append(p)
    for _, label in DEPTH_BANDS:
        here = banded.get(label)
        if not here:
            continue
        excess = [p.deviation - p.gap for p in here]
        print(f"{label:>10} {len(here):>7} {st.median([p.gap for p in here]):>8.2f} "
              f"{st.median(excess):>11.2f} {on_line(excess):>10.0f}% "
              f"{st.median([p.rank for p in here]):>9.0f} "
              f"{st.median([p.rank / (p.depth - 1) for p in here]):>11.2f}")


def windows(path):
    """One run's windows, as (divergence count, summed deviation).

    If the two rank a run's windows alike, counting divergences and summing their prices are
    one map over that run; if they do not, they are two. Pooling runs would answer a different
    question, since a hotter run carries more of both.
    """
    out = []
    for start in range(0, len(path) - WINDOW + 1, WINDOW):
        chunk = [p.deviation for p in path[start:start + WINDOW] if p.deviation > TIE]
        out.append((len(chunk), sum(chunk)))
    return out


def spearman(pairs):
    def ranks(values):
        order = sorted(range(len(values)), key=lambda i: values[i])
        out = [0.0] * len(values)
        i = 0
        while i < len(order):
            j = i
            while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
                j += 1
            shared = (i + j) / 2
            for k in range(i, j + 1):
                out[order[k]] = shared
            i = j + 1
        return out

    xs, ys = ranks([a for a, _ in pairs]), ranks([b for _, b in pairs])
    mx, my = st.fmean(xs), st.fmean(ys)
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys, strict=True))
    den = (sum((x - mx) ** 2 for x in xs) * sum((y - my) ** 2 for y in ys)) ** 0.5
    return num / den if den else float("nan")


def summarise(name, positions):
    excess = [p.deviation - p.gap for p in positions]
    print(f"{name:>20}  n {len(positions):<6} med gap "
          f"{st.median([p.gap for p in positions]):.2f}  med excess {st.median(excess):.2f}  "
          f"took row 2 {on_line(excess):.0f}%  med depth "
          f"{st.median([p.depth for p in positions]):.0f}")


def main(dbs):
    for db in dbs:
        conn, node, ranking = load(db)
        print(f"\n=== {db} ===")

        paths = runs(conn, node, ranking)
        drawn = [(h, p) for h, path in paths for p in path
                 if p.kind == "ranked" and p.deviation > TIE]
        uncovered = sum(1 for _, path in paths for p in path if p.kind == "uncovered")
        taken, unranked, argmax = reader(conn, node, ranking)
        print(f"sampler divergences {len(drawn)}, uncovered {uncovered}")
        print(f"reader divergences  {len(taken)}, unranked {unranked}, "
              f"realises of the top row {argmax}")

        print("\n--- where each population sits on deviation = gap + excess ---")
        if taken:
            summarise("reader (realise)", taken)
        if drawn:
            summarise("sampler (generate)", [p for _, p in drawn])

        if taken:
            by_gap("--- reader, banded by the gap it was paid against ---", taken)
        floor = -1.0
        for ceiling, label in BANDS:
            here = [p for h, p in drawn if h is not None and floor < h <= ceiling]
            floor = ceiling
            if len(here) >= 30:
                by_gap(f"--- sampler at {label}, same banding ---", here)

        if taken:
            by_depth("--- reader, banded by the rows it had ---", taken)
        hot = [p for h, p in drawn if h is not None and h > 0.8]
        if len(hot) >= 30:
            by_depth("--- sampler at 0.9+, banded by the rows it had ---", hot)

        print(f"\n--- {WINDOW}-token windows, within one run: count against cost ---")
        print(f"{'draw':>12} {'runs':>6} {'median Spearman':>16}")
        floor = -1.0
        for ceiling, label in BANDS:
            per_run = []
            for heat, path in paths:
                if heat is None or not floor < heat <= ceiling:
                    continue
                pairs = windows(path)
                if len(pairs) >= 4 and len({c for c, _ in pairs}) > 1:
                    per_run.append(spearman(pairs))
            floor = ceiling
            if per_run:
                print(f"{label:>12} {len(per_run):>6} {st.median(per_run):>16.3f}")
        conn.close()


if __name__ == "__main__":
    main(sys.argv[1:] or ["data/logozoa/bulk.sqlite", "data/continuations/bulk.sqlite"])
