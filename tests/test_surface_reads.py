"""The three reads `docs/SURFACE.md` names, and the segmentation they are stated in.

These sit above the core, so what they are tested against is what the core has no notion
of: where a character ends, which continuation a rule picks, and what a line's worth of
room cuts off. Each read's record half is `core/reads.py`'s and is tested there.
"""

from __future__ import annotations

import pytest

from tokenloom.core import Store
from tokenloom.core import reads as R
from tokenloom.surface import reads as S
from toy import FRAG_HI, FRAG_LO, MODEL, OTHER, USER, ToyAdapter, ToyVocabulary, drew


@pytest.fixture
def tree(tmp_path):
    """Two roots, a fork with a deleted arm, and a fork hidden by one.

        1  The             live
        2   sky            live      -- one live child below 4, so 7 is not a fork
        3    is            a fork: node 2 has 3, 5 and 6, and 6 is deleted
        4     blue         live
        7      is          live, and not a fork
        8      red         deleted
        5    red           a fork, the other arm of the same one
        6    grey          deleted
        9  grey            live, and a second root
    """
    with Store.initialise(tmp_path / "t", vocabulary="toy") as store:
        v = ToyVocabulary()
        store.create(None, "The sky", vocabulary=v, actor=USER)   # 1, 2
        store.create(2, " is blue", vocabulary=v, actor=USER)     # 3, 4
        store.create(2, " red", vocabulary=v, actor=USER)         # 5
        store.create(2, " grey", vocabulary=v, actor=USER)        # 6
        store.create(4, " is", vocabulary=v, actor=USER)          # 7
        store.create(4, " red", vocabulary=v, actor=USER)         # 8
        store.create(None, " grey", vocabulary=v, actor=USER)     # 9
        store.delete(6, actor=USER)
        store.delete(8, actor=USER)
        yield store


@pytest.fixture
def ranked(tmp_path):
    """One node, four alternatives recorded out of logprob order, and each of the three
    things an alternative can be."""
    with Store.initialise(tmp_path / "r", vocabulary="toy") as store:
        tip = tip_of(store, store.create(None, "The sky", vocabulary=ToyVocabulary(),
                                         actor=USER))
        store.generate(
            tip, {"length": 1},
            adapter=ToyAdapter([drew((102, [
                (102, -0.10),   # rank 0, drawn -- a child exists
                (104, -2.00),   # rank 1, realised below and then deleted
                (103, -0.50),   # rank 2, realised below; out of logprob order on purpose
                (105, -3.00),   # rank 3, never realised
            ]))]),
            actor=USER,
        )
        store.realise(tip, MODEL, 2, actor=USER)
        store.delete(tip_of(store, store.realise(tip, MODEL, 1, actor=USER)), actor=USER)
        yield store, tip


def tip_of(store, act):
    """An act names its tip; `create` returns the act, not the node."""
    return R.act_tokens(store.conn, act)[-1].id


# ---- segments ------------------------------------------------------------------------


def words(text):
    """Items that spell themselves, so a segmentation test needs no store."""
    return [(i, b) for i, b in enumerate(text)]


def test_ordinary_english_is_one_node_to_a_segment():
    cells = S.segments(words([b"The", b" sky"]), lambda w: w[1])
    assert [(c.text, len(c.nodes), c.decodes) for c in cells] == [
        ("The", 1, True), (" sky", 1, True)
    ]


def test_a_character_spelled_by_several_tokens_is_one_segment(tree):
    """The shortest run whose bytes decode, which across a fragment is more than one node.
    Nothing addresses a node inside it, which is why it is the unit and not the token."""
    tree.create(None, "é", vocabulary=ToyVocabulary(), actor=USER)
    frags = R.children(tree.conn, None)[-1]
    nodes = R.path_nodes(tree.conn, R.children(tree.conn, frags.id)[0].id)
    assert [n.token_id for n in nodes] == [FRAG_HI, FRAG_LO]

    spelling = R.token_bytes(tree.conn, (n.token_id for n in nodes))
    cells = S.segments(nodes, lambda n: spelling[n.token_id])
    assert len(cells) == 1
    assert cells[0].text == "é"
    assert [n.id for n in cells[0].nodes] == [n.id for n in nodes]


