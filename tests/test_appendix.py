"""The appendix of `docs/CORE.md`, built and then read back.

The appendix is the closest thing to a test the format had before any code existed: seven
stages with real ids and logprobs, walked by hand against every invariant. This is that
walk, done by the implementation, asserting **only what the document states** -- its rows,
its node numbering, and its own *Reading the finished tree*.

Node ids are opaque and this pins them anyway. That is deliberate: the appendix numbers
its nodes 1 through 12, and reproducing that numbering means every merge decision along
the way agreed with the document. A wrong merge shows up here as a renumbering long before
it shows up as a wrong byte.
"""

from __future__ import annotations

import pytest

from appendix import BYTES, MODEL, USER, ScriptedAdapter
from tokenloom.core import Store, violations
from tokenloom.core import reads as R


@pytest.fixture
def tree(tmp_path):
    """The seven stages, in order. Every invariant is checked after each one."""
    store = Store.initialise(tmp_path / "sky", vocabulary="qwen2.5-7b-base")
    adapter = ScriptedAdapter()
    acts = {}

    def clean(stage):
        found = violations(store.conn)
        assert not found, f"stage {stage}: {[str(v) for v in found]}"

    # Stage 1 -- create(null, "The sky"). Authored by the unnamed user; begins a root.
    acts[1] = store.create(None, "The sky", vocabulary=adapter, source=USER)
    clean(1)

    # Stage 2 -- generate(at=2), top_k 5, top_n 5, length 3, seed 42.
    acts[2], _ = store.generate(2, {"top_k": 5, "top_n": 5, "length": 3}, adapter=adapter, seed=42)
    clean(2)

    # The ranking at node 2 stands at five rows, and node 3's logprob is read off it.
    before = R.node_logprob(store.conn, 3)

    # Stage 3 -- generate(at=2), top_k 5, top_n 20, length 2, seed 99.
    acts[3], _ = store.generate(2, {"top_k": 5, "top_n": 20, "length": 2}, adapter=adapter, seed=99)
    clean(3)

    # Stage 4 -- identical to stage 2. Same parameters and the same seed.
    acts[4], _ = store.generate(2, {"top_k": 5, "top_n": 5, "length": 3}, adapter=adapter, seed=42)
    clean(4)

    # Stage 5 -- realise(node 2, source 2, rank 0). The unnamed user takes ` is`.
    acts[5] = store.realise(2, MODEL, 0, actor=USER)
    clean(5)

    # Stage 6 -- create(node 8, "<|endoftext|>🜁"), through the special-token path.
    acts[6] = store.create(8, "<|endoftext|>\U0001f701", vocabulary=adapter,
                           source=USER, special=True)
    clean(6)

    # Stage 7 -- generate(at=12), top_n 200. Refused; no model is called.
    acts[7], answer = store.generate(12, {"top_k": 5, "top_n": 200, "length": 4},
                                     adapter=adapter, seed=7)
    clean(7)

    return store, acts, before, answer


# ---- the rows the appendix prints ---------------------------------------------------


def test_sources_are_numbered_as_the_appendix_numbers_them(tree):
    """Source 1 is the unnamed user; source 2 is the model, named with its quantisation."""
    store, *_ = tree
    assert store.conn.execute("SELECT id, kind, name FROM sources ORDER BY id").fetchall() == [
        (1, "user", ""),
        (2, "model", "qwen2.5-7b-base-q4km"),
    ]


def test_nodes_are_numbered_as_the_appendix_numbers_them(tree):
    """All twelve rows: id, parent, token and source, exactly as the stages print them."""
    store, *_ = tree
    assert store.conn.execute(
        "SELECT id, parent, token_id, source FROM nodes ORDER BY id"
    ).fetchall() == [
        (1, None, 785, 1),        # The          stage 1
        (2, 1, 12884, 1),         # " sky"
        (3, 2, 5023, 2),          # " currently" stage 2
        (4, 3, 702, 2),           # " has"
        (5, 4, 220, 2),           # " "
        (6, 2, 702, 2),           # " has"       stage 3
        (7, 6, 6519, 2),          # " turned"
        (8, 2, 374, 2),           # " is"        stage 5
        (9, 8, 151643, 1),        # <|endoftext|> stage 6
        (10, 9, 9284, 1),         # F0 9F
        (11, 10, 250, 1),         # 9C
        (12, 11, 223, 1),         # 81
    ]


