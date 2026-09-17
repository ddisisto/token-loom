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
    MISSING,
    LlamaCppAdapter,
    Refused,
    bound,
    ends_mid_character,
    reaches,
    resolved_as,
    terminator_for,
    walk,
)
from tokenloom.adapters.llamacpp.client import Props
from tokenloom.core import Position, Ranked, Source

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

    def __len__(self):
        return len(SPELL)


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


# ---- the sampler chain and the echo check --------------------------------------------


class FakeClient:
    """Enough of the client for the constructor. `_request` and `_check` decide everything
    from the request and this adapter's own configuration, so neither reaches a server."""

    def props(self):
        return Props(n_ctx=64, model_alias="fake", model_path="fake")


def offline() -> LlamaCppAdapter:
    return LlamaCppAdapter(Source("model", "fake"), Spelling(), FakeClient())


PROMPT = [3555, 374]  # " What is" -- spelled by SPELL and not ending mid-character

ASK = {"length": 2, "record_rows": 4, "record_mass": 1.0,
       "temperature": 0.8, "cache_prompt": False}


@pytest.mark.parametrize(
    ("named", "chain"),
    [
        ({}, ["temperature"]),
        ({"top_k": 3}, ["top_k", "temperature"]),
        ({"min_p": 0.1}, ["min_p", "temperature"]),
        ({"top_k": 3, "top_p": 0.9, "min_p": 0.1}, ["top_k", "top_p", "min_p", "temperature"]),
    ],
)
def test_the_chain_is_the_samplers_the_request_named_in_the_server_s_order(named, chain):
    """Naming a sampler is what activates it, so the chain and the named set are one thing.
    The order is the server's own and not the caller's: a chain is applied in sequence."""
    payload = offline()._request(PROMPT, {**ASK, **named})
    assert payload["samplers"] == chain
    for sampler in ("top_k", "top_p", "min_p"):
        assert (sampler in payload) is (sampler in named)


def test_the_ungated_samplers_are_sent_whatever_the_chain_holds():
    """`mirostat` replaces the chain and `dynatemp_range` lives inside its `temperature`
    entry, so neither is gated by `samplers` and both are set on every request."""
    payload = offline()._request(PROMPT, ASK)
    assert payload["mirostat"] == 0
    assert payload["dynatemp_range"] == 0.0


def test_a_named_top_k_must_be_covered_and_an_unnamed_one_constrains_nothing():
    """The coupling is a check on a request that names `top_k`, not a rule about draws."""
    narrow = {**ASK, "record_rows": 2}
    assert offline()._request(PROMPT, narrow)["n_probs"] == 2
    with pytest.raises(Refused, match="must cover a top_k"):
        offline()._request(PROMPT, {**narrow, "top_k": 3})


@pytest.mark.parametrize(
    ("sent", "got", "same"),
    [
        (0.8, 0.800000011920929, True),   # the single precision the server holds it in
        (0.0, 0.0, True),
        (0.8, 0.9, False),
        (0, 0.0, True),
        (10, 10, True),
        (10, 11, False),
        (False, False, True),
        (0, False, False),                # equal in Python, different answers here
        (1, True, False),
        (["top_k"], ["top_k"], True),
        (["top_k"], ["top_k", "min_p"], False),
        (0.8, MISSING, False),
    ],
)
def test_resolved_as(sent, got, same):
    """Float tolerance is the derived value here: too tight and every request fails, too
    loose and a resolved-differently parameter passes. It is set to single precision."""
    assert resolved_as(sent, got) is same


def echoed(params, *, prompt_n=2, rows=1):
    """The server reports `generation_settings` flat; the adapter also accepts it nested,
    which is why both shapes are read the same way."""
    return {
        "generation_settings": params,
        "timings": {"prompt_n": prompt_n},
        "completion_probabilities": [{"top_logprobs": [{}] * rows}],
    }


def test_check_passes_when_the_server_reports_what_was_sent():
    payload = {"temperature": 0.8, "samplers": ["temperature"], "n_probs": 4,
               "cache_prompt": False}
    offline()._check(payload, echoed({"temperature": 0.800000011920929, "n_probs": 4,
                                      "samplers": ["temperature"]}), 2)


@pytest.mark.parametrize(
    ("reported", "why"),
    [
        ({"temperature": 1.0, "samplers": ["temperature"], "n_probs": 4}, "temperature"),
        ({"temperature": 0.8, "samplers": ["top_k", "temperature"], "n_probs": 4}, "samplers"),
        ({"temperature": 0.8, "n_probs": 4}, "samplers: .*not reported"),
    ],
)
def test_check_is_a_fault_when_the_server_resolved_something_else(reported, why):
    """Not a refusal: a refusal is decided before the call, and this is the call already
    answered. It is the same shape as the `truncated` cross-check."""
    payload = {"temperature": 0.8, "samplers": ["temperature"], "n_probs": 4,
               "cache_prompt": False}
    with pytest.raises(AssertionError, match=why):
        offline()._check(payload, echoed(reported), 2)


def test_check_reads_cache_prompt_off_the_prompt_tokens_evaluated():
    """The one parameter the server does not echo. With the cache off the whole prompt is
    evaluated, and anything less means a cache state the record does not name."""
    payload = {"samplers": [], "n_probs": 4, "cache_prompt": False}
    offline()._check(payload, echoed({"samplers": [], "n_probs": 4}, prompt_n=2), 2)
    with pytest.raises(AssertionError, match="cache_prompt"):
        offline()._check(payload, echoed({"samplers": [], "n_probs": 4}, prompt_n=1), 2)
    # With the cache on, a short prompt_n is the point of it and not a fault.
    offline()._check({**payload, "cache_prompt": True},
                     echoed({"samplers": [], "n_probs": 4}, prompt_n=1), 2)

def test_check_reads_the_row_count_off_what_came_back_and_not_off_the_echo():
    """`n_probs` above the vocabulary echoes back unclamped while fewer rows arrive, so the
    echo cannot see that fault. Counting the rows is what does -- a net under the refusal
    that normally prevents it, in the shape the `truncated` cross-check already uses."""
    payload = {"samplers": [], "n_probs": 4, "cache_prompt": False}
    offline()._check(payload, echoed({"samplers": [], "n_probs": 4}, rows=4), 2)
    with pytest.raises(AssertionError, match="a position reports 5"):
        offline()._check(payload, echoed({"samplers": [], "n_probs": 4}, rows=5), 2)
