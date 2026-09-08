"""The paths the appendix does not run.

Rejection, liveness, the abandoned-act sweep, declination, a backend that dies mid-call.
Each of these is a statement `docs/CORE.md` makes that the worked example never exercises,
and CLAUDE.md's own note applies: one fault fell out only of running a path nothing had run.
"""

from __future__ import annotations

import json
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
    store.create(None, "The sky", vocabulary=ToyVocabulary(), actor=USER)
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
        store.create(None, "The sky", vocabulary=Lossy(), actor=USER)
    assert R.roots(store.conn) == []  # a rejection leaves no trace


def test_create_rejects_bytes_that_are_not_utf8(store):
    with pytest.raises(Rejected, match="valid UTF-8"):
        store.create(None, b"\xc3", vocabulary=ToyVocabulary(), actor=USER)


def test_create_that_would_add_no_tokens_is_rejected(store):
    with pytest.raises(Rejected):
        store.create(None, "", vocabulary=ToyVocabulary(), actor=USER)
    assert store.conn.execute("SELECT COUNT(*) FROM acts").fetchone()[0] == 0


def test_roots_do_not_merge(store):
    """A root has no parent, so the merge key does not reach it: two roots with the same
    token and source stay distinct, and each begins its own trie."""
    a = store.create(None, "The sky", vocabulary=ToyVocabulary(), actor=USER)
    b = store.create(None, "The sky", vocabulary=ToyVocabulary(), actor=USER)
    assert a != b
    roots = R.roots(store.conn)
    assert len(roots) == 2
    assert roots[0].token_id == roots[1].token_id
    assert roots[0].source == roots[1].source


def test_authored_text_never_collapses_into_a_model_draw_that_matches(store):
    """Source is part of the merge key, so the split is visible in the tree."""
    tip = seeded(store)
    adapter = ToyAdapter([drew((102, [(102, -0.5)]))])  # ` is`
    store.generate(tip, {"length": 1}, adapter=adapter, actor=USER)
    store.create(tip, " is", vocabulary=ToyVocabulary(), actor=USER)
    kids = R.children(store.conn, tip)
    assert [k.token_id for k in kids] == [102, 102]
    assert kids[0].source != kids[1].source


def test_authored_text_may_be_attributed_to_a_source_that_did_not_act(store):
    """Text a model produced elsewhere is recorded as that model's, with the act naming
    whoever entered it. The two questions an act and a node answer come apart here."""
    alice = Source("user", "alice")
    act = store.create(None, "The sky", vocabulary=ToyVocabulary(), actor=alice, source=MODEL)

    assert store.conn.execute(
        "SELECT actor FROM acts WHERE id = ?", (act,)
    ).fetchone()[0] == store.find_source(alice)
    assert {n.source for n in R.act_tokens(store.conn, act)} == {store.find_source(MODEL)}
    assert violations(store.conn) == []


def test_the_source_a_create_names_defaults_to_the_actor(store):
    alice = Source("user", "alice")
    act = store.create(None, "The sky", vocabulary=ToyVocabulary(), actor=alice)
    assert {n.source for n in R.act_tokens(store.conn, act)} == {store.find_source(alice)}


def test_an_actor_is_a_user_and_a_model_acting_is_rejected(store):
    """Acting is not producing. A caller that drives the tree by itself is a named user,
    which keeps `sources` honest: a model in there is something that produced tokens.

    Every act below names a node that does not exist, and each is refused for its actor
    rather than its node -- the actor is a precondition of the act and is checked first.
    """
    for act in (
        lambda: store.create(None, "The sky", vocabulary=ToyVocabulary(), actor=MODEL),
        lambda: store.generate(None, {"length": 1}, adapter=ToyAdapter([]), actor=MODEL),
        lambda: store.realise(1, MODEL, 0, actor=MODEL),
        lambda: store.delete(1, actor=MODEL),
        lambda: store.undelete(1, actor=MODEL),
    ):
        with pytest.raises(Rejected, match="actor is a user"):
            act()
    assert store.conn.execute("SELECT COUNT(*) FROM acts").fetchone()[0] == 0


