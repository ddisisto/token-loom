"""Derived reads. Nothing here is stored.

Computed from the tables and never cached. `docs/CORE.md`'s *Derived reads* names only the
handful a reader would otherwise get wrong; what a client needs is wider than that, and this
is where the width goes.

All of it assumes `INV-TREE-ROOTED`: the ancestry walks bound themselves by the node count so
that a cyclic store raises rather than hanging, but repairing one is `check.py`'s business and
nobody's to do silently.
"""

from __future__ import annotations

import math
import sqlite3
from collections.abc import Iterable, Iterator
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


@dataclass(frozen=True, slots=True)
class PathNode:
    """A node of a path, with what is derived at it rather than stored on it.

    `fork` is *its parent has more than one live child*, which is not `Node.deleted` on a
    sibling: a parent that is itself out of the live tree forks nowhere. A root is never
    one -- it has no parent to part from.
    """

    node: Node
    live: bool
    logprob: float | None
    fork: bool


@dataclass(frozen=True, slots=True)
class Spread:
    """What one source's ranking says about the position it stands at, without the rows.

    `top` and `second` are the two highest logprobs **recorded**; `second` is None only
    where one row is all there is. Whether those are the model's own top two is an
    obligation on whatever wrote them and not a fact about the record, so this says what is
    stored and a reader wanting more reads `docs/ADAPTER.md`.

    `rows` is the recorded depth and `mass` the probability those rows carry between them.
    Both are what accumulated here and neither is any act's parameter, since rankings
    extend -- so a reader comparing two positions carries `rows` along with what it read.
    """

    source: int
    rows: int
    mass: float
    top: float
    second: float | None


@dataclass(frozen=True, slots=True)
class RankedEdge:
    """A ranked edge, what its token spells, and the child that realised it, if any."""

    edge: Edge
    spelling: bytes
    child: Node | None


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


_ANNOTATED_PATH = """
WITH RECURSIVE up(id, parent, token_id, source, deleted, depth) AS (
    SELECT id, parent, token_id, source, deleted, 0 FROM nodes WHERE id = ?
    UNION ALL
    SELECT n.id, n.parent, n.token_id, n.source, n.deleted, up.depth + 1
      FROM nodes n JOIN up ON n.id = up.parent
     WHERE up.depth < (SELECT COUNT(*) FROM nodes)
)
SELECT u.id, u.parent, u.token_id, u.source, u.deleted, u.depth, e.logprob,
       (SELECT COUNT(*) FROM nodes s WHERE s.parent = u.parent AND s.deleted IS NULL)
  FROM up u
  LEFT JOIN edges e
    ON e.node = u.parent AND e.source = u.source AND e.token_id = u.token_id
 ORDER BY u.depth DESC
"""


def annotated_path(conn: sqlite3.Connection, node: int) -> list[PathNode]:
    """Root first, `node` last, each carrying its liveness, its logprob and whether it forks.

    One query. All three want the same ancestry and the same parents, so asking for them
    apart is three walks up where one does; `edges` is unique on `(node, source, token_id)`,
    so the join adds no row.
    """
    rows = conn.execute(_ANNOTATED_PATH, (node,)).fetchall()
    if not rows:
        raise KeyError(f"no node {node}")
    if rows[0][1] is not None:
        raise ValueError(f"ancestry of node {node} does not reach a root; INV-TREE-ROOTED")
    out, live = [], True
    for r in rows:
        above = live
        live = live and r[4] is None
        out.append(PathNode(_node(r), live, r[6], r[1] is not None and above and r[7] > 1))
    return out


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


def _chunks(ids: Iterable[int]) -> Iterator[tuple[str, list[int]]]:
    """Distinct ids in batches small enough for one `IN`, each with its placeholders.

    SQLite bounds how many parameters one statement may carry, and a bulk read asked for a
    whole tree will pass it.
    """
    wanted = sorted(set(ids))
    for i in range(0, len(wanted), 500):
        part = wanted[i : i + 500]
        yield ",".join("?" * len(part)), part


def token_bytes(conn: sqlite3.Connection, ids: Iterable[int]) -> dict[int, bytes]:
    """The `vocab` entries for a set of ids, for a caller about to spell many nodes.

    Raises rather than returning a hole: a node whose token is absent from `vocab` is
    `INV-VOCAB-CLOSED`, and spelling it as nothing would hide that behind a shorter string.
    """
    wanted = sorted(set(ids))  # `ids` is often a generator, and is read twice below
    out: dict[int, bytes] = {}
    for holes, part in _chunks(wanted):
        for token_id, data in conn.execute(
            f"SELECT token_id, bytes FROM vocab WHERE token_id IN ({holes})", part
        ):
            out[token_id] = bytes(data)
    missing = [i for i in wanted if i not in out]
    if missing:
        raise KeyError(f"token ids absent from vocab: {missing[:8]}; INV-VOCAB-CLOSED")
    return out


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


