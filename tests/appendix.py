"""The worked example from `docs/CORE.md`, as data.

The ids, the bytes and the logprobs of node 2's ranking are the document's own -- real
values off `Qwen2.5-7B.i1-Q4_K_M`, copied rather than recomputed. **Where the appendix does
not state a ranking it is invented here**, and those values are named `INVENTED` so that
nothing asserts against them: the appendix records rankings at nodes 3, 4 and 6 only as
"the same way", and a test that pinned numbers the document never printed would be testing
this file rather than the format.
"""

from tokenloom.core import Generation, Position, Ranked, Source, Token

MODEL = Source("model", "qwen2.5-7b-base-q4km")
USER = Source("user", "")

#: Every id the appendix stores, with the bytes the vocabulary spells it. Verified against
#: `tokenizer.ggml.tokens` in the GGUF via the GPT-2 byte decoder.
BYTES: dict[int, bytes] = {
    785: b"The",
    12884: b" sky",
    5023: b" currently",
    702: b" has",
    220: b" ",
    374: b" is",
    572: b" was",
    594: b"'s",
    1030: b" had",
    518: b" at",
    3685: b" below",
    3403: b" above",
    1431: b" now",
    304: b" in",
    323: b" and",
    686: b" will",
    748: b"\xe2\x80\x99s",  # ’s
    646: b" can",
    17167: b" consists",
    5868: b" looks",
    2669: b" already",
    4041: b" comes",
    1083: b" also",
    6519: b" turned",
    151643: b"<|endoftext|>",
    9284: b"\xf0\x9f",
    250: b"\x9c",
    223: b"\x81",
}

#: What the appendix authors, and what it tokenises to. `create` is bytes in, tokens out;
#: this stands in for a tokeniser rather than modelling one.
TOKENISATION: dict[tuple[bytes, bool], list[int]] = {
    (b"The sky", False): [785, 12884],
    # The special-token path: the thirteen characters read as one id, not as thirteen
    # characters' worth. The plain path would give the other reading and the same bytes.
    ("<|endoftext|>\U0001f701".encode(), True): [151643, 9284, 250, 223],
}

#: Stage 2's ranking at node 2, exactly as the appendix prints it. Rank 0 is not the token
#: drawn: ` currently` was, at rank 2.
NODE2_TOP5 = [
    Ranked(374, -1.3218),
    Ranked(702, -1.6666),
    Ranked(5023, -2.0363),
    Ranked(572, -2.7138),
    Ranked(594, -3.7901),
]

#: Stage 3's ranking at node 2 -- the same five, reported bit-identically, and fifteen
#: below them. The appendix prints the fifteen at ranks 5..19; a model reports its own top
#: twenty in its own order, and the extension is what puts them there.
NODE2_TOP20 = NODE2_TOP5 + [
    Ranked(1030, -4.3049),
    Ranked(518, -4.3088),
    Ranked(3685, -4.3841),
    Ranked(3403, -4.3868),
    Ranked(1431, -4.8847),
    Ranked(304, -4.9828),
    Ranked(323, -5.0173),
    Ranked(686, -5.1101),
    Ranked(748, -5.1507),
    Ranked(646, -5.7753),
    Ranked(17167, -5.8098),
    Ranked(5868, -5.8294),
    Ranked(2669, -5.9023),
    Ranked(4041, -5.9496),
    Ranked(1083, -5.9643),
]

# INVENTED -- the appendix says only that rankings are recorded at these nodes "the same
# way". The drawn token is present in each, which is what `top_n >= top_k` buys; nothing
# else about these numbers is claimed and no test reads them.
INVENTED_AT_3 = [Ranked(702, -0.9), Ranked(374, -1.4), Ranked(220, -2.1),
                 Ranked(1431, -3.0), Ranked(304, -3.6)]
INVENTED_AT_4 = [Ranked(220, -0.7), Ranked(1431, -1.9), Ranked(3403, -2.4),
                 Ranked(3685, -2.8), Ranked(304, -3.3)]
INVENTED_AT_6 = [Ranked(6519, -1.1), Ranked(1431, -1.5), Ranked(220, -2.2),
                 Ranked(3403, -2.9), Ranked(304, -3.4)]


def _pos(token_id: int, ranking: list[Ranked]) -> Position:
    return Position(token_id, tuple(ranking))


#: One entry per `generate` the appendix performs, in order: the params it was asked for,
#: the seed, the prompt ids the core should hand the adapter, and what comes back.
GENERATIONS = [
    # Stage 2 -- top_k 5, top_n 5, length 3, seed 42. Terminator `limit`.
    (
        {"top_k": 5, "top_n": 5, "length": 3},
        42,
        [785, 12884],
        Generation("limit", (
            _pos(5023, NODE2_TOP5),
            _pos(702, INVENTED_AT_3),
            _pos(220, INVENTED_AT_4),
        )),
    ),
    # Stage 3 -- top_k 5, top_n 20, length 2, seed 99. Extends node 2's ranking to twenty.
    (
        {"top_k": 5, "top_n": 20, "length": 2},
        99,
        [785, 12884],
        Generation("limit", (
            _pos(702, NODE2_TOP20),
            _pos(6519, INVENTED_AT_6),
        )),
    ),
    # Stage 4 -- identical to stage 2. The model reproduces the path exactly, so every
    # node merges and nothing new is written but the act.
    (
        {"top_k": 5, "top_n": 5, "length": 3},
        42,
        [785, 12884],
        Generation("limit", (
            _pos(5023, NODE2_TOP5),
            _pos(702, INVENTED_AT_3),
            _pos(220, INVENTED_AT_4),
        )),
    ),
    # Stage 7 -- top_n 200 at node 12. The adapter will not report two hundred ranked ids,
    # and reducing the request is not open to it, so it refuses. No model is called.
    (
        {"top_k": 5, "top_n": 200, "length": 4},
        7,
        [785, 12884, 374, 151643, 9284, 250, 223],
        Generation("refused", (), reason="top_n 200 exceeds what this backend will report"),
    ),
]


class ScriptedAdapter:
    """A backend that has already answered.

    It asserts the prompt ids, params and seed the core hands it, which is the half of the
    contract a stub can still check: a core that assembled the wrong path would otherwise
    write a perfectly valid tree of the wrong thing.
    """

    def __init__(self, script=GENERATIONS) -> None:
        self.script = list(script)
        self.calls: list[tuple] = []

    name = "qwen2.5-7b-base"
    source = MODEL

    def tokenize(self, text: bytes, *, special: bool = False) -> list[Token]:
        ids = TOKENISATION[(text, special)]
        return [Token(i, BYTES[i]) for i in ids]

    def bytes_for(self, token_id: int) -> bytes:
        return BYTES[token_id]

    def will_evaluate(self, ids: list[int]) -> bool:
        return True

    def generate(self, ids: list[int], params: dict, seed: int) -> Generation:
        want_params, want_seed, want_ids, answer = self.script.pop(0)
        assert ids == want_ids, f"prompt ids {ids} != {want_ids}"
        assert params == want_params, f"params {params} != {want_params}"
        assert seed == want_seed, f"seed {seed} != {want_seed}"
        self.calls.append((ids, params, seed))
        return answer
