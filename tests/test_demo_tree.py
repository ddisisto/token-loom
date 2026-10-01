"""The one tree that ships with this, held to what `README.md` promises about it.

`data/demo` is tracked and `README.md`'s first instruction is to serve it, which makes it the
only part of the record that is a promise to someone who has not run anything yet. Everything
else in this suite builds the tree it tests, so a tree built by hand against a running model
and committed is the one thing nothing here would notice going wrong.

**The stamp is checked against itself and never against a constant.** The tree is a reference
object replaced by hand when the model or the format changes, so asserting a particular hash
would fail on every deliberate update and teach whoever hits it to edit the number. Asserting
that it still hashes to its *own* most recent stamp survives replacement -- a new tree brings a
new stamp -- and is exactly the drift these tests exist to catch: a migration that rewrote rows,
a checkpoint that landed half a write, a file that travelled badly.

These skip rather than fail where the tree is absent, because a working copy may legitimately
not have it -- `data/` is otherwise scratch and a sparse checkout is not a broken one.
"""

from __future__ import annotations

import pathlib

import pytest

from tokenloom.core import Store, StoreError, check, digest
from tokenloom.core import reads as R
from tokenloom.surface import reads as S

DEMO = pathlib.Path(__file__).resolve().parent.parent / "data" / "demo"


@pytest.fixture
def demo():
    if not (DEMO / "bulk.sqlite").exists():
        pytest.skip(f"no tree at {DEMO}")
    # Read-only, and no claim: this is the posture `README.md` describes, and taking the
    # write lock here would fail against a tree the operator happens to have open.
    with Store.open(DEMO, verify=False) as store:
        yield store.reader()


def test_the_demo_tree_opens_under_a_marker_this_reader_knows(demo):
    """`Store.open` stops on a marker it does not recognise, so reaching the fixture at all
    is the assertion. What this adds is the direction of the failure: a tree left behind by a
    bump is the case, and it reports as a skip nowhere and a failure here."""
    assert demo.execute("SELECT COUNT(*) FROM nodes").fetchone()[0] > 0


def test_the_demo_tree_breaks_no_invariant(demo):
    """Every invariant `docs/CORE.md` names, against a tree grown by hand through a real
    model rather than by a fixture. The suite's other trees are built by the code under test
    and agree with it by construction; this one was built by a person over sessions."""
    assert check.violations(demo) == []


def test_the_demo_tree_still_hashes_to_its_own_last_stamp(demo):
    """What a stamp is for, read back. `docs/CORE.md` specifies the digest and leaves the
    occasion open; the occasion here is the commit, and this is the check that the committed
    bytes are the ones that were stamped."""
    stamped = demo.execute(
        "SELECT hash, created FROM stamps ORDER BY id DESC LIMIT 1"
    ).fetchone()
    assert stamped is not None, "a tracked tree is quoted from, so it is stamped"
    assert digest.of(demo) == stamped[0], (
        f"the tree has moved since it was stamped at {stamped[1]}; "
        "re-stamp it if the change was wanted"
    )


def test_the_demo_tree_has_a_path_the_surface_can_draw(demo):
    """`README.md` says serving it shows the picture, and a tree of live nodes with no live
    root shows an empty page. This is the read the page makes on load -- the first live root,
    under the default rule -- so it fails for the same reason the page would."""
    roots = [n for n in R.roots(demo) if not n.deleted]
    assert roots, "the page opens on the first live root and there must be one"
    cells = S.path(demo, roots[0].id, S.RULES["longest"], False)
    assert cells, "the first live root has a path"
    assert "".join(cell.text for cell in cells).strip(), "and the path decodes to text"


def test_a_tree_from_another_marker_is_refused_rather_than_read(tmp_path):
    """The other direction, which no tree in the repository can show: what `Store.open` does
    when the marker is one it does not know. It is here because the test above rests on it --
    opening the demo tree is only an assertion about its marker if a wrong one would stop."""
    (tmp_path / "tree.json").write_text('{"marker": "token-loom/99", "vocabulary": "toy"}')
    with pytest.raises(StoreError, match="unrecognised marker"):
        Store.open(tmp_path, verify=False)
