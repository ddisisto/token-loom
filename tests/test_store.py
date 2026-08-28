"""The paths the appendix does not run.

Rejection, liveness, the abandoned-act sweep, declination, a backend that dies mid-call.
Each of these is a statement `docs/CORE.md` makes that the worked example never exercises,
and CLAUDE.md's own note applies: one fault fell out only of running a path nothing had run.
"""

from __future__ import annotations

import subprocess
import sys

import pytest

from tokenloom.core import Generation, Rejected, Source, Store, StoreError, violations
from tokenloom.core import reads as R
from toy import MODEL, OTHER, USER, VOCAB, ToyAdapter, ToyVocabulary, drew


@pytest.fixture
def store(tmp_path):
    with Store.initialise(tmp_path / "t", vocabulary="toy") as s:
        yield s


def seeded(store) -> int:
    """`The sky` authored by the unnamed user. Returns the tip."""
    store.create(None, "The sky", vocabulary=ToyVocabulary(), source=USER)
    return R.roots(store.conn)[0].id + 1


# ---- create -------------------------------------------------------------------------


def test_create_rejects_text_that_does_not_round_trip(store):
    """`create` checks the round trip on the text at hand rather than assuming it.

    The comparison is against the reassembly a reader will do, never against a backend's
    own way of turning ids back into text.
    """

    class Lossy(ToyVocabulary):
        def tokenize(self, text, *, special=False):
            return super().tokenize(text)[:-1]  # drops the last token

    with pytest.raises(Rejected, match="round trip"):
        store.create(None, "The sky", vocabulary=Lossy(), source=USER)
    assert R.roots(store.conn) == []  # a rejection leaves no trace


def test_create_rejects_bytes_that_are_not_utf8(store):
    with pytest.raises(Rejected, match="valid UTF-8"):
        store.create(None, b"\xc3", vocabulary=ToyVocabulary(), source=USER)


def test_create_that_would_add_no_tokens_is_rejected(store):
    with pytest.raises(Rejected):
        store.create(None, "", vocabulary=ToyVocabulary(), source=USER)
    assert store.conn.execute("SELECT COUNT(*) FROM acts").fetchone()[0] == 0


def test_roots_do_not_merge(store):
    """A root has no parent, so the merge key does not reach it: two roots with the same
    token and source stay distinct, and each begins its own trie."""
    a = store.create(None, "The sky", vocabulary=ToyVocabulary(), source=USER)
    b = store.create(None, "The sky", vocabulary=ToyVocabulary(), source=USER)
    assert a != b
    roots = R.roots(store.conn)
    assert len(roots) == 2
    assert roots[0].token_id == roots[1].token_id
    assert roots[0].source == roots[1].source


def test_authored_text_never_collapses_into_a_model_draw_that_matches(store):
    """Source is part of the merge key, so the split is visible in the tree."""
    tip = seeded(store)
    adapter = ToyAdapter([drew((102, [(102, -0.5)]))])  # ` is`
    store.generate(tip, {"length": 1}, adapter=adapter, seed=1)
    store.create(tip, " is", vocabulary=ToyVocabulary(), source=USER)
    kids = R.children(store.conn, tip)
    assert [k.token_id for k in kids] == [102, 102]
    assert kids[0].source != kids[1].source


# ---- liveness -----------------------------------------------------------------------


def test_a_delete_names_one_node_and_descendants_are_untouched(store):
    """Whether a node is live is derived by walking the ancestry, so a delete is one write."""
    tip = seeded(store)
    root = R.roots(store.conn)[0].id
    store.delete(root)
    assert R.get_node(store.conn, tip).deleted is False  # the row is untouched
    assert not R.is_live(store.conn, tip)  # but it is not live
    assert not R.is_live(store.conn, root)


def test_a_descendant_deleted_on_its_own_account_stays_deleted(store):
    """Deleting what is already effectively deleted is legal, and is what makes that work."""
    tip = seeded(store)
    root = R.roots(store.conn)[0].id
    store.delete(root)
    store.delete(tip)  # already effectively deleted; legal, and recorded on its own account
    store.undelete(root)
    assert R.is_live(store.conn, root)
    assert not R.is_live(store.conn, tip)