def test_a_run_ending_mid_character_is_a_marked_segment_of_its_own():
    cells = S.segments(words([b"The", b"\xc3"]), lambda w: w[1])
    assert [(c.text, c.decodes) for c in cells] == [("The", True), ("�", False)]


def test_bytes_that_can_never_complete_close_where_they_stand():
    """A truncated character waits for its tail; a byte that is not one is not a tail, and
    treating it as one would reach forward over text that decodes perfectly well."""
    cells = S.segments(words([b"\xc3", b" sky"]), lambda w: w[1])
    assert [(c.text, len(c.nodes), c.decodes) for c in cells] == [
        ("�", 1, False), (" sky", 1, True)
    ]


def test_a_stray_continuation_byte_is_its_own_segment():
    cells = S.segments(words([b"\xa9", b"The"]), lambda w: w[1])
    assert [(c.text, c.decodes) for c in cells] == [("�", False), ("The", True)]


# ---- the continuation rule -----------------------------------------------------------


def test_longest_takes_the_deepest_arm(tree):
    """Node 5 is a leaf and node 3 reaches two further, so the rule goes through 3."""
    assert [n.id for n in S.continuation(tree.conn, 2)] == [3, 4, 7]


def test_longest_breaks_a_tie_by_insertion_order(tree):
    """Nodes 5 and 3 are both live children of 2; make them the same depth and the earlier
    id wins, which is the only part of `longest` that is a choice rather than a reading."""
    tree.delete(4, actor=USER)
    assert [n.id for n in S.continuation(tree.conn, 2)] == [3]


def test_longest_is_not_first(tmp_path):
    """The shallow arm is the earlier child here, which is the only shape that tells the
    two apart -- anywhere the deeper arm is also the earlier one, `first` agrees.

    A preview line follows the rule the same way, so both are asserted against one tree.
    """
    with Store.initialise(tmp_path / "d", vocabulary="toy") as store:
        v = ToyVocabulary()
        store.create(None, "The", vocabulary=v, actor=USER)        # 1
        store.create(1, " sky", vocabulary=v, actor=USER)          # 2
        store.create(2, " red", vocabulary=v, actor=USER)          # 3, a leaf, and earlier
        store.create(2, " is blue", vocabulary=v, actor=USER)      # 4, 5
        assert [n.id for n in R.children(store.conn, 2)] == [3, 4]
        assert [n.id for n in S.continuation(store.conn, 1)] == [2, 4, 5]

        lines = S.branches(store.conn, 1, budget=100)
        assert [reading(b) for b in lines] == [" sky is blue"]
        assert [(b.parts_at, reading(b)) for b in lines[0].branches] == [(len(" sky"), " red")]


def test_a_continuation_does_not_follow_a_deleted_node(tree):
    """Node 8 is the deeper arm below node 4 only if a deleted node counts, and a reader
    cannot generate from one."""
    assert [n.id for n in S.continuation(tree.conn, 4)] == [7]


def test_a_node_that_is_not_live_continues_nowhere(tree):
    assert S.continuation(tree.conn, 6) == []


def test_the_rule_is_a_parameter_and_not_a_rule_of_the_read(tree):
    """What settles which member is right is reading one tree under two of them."""
    first = S.continuation(tree.conn, 2, rule=lambda tree, kids: kids[0])
    last = S.continuation(tree.conn, 2, rule=lambda tree, kids: kids[-1])
    assert [n.id for n in first] == [3, 4, 7]
    assert [n.id for n in last] == [5]


# ---- 1. a path -----------------------------------------------------------------------


def test_a_path_runs_root_to_leaf_through_the_node_asked_about(tree):
    cells = S.path(tree.conn, 2)
    assert "".join(c.text for c in cells) == "The sky is blue is"
    assert [m.node.id for c in cells for m in c.nodes] == [1, 2, 3, 4, 7]


def test_a_path_with_no_rule_is_the_ancestry_alone(tree):
    cells = S.path(tree.conn, 2, rule=None)
    assert [m.node.id for c in cells for m in c.nodes] == [1, 2]


def test_a_paths_text_is_its_bytes(tree):
    """Segmentation regroups nodes and must not change what they spell."""
    cells = S.path(tree.conn, 5)
    assert "".join(c.text for c in cells) == R.path_bytes(tree.conn, 5).decode()


