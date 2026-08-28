"""Against a running llama.cpp. Skipped when there is none.

These assert the things no stub can: that the vocabulary in the model file agrees with the
server's own tokeniser, that authored bytes round-trip through it, and that the logprobs
`docs/CORE.md`'s appendix prints are the ones this backend actually returns.

CLAUDE.md's method note is the reason this file exists at all: planning, using and
exercising are three different instruments and none substitutes.
"""

from __future__ import annotations

import os

import pytest

from tokenloom.adapters.llamacpp.adapter import LlamaCppAdapter
from tokenloom.adapters.llamacpp.client import LlamaCppClient
from tokenloom.adapters.llamacpp.vocab import GgufVocabulary
from tokenloom.core import Source, Store, violations
from tokenloom.core import reads as R

SERVER = os.environ.get("TOKENLOOM_SERVER", "http://localhost:8081")
pytestmark = pytest.mark.live


@pytest.fixture(scope="session")
def adapter():
    try:
        client = LlamaCppClient(SERVER, timeout=120)
        props = client.props()
    except Exception as why:  # noqa: BLE001 -- any failure to reach it is the same skip
        pytest.skip(f"no llama.cpp at {SERVER}: {why}")
    if not os.path.exists(props.model_path):
        pytest.skip(f"the server's model file is not reachable: {props.model_path}")
    vocabulary = GgufVocabulary.cached(props.model_path, props.model_alias)
    name = os.path.basename(props.model_path).removesuffix(".gguf")
    return LlamaCppAdapter(Source("model", name), vocabulary, client)


def is_qwen(adapter) -> bool:
    return len(adapter.vocabulary) == 152064 and adapter.bytes_for(785) == b"The"


# ---- the vocabulary -----------------------------------------------------------------


def test_the_gguf_vocabulary_agrees_with_the_servers_tokeniser(adapter):
    """`/tokenize` with `with_pieces` reports per-token bytes exactly, and the model file
    reports them too. They must be the same answer, including where a token is a fragment
    of a character -- that agreement is what lets bytes come from the file alone."""
    hard = [
        "The sky is blue",
        "🜁 astral plane",
        "👨‍👩‍👧‍👦 zero-width joiners",
        "café combininǵ marks",
        "  repeated   whitespace\t\n",
        "日本語とハングル 한국어",
        "Ωμέγα ẞ ǅ",
    ]
    for text in hard:
        pieces = adapter.client.tokenize(text, special=False)
        for piece in pieces:
            reported = (
                bytes(piece["piece"]) if isinstance(piece["piece"], list)
                else piece["piece"].encode()
            )
            assert adapter.bytes_for(piece["id"]) == reported, (text, piece["id"])


def test_authored_bytes_round_trip(adapter):
    """Obligation 3. Reassembling the ids' bytes returns the input unchanged -- and the
    reassembly is done from the vocabulary, which is what a reader will do."""
    for text in ["The sky", "🜁", "a<|endoftext|>b", "naïve café — em dash", "\U0001f600\U0001f680"]:
        tokens = adapter.tokenize(text.encode())
        assert b"".join(adapter.bytes_for(t.id) for t in tokens) == text.encode(), text


def test_a_control_token_literal_has_two_readings_that_spell_the_same_bytes(adapter):
    """One id, or the ordinary tokens that spell those thirteen characters. The stored ids
    are what tell them apart, and no field in the store records which was meant."""
    one = adapter.tokenize(b"<|endoftext|>", special=True)
    many = adapter.tokenize(b"<|endoftext|>", special=False)
    assert len(one) == 1 and len(many) > 1
    assert b"".join(adapter.bytes_for(t.id) for t in one) == b"<|endoftext|>"
    assert b"".join(adapter.bytes_for(t.id) for t in many) == b"<|endoftext|>"


def test_a_control_token_spells_its_literal_form_and_not_what_a_generation_says(adapter):
    """`completion_probabilities` reports empty bytes for `<|endoftext|>` whether it was
    sampled or merely ranked. The vocabulary is the answer that is taken."""
    if not is_qwen(adapter):
        pytest.skip("token ids are this model's")
    assert adapter.bytes_for(151643) == b"<|endoftext|>"


# ---- the ranking the appendix prints ------------------------------------------------


def test_the_appendix_logprobs_are_what_this_backend_returns(adapter):
    """`docs/CORE.md`'s appendix says its ids and logprobs are real. This is that claim,
    checked -- the twenty rows at node 2, to four places, in the order they are printed.

    It also pins `cache_prompt`: these values are the cold ones, and a warm cache moves
    them by up to 0.056, which is why the adapter leaves the cache off.
    """
    if not is_qwen(adapter):
        pytest.skip("the appendix's ids are Qwen2.5's")
    answer = adapter.generate(
        [785, 12884], {"length": 1, "top_k": 20, "top_n": 20, "temperature": 0.9}, seed=99
    )
    assert answer.terminator == "limit"
    got = [(r.token_id, round(r.logprob, 4)) for r in answer.positions[0].ranking]
    assert got == [
        (374, -1.3218), (702, -1.6666), (5023, -2.0363), (572, -2.7138), (594, -3.7901),
        (1030, -4.3049), (518, -4.3088), (3685, -4.3841), (3403, -4.3868), (1431, -4.8847),
        (304, -4.9828), (323, -5.0173), (686, -5.1101), (748, -5.1507), (646, -5.7753),
        (17167, -5.8098), (5868, -5.8294), (2669, -5.9023), (4041, -5.9496), (1083, -5.9643),
    ]


