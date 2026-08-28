#!/usr/bin/env python
"""Build a synthetic tree and time the reads over it.

**No model and no server.** The rows are inserted directly, because what is being measured
is the store and not the backend -- and a tree big enough to hurt would take days to
generate honestly.

The shape is meant to be plausible rather than adversarial: mostly linear, branching about
one node in fourteen, with a ranking at every node. What the numbers are being weighed
against is whoever is asking; this script only produces them.

    uv run scripts/scale.py
    uv run scripts/scale.py --nodes 100000 --top-n 40
"""

from __future__ import annotations

import argparse
import random
import tempfile
import time
from pathlib import Path

from tokenloom.core import Store, violations
from tokenloom.core import reads as R

VOCAB_SIZE = 300


def build(path: Path, nodes: int, top_n: int, seed: int) -> Store:
    random.seed(seed)
    store = Store.initialise(path, vocabulary="synthetic")
    conn = store.conn
    conn.execute("INSERT INTO sources (id, kind, name) VALUES (1,'user',''),(2,'model','m')")
    conn.executemany(
        "INSERT INTO vocab VALUES (?, ?)",
        [(i, bytes([97 + i % 26])) for i in range(VOCAB_SIZE)],
    )
    conn.execute("INSERT INTO params VALUES (1, '{}')")
    conn.execute("INSERT INTO nodes (id, parent, token_id, source) VALUES (1, NULL, 0, 2)")

    rows: list[tuple] = []
    frontier = [1]
    # A fresh token per child keeps (parent, token_id, source) unique. Reusing one is what
    # the merge key is for, and it rejects this generator rather than the other way round.
    next_token: dict[int, int] = {}
    for node_id in range(2, nodes + 1):
        parent = frontier[-1] if random.random() < 0.93 else random.choice(frontier)
        token = next_token.get(parent, 0)
        next_token[parent] = token + 1
        rows.append((node_id, parent, token % VOCAB_SIZE, 2))
        frontier.append(node_id)
        if len(frontier) > 400:
            frontier.pop(0)
    conn.executemany("INSERT INTO nodes (id, parent, token_id, source) VALUES (?,?,?,?)", rows)

    edges = []
    for node_id in range(1, nodes + 1):
        for rank, token in enumerate(random.sample(range(VOCAB_SIZE), top_n)):
            edges.append((node_id, 2, rank, token, -random.random() * 8))
    conn.executemany("INSERT INTO edges VALUES (?,?,?,?,?)", edges)

    conn.executemany(
        "INSERT INTO acts (op, source, origin, tip, created, params, seed, terminator) "
        "VALUES ('generate', 2, ?, ?, '2026-01-01T00:00:00Z', 1, 1, 'limit')",
        [(row[1], row[0]) for row in rows[::8]],
    )
    conn.commit()
    return store


def timed(label: str, fn) -> None:
    start = time.perf_counter()
    fn()
    print(f"  {label:<50} {(time.perf_counter() - start) * 1000:9.1f} ms")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--nodes", type=int, default=20000)
    ap.add_argument("--top-n", type=int, default=20, dest="top_n")
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--liveness-sample", type=int, default=2000, dest="sample")
    args = ap.parse_args()

    path = Path(tempfile.mkdtemp()) / "scale"
    start = time.perf_counter()
    store = build(path, args.nodes, args.top_n, args.seed)
    conn = store.conn
    counts = {
        table: conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        for table in ("nodes", "edges", "acts")
    }
    deepest = max(range(1, args.nodes + 1), key=lambda n: R.depth(conn, n) if n % 97 == 0 else 0)
    print(
        f"{counts['nodes']} nodes, {counts['edges']} edges, {counts['acts']} acts, "
        f"depth {R.depth(conn, deepest)}, built in {time.perf_counter() - start:.1f}s"
    )
    print(f"  {path}  ({path.joinpath('bulk.sqlite').stat().st_size / 1e6:.1f} MB)\n")

    timed("violations()   -- runs on every open for writing", lambda: violations(conn))
    timed("path_nodes(deepest)", lambda: R.path_nodes(conn, deepest))
    timed("path_bytes(deepest)", lambda: R.path_bytes(conn, deepest))
    timed("unrealised_edges(one node)", lambda: R.unrealised_edges(conn, 1))
    timed("node_logprob(one node)", lambda: R.node_logprob(conn, deepest))
    timed("frequency(one node)", lambda: R.frequency(conn, args.nodes // 2))
    timed("is_live(one node)", lambda: R.is_live(conn, deepest))
    timed("branch_points()", lambda: R.branch_points(conn))
    timed("walk() over the whole tree", lambda: list(R.walk(conn)))
    timed(
        f"is_live over {args.sample} nodes -- the N+1 form",
        lambda: [R.is_live(conn, n) for n in range(1, args.sample + 1)],
    )
    store.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
