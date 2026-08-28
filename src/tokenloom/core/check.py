"""The invariant checker.

Every invariant `docs/CORE.md` names, checked by walking the tables rather than by
trusting the schema -- several are enforced by a UNIQUE constraint, and a checker that
takes the constraint's word for it checks nothing.

A store that fails an invariant is not repaired silently: this reports, and `Store.open`
for writing refuses.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from .schema import KINDS, OPS, TERMINATORS


@dataclass(frozen=True, slots=True)
class Violation:
    invariant: str
    detail: str

    def __str__(self) -> str:
        return f"{self.invariant}: {self.detail}"


class Corrupt(Exception):
    def __init__(self, violations: list[Violation]) -> None:
        super().__init__("; ".join(str(v) for v in violations[:5]))
        self.violations = violations


def violations(conn: sqlite3.Connection) -> list[Violation]:
    """Every invariant, in the order `docs/CORE.md` states them. Empty is clean."""
    bad: list[Violation] = []
    nodes = {
        r[0]: (r[1], r[2], r[3], r[4])
        for r in conn.execute("SELECT id, parent, token_id, source, deleted FROM nodes")
    }
    sources = {r[0]: (r[1], r[2]) for r in conn.execute("SELECT id, kind, name FROM sources")}
    vocab = {r[0] for r in conn.execute("SELECT token_id FROM vocab")}

    bad += _tree_parent(nodes)
    bad += _tree_rooted(nodes)
    bad += _merge_key(nodes)
    bad += _vocab_closed(conn, nodes, vocab)
    bad += _source_closed(conn, nodes, sources)
    bad += _source_named(sources)
    bad += _rank_anchored(conn, nodes)
    bad += _rank_dense_and_unique(conn)
    bad += _acts(conn, nodes)
    return bad


def verify(conn: sqlite3.Connection) -> None:
    found = violations(conn)
    if found:
        raise Corrupt(found)


# ---- the tree ----------------------------------------------------------------------


def _tree_parent(nodes: dict) -> list[Violation]:
    """INV-TREE-PARENT -- every non-null `parent` names a node that exists."""
    return [
        Violation("INV-TREE-PARENT", f"node {nid} names parent {parent}, which does not exist")
        for nid, (parent, _, _, _) in nodes.items()
        if parent is not None and parent not in nodes
    ]


def _tree_rooted(nodes: dict) -> list[Violation]:
    """INV-TREE-ROOTED -- following `parent` from any node reaches a root; no cycles.

    Memoised, so the whole store costs one pass rather than one ancestry walk per node.
    """
    bad: list[Violation] = []
    rooted: set[int] = set()
    for start in nodes:
        if start in rooted:
            continue
        seen: list[int] = []
        on_path: set[int] = set()
        cur: int | None = start
        while cur is not None and cur in nodes and cur not in rooted:
            if cur in on_path:
                bad.append(Violation("INV-TREE-ROOTED", f"cycle through node {cur}"))
                seen = []
                break
            on_path.add(cur)
            seen.append(cur)
            cur = nodes[cur][0]
        rooted.update(seen)
    return bad


def _merge_key(nodes: dict) -> list[Violation]:
    """INV-MERGE-KEY -- `(parent, token_id, source)` is unique.

    Roots are exempt by Sources' rule: two roots with the same token and source stay
    distinct, and SQL's NULL-tolerant UNIQUE happens to agree.
    """
    seen: dict[tuple, int] = {}
    bad = []
    for nid, (parent, token_id, source, _) in sorted(nodes.items()):
        if parent is None:
            continue
        key = (parent, token_id, source)
        if key in seen:
            bad.append(Violation("INV-MERGE-KEY", f"nodes {seen[key]} and {nid} share {key}"))
        seen[key] = nid
    return bad


def _vocab_closed(conn: sqlite3.Connection, nodes: dict, vocab: set[int]) -> list[Violation]:
    """INV-VOCAB-CLOSED -- every `token_id` in `nodes` and `edges` is in `vocab`."""
    bad = [
        Violation("INV-VOCAB-CLOSED", f"node {nid} carries token {tok}, absent from vocab")
        for nid, (_, tok, _, _) in nodes.items()
        if tok not in vocab
    ]
    bad += [
        Violation(
            "INV-VOCAB-CLOSED",
            f"edge ({r[0]}, {r[1]}, {r[2]}) carries token {r[3]}, absent from vocab",
        )
        for r in conn.execute("SELECT node, source, rank, token_id FROM edges")
        if r[3] not in vocab
    ]
    return bad


def _source_closed(conn: sqlite3.Connection, nodes: dict, sources: dict) -> list[Violation]:
    """INV-SOURCE-CLOSED -- every `source` in `nodes`, `edges` and `acts` is in `sources`."""
    bad = [
        Violation("INV-SOURCE-CLOSED", f"node {nid} names source {src}, which does not exist")
        for nid, (_, _, src, _) in nodes.items()
        if src not in sources
    ]
    for table in ("edges", "acts"):
        bad += [
            Violation("INV-SOURCE-CLOSED", f"{table} row names source {r[0]}, which does not exist")
            for r in conn.execute(f"SELECT DISTINCT source FROM {table}")
            if r[0] not in sources
        ]
    return bad


def _source_named(sources: dict) -> list[Violation]:
    """INV-SOURCE-NAMED -- a `model` source has a non-empty name; the empty name is the
    unnamed user and belongs to nothing else."""
    bad = []
    for sid, (kind, name) in sources.items():
        if kind not in KINDS:
            bad.append(Violation("INV-SOURCE-NAMED", f"source {sid} has kind {kind!r}"))
        elif kind == "model" and not name:
            bad.append(Violation("INV-SOURCE-NAMED", f"source {sid} is an unnamed model"))
    return bad


# ---- rankings ----------------------------------------------------------------------


def _rank_anchored(conn: sqlite3.Connection, nodes: dict) -> list[Violation]:
    """INV-RANK-ANCHORED -- no `edges` row names a node that does not exist.

    A deleted node is still held, so its rows are not orphans.
    """
    return [
        Violation("INV-RANK-ANCHORED", f"edge at node {r[0]}, which does not exist")
        for r in conn.execute("SELECT DISTINCT node FROM edges")
        if r[0] not in nodes
    ]


def _rank_dense_and_unique(conn: sqlite3.Connection) -> list[Violation]:
    """INV-RANK-DENSE -- ranks within a `(node, source)` are distinct and contiguous from 0.
    INV-RANK-UNIQUE -- a `token_id` appears at most once within a `(node, source)`."""
    bad = []
    groups: dict[tuple[int, int], list[tuple[int, int]]] = {}
    for node, source, rank, token_id in conn.execute(
        "SELECT node, source, rank, token_id FROM edges ORDER BY node, source, rank"
    ):
        groups.setdefault((node, source), []).append((rank, token_id))
    for (node, source), rows in groups.items():
        ranks = [r for r, _ in rows]
        if sorted(ranks) != list(range(len(ranks))):
            bad.append(
                Violation(
                    "INV-RANK-DENSE",
                    f"node {node}, source {source}: ranks {sorted(ranks)} "
                    f"are not 0..{len(ranks) - 1}",
                )
            )
        tokens = [t for _, t in rows]
        if len(set(tokens)) != len(tokens):
            dupes = {t for t in tokens if tokens.count(t) > 1}
            bad.append(
                Violation(
                    "INV-RANK-UNIQUE", f"node {node}, source {source}: token(s) {dupes} twice"
                )
            )
    return bad


# ---- acts --------------------------------------------------------------------------


def _acts(conn: sqlite3.Connection, nodes: dict) -> list[Violation]:
    bad = []
    for act, op, source, origin, tip, params, seed, terminator, rank in conn.execute(
        "SELECT id, op, source, origin, tip, params, seed, terminator, rank FROM acts ORDER BY id"
    ):
        where = f"act {act} ({op})"
        if op not in OPS:
            bad.append(Violation("INV-ACT-PATH", f"{where}: unknown op"))
            continue

        # INV-ACT-PATH -- a non-null tip names an existing node, descends from origin, and
        # the range from origin exclusive to tip inclusive is non-empty.
        path: list[int] = []
        if tip is None:
            if op != "generate":
                bad.append(Violation("INV-ACT-PATH", f"{where}: only a generate may have no tip"))
        elif tip not in nodes:
            bad.append(Violation("INV-ACT-PATH", f"{where}: tip {tip} does not exist"))
        else:
            cur: int | None = tip
            guard = len(nodes) + 1
            while cur is not None and cur != origin and guard:
                path.append(cur)
                cur = nodes[cur][0] if cur in nodes else None
                guard -= 1
            if cur != origin:
                bad.append(
                    Violation("INV-ACT-PATH", f"{where}: tip {tip} does not descend from {origin}")
                )
            elif not path:
                bad.append(Violation("INV-ACT-PATH", f"{where}: empty range"))

        # INV-ACT-SOURCE
        if op in ("create", "generate"):
            off = [n for n in path if nodes[n][2] != source]
            if off:
                bad.append(
                    Violation(
                        "INV-ACT-SOURCE", f"{where}: nodes {off} do not carry source {source}"
                    )
                )
        elif op == "realise" and tip is not None and tip in nodes and len(path) != 1:
            bad.append(Violation("INV-ACT-SOURCE", f"{where}: realise covers {len(path)} nodes"))

        if terminator is not None and terminator not in TERMINATORS:
            bad.append(Violation("INV-ACT-GENERATE", f"{where}: unknown terminator {terminator!r}"))

        if op == "create":
            # INV-ACT-CREATE
            if tip is None:
                bad.append(Violation("INV-ACT-CREATE", f"{where}: a create names a tip"))
            extra = [
                n
                for n, v in (
                    ("params", params),
                    ("seed", seed),
                    ("terminator", terminator),
                    ("rank", rank),
                )
                if v is not None
            ]
            if extra:
                bad.append(Violation("INV-ACT-CREATE", f"{where}: carries {extra}"))

        elif op == "generate":
            # INV-ACT-GENERATE
            if params is None or seed is None:
                bad.append(Violation("INV-ACT-GENERATE", f"{where}: needs params and seed"))
            if rank is not None:
                bad.append(Violation("INV-ACT-GENERATE", f"{where}: carries a rank"))
            if tip is None and terminator not in (
                None,
                "cancelled",
                "failed",
                "aborted",
                "refused",
            ):
                bad.append(
                    Violation(
                        "INV-ACT-GENERATE", f"{where}: no tip under terminator {terminator!r}"
                    )
                )

        elif op == "realise":
            # INV-ACT-REALISE
            if rank is None or origin is None or tip is None:
                bad.append(Violation("INV-ACT-REALISE", f"{where}: needs rank, origin and tip"))
            extra = [
                n
                for n, v in (("params", params), ("seed", seed), ("terminator", terminator))
                if v is not None
            ]
            if extra:
                bad.append(Violation("INV-ACT-REALISE", f"{where}: carries {extra}"))
            if tip in nodes and origin is not None and rank is not None:
                parent, token_id, node_source, _ = nodes[tip]
                if parent != origin:
                    bad.append(
                        Violation(
                            "INV-ACT-REALISE", f"{where}: tip {tip} is not a child of {origin}"
                        )
                    )
                row = conn.execute(
                    "SELECT token_id FROM edges WHERE node = ? AND source = ? AND rank = ?",
                    (origin, node_source, rank),
                ).fetchone()
                if row is None:
                    bad.append(
                        Violation(
                            "INV-ACT-REALISE",
                            f"{where}: no edge ({origin}, {node_source}, {rank})",
                        )
                    )
                elif row[0] != token_id:
                    bad.append(
                        Violation(
                            "INV-ACT-REALISE",
                            f"{where}: edge ({origin}, {node_source}, {rank}) carries "
                            f"token {row[0]}, but tip {tip} carries {token_id}",
                        )
                    )
    return bad
