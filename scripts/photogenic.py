#!/usr/bin/env -S uv run python
"""Find a stretch of a tree worth photographing: one where the mark has something to say.

    scripts/photogenic.py data/3 data/logozoa

A picture of this instrument is only worth taking where the column is doing several things
at once -- the reader's hue against the sampler's, a ramp with some spread in it rather than
one flat value, and a few transitions between them inside one screen. Scanning for that by
eye means opening roots until one looks right, which is the search this replaces.

**It reimplements the mark's three rules rather than importing them**, because they live in
`src/tokenloom/surface/page/assets/mark.js` and nothing here can run that. So this is a
finder and never a check: `scripts/check-mark.mjs` is what holds the rules to account, and a
disagreement between the two means this file has drifted and the other one is right.

The path is the one the page would draw -- `S.path` under the same continuation rule, with
what is set aside left out -- so a window it names is a window a reader can navigate to.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

from tokenloom.core import Store
from tokenloom.core import reads as R
from tokenloom.surface import reads as S

# A banner is a few lines of a reading column, which is about this many characters at the
# measure the stylesheet caps at. Windows are built to a character budget and not a token
# count, because what fits on screen is bytes of text and tokens vary by an order of
# magnitude.
WIDTH = 520
TIE = 1e-9


def classify(cells, among, took, kinds):
    """What the mark would make of each cell: its class, its place on that taker's scale,
    and whether the value under it can be read at all."""
    out = []
    for cell in cells:
        mine = [
            m for m in cell.nodes
            if m.node.id in took or kinds.get(m.node.source) == "user"
        ]
        drew = [m for m in cell.nodes if diverged(m, among)]
        picked = mine or drew
        if not picked:
            out.append((None, 0.0, False))
            continue
        places = [displaced(m, among) for m in picked]
        odd = any(p is None for p in places)
        out.append((
            "took" if mine else "drew",
            1.0 if odd else max(places),
            odd,
        ))
    return out


def ranking(mark, among):
    """The ranking this node's own source recorded here, or None where there is none to
    read -- two sources ranked, or a ranking belonging to someone else."""
    rows = among.get(mark.node.id, ())
    if len(rows) != 1 or rows[0].source != mark.node.source or rows[0].top is None:
        return None
    return rows[0]


def diverged(mark, among):
    row = ranking(mark, among)
    return row is not None and mark.logprob is not None and mark.logprob < row.top - TIE


def displaced(mark, among):
    row = ranking(mark, among)
    if row is None or mark.logprob is None:
        return None
    return min(1.0, max(0.0, 1.0 - math.exp(mark.logprob - row.top)))


def windows(cells, state):
    """Every run of consecutive cells that fills a screen's worth of text."""
    i = 0
    while i < len(cells):
        chars, j = 0, i
        while j < len(cells) and chars < WIDTH:
            chars += len(cells[j].text)
            j += 1
        if chars >= WIDTH:
            yield i, j
        i += 1


def score(state, lo, hi):
    """How much a window has to show. Variety first, then the ramp, then how often it
    changes hands -- a screen of one long run says less than the same count scattered."""
    seen = state[lo:hi]
    kinds = {s[0] for s in seen}
    spread = {}
    for cls in ("took", "drew"):
        places = [s[1] for s in seen if s[0] == cls and not s[2]]
        spread[cls] = (max(places) - min(places)) if len(places) > 1 else 0.0
    changes = sum(1 for a, b in zip(seen, seen[1:], strict=False) if a[0] != b[0])
    return (
        3 * ("took" in kinds)
        + 3 * ("drew" in kinds)
        + 1 * (None in kinds)
        + 2 * any(s[2] for s in seen)
        + 4 * (spread["took"] + spread["drew"])
        + min(changes, 12) / 3
    )


def survey(where: Path):
    with Store.open(where, verify=False) as store:
        conn = store.reader()
        kinds = {r[0]: r[1] for r in conn.execute("SELECT id, kind FROM sources")}
        best = []
        for root in R.roots(conn):
            if root.deleted:
                continue
            cells = S.path(conn, root.id, S.RULES["longest"], False)
            if len(cells) < 40:
                continue
            among = S.overlays(conn, cells)
            took = R.realised(conn, (m.node.id for c in cells for m in c.nodes))
            state = classify(cells, among, took, kinds)
            for lo, hi in windows(cells, state):
                best.append((score(state, lo, hi), root.id, lo, hi, cells, state))
        best.sort(key=lambda row: -row[0])
        return best


def show(points, where, limit=3):
    print(f"\n=== {where}")
    if not points:
        print("  nothing long enough to frame")
        return
    taken = []
    for row in points:
        # One window per root, so three suggestions are three places and not three
        # overlapping views of the same paragraph.
        if any(row[1] == seen[1] for seen in taken):
            continue
        taken.append(row)
        if len(taken) == limit:
            break
    for points_, root, lo, hi, cells, state in taken:
        seen = state[lo:hi]
        counts = {k: sum(1 for s in seen if s[0] == k) for k in ("took", "drew", None)}
        odd = sum(1 for s in seen if s[2])
        node = cells[hi - 1].nodes[-1].node.id
        text = "".join(c.text for c in cells[lo:hi])
        print(f"\n  root {root} · cells {lo}-{hi} · ends at node {node} · score {points_:.1f}")
        print(f"  reader {counts['took']} · sampler {counts['drew']} · plain {counts[None]}"
              f" · placeholder {odd}")
        print("  " + repr(text[:300]))


if __name__ == "__main__":
    for arg in sys.argv[1:] or ["data/3"]:
        show(survey(Path(arg)), arg)