# ---- liveness -----------------------------------------------------------------------


def test_a_delete_names_one_node_and_descendants_are_untouched(store):
    """Whether a node is live is derived by walking the ancestry, so a delete touches one
    node however many it takes out of the live tree."""
    tip = seeded(store)
    root = R.roots(store.conn)[0].id
    store.delete(root, actor=USER)
    assert R.get_node(store.conn, tip).deleted is False  # the row is untouched
    assert not R.is_live(store.conn, tip)  # but it is not live
    assert not R.is_live(store.conn, root)


def test_a_descendant_deleted_on_its_own_account_stays_deleted(store):
    """Deleting what is already effectively deleted is legal, and is what makes that work."""
    tip = seeded(store)
    root = R.roots(store.conn)[0].id
    store.delete(root, actor=USER)
    store.delete(tip, actor=USER)  # already effectively deleted; legal, and on its own account
    store.undelete(root, actor=USER)
    assert R.is_live(store.conn, root)
    assert not R.is_live(store.conn, tip)


def test_deleting_and_undeleting_are_recorded_in_acts(store):
    """`acts` is where a reader goes to find what was done, and these are the writes with
    the largest effect on what a reader sees."""
    tip = seeded(store)
    before = store.conn.execute("SELECT COUNT(*) FROM acts").fetchone()[0]
    first = store.delete(tip, actor=USER)
    second = store.undelete(tip, actor=USER)

    rows = store.conn.execute(
        "SELECT id, op, origin, tip FROM acts WHERE id > ? ORDER BY id", (before,)
    ).fetchall()
    assert rows == [(first, "delete", tip, None), (second, "undelete", tip, None)]


def test_the_flag_is_the_state_and_the_act_is_the_record_of_it_changing(store):
    """Liveness comes from `deleted` and never from `acts`, so a delete that changed no
    state is legal and records an act that a reader of liveness never consults."""
    tip = seeded(store)
    store.delete(tip, actor=USER)
    again = store.delete(tip, actor=USER)  # changed nothing, and is recorded anyway
    recorded = store.conn.execute("SELECT op FROM acts WHERE id = ?", (again,)).fetchone()
    assert recorded == ("delete",)
    assert not R.is_live(store.conn, tip)
    store.undelete(tip, actor=USER)
    assert R.is_live(store.conn, tip)


def test_changing_liveness_begins_anywhere(store):
    """Liveness is what these change, so requiring a live node would put `undelete` out of
    reach. Here the node is not live when it is undeleted and is not live after, because
    the flag it clears was never the one keeping it out."""
    tip = seeded(store)
    root = R.roots(store.conn)[0].id
    store.delete(tip, actor=USER)
    store.delete(root, actor=USER)
    store.undelete(tip, actor=USER)
    assert R.get_node(store.conn, tip).deleted is False  # the act did what it says
    assert not R.is_live(store.conn, tip)  # and the ancestor still governs


def test_changing_liveness_still_names_a_node_that_exists(store):
    seeded(store)
    for act in (lambda: store.delete(9999, actor=USER), lambda: store.undelete(9999, actor=USER)):
        with pytest.raises(Rejected, match="no node 9999"):
            act()


