"""The descent, and the other forms of the same answers.

Liveness is derived from an ancestry, and there are three ways to reach it: walk up from
one node, run down the whole tree carrying it, or read it off a path already fetched. The
tests that matter here are the ones that hold the three against each other, because a bulk
form that disagrees with the single-node form is the kind of fault nothing else reports.

The bulk reads that are not the descent are here for the same reason.
"""

from __future__ import annotations

import math

import pytest

from tokenloom.core import Store
from tokenloom.core import reads as R
from toy import OTHER, USER, ToyAdapter, ToyVocabulary, drew


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


def test_depth_agrees_with_the_descent_that_reached_a_node(tree):
    """`depth` walks up and the descent counts down; they are one number from two ends."""
    for d, node, _ in R.descend(tree.conn):
        assert R.depth(tree.conn, node.id) == d, f"node {node.id}"


def test_a_descent_from_a_leaf_yields_nothing(tree):
    assert list(R.descend(tree.conn, 4)) == []


def test_a_descent_from_a_node_that_does_not_exist_raises(tree):
    with pytest.raises(KeyError, match="no node 9999"):
        list(R.descend(tree.conn, 9999))


# ---- the other bulk forms -----------------------------------------------------------


def test_unrealised_counts_agrees_with_unrealised_edges_at_every_node(tmp_path):
    """The branchable set asked for many nodes at once. Two of the fixture's ranked edges
    have children and the rest do not, so a count that ignored the join would be wrong at
    every node rather than at none."""
    with Store.initialise(tmp_path / "u", vocabulary="toy") as store:
        adapter = ToyAdapter([
            drew((101, [(101, -0.1), (102, -0.5), (103, -1.0)])),
            drew((105, [(105, -0.2), (106, -0.9)])),
        ])
        store.create(None, "The", vocabulary=ToyVocabulary(), actor=USER)
        store.generate(1, {"length": 1}, adapter=adapter, actor=USER)
        store.generate(2, {"length": 1}, adapter=adapter, actor=USER)
        every = [r[0] for r in store.conn.execute("SELECT id FROM nodes")]

        counts = R.unrealised_counts(store.conn, every)
        assert counts == {
            node: len(R.unrealised_edges(store.conn, node))
            for node in every
            if R.unrealised_edges(store.conn, node)
        }
        assert counts == {1: 2, 2: 1}  # and node 3, the tip, is absent rather than 0
        assert R.unrealised_counts(store.conn, [3]) == {}


def test_a_recorded_depth_is_what_accumulated_and_not_what_any_act_asked_for(tmp_path):
    """Two generations at one node, each asking for a different number of rows.

    Rows already present keep their values and new tokens append below, so the depth is the
    union and is neither generation's parameter. Nothing in the record carries the union, so
    a reader that reached for an act's `record_rows` would be wrong here by 2 and by 1.
    """
    with Store.initialise(tmp_path / "d", vocabulary="toy") as store:
        store.create(None, "The", vocabulary=ToyVocabulary(), actor=USER)
        store.generate(
            1, {"length": 1, "record_rows": 3},
            adapter=ToyAdapter([drew((101, [(101, -0.1), (102, -0.5), (103, -1.0)]))]),
            actor=USER,
        )
        store.generate(
            1, {"length": 1, "record_rows": 4},
            adapter=ToyAdapter([
                drew((101, [(101, -0.1), (102, -0.5), (104, -2.0), (105, -2.5)])),
            ]),
            actor=USER,
        )
        model = next(iter(R.recorded_depths(store.conn, [1])[1]))
        assert R.recorded_depths(store.conn, [1]) == {1: {model: 5}}
        assert len(R.ranking(store.conn, 1)) == 5  # the read it has to agree with


def test_a_depth_is_per_source_because_two_rankings_are_not_one(tmp_path):
    """A node two sources ranked holds two rankings. Summing them counts rows of different
    distributions together, which is the number a single `COUNT` would return."""
    with Store.initialise(tmp_path / "s", vocabulary="toy") as store:
        store.create(None, "The", vocabulary=ToyVocabulary(), actor=USER)
        store.generate(
            1, {"length": 1},
            adapter=ToyAdapter([drew((101, [(101, -0.1), (102, -0.5), (103, -1.0)]))]),
            actor=USER,
        )
        store.generate(
            1, {"length": 1},
            adapter=ToyAdapter([drew((105, [(105, -0.2), (106, -0.9)]))], source=OTHER),
            actor=USER,
        )
        depths = R.recorded_depths(store.conn, [1])[1]
        assert sorted(depths.values()) == [2, 3]
        assert len(depths) == 2, "one entry here would be a depth of 5, which nothing has"


