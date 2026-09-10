"""The llama.cpp adapter's repairs and its recording bounds, without a server.

The repairs are not guessable from the API surface and each produces a record that is
quietly wrong rather than an error; their values were taken off the running server rather
than constructed, so what is being tested is the repair and not a model of it. The bounds
are arithmetic over what comes back, which is the kind of derived value nothing disagrees
with -- so they are reached here on purpose.
"""

from __future__ import annotations

import math

import pytest

from tokenloom.adapters.llamacpp.adapter import (
    bound,
    ends_mid_character,
    reaches,
    terminator_for,
    walk,
)
from tokenloom.core import Position, Ranked

#: Real bytes off `tokenizer.ggml.tokens`, for the ids the measured response below carries.
SPELL: dict[int, bytes] = {
    11162: b" \xf0\x9f",
    236: b"\x8e",
    107: b"\xaf",
    198: b"\n",
    2: b"#",
    16: b"1",
    13: b".",
    248: b"\x9a",
    222: b"\x80",
    3555: b" What",
    374: b" is",
    151643: b"<|endoftext|>",
}


class Spelling:
    def spell(self, ids):
        return b"".join(SPELL[i] for i in ids)

    def bytes_for(self, token_id):
        return SPELL[token_id]


def group(token_id: int, data: bytes, ranked=((1, -1.0),)) -> dict:
    return {
        "id": token_id,
        "bytes": list(data),
        "top_logprobs": [{"id": i, "logprob": lp} for i, lp in ranked],
    }


# ---- the regrouping repair -----------------------------------------------------------


def test_walk_reunites_a_measured_response_with_merged_groups():
    """Twelve tokens reported as eight entries.

    Taken verbatim off `/completion` on an emoji-heavy prompt. Two characters are each
    spelled by three tokens, and each yields *one* entry carrying the group's bytes and
    the **last** fragment's id -- so ` 🎯` is [11162, 236, 107] reported as id 107.
    """
    tokens = [11162, 236, 107, 198, 2, 16, 13, 11162, 248, 222, 3555, 374]
    groups = [
        group(107, b" \xf0\x9f\x8e\xaf"),
        group(198, b"\n"),
        group(2, b"#"),
        group(16, b"1"),
        group(13, b"."),
        group(222, b" \xf0\x9f\x9a\x80"),
        group(3555, b" What"),
        group(374, b" is"),
    ]
    positions = walk(tokens, groups, Spelling())

    # Every token the model emitted is a position, in order -- not one per group.
    assert [p.token_id for p in positions] == tokens
    # The interior fragments of each group are declinations: no distribution was reported
    # for them, and the core records that as an absent ranked edge rather than an estimate.
    assert [i for i, p in enumerate(positions) if p.ranking is None] == [0, 1, 7, 8]
    # The ranking lands on the token the group names, which is its last.
    assert positions[2].ranking is not None and positions[2].token_id == 107
    assert positions[9].ranking is not None and positions[9].token_id == 222


def test_walk_is_the_identity_when_nothing_merged():
    tokens = [3555, 374, 198]
    groups = [group(3555, b" What"), group(374, b" is"), group(198, b"\n")]
    positions = walk(tokens, groups, Spelling())
    assert [p.token_id for p in positions] == tokens
    assert all(p.ranking is not None for p in positions)


def test_a_control_token_reports_empty_bytes_and_is_matched_on_its_id():
    """`completion_probabilities` gives `{"id": 151643, "token": "", "bytes": []}` for
    `<|endoftext|>` whether it was sampled or merely ranked, while the vocabulary spells
    it in full. Matching on bytes would consume the whole rest of the sequence."""
    positions = walk([151643], [group(151643, b"")], Spelling())
    assert [p.token_id for p in positions] == [151643]
    assert positions[0].ranking is not None


def test_walk_refuses_to_guess_when_the_two_disagree():
    """A group whose bytes never assemble is a disagreement between the sequence and the
    accounting, and passing it through is exactly the quiet wrongness this exists to stop."""
    with pytest.raises(AssertionError, match="ran out of tokens"):
        walk([3555], [group(374, b" is")], Spelling())


def test_tokens_after_the_last_group_are_declinations():
    positions = walk([3555, 374], [group(3555, b" What")], Spelling())
    assert [(p.token_id, p.ranking is None) for p in positions] == [(3555, False), (374, True)]


# ---- the path predicate --------------------------------------------------------------