def ranking_with_children(conn: sqlite3.Connection, node: int) -> list[RankedEdge]:
    """Every ranked edge at a node, what it spells, and what became of it.

    The alternatives at a position with the one taken sitting among them, rather than the
    branchable set alone -- which is the same rows, filtered to those with no child. A child
    carrying `deleted` is still a child: the merge key is what forbids realising it again,
    and `undelete` rather than `realise` is what brings it back.

    Recorded order, source by source. Descending logprob is expected of a model rather than
    enforced, so this does not sort.
    """
    rows = conn.execute(
        """
        SELECT e.node, e.source, e.rank, e.token_id, e.logprob, v.bytes,
               c.id, c.parent, c.token_id, c.source, c.deleted
          FROM edges e
          JOIN vocab v ON v.token_id = e.token_id
          LEFT JOIN nodes c
            ON c.parent = e.node AND c.token_id = e.token_id AND c.source = e.source
         WHERE e.node = ?
         ORDER BY e.source, e.rank
        """,
        (node,),
    ).fetchall()
    return [
        RankedEdge(Edge(*r[:5]), bytes(r[5]), _node(r[6:11]) if r[6] is not None else None)
        for r in rows
    ]


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


def recorded_depths(
    conn: sqlite3.Connection, nodes: Iterable[int]
) -> dict[int, dict[int, int]]:
    """How many ranked edges stand at each of `nodes`, per source.

    Keyed by node and then by source, because a node two sources ranked holds two rankings
    and one count over both is a depth of nothing. A node nothing has ranked is absent
    rather than empty, the same shape `unrealised_counts` answers in and for the same
    reason: most of a tree has no ranking at all.

    This is what anything read off a ranking has to be read against. Rankings accumulate and
    are never rewritten, so what is stored at a node is not recoverable from the parameters
    of any generation that passed through it -- a quantity computed over a ranking is a
    quantity over however many rows have landed, and `docs/CORE.md` says so under *Derived
    reads*. Nothing here interprets them.
    """
    out: dict[int, dict[int, int]] = {}
    for holes, part in _chunks(nodes):
        for node, source, rows in conn.execute(
            f"SELECT node, source, COUNT(*) FROM edges WHERE node IN ({holes}) "
            "GROUP BY node, source",
            part,
        ):
            out.setdefault(node, {})[source] = rows
    return out


def spreads(conn: sqlite3.Connection, nodes: Iterable[int]) -> dict[int, list[Spread]]:
    """What each of `nodes` ranked, summarised per source and without the rows themselves.

    A node several sources ranked gets several entries, in source order; one summary over
    their union would describe a distribution nothing produced. A node nothing ranked is
    absent rather than empty, as in `recorded_depths`, since most of a tree has no ranking.

    **The rows are read and summarised here rather than aggregated in SQL.** The second
    highest logprob is not an aggregate, and the mass wants `exp`, which SQLite has only
    where it was compiled in. What that costs is the recorded depth times the nodes asked
    about -- the record's own size over those nodes, and not a multiple of it -- in one
    statement per batch.
    """
    held: dict[int, dict[int, list[float]]] = {}
    for holes, part in _chunks(nodes):
        for node, source, logprob in conn.execute(
            f"SELECT node, source, logprob FROM edges WHERE node IN ({holes}) "
            "ORDER BY node, source, logprob DESC",
            part,
        ):
            held.setdefault(node, {}).setdefault(source, []).append(logprob)
    return {
        node: [
            Spread(
                source,
                len(ranked),
                sum(math.exp(p) for p in ranked),
                ranked[0],
                ranked[1] if len(ranked) > 1 else None,
            )
            for source, ranked in sorted(by_source.items())
        ]
        for node, by_source in held.items()
    }


def unrealised_counts(conn: sqlite3.Connection, nodes: Iterable[int]) -> dict[int, int]:
    """How large the branchable set is at each of `nodes`, for those where it is not empty.

    The same `LEFT JOIN` as `unrealised_edges`, asked of many nodes at once. A node absent
    from the result has none, which is most of a tree. It takes the nodes rather than
    answering for the whole store because a listing is usually a subtree, and a query bound
    to what was asked for beats one that grinds every edge; `scripts/scale.py` weighs the
    three shapes.
    """
    out: dict[int, int] = {}
    for holes, part in _chunks(nodes):
        out.update(
            conn.execute(
                f"""
                SELECT e.node, COUNT(*)
                  FROM edges e
                  LEFT JOIN nodes c
                    ON c.parent = e.node AND c.token_id = e.token_id AND c.source = e.source
                 WHERE c.id IS NULL AND e.node IN ({holes})
                 GROUP BY e.node
                """,
                part,
            )
        )
    return out


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
