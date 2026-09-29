"""The digest, and what it must and must not notice.

`docs/CORE.md`'s *What the digest is* states an encoding rather than leaving it to an
implementation, so these are tests of the document as much as of the code. Two of the rules
are there because they were got wrong in prose first and measured before any of this existed:
a table arriving empty and a column arriving null are both changes the format permits without
a `marker` bump, and a digest that could see either would break every stamp taken before it,
silently, at the one moment nothing else reports anything.

Each case mutates a real store and asserts which way the digest moves. Asserting the digest
*value* would be asserting this file, so nothing here names one.
"""

from __future__ import annotations

import sqlite3
import struct

import pytest

from tokenloom.core import Store, digest
from tokenloom.core import reads as R
from toy import MODEL, USER, ToyAdapter, ToyVocabulary, drew


@pytest.fixture
def tree(tmp_path):
    """A store with something in every table the digest covers."""
    with Store.initialise(tmp_path / "d", vocabulary="toy") as store:
        store.create(None, "The sky", vocabulary=ToyVocabulary(), actor=USER)
        tip = R.roots(store.conn)[0].id + 1
        store.generate(
            tip, {"length": 1},
            adapter=ToyAdapter([drew((102, [(102, -0.5), (103, -1.5)], -0.5))]), actor=USER,
        )
        yield store


def moves(store, change) -> bool:
    """Whether `change` moves the digest. The store is left as `change` left it."""
    before = digest.of(store.conn)
    change(store.conn)
    store.conn.commit()
    return digest.of(store.conn) != before


# ---- what it must notice ------------------------------------------------------------


def test_the_same_store_digests_the_same_twice(tree):
    assert digest.of(tree.conn) == digest.of(tree.conn)


def test_a_renamed_source_moves_it(tree):
    """`sources` is reached through an id every node carries, so a tree whose model was
    renamed has identical nodes and is not the same tree. Naming only the tables a reader thinks
    of as the observation -- vocabulary, nodes, edges, acts -- is the easy mistake, and it leaves
    the two reached through ids out."""
    assert moves(tree, lambda c: c.execute("UPDATE sources SET name = 'elsewhere' "
                                           "WHERE kind = 'model'"))


def test_a_rewritten_interned_request_moves_it(tree):
    """`params` is reached the same way, through an id on the act."""
    assert moves(tree, lambda c: c.execute("UPDATE params SET json = '{\"length\":99}'"))


def test_a_logprob_differing_in_its_last_bit_moves_it(tree):
    """A real is hashed as its IEEE-754 bits, so two values a decimal rendering would show
    alike are still two values. This is the one place a formatted digest would quietly call
    two different trees one."""
    (value,) = tree.conn.execute("SELECT logprob FROM edges LIMIT 1").fetchone()
    bits = bytearray(struct.pack(">d", value))
    bits[-1] ^= 1
    nudged = struct.unpack(">d", bytes(bits))[0]
    assert nudged != value
    assert f"{nudged:.6f}" == f"{value:.6f}", "and a rendering would not have seen it"
    assert moves(tree, lambda c: c.execute(
        "UPDATE edges SET logprob = ? WHERE logprob = ?", (nudged, value)))


def test_setting_a_deleted_flag_moves_it(tree):
    """Null and a value are still told apart, which is what the null rule must not cost:
    `deleted` is null or `1`, and one contributes nothing while the other contributes."""
    assert moves(tree, lambda c: c.execute("UPDATE nodes SET deleted = 1 WHERE id = 1"))


def test_emptying_a_table_moves_it(tree):
    assert moves(tree, lambda c: c.execute("DELETE FROM edges"))


# ---- what it must not notice --------------------------------------------------------


def test_a_table_arriving_empty_does_not_move_it(tree):
    """A table arriving is not a `marker` change, so a tree that predates one is conforming
    and must still verify against a stamp taken before it."""
    assert not moves(tree, lambda c: c.execute(
        "CREATE TABLE later (id INTEGER PRIMARY KEY, what TEXT)"))


def test_a_column_arriving_null_does_not_move_it_and_a_value_in_it_does(tree):
    """The same rule one level down, and the case that is coming: recording the conditions an
    act was made under adds columns to `acts`, and every act written before that holds null in
    them."""
    assert not moves(tree, lambda c: c.execute("ALTER TABLE acts ADD COLUMN condition TEXT"))
    assert moves(tree, lambda c: c.execute("UPDATE acts SET condition = 'cold' WHERE id = 1"))