@pytest.mark.parametrize(
    ("data", "refused", "why"),
    [
        (b"The sky", False, "ends on a boundary"),
        (b"The\xf0\x9f\x9c\x81", False, "a complete multi-token character"),
        (b"The\xf0\x9f", True, "ends mid-character: one of four"),
        (b"The\xf0\x9f\x9c", True, "ends mid-character: three of four"),
        (b"The\xc3", True, "ends mid-character: one of two"),
        (b"The\xc3\xa9", False, "a complete two-byte character"),
        (b"The\x9c sky", False, "a completed invalid sequence, valid bytes after"),
        (b"The\xf0\x9f sky", False, "an incomplete character, valid text after"),
        (b"The\x9c", False, "a stray continuation byte last -- accepted, and measured"),
        (b"", False, "nothing is pending"),
    ],
)
def test_ends_mid_character(data, refused, why):
    """Every case here was put to the server. The predicate asks about the **tail alone**:
    a path that does not decode end to end is not thereby unreachable, which is a narrower
    answer than either candidate `docs/ADAPTER.md` set out."""
    assert ends_mid_character(data) is refused, why


# ---- the terminator ------------------------------------------------------------------


def test_stop_type_maps_to_a_terminator():
    assert terminator_for("eos") == "eos"
    assert terminator_for("limit") == "limit"


@pytest.mark.parametrize("stop_type", ["word", "none"])
def test_an_unexpected_stop_type_is_a_fault_and_not_a_terminator(stop_type):
    """This adapter does not expose `stop`, so `word` cannot arise honestly -- and there
    is no `stop` terminator to record, because a stop string that does not land on a token
    boundary loses bytes the model emitted and the loss is undecidable from the response."""
    with pytest.raises(AssertionError):
        terminator_for(stop_type)


# ---- the recording bounds ------------------------------------------------------------

#: Halving probabilities, so a prefix's mass is exact in binary and the assertions below
#: can be arithmetic rather than eyeballed. They sum to 0.96875, never to one -- which is
#: what a real ranking does too, by the mass of the vocabulary it does not report.
PROBS = (0.5, 0.25, 0.125, 0.0625, 0.03125)
RANKING = tuple(Ranked(100 + i, math.log(p)) for i, p in enumerate(PROBS))


@pytest.mark.parametrize("mass", [0.1, 0.49, 0.6, 0.9, 0.96])
def test_reaches_is_the_shortest_prefix_that_gets_there(mass):
    """Stated as the definition rather than as a count: the prefix reaches the mass and
    dropping its last row does not."""
    k = reaches(RANKING, mass)
    assert sum(PROBS[:k]) >= mass
    assert k == 1 or sum(PROBS[: k - 1]) < mass


def test_reaches_is_the_whole_ranking_when_the_mass_is_never_there():
    assert reaches(RANKING, 1.0) == len(RANKING)


def test_bound_keeps_a_prefix_and_never_reorders_or_rescales():
    [kept] = bound([Position(RANKING[0].token_id, RANKING)], 0.9)
    assert kept.ranking == RANKING[: len(kept.ranking)]
    assert len(kept.ranking) == reaches(RANKING, 0.9)


def test_bound_at_mass_one_keeps_every_row():
    [kept] = bound([Position(RANKING[0].token_id, RANKING)], 1.0)
    assert kept.ranking == RANKING


def test_bound_floors_at_two_rows():
    """One row holds the mass here, and one row offers nothing to branch into."""
    assert reaches(RANKING, 0.01) == 1
    [kept] = bound([Position(RANKING[0].token_id, RANKING)], 0.01)
    assert len(kept.ranking) == 2


def test_bound_extends_to_the_token_drawn():
    """A sampler reaching past the mass bound would otherwise leave the node with no
    covering ranked edge, and so no derivable logprob."""
    assert reaches(RANKING, 0.01) == 1
    drawn = RANKING[3]
    [kept] = bound([Position(drawn.token_id, RANKING)], 0.01)
    assert kept.ranking[-1] == drawn
    assert drawn.token_id in [row.token_id for row in kept.ranking]


def test_bound_does_not_invent_a_row_for_a_token_that_was_never_ranked():
    """The extension finds the drawn token or does nothing. It never appends one."""
    [kept] = bound([Position(9999, RANKING)], 0.01)
    assert len(kept.ranking) == 2
    assert 9999 not in [row.token_id for row in kept.ranking]


def test_bound_passes_a_declination_through():
    """`None` is a position the backend could give no distribution for, and it is not an
    empty ranking. Nothing here fills it."""
    declined = Position(RANKING[0].token_id, None)
    assert bound([declined], 0.9) == [declined]