def test_an_act_begins_at_a_live_node(store):
    tip = seeded(store)
    store.delete(tip)
    for act in (
        lambda: store.create(tip, " is", vocabulary=ToyVocabulary(), source=USER),
        lambda: store.generate(tip, {"length": 1}, adapter=ToyAdapter([]), seed=1),
        lambda: store.realise(tip, MODEL, 0, actor=USER),
    ):
        with pytest.raises(Rejected, match="not live"):
            act()


def test_liveness_constrains_where_an_act_starts_not_what_it_produces(store):
    """A generation whose path merges into a deleted node extends below it, and those
    nodes are recorded and are not live -- the same answer `delete` gives for every
    descendant."""
    tip = seeded(store)
    adapter = ToyAdapter([
        drew((102, [(102, -0.5)])),                     # ` is`   -> a node we then delete
        drew((102, [(102, -0.5)]), (103, [(103, -0.7)])),  # ` is`, ` blue`
    ])
    store.generate(tip, {"length": 1}, adapter=adapter, seed=1)
    dead = R.children(store.conn, tip)[0].id
    store.delete(dead)

    # The act starts at `tip`, which is live. Its path passes through `dead`, which is not.
    _, answer = store.generate(tip, {"length": 2}, adapter=adapter, seed=2)
    assert answer.terminator == "limit"
    below = R.children(store.conn, dead)
    assert len(below) == 1
    assert not R.is_live(store.conn, below[0].id)
    assert violations(store.conn) == []


# ---- generate -----------------------------------------------------------------------


def test_generate_writes_provenance_before_the_nodes(store):
    """No node can ever belong to an act the store has not heard of.

    Checked from inside the model call: at that moment the act is committed, in flight,
    and has produced nothing.
    """
    tip = seeded(store)
    seen = {}

    def peek(ids, params, seed):
        seen["acts"] = store.conn.execute(
            "SELECT id, op, tip, terminator FROM acts WHERE op = 'generate'"
        ).fetchall()
        seen["nodes"] = store.conn.execute("SELECT COUNT(*) FROM nodes").fetchone()[0]
        return drew((102, [(102, -0.5)]))

    store.generate(tip, {"length": 1}, adapter=ToyAdapter([peek]), seed=1)
    assert seen["acts"] == [(2, "generate", None, None)]  # committed, in flight, no tip
    assert seen["nodes"] == 2  # only what `create` wrote


def test_a_backend_that_breaks_mid_call_records_failed(store):
    tip = seeded(store)
    adapter = ToyAdapter([RuntimeError("the backend broke under it")])
    with pytest.raises(RuntimeError):
        store.generate(tip, {"length": 1}, adapter=adapter, seed=1)
    assert store.conn.execute(
        "SELECT tip, terminator FROM acts WHERE op = 'generate'"
    ).fetchone() == (None, "failed")
    assert violations(store.conn) == []


def test_length_must_be_a_positive_integer_and_is_rejected_not_refused(store):
    """`length` is the field the core reads. A bad one is the core's rejection, which
    leaves no trace -- not the adapter's refusal, which is recorded."""
    tip = seeded(store)
    for bad in (0, -1, 1.5, None, True, "3"):
        with pytest.raises(Rejected, match="length"):
            store.generate(tip, {"length": bad}, adapter=ToyAdapter([]), seed=1)
    assert store.conn.execute("SELECT COUNT(*) FROM acts WHERE op = 'generate'").fetchone()[0] == 0


def test_limit_means_it_drew_the_requested_length(store):
    """A backend claiming `limit` on fewer tokens is one the core will not write for."""
    tip = seeded(store)
    adapter = ToyAdapter([drew((102, [(102, -0.5)]))])
    with pytest.raises(StoreError, match="drew 1 of 3"):
        store.generate(tip, {"length": 3}, adapter=adapter, seed=1)


def test_a_terminator_that_wrote_nothing_may_not_report_tokens(store):
    tip = seeded(store)
    reported = drew((102, [(102, -0.5)])).positions
    adapter = ToyAdapter([Generation("refused", reported)])
    with pytest.raises(StoreError, match="wrote nothing"):
        store.generate(tip, {"length": 1}, adapter=adapter, seed=1)


