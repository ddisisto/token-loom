"""The descent, and the two other forms of the same answer.

Liveness is derived from an ancestry, and there are three ways to reach it: walk up from
one node, run down the whole tree carrying it, or read it off a path already fetched. The
tests that matter here are the ones that hold the three against each other, because a bulk
form that disagrees with the single-node form is the kind of fault nothing else reports.
"""

from __future__ import annotations

import pytest

from tokenloom.core import Store
from tokenloom.core import reads as R
from toy import USER, ToyVocabulary


@pytest.fixture
def tree(tmp_path):
    """Two roots, a fork, and a delete with a node under it.

        1  The          live
        2   sky         live
        3    is         deleted
        4     blue      live row, not live
        5    red        live
        6  grey         live, and a second root
    """
    with Store.initialise(tmp_path / "t", vocabulary="toy") as store:
        store.create(None, "The sky", vocabulary=ToyVocabulary(), actor=USER)
        store.create(2, " is blue", vocabulary=ToyVocabulary(), actor=USER)
        store.create(2, " red", vocabulary=ToyVocabulary(), actor=USER)
        store.create(None, " grey", vocabulary=ToyVocabulary(), actor=USER)
        store.delete(3, actor=USER)
        yield store


# ---- the three forms agree ----------------------------------------------------------


def test_the_descent_agrees_with_is_live_at_every_node(tree):
    """The bulk form and the single-node form are the same read at different widths."""
    for _, node, live in R.descend(tree.conn):
        assert live == R.is_live(tree.conn, node.id), f"node {node.id}"


def test_path_liveness_agrees_with_is_live_along_a_path(tree):
    """A path already holds every `deleted` its own liveness depends on."""
    for target in (4, 5, 6):
        nodes = R.path_nodes(tree.conn, target)
        assert R.path_liveness(nodes) == [R.is_live(tree.conn, n.id) for n in nodes]


def test_a_deleted_row_and_a_node_that_is_not_live_are_different_things(tree):
    """Only node 3 carries the flag; node 4 is out of the live tree without one, which is
    what a descent has to carry and a row cannot say."""
    flags = {n.id: n.deleted for _, n, _ in R.descend(tree.conn)}
    liveness = {n.id: live for _, n, live in R.descend(tree.conn)}
    assert flags == {1: False, 2: False, 3: True, 4: False, 5: False, 6: False}
    assert liveness == {1: True, 2: True, 3: False, 4: False, 5: True, 6: True}


# ---- what the descent visits, and in what order -------------------------------------


def test_the_descent_reaches_every_node_exactly_once(tree):
    seen = [n.id for _, n, _ in R.descend(tree.conn)]
    every = [r[0] for r in tree.conn.execute("SELECT id FROM nodes")]
    assert sorted(seen) == sorted(every)
    assert len(seen) == len(set(seen))


def test_the_descent_is_depth_first(tree):
    """Depth-first means a node's parent is the nearest earlier row one level shallower.
    Asserting the relation rather than a sequence keeps this from passing on a fixture."""
    seen: list[tuple[int, R.Node]] = []
    for depth, node, _ in R.descend(tree.conn):
        if depth == 0:
            assert node.parent is None
        else:
            above = next(n for d, n in reversed(seen) if d == depth - 1)
            assert node.parent == above.id
        seen.append((depth, node))
    assert len(seen) > 1


def test_siblings_come_in_id_order(tree):
    order = [n.id for _, n, _ in R.descend(tree.conn)]
    for parent in (None, 2):
        kids = [k.id for k in R.children(tree.conn, parent)]
        assert [i for i in order if i in kids] == kids


# ---- anchoring ----------------------------------------------------------------------


def test_a_subtree_descent_inherits_liveness_from_above_its_anchor(tree):
    """Nothing below node 3 carries `deleted`, so a descent that assumed its anchor live
    would report node 4 as live. The anchor's own ancestry is what settles it."""
    below = list(R.descend(tree.conn, 3))
    assert [n.id for _, n, _ in below] == [4]
    assert below[0][1].deleted is False
    assert below[0][2] is False


def test_a_subtree_descent_carries_a_delete_below_its_anchor(tree):
    assert {n.id: live for _, n, live in R.descend(tree.conn, 2)} == {
        3: False,
        4: False,
        5: True,
    }


def test_depth_is_relative_to_where_the_descent_started(tree):
    """Node 4 is three below the root and one below node 3."""
    assert dict((n.id, d) for d, n, _ in R.descend(tree.conn)) == {
        1: 0, 2: 1, 3: 2, 4: 3, 5: 2, 6: 0,
    }
    assert dict((n.id, d) for d, n, _ in R.descend(tree.conn, 3)) == {4: 0}


def test_a_descent_from_a_leaf_yields_nothing(tree):
    assert list(R.descend(tree.conn, 4)) == []


def test_a_descent_from_a_node_that_does_not_exist_raises(tree):
    with pytest.raises(KeyError, match="no node 9999"):
        list(R.descend(tree.conn, 9999))


# ---- cost ---------------------------------------------------------------------------


def test_the_whole_tree_costs_one_query(tree):
    """What the descent is for. `is_live` per node is one recursive walk each, which is
    the N+1 the composite reads cannot afford."""
    counted = 0

    def count(statement):
        nonlocal counted
        counted += 1
        return None

    tree.conn.set_trace_callback(count)
    list(R.descend(tree.conn))
    tree.conn.set_trace_callback(None)
    assert counted == 1