def test_every_mark_on_a_path_agrees_with_the_single_node_read(tree):
    for cell in S.path(tree.conn, 5):
        for mark in cell.nodes:
            assert mark.live == R.is_live(tree.conn, mark.node.id)
            assert mark.logprob == R.node_logprob(tree.conn, mark.node.id)


def test_a_fork_is_a_parent_with_more_than_one_live_child(tree):
    """Node 3 and node 5 are the two arms of the same fork, so both carry the mark; the
    mark is on the node that parts, not on the parent it parts at."""
    marks = {m.node.id: m.fork for m in R.annotated_path(tree.conn, 5)}
    assert marks == {1: False, 2: False, 5: True}
    assert R.annotated_path(tree.conn, 3)[-1].fork is True


def test_a_deleted_sibling_hides_a_fork(tree):
    """Node 4 has two children and one is deleted, so node 7 is not a fork. Liveness is
    what the surface follows, and the record still holds node 8."""
    assert R.annotated_path(tree.conn, 7)[-1].fork is False
    assert len(R.children(tree.conn, 4)) == 2


def test_a_parent_that_is_not_live_forks_nowhere(tree):
    """A count of `deleted` on the siblings alone would call these two a fork. Liveness is
    what the surface follows, and nothing below node 6 is on the live tree at all."""
    v = ToyVocabulary()
    tree.undelete(6, actor=USER)            # an act begins at a live node
    a = tip_of(tree, tree.create(6, " is", vocabulary=v, actor=USER))
    b = tip_of(tree, tree.create(6, " red", vocabulary=v, actor=USER))
    assert [R.annotated_path(tree.conn, n)[-1].fork for n in (a, b)] == [True, True]

    tree.delete(6, actor=USER)
    assert [R.annotated_path(tree.conn, n)[-1].fork for n in (a, b)] == [False, False]


def test_a_root_is_never_a_fork(tree):
    """There are two roots and neither parts from anything: a fork is about a parent."""
    assert len(R.roots(tree.conn)) == 2
    assert [R.annotated_path(tree.conn, r.id)[0].fork for r in R.roots(tree.conn)] == [
        False, False
    ]


def test_a_path_below_a_deleted_node_is_marked_dead_without_carrying_the_flag(tree):
    marks = {m.node.id: (m.node.deleted, m.live) for m in R.annotated_path(tree.conn, 8)}
    assert marks[4] == (False, True)
    assert marks[8] == (True, False)


# ---- what is hidden ------------------------------------------------------------------


def ids(cells):
    return [m.node.id for cell in cells for m in cell.nodes]


def test_a_hidden_pass_carries_the_path_on_from_where_the_live_one_ran_out(tree):
    """Node 4's arms are 7 and 8, and 8 is already set aside. Setting 7 aside as well
    leaves the live path ending at 4, which is the tail a reader truncated; asking for what
    is hidden reaches it again, marked, so there is somewhere to undo it from."""
    tree.delete(7, actor=USER)
    assert ids(S.path(tree.conn, 4)) == [1, 2, 3, 4]

    marks = [m for cell in S.path(tree.conn, 4, hidden=True) for m in cell.nodes]
    assert [m.node.id for m in marks] == [1, 2, 3, 4, 7]
    assert [m.live for m in marks] == [True, True, True, True, False]


def test_a_hidden_pass_appends_and_never_chooses(tree):
    """The trap. Node 8 is set aside and made the deeper arm below node 4, so a rule handed
    both arms at once would take it -- and the reader would be moved by a toggle that only
    says what to draw. The live path is picked first and is the same path either way.
    """
    tree.undelete(8, actor=USER)  # an act begins at a live node
    tree.create(8, " is blue red grey", vocabulary=ToyVocabulary(), actor=USER)
    tree.delete(8, actor=USER)

    # What the rule does when it is offered both, which is what must not happen.
    assert S.continuation(tree.conn, 4, hidden=True)[0].id == 8
    assert ids(S.path(tree.conn, 4, hidden=True)) == [1, 2, 3, 4, 7]
    assert ids(S.path(tree.conn, 4, hidden=True)) == ids(S.path(tree.conn, 4))