def test_top_n_at_least_top_k_keeps_the_drawn_token_in_its_own_ranking(adapter):
    """The drawn token is unmarked in the response and is found by id, never by rank. With
    `top_k == top_n` it is always there, which is what makes a node's logprob derivable."""
    for seed in range(12):
        answer = adapter.generate(
            [785, 12884], {"length": 3, "top_k": 8, "top_n": 8, "temperature": 1.3}, seed=seed
        )
        for position in answer.positions:
            assert position.ranking is not None
            assert position.token_id in [r.token_id for r in position.ranking]


# ---- refusal ------------------------------------------------------------------------


def test_a_path_that_ends_mid_character_is_refused_and_the_predicate_agrees(adapter):
    """The core forms the position; the adapter decides its backend will not take it.

    `will_evaluate` and `generate` must give the same answer -- asking is not declining,
    but it would be useless if it disagreed with what declining does.
    """
    if not is_qwen(adapter):
        pytest.skip("the fragment ids are Qwen2.5's")
    mid = [785, 9284]  # 'The' + the first two bytes of 🜁
    assert adapter.will_evaluate(mid) is False
    answer = adapter.generate(mid, {"length": 2, "top_k": 5, "top_n": 5, "temperature": 1.0}, 1)
    assert answer.terminator == "refused"
    assert adapter.will_evaluate([785, 9284, 250, 223]) is True  # the complete character


@pytest.mark.parametrize(
    ("params", "why"),
    [
        ({"length": 2, "top_k": 5, "top_n": 3, "temperature": 1.0}, "top_n >= top_k"),
        ({"length": 2, "top_k": 0, "top_n": 5, "temperature": 1.0}, "positive integer"),
        ({"length": 2, "top_k": 5, "top_n": 10**9, "temperature": 1.0}, "exceeds the vocabulary"),
        ({"length": 2, "top_k": 5, "top_n": 5}, "required to describe the draw"),
        ({"length": 2, "top_k": 5, "top_n": 5, "temperature": 1.0, "mirostat": 2}, "understand"),
        ({"length": 10**6, "top_k": 5, "top_n": 5, "temperature": 1.0}, "exceeds n_ctx"),
    ],
)
def test_the_refusal_list(adapter, params, why):
    """Refused rather than adjusted, and refused in one place. Every one of these is a
    request the server would otherwise meet approximately: it clamps `n_probs` above the
    vocabulary, and it truncates a generation that will not fit while still reporting
    `stop_type: limit`."""
    answer = adapter.generate([785, 12884], params, 1)
    assert answer.terminator == "refused"
    assert why in answer.reason


def test_an_empty_prompt_is_refused_rather_than_generating_nothing(adapter):
    answer = adapter.generate([], {"length": 2, "top_k": 5, "top_n": 5, "temperature": 1.0}, 1)
    assert answer.terminator == "refused"


# ---- through the store --------------------------------------------------------------


def test_a_tree_built_against_the_real_server_holds_every_invariant(adapter, tmp_path):
    """The whole instrument, end to end: author, generate, branch at an edge nothing drew,
    continue from it, author fragments below, refuse at one of them, delete, and check."""
    with Store.initialise(tmp_path / "live", vocabulary=adapter.name) as store:
        user = Source("user", "")
        draw = {"top_k": 10, "top_n": 10, "temperature": 0.9}

        store.create(None, "The sky", vocabulary=adapter, source=user)
        tip = R.roots(store.conn)[0].id + 1
        store.generate(tip, {"length": 4, **draw}, adapter=adapter, seed=42)

        # Branch at a ranked edge nothing took. This is the operation the format exists for.
        unrealised = R.unrealised_edges(store.conn, tip)
        assert unrealised, "a generation must leave alternatives at the node it started from"
        branch = store.realise(tip, adapter.source, unrealised[0].rank, actor=user)
        taken = store.conn.execute(
            "SELECT tip FROM acts WHERE id = ?", (branch,)
        ).fetchone()[0]
        assert R.node_logprob(store.conn, taken) == pytest.approx(unrealised[0].logprob)

        _, answer = store.generate(taken, {"length": 6, **draw}, adapter=adapter, seed=7)
        assert answer.terminator in ("limit", "eos")

        store.create(taken, "🜁", vocabulary=adapter, source=user)
        fragment = R.children(store.conn, taken)[-1].id
        # A fragment node is a node like any other, and the adapter is what declines it.
        _, refusal = store.generate(fragment, {"length": 2, **draw}, adapter=adapter, seed=1)
        assert refusal.terminator == "refused"

        store.delete(tip)
        assert not R.is_live(store.conn, taken)
        assert violations(store.conn) == []


def test_eos_is_drawable_and_is_a_node(adapter):
    """`docs/CORE-status.md` lists `eos` as specified and unwitnessed. It is drawable on
    this model after a document-ending prompt, and it arrives as an ordinary node."""
    if not is_qwen(adapter):
        pytest.skip("the prompt ids are Qwen2.5's")
    for seed in range(12):
        answer = adapter.generate(
            [576, 835, 13],  # ' The end.'
            {"length": 6, "top_k": 5, "top_n": 5, "temperature": 1.0}, seed,
        )
        if answer.terminator == "eos":
            assert answer.positions[-1].token_id == 151643
            assert adapter.bytes_for(151643) == b"<|endoftext|>"
            return
    pytest.fail("no eos draw in twelve seeds after ' The end.'")
