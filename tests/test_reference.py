"""The reference arm the record already holds, which is what a hover reads before it spends.

`docs/SPINE.md` has the reference arm as the model left alone from a position. A greedy
rollout merges onto whatever an earlier one wrote, so the descent that never leaves the top
row *is* what rolling again would produce -- which is the only reason reading it is allowed
to stand in for asking.

**Every refusal here is a refusal somewhere else, restated.** A position two sources ranked,
a tie at the top, a child below the top row: each is a case `docs/SURFACE.md` or the mark
already settles, and the arm follows those answers rather than reaching its own. A test that
only drove the happy path would pass on an implementation that had quietly decided one of
them, and the wrong decision is invisible -- the arm would simply go somewhere, and nothing
about a plausible continuation says it was the model's.
"""

from __future__ import annotations

import pytest

from tokenloom.core import Store
from tokenloom.surface import reads as S
from toy import MODEL, OTHER, USER, ToyAdapter, ToyVocabulary, drew

THE, SKY, IS, BLUE, RED, GREY = 100, 101, 102, 103, 104, 105


@pytest.fixture
def store(tmp_path):
    with Store.initialise(tmp_path / "t", vocabulary="toy") as held:
        held.create(None, "The sky", vocabulary=ToyVocabulary(), actor=USER)
        yield held


def rolled(store, at, *steps, source=MODEL):
    """A generation drawing each token given, each with the ranking given beside it."""
    act, _ = store.generate(
        at, {"length": len(steps)}, adapter=ToyAdapter([drew(*steps)], source), actor=USER
    )
    return act


def text(arm):
    return "".join(cell.text for cell in arm.cells)


# ---- following the top row ------------------------------------------------------------


def test_the_arm_follows_the_top_row_as_far_as_the_record_goes(store):
    """The ordinary case: a greedy run leaves a chain of top-row children, and the arm is
    that chain. `ENDS` says the tree ran out first, which is what makes it extendable."""
    rolled(
        store, 2,
        (IS, [(IS, -0.1), (RED, -2.0)]),
        (BLUE, [(BLUE, -0.2), (GREY, -1.5)]),
    )
    arm = S.reference(store.conn, 2, 40)
    assert text(arm) == " is blue"
    assert arm.why == S.ENDS


def test_the_arm_stops_at_a_child_below_the_top_row(store):
    """The case the whole read turns on. A sampled divergence leaves a child that is *not*
    the model's preference, and an arm that followed it would report the sampler's path as
    the model's -- the one error `docs/SPINE.md` says nothing else in the record corrects."""
    rolled(store, 2, (RED, [(IS, -0.1), (RED, -2.0)]))
    arm = S.reference(store.conn, 2, 40)
    assert arm.nodes == []
    assert text(arm) == ""


def test_the_arm_prefers_the_top_row_over_a_sibling_that_was_also_taken(store):
    """Both rows have children, so the arm is a choice and not a walk. It takes the model's
    and not the one that happens to be first, nor the one with more below it."""
    rolled(store, 2, (RED, [(IS, -0.1), (RED, -2.0)]), (GREY, [(GREY, -0.1)]))
    rolled(store, 2, (IS, [(IS, -0.1), (RED, -2.0)]))
    arm = S.reference(store.conn, 2, 40)
    assert text(arm) == " is"


def test_the_limit_is_in_nodes_and_cuts_the_arm_short(store):
    """`FULL` and not one of the three refusals, which is the whole difference: an arm that
    filled the room it was given is not evidence the tree has no more."""
    rolled(
        store, 2,
        (IS, [(IS, -0.1)]), (BLUE, [(BLUE, -0.1)]), (RED, [(RED, -0.1)]),
    )
    arm = S.reference(store.conn, 2, 2)
    assert [n.token_id for n in arm.nodes] == [IS, BLUE]
    assert arm.why == S.FULL


# ---- what it refuses to answer ---------------------------------------------------------


def test_a_position_nothing_ranked_ends_the_arm_and_is_somewhere_to_spend(store):
    """A `create` records no ranking, so its child is a token with no top row above it. An
    arm that walked an only child would be reporting the reader's text as the model's.

    It reports `ENDS` and not a refusal, which is the part that costs money to get wrong: a
    roll here writes the ranking the position is missing and the arm reads afterwards, so
    this is one of the places a price is honest.
    """
    store.create(2, " is", vocabulary=ToyVocabulary(), actor=USER)
    arm = S.reference(store.conn, 2, 40)
    assert arm.nodes == []
    assert arm.why == S.ENDS