def test_a_node_that_is_hidden_continues_nowhere_until_it_is_asked_for(tree):
    """Node 6 was set aside with a tail below it. The path through it stops there, because
    a continuation follows liveness; the toggle is what carries it down."""
    tree.undelete(6, actor=USER)
    tree.create(6, " is blue", vocabulary=ToyVocabulary(), actor=USER)  # 10, 11
    tree.delete(6, actor=USER)

    assert ids(S.path(tree.conn, 6)) == [1, 2, 6]
    assert ids(S.path(tree.conn, 6, hidden=True)) == [1, 2, 6, 10, 11]


def test_the_ancestry_alone_is_the_ancestry_whatever_the_toggle_says(tree):
    """`rule=None` asks for what is above a node and nothing below it, so there is no pass
    for a hidden one to follow."""
    assert S.path(tree.conn, 6, rule=None, hidden=True) == S.path(tree.conn, 6, rule=None)


# ---- overlays ------------------------------------------------------------------------


def test_what_a_node_stands_in_is_its_parents_ranking_and_not_its_own(ranked):
    """The trap. A node's own ranked edges are the alternatives for what *follows* it, so
    a read that attached them would describe the wrong position -- and would be right at
    every node of a chain where each carries a ranking of the same width, which is most of
    a generated path.
    """
    store, tip = ranked
    child = R.children(store.conn, tip)[0]
    cells = S.path(store.conn, child.id, rule=None)
    drawn = S.overlays(store.conn, cells)

    (stood,) = drawn[child.id]
    assert stood.rows == len(R.ranking(store.conn, tip)), "the parent's ranking"
    assert child.id not in R.spreads(store.conn, [child.id]), "the child ranked nothing"
    assert stood.top == max(e.logprob for e in R.ranking(store.conn, tip))


def test_a_root_stands_in_no_ranking_and_is_absent(ranked):
    """A root has no parent, so there is no position above it to summarise. Absent rather
    than empty: a reader drawing nothing and a reader drawing a zero are different."""
    store, tip = ranked
    cells = S.path(store.conn, tip, rule=None)
    root = cells[0].nodes[0].node
    assert root.parent is None
    assert root.id not in S.overlays(store.conn, cells)


def test_a_flag_is_the_node_against_the_top_of_what_it_stood_in(ranked):
    """What the first overlay is made of, and it needs nothing the path does not carry: the
    node's own logprob is on it already, and the top row comes from what it stood in. The
    price is the two apart, so the node that took the top row is the one that pays nothing.

    A deleted child is priced like any other. Liveness decides what is drawn; it has never
    decided what a ranking recorded.
    """
    store, tip = ranked
    rows = {edge.token_id: edge.logprob for edge in R.ranking(store.conn, tip)}
    top = max(rows.values())

    priced = {}
    for child in R.children(store.conn, tip):
        cells = S.path(store.conn, child.id, rule=None)
        mark = cells[-1].nodes[-1]
        (stood,) = S.overlays(store.conn, cells)[child.id]
        assert stood.top == top
        priced[child.token_id] = stood.top - mark.logprob

    assert priced == pytest.approx({t: top - rows[t] for t in priced})
    assert [t for t, cost in priced.items() if cost == 0] == [
        max(rows, key=lambda t: rows[t])
    ], "exactly the token that took the top row is unflagged"


def test_an_authored_node_stands_in_a_ranking_it_has_no_row_in(ranked):
    """Two ways to have no value, and they are not one. An authored token was never ranked,
    so it is off the scale rather than at its end -- but the position it occupies still has
    a distribution, which is why the spread is about the position and the flag is about the
    node.
    """
    store, tip = ranked
    written = tip_of(store, store.create(tip, " grey", vocabulary=ToyVocabulary(),
                                         actor=USER))
    cells = S.path(store.conn, written, rule=None)
    mark = cells[-1].nodes[-1]

    assert mark.logprob is None, "nothing ranked it, so it has no row"
    assert written in S.overlays(store.conn, cells), "the position was ranked all the same"


def test_overlays_are_one_query_whatever_the_path_holds(ranked):
    """What decorating the output rather than joining the recursion is for. A spread per
    node would be one statement each, which is the N+1 the three reads exist to avoid."""
    store, tip = ranked
    cells = S.path(store.conn, tip, rule=None)
    counted = 0

    def count(statement):
        nonlocal counted
        counted += 1

    store.conn.set_trace_callback(count)
    S.overlays(store.conn, cells)
    store.conn.set_trace_callback(None)
    assert counted == 1