def test_a_node_nothing_ranked_is_absent_and_deleting_a_child_changes_no_depth(tmp_path):
    """Two traps in one fixture. A tip has no ranking and is left out rather than reported
    as zero; and an edge is not a child, so marking the node that realised one does not take
    the row away -- a reader that joined depth to `nodes` would lose it."""
    with Store.initialise(tmp_path / "n", vocabulary="toy") as store:
        store.create(None, "The", vocabulary=ToyVocabulary(), actor=USER)
        store.generate(
            1, {"length": 1},
            adapter=ToyAdapter([drew((101, [(101, -0.1), (102, -0.5)]))]),
            actor=USER,
        )
        assert R.recorded_depths(store.conn, [2]) == {}
        before = R.recorded_depths(store.conn, [1])

        store.delete(2, actor=USER)
        assert R.recorded_depths(store.conn, [1]) == before


def test_a_spread_summarises_the_rows_and_agrees_with_reading_them(tmp_path):
    """Four rows recorded out of logprob order, which is what the store allows and what a
    later act produces. Every field is computed from the rows rather than written down, so
    a summary that sorted wrongly or counted the union would disagree here.
    """
    rows = [(101, -0.10), (104, -2.00), (102, -0.50), (105, -3.00)]
    with Store.initialise(tmp_path / "p", vocabulary="toy") as store:
        store.create(None, "The", vocabulary=ToyVocabulary(), actor=USER)
        store.generate(
            1, {"length": 1}, adapter=ToyAdapter([drew((101, rows))]), actor=USER
        )
        (spread,) = R.spreads(store.conn, [1])[1]

        logprobs = sorted((lp for _, lp in rows), reverse=True)
        assert spread.rows == len(rows)
        assert spread.top == logprobs[0]
        assert spread.second == logprobs[1]
        assert spread.mass == pytest.approx(sum(math.exp(lp) for lp in logprobs))
        assert spread.top > spread.second, "recorded order is not logprob order"

        # The same numbers the row-by-row read gives, which is what it has to agree with.
        read = R.ranking(store.conn, 1)
        assert spread.rows == len(read)
        assert spread.top == max(e.logprob for e in read)


def test_a_spread_is_per_source_because_two_rankings_are_not_one(tmp_path):
    """Summing two sources' rows would describe a distribution neither model produced, and
    the mass of the union can exceed one while each part is a prefix of a distribution."""
    with Store.initialise(tmp_path / "q", vocabulary="toy") as store:
        store.create(None, "The", vocabulary=ToyVocabulary(), actor=USER)
        store.generate(
            1, {"length": 1},
            adapter=ToyAdapter([drew((101, [(101, -0.1), (102, -0.5), (103, -1.0)]))]),
            actor=USER,
        )
        store.generate(
            1, {"length": 1},
            adapter=ToyAdapter([drew((105, [(105, -0.2), (106, -0.9)]))], source=OTHER),
            actor=USER,
        )
        found = R.spreads(store.conn, [1])[1]
        assert [s.rows for s in found] == [3, 2]
        assert len({s.source for s in found}) == 2
        assert {s.source: s.rows for s in found} == R.recorded_depths(store.conn, [1])[1]


def test_a_node_nothing_ranked_has_no_spread_and_one_row_has_no_second(tmp_path):
    """A tip is absent rather than reported as an empty ranking, and a lone row leaves
    `second` unset rather than repeating the first -- which a gap read off it would make
    zero, saying the model was torn where it had one recorded option."""
    with Store.initialise(tmp_path / "o", vocabulary="toy") as store:
        store.create(None, "The", vocabulary=ToyVocabulary(), actor=USER)
        store.generate(
            1, {"length": 1}, adapter=ToyAdapter([drew((101, [(101, -0.1)]))]), actor=USER
        )
        assert R.spreads(store.conn, [2]) == {}
        (spread,) = R.spreads(store.conn, [1])[1]
        assert (spread.rows, spread.second) == (1, None)


def test_token_bytes_agrees_with_node_bytes(tree):
    spell = R.token_bytes(tree.conn, (n.token_id for _, n, _ in R.descend(tree.conn)))
    for _, node, _ in R.descend(tree.conn):
        assert spell[node.token_id] == R.node_bytes(tree.conn, node.id)


def test_token_bytes_raises_on_a_token_the_vocabulary_does_not_hold(tree):
    """Both callers hand it a generator, so the ids have to be held rather than read twice:
    an exhausted one reports nothing missing and hands back a shorter dictionary."""
    for ids in ([9999], iter([9999])):
        with pytest.raises(KeyError, match="INV-VOCAB-CLOSED"):
            R.token_bytes(tree.conn, ids)


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
