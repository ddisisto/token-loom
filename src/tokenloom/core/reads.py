"""Derived reads. Nothing here is stored.

Computed from the tables and never cached. `docs/CORE.md`'s *Derived reads* names only the
handful a reader would otherwise get wrong; what a client needs is wider than that, and this
is where the width goes.

All of it assumes `INV-TREE-ROOTED`: the ancestry walks bound themselves by the node count so
that a cyclic store raises rather than hanging, but repairing one is `check.py`'s business and
nobody's to do silently.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Node:
    id: int
    parent: int | None
    token_id: int
    source: int
    deleted: bool


@dataclass(frozen=True, slots=True)
class Edge:
    node: int
    source: int
    rank: int
    token_id: int
    logprob: float


def _node(row: tuple) -> Node:
    return Node(row[0], row[1], row[2], row[3], bool(row[4]))


# ---- the tree ----------------------------------------------------------------------


def node_exists(conn: sqlite3.Connection, node: int) -> bool:
    return conn.execute("SELECT 1 FROM nodes WHERE id = ?", (node,)).fetchone() is not None


def get_node(conn: sqlite3.Connection, node: int) -> Node:
    row = conn.execute(
        "SELECT id, parent, token_id, source, deleted FROM nodes WHERE id = ?", (node,)
    ).fetchone()
    if row is None:
        raise KeyError(f"no node {node}")
    return _node(row)


def path_nodes(conn: sqlite3.Connection, node: int) -> list[Node]:
    """Root first, `node` last. The sequence of tokens down to a node is its context, and
    it is the only thing a node means."""
    rows = conn.execute(
        """
        WITH RECURSIVE up(id, parent, token_id, source, deleted, depth) AS (
            SELECT id, parent, token_id, source, deleted, 0 FROM nodes WHERE id = ?
            UNION ALL
            SELECT n.id, n.parent, n.token_id, n.source, n.deleted, up.depth + 1
              FROM nodes n JOIN up ON n.id = up.parent
             WHERE up.depth < (SELECT COUNT(*) FROM nodes)
        )
        SELECT id, parent, token_id, source, deleted, depth FROM up ORDER BY depth DESC
        """,
        (node,),
    ).fetchall()
    if not rows:
        raise KeyError(f"no node {node}")
    if rows[0][1] is not None:
        raise ValueError(f"ancestry of node {node} does not reach a root; INV-TREE-ROOTED")
    return [_node(r) for r in rows]


def path_token_ids(conn: sqlite3.Connection, node: int) -> list[int]:
    """What a backend is handed, and what makes a path replayable: ids, concatenated."""
    return [n.token_id for n in path_nodes(conn, node)]


def depth(conn: sqlite3.Connection, node: int) -> int:
    """A node's distance from the root, in tokens. A root is 0."""
    return len(path_nodes(conn, node)) - 1


def children(conn: sqlite3.Connection, node: int | None) -> list[Node]:
    if node is None:
        rows = conn.execute(
            "SELECT id, parent, token_id, source, deleted FROM nodes "
            "WHERE parent IS NULL ORDER BY id"
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT id, parent, token_id, source, deleted FROM nodes "
            "WHERE parent = ? ORDER BY id",
            (node,),
        ).fetchall()
    return [_node(r) for r in rows]


def roots(conn: sqlite3.Connection) -> list[Node]:
    """Each root begins its own trie. They share a store and a vocabulary and nothing else."""
    return children(conn, None)


def path_liveness(nodes: list[Node]) -> list[bool]:
    """Whether each node of a path is live, root first.

    Takes the list `path_nodes` returns rather than a connection: an ancestry already
    carries every `deleted` the answer depends on, so a path needs no second query.
    """
    live, out = True, []
    for n in nodes:
        live = live and not n.deleted
        out.append(live)
    return out


def is_live(conn: sqlite3.Connection, node: int) -> bool:
    """Neither it nor any ancestor carries `deleted`. One ancestry walk per call, so asking
    for many nodes is what `descend` is for. `scripts/scale.py` is what weighs the two."""
    return path_liveness(path_nodes(conn, node))[-1]


_DESCENT = """
WITH RECURSIVE down(id, parent, token_id, source, deleted, live, depth) AS (
    SELECT id, parent, token_id, source, deleted, (deleted IS NULL) AND ?, 0
      FROM nodes WHERE parent {anchor}
    UNION ALL
    SELECT n.id, n.parent, n.token_id, n.source, n.deleted,
           (n.deleted IS NULL) AND down.live, down.depth + 1
      FROM nodes n JOIN down ON n.parent = down.id
     WHERE down.depth < (SELECT COUNT(*) FROM nodes)
)
SELECT id, parent, token_id, source, deleted, live, depth FROM down
"""