# ---- 2. a ranking --------------------------------------------------------------------


def test_a_ranking_is_shown_in_descending_logprob(ranked):
    """The store keeps recorded order and expects descending rather than enforcing it.
    The surface sorts, which is why the fixture records them out of order."""
    store, tip = ranked
    assert [e.edge.rank for e in R.ranking_with_children(store.conn, tip)] == [0, 1, 2, 3]
    assert [e.edge.token_id for e in S.ranking(store.conn, tip)] == [102, 103, 104, 105]


def test_a_ranking_shows_what_was_taken_among_the_alternatives(ranked):
    """Not the branchable set alone: a reader looking at a position needs to see the one
    taken sitting among the rest, and the branchable set is then the rows with no child."""
    store, tip = ranked
    rows = S.ranking(store.conn, tip)
    assert [e.child is None for e in rows] == [False, False, False, True]
    assert [e.edge.token_id for e in rows if e.child is None] == [
        e.token_id for e in R.unrealised_edges(store.conn, tip)
    ]


def test_every_row_spells_its_token(ranked):
    store, tip = ranked
    for row in S.ranking(store.conn, tip):
        assert row.spelling == ToyVocabulary().bytes_for(row.edge.token_id)


def test_a_deleted_child_is_still_a_child(ranked):
    """The merge key is what forbids realising the edge again, so reporting it as
    branchable would offer a write that is rejected."""
    store, tip = ranked
    row = next(e for e in S.ranking(store.conn, tip) if e.edge.token_id == 104)
    assert row.child is not None
    assert row.child.deleted is True
    assert 104 not in {e.token_id for e in R.unrealised_edges(store.conn, tip)}


def test_two_sources_are_two_rankings_and_are_not_interleaved(tmp_path):
    """A rank alone names nothing, and one order over the union of two distributions would
    sit rows side by side that were never alternatives to each other."""
    with Store.initialise(tmp_path / "s", vocabulary="toy") as store:
        tip = tip_of(store, store.create(None, "The sky", vocabulary=ToyVocabulary(),
                                         actor=USER))
        store.generate(tip, {"length": 1},
                       adapter=ToyAdapter([drew((102, [(102, -9.0)]))]), actor=USER)
        store.generate(tip, {"length": 1},
                       adapter=ToyAdapter([drew((103, [(103, -0.1)]))], source=OTHER),
                       actor=USER)
        rows = S.ranking(store.conn, tip)
        assert len({e.edge.source for e in rows}) == 2
        assert [e.edge.source for e in rows] == sorted(e.edge.source for e in rows)


# ---- 3. a branch subtree -------------------------------------------------------------


@pytest.fixture
def band(tmp_path):
    """A tree shaped for the band: one line with a fork partway along it.

        1  The
        2   sky      a line from here reads " sky is blue"
        3    is
        4     blue
        6     red    parts from that line after " sky is"
        5   red      the other line at the split below node 1
    """
    with Store.initialise(tmp_path / "b", vocabulary="toy") as store:
        v = ToyVocabulary()
        store.create(None, "The", vocabulary=v, actor=USER)        # 1
        store.create(1, " sky is blue", vocabulary=v, actor=USER)  # 2, 3, 4
        store.create(1, " red", vocabulary=v, actor=USER)          # 5
        store.create(3, " red", vocabulary=v, actor=USER)          # 6
        yield store


def reading(branch):
    return "".join(c.text for c in branch.segments)


def test_a_line_follows_the_rule_that_selecting_it_would(band):
    """What a preview shows is a truthful prefix of what taking it gives."""
    lines = S.branches(band.conn, 1, budget=100)
    assert [reading(b) for b in lines] == [" sky is blue", " red"]
    assert [b.parts_at for b in lines] == [0, 0]
    taken = S.continuation(band.conn, 1)
    assert reading(lines[0]) == "".join(
        R.node_bytes(band.conn, n.id).decode() for n in taken
    )


def test_a_nested_line_parts_where_it_parts_and_not_where_it_is_deep(band):
    """The indentation is where paths part: node 6 parts after ' sky is', which is seven
    characters into the line above it, not three tokens into it."""
    lines = S.branches(band.conn, 1, budget=100)
    inner = lines[0].branches
    assert [reading(b) for b in inner] == [" red"]
    assert inner[0].parts_at == len(" sky is")
    assert inner[0].branches == []