def test_the_physical_order_of_rows_does_not_move_it(tree):
    """Rows are walked in the key's order, so a table rewritten back to front is the same
    table. Nothing stores an order for this to be able to see."""
    def rewrite(conn: sqlite3.Connection) -> None:
        rows = conn.execute("SELECT node, source, token_id, logprob FROM edges "
                            "ORDER BY logprob").fetchall()
        conn.execute("DELETE FROM edges")
        conn.executemany("INSERT INTO edges VALUES (?, ?, ?, ?)", reversed(rows))

    assert not moves(tree, rewrite)


def test_a_stamp_does_not_move_it(tree):
    """A stamp cannot attest itself, which is the one table the digest leaves out -- and is
    why stamping twice in a row is a thing that can be done at all."""
    assert not moves(tree, lambda c: c.execute(
        "INSERT INTO stamps (hash, created) VALUES ('x', '2026-01-01T00:00:00Z')"))


# ---- the framing --------------------------------------------------------------------


def test_null_zero_and_empty_text_frame_apart():
    """Three values a looser encoding would run together, and `deleted` and `parent` are
    where that would show."""
    assert len({digest.frame(None), digest.frame(0), digest.frame("")}) == 3


def test_a_blob_and_the_text_that_spells_it_frame_apart():
    """`vocab.bytes` is a blob and `sources.name` is text, so the tag is what keeps a row of
    one from being a row of the other."""
    assert digest.frame(b"abc") != digest.frame("abc")


def test_text_is_length_framed_so_it_cannot_run_into_what_follows():
    """Two adjacent values must not write what one longer value writes."""
    assert digest.frame("ab") + digest.frame("c") != digest.frame("abc") + digest.frame("")


def test_a_bool_is_refused_rather_than_stored_as_an_integer():
    """SQLite has no bool, so one reaching here is a caller's bug and not a value to hash --
    and `True` would otherwise frame exactly as `1`."""
    with pytest.raises(TypeError, match="bool"):
        digest.frame(True)


# ---- stamping -----------------------------------------------------------------------


def test_stamping_records_the_digest_and_leaves_the_tree_as_it_was(tree):
    """The invariant, not the value: whatever the digest is, stamping must not change it.
    A stamp is an observation of the tree and not a change to it."""
    before = digest.of(tree.conn)
    stamp, found = tree.stamp()
    assert found == before
    assert digest.of(tree.conn) == before, "stamping moved what it was measuring"
    assert [(s.id, s.hash) for s in R.stamps(tree.conn)] == [(stamp, before)]


def test_two_stamps_may_carry_one_hash(tree):
    """Stamping a tree that has not moved records that it had not moved, which is why
    `hash` is not unique."""
    _, first = tree.stamp()
    _, second = tree.stamp()
    assert first == second
    assert len(R.stamps(tree.conn)) == 2


def test_a_stamp_names_no_actor(tree):
    """A digest is recomputable by anyone and influenced by nobody, so a name beside it
    would be a fact about the record's keeping rather than about the record."""
    tree.stamp()
    columns = {r[1] for r in tree.conn.execute("PRAGMA table_info(stamps)")}
    assert columns == {"id", "hash", "created"}


def test_an_act_after_a_stamp_moves_the_tree_away_from_it(tree):
    """Stamping does not fix the tree. The stamp then describes a state the tree has left,
    which is what makes it worth dating."""
    _, taken = tree.stamp()
    tip = R.roots(tree.conn)[0].id + 1
    tree.realise(tip, MODEL, 103, actor=USER)
    assert digest.of(tree.conn) != taken
    assert R.stamps(tree.conn)[-1].hash == taken, "and the stamp still says what it said"


def test_a_tree_written_before_the_table_existed_gains_it_on_opening_to_write(tmp_path):
    """A writer creates what its `marker` defines and the tree lacks. Reached on purpose,
    because a store this implementation made always has the table already."""
    with Store.initialise(tmp_path / "old", vocabulary="toy") as store:
        store.create(None, "The sky", vocabulary=ToyVocabulary(), actor=USER)
        before = digest.of(store.conn)
    conn = sqlite3.connect(tmp_path / "old" / "bulk.sqlite")
    conn.execute("DROP TABLE stamps")
    conn.commit()
    conn.close()

    with Store.open(tmp_path / "old") as reader:
        assert R.stamps(reader.conn) == [], "and a reader does not mind that it is missing"
        assert digest.of(reader.conn) == before, "nor does the digest"

    with Store.open(tmp_path / "old", write=True) as store:
        assert digest.of(store.conn) == before, "the table arriving changed nothing"
        store.stamp()
        assert len(R.stamps(store.conn)) == 1
