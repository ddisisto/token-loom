"""A toy vocabulary and a programmable backend, for the paths the appendix does not reach.

The appendix is a fixture for one worked tree. These are for constructing a *particular*
situation -- a deleted ancestor, a declined ranking, a backend that dies mid-call -- which
means the vocabulary has to be small enough to reason about by hand.
"""

from tokenloom.core import Generation, Position, Ranked, Source, Token

MODEL = Source("model", "toy-1")
OTHER = Source("model", "toy-2")
USER = Source("user", "")

WORDS = ["The", " sky", " is", " blue", " red", " grey", " ", "<|eot|>"]
#: Ids are 100 upward for whole words, then two fragments of one character: `\xc3\xa9`
#: split in half, so a path can be formed that ends inside a character.
VOCAB: dict[int, bytes] = {100 + i: w.encode() for i, w in enumerate(WORDS)}
FRAG_HI, FRAG_LO = 200, 201
VOCAB[FRAG_HI] = b"\xc3"
VOCAB[FRAG_LO] = b"\xa9"

BY_BYTES = {v: k for k, v in VOCAB.items()}


class ToyVocabulary:
    """Greedy longest-match over `WORDS`. `special` is accepted and changes nothing here:
    the toy has no control token whose literal spelling is also ordinary text."""

    name = "toy"

    def tokenize(self, text: bytes, *, special: bool = False) -> list[Token]:
        out, i = [], 0
        while i < len(text):
            for width in range(min(8, len(text) - i), 0, -1):
                piece = text[i : i + width]
                if piece in BY_BYTES:
                    out.append(Token(BY_BYTES[piece], piece))
                    i += width
                    break
            else:
                raise ValueError(f"toy vocabulary cannot spell {text[i:i + 1]!r}")
        return out

    def bytes_for(self, token_id: int) -> bytes:
        return VOCAB[token_id]


class ToyAdapter(ToyVocabulary):
    """Answers from a script, or from a callable, or raises. Whatever a test needs."""

    def __init__(self, answers, source: Source = MODEL) -> None:
        self.answers = list(answers)
        self.source = source
        self.prompts: list[list[int]] = []

    def will_evaluate(self, ids: list[int]) -> bool:
        return True

    def generate(self, ids: list[int], params: dict, seed: int) -> Generation:
        self.prompts.append(list(ids))
        answer = self.answers.pop(0)
        if isinstance(answer, BaseException):
            raise answer
        if callable(answer):
            return answer(ids, params, seed)
        return answer


def drew(*pairs) -> Generation:
    """`drew((token_id, [(id, logprob), ...]), ...)` -> a `limit` generation.

    A ranking of `None` is a declination: a position the backend could give no
    distribution for, which the core records as an absent ranked edge and never as an
    estimate.
    """
    positions = tuple(
        Position(tok, None if ranking is None else tuple(Ranked(i, lp) for i, lp in ranking))
        for tok, ranking in pairs
    )
    return Generation("limit", positions)