def test_a_position_two_sources_ranked_declines_rather_than_ending(store):
    """`docs/SURFACE.md` has the surface refuse rather than choose where two models ranked,
    because their values were never alternatives to each other. The arm does not get to
    pick a winner by having a stronger opinion than the page.

    **And it is not the same answer as the record running out.** This read will never follow
    this position however much is spent on it, so a caller that read the two as one absence
    would offer to buy what cannot be sold.
    """
    rolled(store, 2, (IS, [(IS, -0.1), (RED, -2.0)]))
    rolled(store, 2, (RED, [(RED, -0.05)]), source=OTHER)
    arm = S.reference(store.conn, 2, 40)
    assert arm.nodes == []
    assert arm.why == S.DECLINES


def test_a_declined_position_ends_the_arm(store):
    """A backend that gave no distribution leaves a node with no edges at its parent, which
    is an absence and not a flat ranking. It reads as the record running out rather than as
    a refusal, because a roll here records the ranking that is missing."""
    rolled(store, 2, (IS, None))
    arm = S.reference(store.conn, 2, 40)
    assert arm.nodes == []
    assert arm.why == S.ENDS


def test_a_tie_at_the_top_takes_the_first_child_in_insertion_order(store):
    """Near-ties do not arrive in a reproducible order, so two rows within the tolerance are
    one row. Which child is then taken has to come from the record's own order rather than
    from whichever the backend happened to list first."""
    rolled(store, 2, (IS, [(IS, -0.5), (RED, -0.5 + S.TIE / 2)]))
    rolled(store, 2, (RED, [(IS, -0.5), (RED, -0.5 + S.TIE / 2)]))
    arm = S.reference(store.conn, 2, 40)
    assert [n.id for n in arm.nodes] == [3]


# ---- liveness --------------------------------------------------------------------------


def test_a_set_aside_arm_is_not_followed_and_the_toggle_reaches_it(store):
    """A reader who pruned an arm is not shown it as the model's preference. `hidden` is how
    they reach it again, and it is the same flag every other read carries."""
    rolled(store, 2, (IS, [(IS, -0.1), (RED, -2.0)]))
    store.delete(3, actor=USER)
    assert S.reference(store.conn, 2, 40).nodes == []
    assert text(S.reference(store.conn, 2, 40, hidden=True)) == " is"


def test_a_closed_arm_says_so_rather_than_reading_as_the_record_running_out(store):
    """**The one that costs real money to conflate.** The record has this continuation and
    the reader put it away, so a roll here merges onto a node still carrying the flag and
    writes nothing at all -- a caller that read this as the tree ending would charge for
    inference and have nothing to show for it. What reaches it is `undelete`.

    With the toggle on there is nothing closed about it: the arm follows straight through,
    so the reason belongs to the read's liveness and not to the node.
    """
    rolled(store, 2, (IS, [(IS, -0.1), (RED, -2.0)]), (BLUE, [(BLUE, -0.2)]))
    store.delete(4, actor=USER)
    arm = S.reference(store.conn, 2, 40)
    assert text(arm) == " is"
    assert arm.why == S.CLOSED
    assert S.reference(store.conn, 2, 40, hidden=True).why == S.ENDS


def test_a_tie_with_one_live_child_carries_on_rather_than_reading_as_closed(store):
    """Closed is every way onward being set aside and not any of them. A tie at the top is
    several rows and one taken child, so putting one away leaves the other to follow -- and
    an arm that stopped there would report a reader's tidying as the model's silence."""
    rolled(store, 2, (IS, [(IS, -0.5), (RED, -0.5 + S.TIE / 2)]))
    rolled(store, 2, (RED, [(IS, -0.5), (RED, -0.5 + S.TIE / 2)]))
    store.delete(3, actor=USER)
    arm = S.reference(store.conn, 2, 40)
    assert [n.id for n in arm.nodes] == [4]
    assert arm.why == S.ENDS


# ---- segments --------------------------------------------------------------------------


def test_a_character_spelled_by_two_tokens_is_one_cell(store):
    """The arm is drawn as text, so it is segmented the way a path is: nothing addresses a
    node inside a character, and two halves of one are one cell and not two."""
    rolled(store, 2, (200, [(200, -0.1)]), (201, [(201, -0.1)]))
    arm = S.reference(store.conn, 2, 40)
    assert len(arm.nodes) == 2
    assert [(cell.text, cell.decodes) for cell in arm.cells] == [("é", True)]