def test_the_acts_that_produce_nodes_begin_at_a_live_node(store):
    tip = seeded(store)
    store.delete(tip, actor=USER)
    for act in (
        lambda: store.create(tip, " is", vocabulary=ToyVocabulary(), actor=USER),
        lambda: store.generate(tip, {"length": 1}, adapter=ToyAdapter([]), actor=USER),
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
    store.generate(tip, {"length": 1}, adapter=adapter, actor=USER)
    dead = R.children(store.conn, tip)[0].id
    store.delete(dead, actor=USER)

    # The act starts at `tip`, which is live. Its path passes through `dead`, which is not.
    _, answer = store.generate(tip, {"length": 2}, adapter=adapter, actor=USER)
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

    def peek(ids, params):
        seen["acts"] = store.conn.execute(
            "SELECT id, op, tip, terminator FROM acts WHERE op = 'generate'"
        ).fetchall()
        seen["nodes"] = store.conn.execute("SELECT COUNT(*) FROM nodes").fetchone()[0]
        return drew((102, [(102, -0.5)]))

    store.generate(tip, {"length": 1}, adapter=ToyAdapter([peek]), actor=USER)
    assert seen["acts"] == [(2, "generate", None, None)]  # committed, in flight, no tip
    assert seen["nodes"] == 2  # only what `create` wrote


def test_a_generate_that_begins_a_root_cannot_record_its_first_ranking(store):
    """A ranking belongs to the node the position was computed at, and position 0 of a
    root-beginning generate has no such node.

    Not a fault in the implementation and not one a lock could fix -- it follows from a
    node's logprob being the ranked edge at its *parent*, and a root has none. The path is
    here because nothing else runs it: `create` is how a root gets made in practice, and
    the one backend that exists refuses an empty prompt.
    """
    adapter = ToyAdapter([drew(
        (100, [(100, -0.1), (101, -0.5)]),   # position 0: computed at nothing
        (101, [(101, -0.2), (102, -0.9)]),   # position 1: computed at the root
    )])
    store.generate(None, {"length": 2}, adapter=adapter, actor=USER)

    root = R.roots(store.conn)[0]
    assert root.token_id == 100
    child = R.children(store.conn, root.id)[0]

    # Position 0's ranking is not recorded anywhere -- not at the root, not orphaned.
    assert store.conn.execute("SELECT COUNT(*) FROM edges WHERE node = ?", (root.id,)) \
        .fetchone()[0] == 2  # position 1's two rows, and only those
    assert {e.token_id for e in R.ranking(store.conn, root.id)} == {101, 102}

    assert R.node_logprob(store.conn, root.id) is None  # no parent to carry the edge
    assert R.node_logprob(store.conn, child.id) == -0.2  # the position that had a node


def test_a_backend_that_breaks_mid_call_records_failed(store):
    tip = seeded(store)
    adapter = ToyAdapter([RuntimeError("the backend broke under it")])
    with pytest.raises(RuntimeError):
        store.generate(tip, {"length": 1}, adapter=adapter, actor=USER)
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
            store.generate(tip, {"length": bad}, adapter=ToyAdapter([]), actor=USER)
    assert store.conn.execute("SELECT COUNT(*) FROM acts WHERE op = 'generate'").fetchone()[0] == 0


def test_limit_means_it_drew_the_requested_length(store):
    """A backend claiming `limit` on fewer tokens is one the core will not write for."""
    tip = seeded(store)
    adapter = ToyAdapter([drew((102, [(102, -0.5)]))])
    with pytest.raises(StoreError, match="drew 1 of 3"):
        store.generate(tip, {"length": 3}, adapter=adapter, actor=USER)


def test_a_terminator_that_wrote_nothing_may_not_report_tokens(store):
    tip = seeded(store)
    reported = drew((102, [(102, -0.5)])).positions
    adapter = ToyAdapter([Generation("refused", reported)])
    with pytest.raises(StoreError, match="wrote nothing"):
        store.generate(tip, {"length": 1}, adapter=adapter, actor=USER)


def test_an_answer_the_store_will_not_write_records_failed_and_is_not_left_in_flight(store):
    """The writer is right here and knows, so it says so rather than leaving the act for
    the next writer to sweep as `aborted` -- which would assert the writer was gone.

    A vocabulary that disagrees at an id the store already holds is the way this happens
    for real: it is what a wrong model file looks like from inside a generation.
    """
    tip = seeded(store)

    class Wrong(ToyVocabulary):
        def bytes_for(self, token_id):
            return b"Xhe" if token_id == 100 else VOCAB[token_id]

    adapter = ToyAdapter([drew((100, [(100, -0.5)]))])
    adapter.bytes_for = Wrong().bytes_for
    with pytest.raises(StoreError, match="vocabulary disagrees at id 100"):
        store.generate(tip, {"length": 1}, adapter=adapter, actor=USER)

    assert store.conn.execute(
        "SELECT tip, terminator FROM acts WHERE op = 'generate'"
    ).fetchall() == [(None, "failed")]
    # Nothing of the rejected answer landed, and the sweep has nothing to find.
    assert store.conn.execute("SELECT COUNT(*) FROM nodes").fetchone()[0] == 2
    assert violations(store.conn) == []
    store.close()  # the next writer needs the claim, so this one has to let go of it
    with Store.open(store.path, write=True) as later:
        assert later.conn.execute(
            "SELECT terminator FROM acts WHERE op = 'generate'"
        ).fetchone() == ("failed",)


def test_an_interrupted_writer_is_left_for_the_sweep_and_not_called_failed(store):
    """`docs/ADAPTER.md`: an adapter that cannot be interrupted never produces
    `cancelled`, and stopping one of its generations means killing the writer, which the
    next writer records as `aborted`.

    So a `KeyboardInterrupt` must pass through untouched. Calling it `failed` would claim
    the backend broke, and would also put the one terminator this backend cannot reach
    within reach by the wrong route.
    """
    tip = seeded(store)
    adapter = ToyAdapter([KeyboardInterrupt()])
    with pytest.raises(KeyboardInterrupt):
        store.generate(tip, {"length": 1}, adapter=adapter, actor=USER)

    assert store.conn.execute(
        "SELECT terminator FROM acts WHERE op = 'generate'"
    ).fetchone() == (None,)  # still in flight
    store.close()
    with Store.open(store.path, write=True) as later:  # claiming is what sweeps
        assert later.conn.execute(
            "SELECT tip, terminator FROM acts WHERE op = 'generate'"
        ).fetchone() == (None, "aborted")


def test_every_key_but_length_reaches_the_adapter_uninterpreted_and_is_stored(store):
    """`length` is the field the core reads; the rest is passed through and interned.

    The core neither supplies a parameter nor reads one it was not promised, so a key it
    has never heard of makes the round trip unchanged -- which is what lets a backend
    require whatever describes its own draw.
    """
    tip = seeded(store)
    asked = {"length": 1, "seed": 42, "temperature": 0.7, "a_key_the_core_never_heard_of": None}
    adapter = ToyAdapter([drew((102, [(102, -0.5)]))])
    act, _ = store.generate(tip, asked, adapter=adapter, actor=USER)

    assert adapter.params == [asked]  # reached the backend entire
    stored = store.conn.execute(
        "SELECT p.json FROM acts a JOIN params p ON p.id = a.params WHERE a.id = ?", (act,)
    ).fetchone()[0]
    assert json.loads(stored) == asked  # and was recorded entire


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
    store.generate(tip, {"length": 1}, adapter=adapter, actor=USER)
    store.generate(tip, {"length": 1}, adapter=adapter, actor=USER)

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
    store.generate(tip, {"length": 1}, adapter=adapter, actor=USER)
    node = R.children(store.conn, tip)[0].id
    assert R.ranking(store.conn, tip) == []
    assert R.node_logprob(store.conn, node) is None

    store.generate(tip, {"length": 1}, adapter=adapter, actor=USER)
    assert R.node_logprob(store.conn, node) == pytest.approx(-0.42)
    assert violations(store.conn) == []


def test_a_ranking_belongs_to_the_node_not_to_the_generation(store):
    """Two sources ranking at one node are two rankings; a rank alone names nothing."""
    tip = seeded(store)
    store.generate(
        tip, {"length": 1}, adapter=ToyAdapter([drew((102, [(102, -0.5)]))]), actor=USER
    )
    store.generate(
        tip, {"length": 1},
        adapter=ToyAdapter([drew((103, [(103, -0.9)]))], source=OTHER), actor=USER,
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
        adapter=ToyAdapter([drew((102, [(103, -0.2), (102, -0.5)]))]), actor=USER,
    )
    act = store.realise(tip, MODEL, 0, actor=USER)  # rank 0 is 103, which nothing drew
    node = [n for n in R.children(store.conn, tip) if n.token_id == 103][0]
    # The act names the actor; the node carries the model that ranked the edge, and the
    # act stores no model of its own. All looked up rather than assumed -- ids are opaque.
    assert node.source == store.find_source(MODEL)
    assert store.conn.execute(
        "SELECT actor, model FROM acts WHERE id = ?", (act,)
    ).fetchone() == (store.find_source(USER), None)
    assert node.source != store.find_source(USER)
    assert violations(store.conn) == []


def test_realising_a_realised_edge_writes_only_the_act(store):
    """If the node already exists the merge key finds it, and only the act is written."""
    tip = seeded(store)
    store.generate(
        tip, {"length": 1}, adapter=ToyAdapter([drew((102, [(102, -0.5)]))]), actor=USER
    )
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
            adapter=_with(Disagreeing(), [drew((100, [(100, -0.5)]))]), actor=USER,
        )


