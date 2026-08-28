"""Every invariant, against a store built to violate exactly it.

The checker's whole job is to not take the schema's word for anything, so these cases are
built against a **relaxed** schema -- same tables and columns, with the UNIQUE and PRIMARY
KEY clauses dropped. A checker tested only through the real DDL would be testing SQLite.

`INV-RANK-DENSE` and the rest are asserted by name: what is being tested is that the right
invariant fires, not merely that something did.
"""

from __future__ import annotations

import sqlite3

import pytest

from tokenloom.core import Store, violations
from tokenloom.core.check import Corrupt
from tokenloom.core.schema import DDL

#: The locked schema's tables and columns with every UNIQUE and PRIMARY KEY clause gone,
#: written out rather than derived, so that what a case is handed is legible at a glance.
#: `columns_of` asserts it has not drifted from the real DDL.
RELAXED = """
CREATE TABLE vocab  (token_id INTEGER, bytes BLOB NOT NULL);
CREATE TABLE sources(id INTEGER, kind TEXT NOT NULL, name TEXT NOT NULL);
CREATE TABLE nodes  (id INTEGER, parent INTEGER, token_id INTEGER NOT NULL,
                     source INTEGER NOT NULL, deleted INTEGER);
CREATE TABLE edges  (node INTEGER NOT NULL, source INTEGER NOT NULL, rank INTEGER NOT NULL,
                     token_id INTEGER NOT NULL, logprob REAL NOT NULL);
CREATE TABLE params (id INTEGER, json TEXT NOT NULL);
CREATE TABLE acts   (id INTEGER, op TEXT NOT NULL, source INTEGER NOT NULL, origin INTEGER,
                     tip INTEGER, created TEXT NOT NULL, params INTEGER, seed INTEGER,
                     terminator TEXT, rank INTEGER);
"""