def descend(
    conn: sqlite3.Connection, node: int | None = None
) -> Iterator[tuple[int, Node, bool]]:
    """Depth-first from the roots, or from below `node`, yielding `(depth, node, live)`.

    One query, with liveness carried down rather than walked up per node. Siblings come in
    id order, and `depth` is relative to where the descent started.
    """
    if node is None:
        rows = conn.execute(_DESCENT.format(anchor="IS NULL"), (1,)).fetchall()
    else:
        rows = conn.execute(
            _DESCENT.format(anchor="= ?"), (is_live(conn, node), node)
        ).fetchall()

    below: dict[int, list[tuple]] = {}
    top = []
    for r in rows:
        (top if r[6] == 0 else below.setdefault(r[1], [])).append(r)
    for kids in below.values():
        kids.sort(key=lambda r: r[0])
    top.sort(key=lambda r: r[0])

    stack = list(reversed(top))
    while stack:
        r = stack.pop()
        yield r[6], _node(r), bool(r[5])
        stack.extend(reversed(below.get(r[0], ())))


# ---- bytes -------------------------------------------------------------------------


def node_bytes(conn: sqlite3.Connection, node: int) -> bytes:
    """A node's bytes are its token's bytes -- its `vocab` entry, and never an occurrence's."""
    row = conn.execute(
        "SELECT v.bytes FROM nodes n JOIN vocab v ON v.token_id = n.token_id WHERE n.id = ?",
        (node,),
    ).fetchone()
    if row is None:
        raise KeyError(f"no node {node}, or its token is not in vocab")
    return bytes(row[0])


def path_bytes(conn: sqlite3.Connection, node: int) -> bytes:
    """The bytes of each node from the root down, in order.

    May not decode: the format has no notion of a character boundary, and what a reader
    shows in place of bytes that have no string form is the reader's to choose.
    """
    spell = dict(conn.execute("SELECT token_id, bytes FROM vocab").fetchall())
    return b"".join(bytes(spell[n.token_id]) for n in path_nodes(conn, node))


# ---- rankings ----------------------------------------------------------------------


def ranking(conn: sqlite3.Connection, node: int, source: int | None = None) -> list[Edge]:
    """The alternatives recorded at a node, in the order the source presented them.

    Descending logprob is expected of a model and is not enforced, so this does not sort.
    """
    sql = "SELECT node, source, rank, token_id, logprob FROM edges WHERE node = ?"
    args: tuple = (node,)
    if source is not None:
        sql += " AND source = ?"
        args += (source,)
    return [Edge(*r) for r in conn.execute(sql + " ORDER BY source, rank", args)]


def node_logprob(conn: sqlite3.Connection, node: int) -> float | None:
    """The ranked edge at its parent, for its source, carrying its `token_id`.

    `None` where no covering edge was recorded -- a root, a node a generation declined to
    rank, or one a stop condition produced. Nothing records *why* it is missing.
    """
    row = conn.execute(
        """
        SELECT e.logprob FROM nodes n
          JOIN edges e ON e.node = n.parent AND e.source = n.source AND e.token_id = n.token_id
         WHERE n.id = ?
        """,
        (node,),
    ).fetchone()
    return row[0] if row else None


def unrealised_edges(conn: sqlite3.Connection, node: int) -> list[Edge]:
    """Ranked edges at a node with no matching child. This is the branchable set."""
    rows = conn.execute(
        """
        SELECT e.node, e.source, e.rank, e.token_id, e.logprob
          FROM edges e
          LEFT JOIN nodes c
            ON c.parent = e.node AND c.token_id = e.token_id AND c.source = e.source
         WHERE e.node = ? AND c.id IS NULL
         ORDER BY e.source, e.rank
        """,
        (node,),
    ).fetchall()
    return [Edge(*r) for r in rows]


# ---- acts --------------------------------------------------------------------------


def act_tokens(conn: sqlite3.Connection, act: int) -> list[Node]:
    """The path from `origin` (exclusive) to `tip` (inclusive), in order.

    Nothing else is stored, because each node has one parent and that path is therefore
    unique. Empty for an act that produced no nodes.
    """
    row = conn.execute("SELECT origin, tip FROM acts WHERE id = ?", (act,)).fetchone()
    if row is None:
        raise KeyError(f"no act {act}")
    origin, tip = row
    if tip is None:
        return []
    chain = path_nodes(conn, tip)
    if origin is None:
        return chain
    for i, n in enumerate(chain):
        if n.id == origin:
            return chain[i + 1 :]
    raise ValueError(f"act {act}: tip {tip} does not descend from origin {origin}; INV-ACT-PATH")
