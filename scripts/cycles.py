"""Generated runs that end in a repetition over token ids, and at what period.

`docs/SPINE.md` reads a cycle as a diagnosis rather than a fault -- from here, the model's
preference is an attractor -- and needs to know how often one arrives to say whether detecting
them is insurance or a common path. The rule stated here is what that count means:

    a run of at least MINIMUM tokens ends in a cycle when some block of at most LONGEST
    tokens repeats to the end of it, at least twice and across at least SPAN tokens.

Both conditions are there to keep ordinary language out. Two repeats of a three-token block is
six tokens of coincidence and English produces it constantly; the same block twenty times is an
attractor, and so is a twenty-token block twice. The smallest qualifying period is reported,
since a run repeating a period of 4 also repeats one of 8. No text is decoded; a repetition over
ids is a repetition.

    uv run python scripts/cycles.py data/logozoa/bulk.sqlite data/continuations/bulk.sqlite
"""

from __future__ import annotations

import json
import sqlite3
import sys
from collections import Counter

MINIMUM = 12
LONGEST = 30
SPAN = 12


def period(tail):
    """The shortest period the run ends on, or None. `tail` runs backwards from the last token."""
    for p in range(1, LONGEST + 1):
        repeats = 1
        while (repeats + 1) * p <= len(tail) and tail[repeats * p:(repeats + 1) * p] == tail[:p]:
            repeats += 1
        if repeats >= 2 and repeats * p >= SPAN:
            return p
    return None


def main(dbs):
    for db in dbs:
        conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        parent, token = {}, {}
        for i, p, t in conn.execute("select id,parent,token_id from nodes"):
            parent[i], token[i] = p, t

        runs, cycles, greedy, periods = 0, 0, 0, Counter()
        for origin, tip, params in conn.execute(
            "select a.origin,a.tip,p.json from acts a left join params p on p.id=a.params"
            " where a.op='generate' and a.tip is not null"
        ):
            heat = (json.loads(params) or {}).get("temperature") if params else None
            chain, cursor = [], tip
            while cursor is not None and cursor != origin:
                chain.append(token[cursor])
                cursor = parent[cursor]
            if len(chain) < MINIMUM:
                continue
            runs += 1
            if heat == 0:
                greedy += len(chain)
            found = period(list(reversed(chain)))
            if found:
                cycles += 1
                periods[found] += 1
        share = 100 * cycles / runs if runs else 0
        print(f"{db}: {cycles} of {runs} runs of {MINIMUM}+ tokens end in a cycle "
              f"({share:.1f}%), over {greedy} greedy positions")
        if periods:
            print("  periods: " + ", ".join(f"{p}x{n}" for p, n in sorted(periods.items())))
        conn.close()


if __name__ == "__main__":
    main(sys.argv[1:] or ["data/logozoa/bulk.sqlite", "data/continuations/bulk.sqlite"])