def test_the_core_supplies_a_seed_when_a_caller_does_not(store):
    tip = seeded(store)
    store.generate(tip, {"length": 1}, adapter=ToyAdapter([drew((102, [(102, -0.5)]))]))
    seed = store.conn.execute("SELECT seed FROM acts WHERE op = 'generate'").fetchone()[0]
    assert isinstance(seed, int) and 0 <= seed < 2**31


# ---- rankings -----------------------------------------------------------------------


def test_a_ranking_extends_and_is_never_rewritten(store):
    """A later generation contributes only tokens not already recorded, appended at
    continuing ranks -- so a token that would outrank a stored one is appended *below* it.

    Rank means the k-th alternative recorded here, not the model's k-th choice.
    """
    tip = seeded(store)
    adapter = ToyAdapter([
        drew((103, [(103, -1.0), (104, -2.0)])),                 # two rows at `tip`
        drew((105, [(102, -0.1), (103, -1.0), (105, -3.0)])),    # 102 outranks both
    ])
    store.generate(tip, {"length": 1}, adapter=adapter, seed=1)
    store.generate(tip, {"length": 1}, adapter=adapter, seed=2)

    rows = R.ranking(store.conn, tip)
    assert [(e.rank, e.token_id, e.logprob) for e in rows] == [
        (0, 103, -1.0),   # kept its value and its rank
        (1, 104, -2.0),
        (2, 102, -0.1),   # would outrank rank 0; appended below it regardless
        (3, 105, -3.0),
    ]


def test_a_declined_position_records_no_covering_edge(store):
    """A generation that can give no ranking for a position declines rather than guesses,
    and the absence is the whole record. A later generation supplies the covering edge
    with no further mechanism."""
    tip = seeded(store)
    adapter = ToyAdapter([
        drew((102, None)),                     # declined
        drew((102, [(102, -0.42), (103, -1.0)])),
    ])
    store.generate(tip, {"length": 1}, adapter=adapter, seed=1)
    node = R.children(store.conn, tip)[0].id
    assert R.ranking(store.conn, tip) == []
    assert R.node_logprob(store.conn, node) is None

    store.generate(tip, {"length": 1}, adapter=adapter, seed=2)
    assert R.node_logprob(store.conn, node) == pytest.approx(-0.42)
    assert violations(store.conn) == []


def test_a_ranking_belongs_to_the_node_not_to_the_generation(store):
    """Two sources ranking at one node are two rankings; a rank alone names nothing."""
    tip = seeded(store)
    store.generate(tip, {"length": 1}, adapter=ToyAdapter([drew((102, [(102, -0.5)]))]), seed=1)
    store.generate(
        tip, {"length": 1},
        adapter=ToyAdapter([drew((103, [(103, -0.9)]))], source=OTHER), seed=2,
    )
    rows = R.ranking(store.conn, tip)
    assert len(rows) == 2
    assert len({e.source for e in rows}) == 2
    assert all(e.rank == 0 for e in rows)  # rank is per (node, source)


# ---- realise ------------------------------------------------------------------------


def test_realise_takes_an_edge_and_calls_no_model(store):
    tip = seeded(store)
    store.generate(
        tip, {"length": 1},
        adapter=ToyAdapter([drew((102, [(103, -0.2), (102, -0.5)]))]), seed=1,
    )
    act = store.realise(tip, MODEL, 0, actor=USER)  # rank 0 is 103, which nothing drew
    node = [n for n in R.children(store.conn, tip) if n.token_id == 103][0]
    # The act's source is who acted; the node carries the source of the model that ranked
    # the edge. Both are looked up rather than assumed -- source ids are opaque.
    assert node.source == store.find_source(MODEL)
    assert store.conn.execute(
        "SELECT source FROM acts WHERE id = ?", (act,)
    ).fetchone()[0] == store.find_source(USER)
    assert node.source != store.find_source(USER)
    assert violations(store.conn) == []