def columns_of(ddl: str) -> dict[str, list[str]]:
    conn = sqlite3.connect(":memory:")
    conn.executescript(ddl)
    tables = [r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name")]
    return {t: [r[1] for r in conn.execute(f"PRAGMA table_info({t})")] for t in tables}


def test_the_relaxed_schema_has_not_drifted_from_the_locked_one():
    """Same tables, same columns, same order -- only the constraints differ. Without this
    the checker could be passing against a schema the store never writes."""
    assert columns_of(RELAXED) == columns_of(DDL)


def bare() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.executescript(RELAXED)
    conn.execute("INSERT INTO sources (id, kind, name) VALUES (1, 'user', '')")
    conn.execute("INSERT INTO sources (id, kind, name) VALUES (2, 'model', 'm')")
    conn.execute("INSERT INTO vocab (token_id, bytes) VALUES (10, 'a'), (11, 'b'), (12, 'c')")
    return conn


def node(conn, nid, parent, token=10, source=1, deleted=None):
    conn.execute(
        "INSERT INTO nodes (id, parent, token_id, source, deleted) VALUES (?, ?, ?, ?, ?)",
        (nid, parent, token, source, deleted),
    )


def act(conn, aid, op, source=1, origin=None, tip=None, params=None, seed=None,
        terminator=None, rank=None):
    conn.execute(
        "INSERT INTO acts (id, op, source, origin, tip, created, params, seed, terminator, rank) "
        "VALUES (?, ?, ?, ?, ?, '2026-01-01T00:00:00Z', ?, ?, ?, ?)",
        (aid, op, source, origin, tip, params, seed, terminator, rank),
    )


def names(conn) -> set[str]:
    return {v.invariant for v in violations(conn)}


# ---- a clean store ------------------------------------------------------------------


def test_a_valid_store_has_no_violations():
    conn = bare()
    node(conn, 1, None)
    node(conn, 2, 1, token=11)
    act(conn, 1, "create", origin=None, tip=2)
    assert violations(conn) == []


# ---- the tree -----------------------------------------------------------------------


def test_inv_tree_parent():
    conn = bare()
    node(conn, 1, 999)
    assert "INV-TREE-PARENT" in names(conn)


def test_inv_tree_rooted_catches_a_cycle():
    """Following `parent` from any node reaches a root; there are no cycles."""
    conn = bare()
    node(conn, 1, 2)
    node(conn, 2, 1, token=11)
    assert "INV-TREE-ROOTED" in names(conn)


def test_inv_tree_rooted_terminates_on_a_long_chain():
    """The memoised walk must not be quadratic on a deep tree, nor loop on a clean one."""
    conn = bare()
    node(conn, 1, None)
    for i in range(2, 2000):
        node(conn, i, i - 1, token=10 + i % 3)
    assert violations(conn) == []


def test_inv_merge_key():
    conn = bare()
    node(conn, 1, None)
    node(conn, 2, 1, token=11, source=1)
    node(conn, 3, 1, token=11, source=1)
    assert "INV-MERGE-KEY" in names(conn)


def test_roots_are_exempt_from_the_merge_key():
    """Two roots with the same token and source stay distinct -- Sources' rule, not an
    artefact of SQL's NULL-tolerant UNIQUE."""
    conn = bare()
    node(conn, 1, None, token=10, source=1)
    node(conn, 2, None, token=10, source=1)
    assert "INV-MERGE-KEY" not in names(conn)


# ---- closure ------------------------------------------------------------------------


def test_inv_vocab_closed_on_a_node_and_on_an_edge():
    conn = bare()
    node(conn, 1, None, token=99)
    assert "INV-VOCAB-CLOSED" in names(conn)

    conn = bare()
    node(conn, 1, None)
    conn.execute("INSERT INTO edges VALUES (1, 2, 0, 99, -1.0)")
    assert "INV-VOCAB-CLOSED" in names(conn)


def test_inv_source_closed():
    conn = bare()
    node(conn, 1, None, source=99)
    assert "INV-SOURCE-CLOSED" in names(conn)


def test_inv_source_named():
    conn = bare()
    conn.execute("INSERT INTO sources (id, kind, name) VALUES (3, 'model', '')")
    assert "INV-SOURCE-NAMED" in names(conn)


# ---- rankings -----------------------------------------------------------------------


def test_inv_rank_anchored():
    conn = bare()
    conn.execute("INSERT INTO edges VALUES (999, 2, 0, 10, -1.0)")
    assert "INV-RANK-ANCHORED" in names(conn)


def test_a_deleted_nodes_edges_are_not_orphans():
    """A deleted node is still held, so its rows are not orphans."""
    conn = bare()
    node(conn, 1, None, deleted=1)
    conn.execute("INSERT INTO edges VALUES (1, 2, 0, 10, -1.0)")
    assert "INV-RANK-ANCHORED" not in names(conn)


def test_inv_rank_dense():
    conn = bare()
    node(conn, 1, None)
    conn.execute("INSERT INTO edges VALUES (1, 2, 0, 10, -1.0), (1, 2, 2, 11, -2.0)")
    assert "INV-RANK-DENSE" in names(conn)


def test_inv_rank_unique():
    conn = bare()
    node(conn, 1, None)
    conn.execute("INSERT INTO edges VALUES (1, 2, 0, 10, -1.0), (1, 2, 1, 10, -2.0)")
    assert "INV-RANK-UNIQUE" in names(conn)


def test_ranks_are_per_node_and_source_so_two_sources_both_start_at_zero():
    conn = bare()
    node(conn, 1, None)
    conn.execute("INSERT INTO edges VALUES (1, 1, 0, 10, -1.0), (1, 2, 0, 11, -2.0)")
    assert violations(conn) == []


def test_descending_logprob_is_not_an_invariant():
    """Rank is the order the source presented. Near-ties come back in whatever order a
    backend produces, and imposing a sort would turn stored order on values that are not
    reproducible to the last bit."""
    conn = bare()
    node(conn, 1, None)
    conn.execute("INSERT INTO edges VALUES (1, 2, 0, 10, -9.0), (1, 2, 1, 11, -0.1)")
    assert violations(conn) == []


# ---- acts ---------------------------------------------------------------------------


def test_inv_act_path_only_a_generate_may_have_no_tip():
    conn = bare()
    node(conn, 1, None)
    act(conn, 1, "create", tip=None)
    assert "INV-ACT-PATH" in names(conn)


def test_inv_act_path_tip_must_descend_from_origin():
    conn = bare()
    node(conn, 1, None)
    node(conn, 2, None, token=11)
    act(conn, 1, "create", origin=1, tip=2)
    assert "INV-ACT-PATH" in names(conn)


def test_inv_act_path_range_is_non_empty():
    """An act that produced nodes covers a non-empty range: origin exclusive, tip inclusive."""
    conn = bare()
    node(conn, 1, None)
    act(conn, 1, "create", origin=1, tip=1)
    assert "INV-ACT-PATH" in names(conn)


def test_inv_act_source():
    conn = bare()
    node(conn, 1, None, source=1)
    node(conn, 2, 1, token=11, source=2)
    act(conn, 1, "create", source=1, origin=None, tip=2)
    assert "INV-ACT-SOURCE" in names(conn)


def test_inv_act_create_carries_no_generate_or_realise_fields():
    conn = bare()
    node(conn, 1, None)
    act(conn, 1, "create", tip=1, seed=5)
    assert "INV-ACT-CREATE" in names(conn)


def test_inv_act_generate_needs_params_and_seed():
    conn = bare()
    node(conn, 1, None, source=2)
    act(conn, 1, "generate", source=2, tip=1)
    assert "INV-ACT-GENERATE" in names(conn)


def test_inv_act_generate_null_tip_needs_a_terminator_that_allows_one():
    conn = bare()
    act(conn, 1, "generate", source=2, params=1, seed=1, terminator="limit", tip=None)
    assert "INV-ACT-GENERATE" in names(conn)


@pytest.mark.parametrize("terminator", ["cancelled", "failed", "aborted", "refused", None])
def test_inv_act_generate_allows_a_null_tip_under_these(terminator):
    conn = bare()
    act(conn, 1, "generate", source=2, params=1, seed=1, terminator=terminator, tip=None)
    assert "INV-ACT-GENERATE" not in names(conn)


def test_inv_act_realise_needs_the_edge_it_names():
    conn = bare()
    node(conn, 1, None, source=2)
    node(conn, 2, 1, token=11, source=2)
    act(conn, 1, "realise", source=1, origin=1, tip=2, rank=0)
    assert "INV-ACT-REALISE" in names(conn)


def test_inv_act_realise_edge_must_carry_the_tips_token():
    conn = bare()
    node(conn, 1, None, source=2)
    node(conn, 2, 1, token=11, source=2)
    conn.execute("INSERT INTO edges VALUES (1, 2, 0, 12, -1.0)")  # a different token
    act(conn, 1, "realise", source=1, origin=1, tip=2, rank=0)
    assert "INV-ACT-REALISE" in names(conn)


def test_a_well_formed_realise_is_clean():
    conn = bare()
    node(conn, 1, None, source=2)
    node(conn, 2, 1, token=11, source=2)
    conn.execute("INSERT INTO edges VALUES (1, 2, 0, 11, -1.0)")
    act(conn, 1, "realise", source=1, origin=1, tip=2, rank=0)
    assert violations(conn) == []


def test_an_unknown_terminator_is_caught():
    conn = bare()
    act(conn, 1, "generate", source=2, params=1, seed=1, terminator="stop")
    assert "INV-ACT-GENERATE" in names(conn)


# ---- and what a writer does about it ------------------------------------------------


def test_a_writer_will_not_write_to_a_store_that_fails_an_invariant(tmp_path):
    """A store that fails an invariant is not repaired silently."""
    path = tmp_path / "t"
    Store.initialise(path, vocabulary="toy").close()
    conn = sqlite3.connect(path / "bulk.sqlite")
    conn.execute("INSERT INTO nodes (id, parent, token_id, source) VALUES (1, 42, 10, 1)")
    conn.commit()
    conn.close()

    with pytest.raises(Corrupt, match="INV-TREE-PARENT"):
        Store.open(path, write=True)
    reader = Store.open(path)  # a reader still opens, and reports
    assert "INV-TREE-PARENT" in names(reader.conn)