def test_a_budget_cuts_a_line_at_a_segment_and_counts_what_went_with_it(band):
    """A line clipped before its own fork has nowhere to hang that fork's alternatives, so
    they are dropped, and a silent truncation would read as 'that is all of them'."""
    lines = S.branches(band.conn, 1, budget=5)
    assert reading(lines[0]) == " sky"
    assert lines[0].branches == []
    assert lines[0].dropped == 1


def test_a_line_always_gets_its_first_segment(band):
    """A line that showed nothing is not a line."""
    lines = S.branches(band.conn, 1, budget=0)
    assert [reading(b) for b in lines] == [" sky", " red"]


def test_a_budget_that_reaches_the_fork_keeps_it(band):
    lines = S.branches(band.conn, 1, budget=len(" sky is"))
    assert reading(lines[0]) == " sky is"
    assert [b.parts_at for b in lines[0].branches] == [len(" sky is")]
    assert lines[0].dropped == 0


def test_a_divergence_inside_a_character_is_counted_rather_than_offered(tmp_path):
    """A segment cannot be split, so there is no column at which such a line begins. It is
    counted with what the budget cut, since what a reader is owed is how many are missing.
    """
    with Store.initialise(tmp_path / "f", vocabulary="toy") as store:
        v = ToyVocabulary()
        store.create(None, "The", vocabulary=v, actor=USER)      # 1
        store.create(1, "é", vocabulary=v, actor=USER)      # 2 hi, 3 lo
        store.create(2, " sky", vocabulary=v, actor=USER)        # 4, parts inside node 2
        assert R.get_node(store.conn, 2).token_id == FRAG_HI
        assert R.get_node(store.conn, 3).token_id == FRAG_LO

        lines = S.branches(store.conn, 1, budget=100)
        assert [reading(b) for b in lines] == ["é"]
        assert lines[0].branches == []
        assert lines[0].dropped == 1


def test_a_leaf_has_no_band(band):
    assert S.branches(band.conn, 4, budget=100) == []


def test_the_band_is_depth_first(band):
    """The line being read comes first, then its siblings at the split, and within each
    line the lines that part from it."""
    store = band
    v = ToyVocabulary()
    store.create(4, " is blue", vocabulary=v, actor=USER)   # 7, 8 -- keeps node 4 the deeper arm
    store.create(6, " grey", vocabulary=v, actor=USER)      # 9, below node 6
    store.create(6, " blue", vocabulary=v, actor=USER)      # 10, the same depth as 9

    def flatten(lines, depth=0):
        for line in lines:
            yield depth, reading(line)
            yield from flatten(line.branches, depth + 1)

    lines = S.branches(store.conn, 1, budget=100)
    assert list(flatten(lines)) == [
        (0, " sky is blue is blue"),
        (1, " red grey"),
        (2, " blue"),
        (0, " red"),
    ]


# ---- cost ----------------------------------------------------------------------------


def chain(store, length):
    v = ToyVocabulary()
    node = tip_of(store, store.create(None, "The", vocabulary=v, actor=USER))
    for _ in range(length):
        node = tip_of(store, store.create(node, " sky", vocabulary=v, actor=USER))
    return node


def test_a_path_costs_the_same_whatever_its_length(tmp_path):
    """Every bulk read the core ships is N+1 as built, and what these three are written
    against is that they are not. The count is the invariant; the number is not."""
    counts = []
    for length in (4, 40):
        with Store.initialise(tmp_path / f"c{length}", vocabulary="toy") as store:
            leaf = chain(store, length)
            seen = 0

            def count(statement):
                nonlocal seen
                seen += 1

            store.conn.set_trace_callback(count)
            cells = S.path(store.conn, leaf)
            store.conn.set_trace_callback(None)
            assert sum(len(c.nodes) for c in cells) == length + 1
            counts.append(seen)
    assert counts[0] == counts[1]


# ---- naming a root ---------------------------------------------------------------------


def reading_label(name):
    return "".join(cell.text for cell in name.segments)


def test_a_label_stops_where_the_tree_parts_and_says_it_did(tree):
    """Node 2 has two live children, so the text belonging to the root alone ends there."""
    name = S.label(tree.conn, 1, 100)
    assert reading_label(name) == "The sky"
    assert name.forked is True