def test_realising_a_realised_edge_writes_only_the_act(store):
    """If the node already exists the merge key finds it, and only the act is written."""
    tip = seeded(store)
    store.generate(tip, {"length": 1}, adapter=ToyAdapter([drew((102, [(102, -0.5)]))]), seed=1)
    before = store.conn.execute("SELECT COUNT(*) FROM nodes").fetchone()[0]
    store.realise(tip, MODEL, 0, actor=USER)
    assert store.conn.execute("SELECT COUNT(*) FROM nodes").fetchone()[0] == before


def test_realise_needs_an_edge_that_exists(store):
    tip = seeded(store)
    with pytest.raises(Rejected, match="no source"):
        store.realise(tip, MODEL, 0, actor=USER)


# ---- vocabulary ---------------------------------------------------------------------


def test_vocab_writes_verify(store):
    """An id already present must spell what the vocabulary says now, or the write fails.

    This catches a store opened against the wrong vocabulary at the first id the two
    disagree on.
    """
    tip = seeded(store)

    class Disagreeing(ToyVocabulary):
        def bytes_for(self, token_id):
            return b"different" if token_id == 100 else VOCAB[token_id]

    with pytest.raises(StoreError, match="vocabulary disagrees at id 100"):
        store.generate(
            tip, {"length": 1},
            adapter=_with(Disagreeing(), [drew((100, [(100, -0.5)]))]), seed=1,
        )


def _with(vocabulary, answers):
    adapter = ToyAdapter(answers)
    adapter.bytes_for = vocabulary.bytes_for
    return adapter


# ---- the lock and the sweep ---------------------------------------------------------


def test_an_abandoned_generation_is_recorded_aborted(tmp_path):
    """A writer holds the lock for the whole of an act, so acquiring it means no other
    writer is live -- and every act still in flight is one whose writer is gone.

    The writer is killed for real, mid-call, in a subprocess. Nothing else reaches
    `aborted`.
    """
    path = tmp_path / "t"
    src = _ABANDON_SCRIPT.format(path=str(path), tests=_TESTS_DIR)
    proc = subprocess.run([sys.executable, "-c", src], capture_output=True, text=True, timeout=30)
    assert proc.returncode != 0, proc.stdout + proc.stderr

    with Store.open(path, write=True) as store:  # acquiring is what sweeps
        assert store.conn.execute(
            "SELECT tip, terminator FROM acts WHERE op = 'generate'"
        ).fetchall() == [(None, "aborted")]
        assert violations(store.conn) == []


_TESTS_DIR = str(__import__("pathlib").Path(__file__).parent)

_ABANDON_SCRIPT = """
import os, sys
sys.path.insert(0, {tests!r})
from tokenloom.core import Store
from toy import USER, ToyAdapter, ToyVocabulary

store = Store.initialise({path!r}, vocabulary="toy")
store.create(None, "The sky", vocabulary=ToyVocabulary(), source=USER)
tip = 2

def die(ids, params, seed):
    os._exit(9)  # the writer is gone, mid-call, with the act committed and in flight

store.generate(tip, {{"length": 1}}, adapter=ToyAdapter([die]), seed=1)
"""


def test_a_reader_takes_no_lock_and_will_not_write(tmp_path):
    path = tmp_path / "t"
    with Store.initialise(path, vocabulary="toy") as w:
        w.create(None, "The sky", vocabulary=ToyVocabulary(), source=USER)
    reader = Store.open(path)
    assert R.path_bytes(reader.conn, 2) == b"The sky"
    with pytest.raises(StoreError, match="opened for reading"):
        reader.delete(1)


def test_a_reader_that_does_not_recognise_marker_stops(tmp_path):
    path = tmp_path / "t"
    Store.initialise(path, vocabulary="toy").close()
    (path / "tree.json").write_text('{"marker": "token-loom/nodes-99"}')
    with pytest.raises(StoreError, match="unrecognised marker"):
        Store.open(path)


def test_a_source_of_kind_model_must_be_named():
    """INV-SOURCE-NAMED, refused at the door: two unnamed models would be one source."""
    with pytest.raises(ValueError, match="must be named"):
        Source("model", "")
    assert Source("user", "").name == ""  # the empty name is the unnamed user