def _with(vocabulary, answers):
    adapter = ToyAdapter(answers)
    adapter.bytes_for = vocabulary.bytes_for
    return adapter


# ---- the claim and the sweep --------------------------------------------------------


def test_a_second_writer_is_refused_rather_than_left_waiting(store):
    """The claim is what a client holds to say *this tree is mine until I am done*, and
    refusing without blocking is what lets the one turned away report it.

    A writer that waited would report nothing, which is the whole reason the claim is
    taken this way rather than blocking.
    """
    with pytest.raises(StoreError, match="another writer holds"):
        Store.open(store.path, write=True)

    reader = Store.open(store.path)  # a reader is not a writer and is never refused
    assert R.roots(reader.conn) == R.roots(store.conn)

    store.close()
    with Store.open(store.path, write=True):  # and the claim is released by closing
        pass


def test_an_abandoned_generation_is_recorded_aborted(tmp_path):
    """One claim is one writer, so a generation still in flight when a claim is taken is
    one whose writer is gone.

    The writer is killed for real, mid-call, in a subprocess. Nothing else reaches
    `aborted`. That the open below succeeds at all is the second thing this witnesses: a
    claim dies with the process holding it, so an abandoned one never has to be broken.
    """
    path = tmp_path / "t"
    src = _ABANDON_SCRIPT.format(path=str(path), tests=_TESTS_DIR)
    proc = subprocess.run([sys.executable, "-c", src], capture_output=True, text=True, timeout=30)
    assert proc.returncode != 0, proc.stdout + proc.stderr

    with Store.open(path, write=True) as store:  # claiming is what sweeps
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
store.create(None, "The sky", vocabulary=ToyVocabulary(), actor=USER)
tip = 2

def die(ids, params):
    os._exit(9)  # the writer is gone, mid-call, with the act committed and in flight

store.generate(tip, {{"length": 1}}, adapter=ToyAdapter([die]), actor=USER)
"""


def test_a_reader_takes_no_lock_and_will_not_write(tmp_path):
    path = tmp_path / "t"
    with Store.initialise(path, vocabulary="toy") as w:
        w.create(None, "The sky", vocabulary=ToyVocabulary(), actor=USER)
    reader = Store.open(path)
    assert R.path_bytes(reader.conn, 2) == b"The sky"
    with pytest.raises(StoreError, match="opened for reading"):
        reader.delete(1, actor=USER)


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