def test_a_label_cut_for_room_does_not_claim_the_tree_parts(tree):
    """The two stops read the same in the text and do not mean the same thing, which is the
    whole reason `forked` is carried separately."""
    name = S.label(tree.conn, 1, 3)
    assert reading_label(name) == "The"
    assert name.forked is False


def test_a_label_that_reaches_a_leaf_does_not_claim_the_tree_parts(tree):
    name = S.label(tree.conn, 9, 100)
    assert reading_label(name) == " grey"
    assert name.forked is False


def test_a_deleted_arm_does_not_part_a_label(tree):
    """Node 4 has two children and one is deleted, so the walk goes through it. Liveness is
    what parts a label, and a label that counted the record's children would stop here."""
    name = S.label(tree.conn, 3, 100)
    assert reading_label(name) == " is blue is"
    assert name.forked is False


def test_no_root_parts_at_itself_however_many_there_are(tree):
    """A root has no incoming edge, so it cannot be the node a parent parts at, and a label
    is never empty. Two roots in one store are not siblings of each other."""
    for root in R.roots(tree.conn):
        assert reading_label(S.label(tree.conn, root.id, 100)) != ""


def test_a_label_parting_inside_a_character_keeps_the_mark(tmp_path):
    """A segment cannot be split, so a divergence inside one leaves a label ending in the
    bytes that do not decode -- shown as U+FFFD, as everywhere else. The tree does part
    there, and `forked` says so."""
    with Store.initialise(tmp_path / "f", vocabulary="toy") as store:
        v = ToyVocabulary()
        store.create(None, "The", vocabulary=v, actor=USER)  # 1
        store.create(1, "é", vocabulary=v, actor=USER)  # 2 hi, 3 lo
        store.create(2, " sky", vocabulary=v, actor=USER)  # 4, parts inside the character
        name = S.label(store.conn, 1, 100)
        assert reading_label(name) == "The�"
        assert [cell.decodes for cell in name.segments] == [True, False]
        assert name.forked is True


def test_naming_a_root_does_not_cost_what_reading_one_does(tmp_path):
    """The walk asks for children a node at a time and stops, so what it reads is set by the
    budget and not by the tree. The invariant is that a longer chain costs the same."""
    counts = []
    for length in (4, 40):
        with Store.initialise(tmp_path / f"n{length}", vocabulary="toy") as store:
            chain(store, length)
            seen = 0

            def count(statement):
                nonlocal seen
                seen += 1

            store.conn.set_trace_callback(count)
            S.label(store.conn, 1, 12)
            store.conn.set_trace_callback(None)
            counts.append(seen)
    assert counts[0] == counts[1]


# ---- what the tree below a node holds --------------------------------------------------


@pytest.fixture
def lopsided(tmp_path):
    """One fork whose arms disagree about which is the bigger, so that a rule by one
    measure and a rule by another cannot both be right.

        1  The
        2   sky        a chain: tall and thin
        3    is
        4     blue
        5   is         a bush: short and wide
        6    blue
        7    red
        8    grey
    """
    with Store.initialise(tmp_path / "l", vocabulary="toy") as store:
        v = ToyVocabulary()
        store.create(None, "The", vocabulary=v, actor=USER)     # 1
        store.create(1, " sky is blue", vocabulary=v, actor=USER)  # 2, 3, 4
        store.create(1, " is", vocabulary=v, actor=USER)        # 5
        store.create(5, " blue", vocabulary=v, actor=USER)      # 6
        store.create(5, " red", vocabulary=v, actor=USER)       # 7
        store.create(5, " grey", vocabulary=v, actor=USER)      # 8
        yield store


def walk(tree, node, what):
    """The same measure, computed by recursion rather than by the fold under test. Two
    implementations of one number is the only way a fold that is wrong everywhere in the
    same direction gets caught."""
    kids = tree.below(node)
    below = [walk(tree, k.id, what) for k in kids]
    if what == "height":
        return 1 + max(below, default=0)
    if what == "size":
        return 1 + sum(below)
    if what == "forks":
        return int(len(kids) > 1) + sum(below)
    return 1 + (below[0] if len(kids) == 1 else 0)  # run