def test_node_4_and_node_6_are_both_has_and_are_different_nodes(tree):
    """One is a child of node 3 and one of node 2, so the merge key never brings them
    together."""
    store, *_ = tree
    four, six = R.get_node(store.conn, 4), R.get_node(store.conn, 6)
    assert four.token_id == six.token_id == 702
    assert four.source == six.source
    assert (four.parent, six.parent) == (3, 2)


def test_stage_3_extends_node_2s_ranking_from_five_rows_to_twenty(tree):
    """The five already stored keep their values; the fifteen below them are appended."""
    store, *_ = tree
    rows = R.ranking(store.conn, 2, source=2)
    assert [(e.rank, e.token_id, round(e.logprob, 4)) for e in rows] == [
        (0, 374, -1.3218), (1, 702, -1.6666), (2, 5023, -2.0363),
        (3, 572, -2.7138), (4, 594, -3.7901),
        (5, 1030, -4.3049), (6, 518, -4.3088), (7, 3685, -4.3841), (8, 3403, -4.3868),
        (9, 1431, -4.8847), (10, 304, -4.9828), (11, 323, -5.0173), (12, 686, -5.1101),
        (13, 748, -5.1507), (14, 646, -5.7753), (15, 17167, -5.8098), (16, 5868, -5.8294),
        (17, 2669, -5.9023), (18, 4041, -5.9496), (19, 1083, -5.9643),
    ]


def test_node_3s_logprob_is_unchanged_by_the_extension(tree):
    """−2.0363 before the extension and −2.0363 after it.

    This is the invariant the whole extend-never-rewrite rule exists for, and it is
    asserted as an unchanged *value at an address* rather than as a number: what matters
    is that the later generation did not move it.
    """
    store, _, before, _ = tree
    assert R.node_logprob(store.conn, 3) == before == pytest.approx(-2.0363)


def test_node_5_and_node_8_have_no_ranking(tree):
    """Node 5 is a tip generation stopped at, so no distribution for a following position
    was ever computed. Node 8 was realised, and nothing has generated from it."""
    store, *_ = tree
    assert R.ranking(store.conn, 5) == []
    assert R.ranking(store.conn, 8) == []


def test_stage_4_writes_an_act_and_no_nodes(tree):
    """Every field but the id identical to act 2 -- and the node count does not move."""
    store, acts, _, _ = tree
    fields = "op, source, origin, tip, params, seed, terminator"
    two = store.conn.execute(f"SELECT {fields} FROM acts WHERE id = ?", (acts[2],)).fetchone()
    four = store.conn.execute(f"SELECT {fields} FROM acts WHERE id = ?", (acts[4],)).fetchone()
    assert two == four == ("generate", 2, 2, 5, 1, 42, "limit")


def test_the_act_source_and_the_node_source_differ_on_realise(tree):
    """A reader acted; the model is what ranked the edge, and the node carries the model."""
    store, acts, _, _ = tree
    op, source, origin, tip, rank = store.conn.execute(
        "SELECT op, source, origin, tip, rank FROM acts WHERE id = ?", (acts[5],)
    ).fetchone()
    assert (op, source, origin, tip, rank) == ("realise", 1, 2, 8, 0)
    assert R.get_node(store.conn, 8).source == 2


def test_stage_7_is_an_act_with_no_tip(tree):
    """Nothing was drawn and no node exists to name. Params row 3 holds the request that
    was refused and stays there."""
    store, acts, _, answer = tree
    assert answer.terminator == "refused"
    assert store.conn.execute(
        "SELECT op, source, origin, tip, params, seed, terminator FROM acts WHERE id = ?",
        (acts[7],),
    ).fetchone() == ("generate", 2, 12, None, 3, 7, "refused")
    assert store.conn.execute("SELECT json FROM params WHERE id = 3").fetchone()[0] == (
        '{"length":4,"top_k":5,"top_n":200}'
    )