def test_every_fold_agrees_with_walking_the_tree(tree):
    """The fold runs once over a flat reversed list and is easy to get wrong in a way that
    is consistent, so nothing else would disagree with it. This disagrees with it."""
    for hidden in (False, True):
        held = S.Subtree(tree.conn, None, hidden)
        for node in held.nodes():
            for name, read in S.DOWNWARD.items():
                assert read(held, node.id) == walk(held, node.id, name), (
                    f"{name} at {node.id}, hidden={hidden}"
                )


def test_the_run_stops_at_a_fork_and_at_a_leaf(tree):
    """Both are places the walking stops, so the corridor is one node long at each. A run
    that counted past a fork would say a reader could move without choosing."""
    held = S.Subtree(tree.conn, None)
    assert len(held.below(2)) > 1 and held.run(2) == 1, "a fork is the end of a corridor"
    assert held.below(7) == [] and held.run(7) == 1, "and so is a leaf"
    assert held.run(1) == 1 + held.run(2), "one child is no choice, so the corridor carries"


def test_the_rules_are_the_measures_and_longest_is_the_height_one(lopsided):
    """The relation the whole of this rests on. If `longest` were written separately it
    could drift from the measure it is, and nothing but this would notice."""
    assert set(S.RULES) == (set(S.DOWNWARD) - {"height"}) | {"longest"}
    assert S.longest is S.RULES["longest"]
    held = S.Subtree(lopsided.conn, None)
    kids = held.below(1)
    assert S.longest(held, kids) is S.argmax(S.Subtree.height)(held, kids)


def test_a_rule_by_another_measure_takes_another_path(lopsided):
    """Otherwise the family is decoration. The fork's tall arm and its wide arm are
    different nodes, so a rule that reads height and one that reads size cannot agree."""
    taken = {
        name: ids(S.path(lopsided.conn, 1, rule))[1]
        for name, rule in S.RULES.items()
    }
    assert taken["longest"] == 2, "the tall arm"
    assert taken["size"] == 5 and taken["forks"] == 5, "the wide one"
    assert taken["run"] == 2, "the corridor, which is the tall arm again"


def test_what_is_beneath_reaches_the_ancestry_and_not_only_the_continuation(tree):
    """The descent is anchored above the roots for this reason: what lies below an ancestor
    is where the tree widened, which is the question a reader asks of what they have read.
    A descent anchored at the node asked about would leave the root itself unmeasured."""
    cells = S.path(tree.conn, 1)
    under = S.beneath(tree.conn, cells)
    assert set(under) == set(ids(cells))
    assert under[1]["height"] == 5 and under[1]["size"] == 6
    assert under[1]["forks"] == 1, "node 2 is the only live fork"


def test_what_is_beneath_follows_the_toggle_where_the_rule_never_does(tree):
    """The one place a measure and the rule it generates part company. `docs/SURFACE.md`
    has the rule take the live path first and admit what is set aside only below a live
    leaf, so it is never offered both at one parent; a measure only reports, so it counts
    what the page is showing. The disagreement is how a reader sees what they pruned.
    """
    cells = S.path(tree.conn, 1)
    live = S.beneath(tree.conn, cells, hidden=False)
    shown = S.beneath(tree.conn, cells, hidden=True)

    assert live[2]["size"] < shown[2]["size"], "what was set aside is counted when shown"
    assert live[2]["forks"] == 1 and shown[2]["forks"] == 2, "and a hidden arm makes a fork"
    # And the path itself does not move, whatever the measure says about it.
    assert ids(S.path(tree.conn, 1)) == ids(cells)


def test_what_is_beneath_costs_the_same_whatever_the_path_holds(tree):
    """One descent and a couple of small reads around it, none of them per node -- which is
    the property, and not the number. A measure asked for node by node would be the N+1 the
    three reads exist to avoid, and would grow with the path where this does not.
    """
    def asked(node):
        cells = S.path(tree.conn, node)
        counted = 0

        def count(statement):
            nonlocal counted
            counted += 1

        tree.conn.set_trace_callback(count)
        S.beneath(tree.conn, cells)
        tree.conn.set_trace_callback(None)
        return len(ids(cells)), counted

    short, long = asked(9), asked(1)
    assert short[0] < long[0], "the two paths are different lengths"
    assert short[1] == long[1], "and cost the same to measure"