def test_identical_requests_intern_to_one_params_row(tree):
    """Stages 2 and 4 ask for the same thing, so the store holds three rows and not four."""
    store, *_ = tree
    assert store.conn.execute("SELECT COUNT(*) FROM params").fetchone()[0] == 3


def test_vocab_holds_only_the_ids_this_tree_stores(tree):
    """Filled from the vocabulary and never from a generation, so the directory stays
    self-contained and small."""
    store, *_ = tree
    stored = dict(store.conn.execute("SELECT token_id, bytes FROM vocab"))
    assert {k: bytes(v) for k, v in stored.items()} == BYTES


# ---- Reading the finished tree ------------------------------------------------------


def test_path_bytes_to_node_5(tree):
    store, *_ = tree
    assert R.path_bytes(store.conn, 5) == b"The sky currently has "


def test_path_bytes_to_node_12(tree):
    """`The sky is<|endoftext|>🜁`. Display shows the end-of-text token literally, and the
    three fragment nodes reassemble into one character."""
    store, *_ = tree
    assert R.path_bytes(store.conn, 12) == "The sky is<|endoftext|>\U0001f701".encode()


def test_nodes_10_and_11_spell_fragments(tree):
    """Neither is valid UTF-8 alone, and the record treats them as it treats any node."""
    store, *_ = tree
    for node in (10, 11):
        with pytest.raises(UnicodeDecodeError):
            R.node_bytes(store.conn, node).decode("utf-8")
        assert R.path_bytes(store.conn, node)  # a path through one is still readable as bytes


def test_node_3s_logprob(tree):
    """−2.0363: the edge at node 2 for source 2 carrying token 5023. Stored once, derived
    rather than duplicated."""
    store, *_ = tree
    assert R.node_logprob(store.conn, 3) == pytest.approx(-2.0363)
    assert R.node_logprob(store.conn, 1) is None  # a root has no parent to carry one


def test_unrealised_edges_at_node_2_are_ranks_3_through_19(tree):
    """Ranks 0, 1 and 2 have children: nodes 8, 6 and 3. This is the branchable set."""
    store, *_ = tree
    assert [e.rank for e in R.unrealised_edges(store.conn, 2)] == list(range(3, 20))


def test_sampling_frequency(tree):
    """2 at node 3 -- acts 2 and 4 both pass through it. 1 at node 2: four acts begin
    there, and an act's range begins below its origin."""
    store, acts, _, _ = tree
    assert R.frequency(store.conn, 3) == 2
    assert R.acts_through(store.conn, 3) == sorted([acts[2], acts[4]])
    assert R.frequency(store.conn, 2) == 1
    assert R.acts_through(store.conn, 2) == [acts[1]]


def test_depth_of_node_12_is_6(tree):
    store, *_ = tree
    assert R.depth(store.conn, 12) == 6
    assert R.depth(store.conn, 1) == 0


def test_branch_points_are_node_2_alone(tree):
    store, *_ = tree
    assert R.branch_points(store.conn) == [2]
    assert [c.id for c in R.children(store.conn, 2)] == [3, 6, 8]


def test_agreement(tree):
    """Node 3 is produced by two acts. No node here has a cross-source sibling."""
    store, *_ = tree
    found = R.agreement(store.conn)
    assert found["repeated"] == [3, 4, 5]
    assert found["cross_source"] == []


def test_an_acts_tokens_are_the_path_from_origin_exclusive_to_tip_inclusive(tree):
    store, acts, _, _ = tree
    assert [n.id for n in R.act_tokens(store.conn, acts[1])] == [1, 2]
    assert [n.id for n in R.act_tokens(store.conn, acts[2])] == [3, 4, 5]
    assert [n.id for n in R.act_tokens(store.conn, acts[5])] == [8]
    assert R.act_tokens(store.conn, acts[7]) == []


def test_the_finished_tree_holds_every_invariant(tree):
    store, *_ = tree
    assert violations(store.conn) == []
