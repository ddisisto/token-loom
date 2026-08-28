"""The llama.cpp adapter: the three operations, and the repairs behind them.

An adapter absorbs its backend's faults rather than passing them through. This one has
four to absorb, all recorded in `docs/SERVER.md`, and every one of them produces a record
that is *quietly wrong* rather than an error:

1. `completion_probabilities` is the generated sequence regrouped onto character
   boundaries, not the sequence itself. `walk` puts the two back together.
2. `n_probs` above the vocabulary size is silently clamped. Refused.
3. A prompt plus a requested length that will not fit is silently truncated -- and the
   response still says `stop_type: limit`, which in the core means "it drew the requested
   length". Refused before it can happen, and cross-checked after.
4. The server's default sampler chain applies whatever this adapter does not set, so a
   request naming `top_k` and `temperature` would also get `min_p`, `top_p` and repetition
   penalties nobody asked for. Every sampler not exposed is neutralised explicitly.

**`cache_prompt` is off by default here, and that is a fidelity choice.** A full cache hit
evaluates no prompt tokens, which changes the reduction order and perturbs the logits.
Measured on this build: cold against cold is bit-identical, warm against warm is
bit-identical, and cold against warm differs by up to **0.056** in logprob at the top of a
five-row ranking -- enough to reorder near-ties. Each cache state is internally
reproducible, so this is not noise; it is a second variable. Obligation 5 asks that a
ranking depend on the model and the path and on nothing else, and leaving the cache on
would quietly make it depend on what was generated before it. Turn it back on with
`cache_prompt=True` where re-evaluating a long prompt costs more than the last two decimal
places are worth.
"""

from __future__ import annotations

from pathlib import Path

from ...core import Generation, Position, Ranked, Source, Token
from .client import LlamaCppClient, ServerError
from .vocab import GgufVocabulary

#: What a caller may name. Anything else is refused rather than ignored: obligation 6
#: forbids substituting a default for a parameter the backend does not understand.
KNOWN = frozenset({"length", "top_k", "top_n", "temperature", "top_p", "min_p"})

#: All four are required, so that a recorded `params` row is a complete description of the
#: draw. The core reads only `length`; the rest is what makes the act reproducible.
REQUIRED = ("length", "top_k", "top_n", "temperature")

#: Every sampler this adapter does not expose, set to its identity. Without these the
#: server's own defaults -- `min_p` 0.05, `top_p` 0.95, a repetition window of 64 -- would
#: silently join the request.
NEUTRAL = {
    "top_p": 1.0,
    "min_p": 0.0,
    "typical_p": 1.0,
    "top_n_sigma": -1.0,
    "xtc_probability": 0.0,
    "repeat_penalty": 1.0,
    "presence_penalty": 0.0,
    "frequency_penalty": 0.0,
    "dry_multiplier": 0.0,
    "mirostat": 0,
}

#: `0xFFFFFFFF` is llama.cpp's "choose one for me". A seed it would replace is a seed it
#: cannot honour, and an adapter whose backend cannot seed its sampler refuses.
MAX_SEED = 2**32 - 2


class Refused(Exception):
    """Carried out of the checks and turned into a `refused` act by `generate`."""


class LlamaCppAdapter:
    """One vocabulary, one server, one model."""

    def __init__(
        self,
        source: Source,
        vocabulary: GgufVocabulary,
        client: LlamaCppClient,
        *,
        cache_prompt: bool = False,
    ) -> None:
        self.source = source
        self.vocabulary = vocabulary
        self.client = client
        self.cache_prompt = cache_prompt
        self.n_ctx = client.props().n_ctx

    @classmethod
    def connect(
        cls,
        gguf_path: str | Path,
        *,
        source_name: str,
        base_url: str = "http://localhost:8081",
        vocabulary_name: str | None = None,
        cache_prompt: bool = False,
    ) -> LlamaCppAdapter:
        client = LlamaCppClient(base_url)
        vocabulary = GgufVocabulary.cached(gguf_path, vocabulary_name or source_name)
        return cls(Source("model", source_name), vocabulary, client, cache_prompt=cache_prompt)

    @property
    def name(self) -> str:
        return self.vocabulary.name

    # ---- tokenize and bytes_for ----------------------------------------------------

    def tokenize(self, text: bytes, *, special: bool = False) -> list[Token]:
        """Ids from the server, bytes from the vocabulary.

        `/tokenize` with `with_pieces` reports per-token bytes exactly, and this takes the
        ids from it and spells them itself anyway -- obligation 2 asks for what the
        vocabulary says, and taking both from the same place would mean the round trip
        `create` performs could never disagree with anything.
        """
        pieces = self.client.tokenize(text.decode("utf-8"), special=special)
        return [Token(p["id"], self.vocabulary.bytes_for(p["id"])) for p in pieces]

    def bytes_for(self, token_id: int) -> bytes:
        return self.vocabulary.bytes_for(token_id)

    # ---- the path predicate --------------------------------------------------------

    def will_evaluate(self, ids: list[int]) -> bool:
        """Whether the backend would accept this path. Asking is not declining: this
        writes nothing and stands in for no refusal."""
        return bool(ids) and not ends_mid_character(self.vocabulary.spell(ids))

    # ---- generate ------------------------------------------------------------------

    def generate(self, ids: list[int], params: dict, seed: int) -> Generation:
        """Draw from `ids`, or refuse. Met or refused, never adjusted."""
        try:
            payload = self._request(ids, params, seed)
        except Refused as why:
            return Generation("refused", (), reason=str(why))

        try:
            answer = self.client.completion(ids, payload)
        except ServerError as exc:
            if exc.status == 500 and "Content-only" in exc.body:
                # The path predicate should have caught this. If it did not, the predicate
                # is wrong, and saying so is more useful than recording a `failed`.
                raise AssertionError(
                    f"the server refused a path `will_evaluate` accepted: {exc}"
                ) from exc
            raise

        if answer.get("truncated"):
            raise AssertionError(
                "the server truncated a request that was checked for room; "
                f"asked {params['length']}, drew {answer.get('tokens_predicted')}"
            )

        positions = walk(answer["tokens"], answer["completion_probabilities"], self.vocabulary)
        return Generation(terminator_for(answer["stop_type"]), tuple(positions))

    def _request(self, ids: list[int], params: dict, seed: int) -> dict:
        """Every refusal, in one place. Each is decidable from the request and this
        adapter's own configuration, which is why there is no second way to decline."""
        unknown = set(params) - KNOWN
        if unknown:
            raise Refused(f"parameters this backend does not understand: {sorted(unknown)}")
        missing = [key for key in REQUIRED if key not in params]
        if missing:
            raise Refused(f"parameters required to describe the draw: {missing}")

        length, top_k, top_n = params["length"], params["top_k"], params["top_n"]
        if not isinstance(top_k, int) or top_k < 1:
            raise Refused(f"top_k must be a positive integer, not {top_k!r}")
        if not isinstance(top_n, int) or top_n < top_k:
            raise Refused(f"top_n >= top_k > 0; asked top_n {top_n!r}, top_k {top_k}")
        if top_n > len(self.vocabulary):
            # The server reports the whole vocabulary and calls it top_n; that is a
            # parameter adjusted rather than met.
            raise Refused(
                f"top_n {top_n} exceeds the vocabulary ({len(self.vocabulary)}); "
                "the server would clamp it silently"
            )
        if not 0 <= seed <= MAX_SEED:
            raise Refused(f"seed must be in 0..{MAX_SEED}; {seed} cannot be honoured")
        if not ids:
            # An empty prompt is accepted and generates nothing, so a request for `length`
            # tokens cannot be met.
            raise Refused("an empty prompt generates nothing; this request cannot be met")
        if ends_mid_character(self.vocabulary.spell(ids)):
            raise Refused("this backend will not evaluate a path whose bytes end mid-character")
        room = len(ids) + length
        if room > self.n_ctx:
            # Otherwise the server truncates and still reports `stop_type: limit`.
            raise Refused(
                f"{len(ids)} prompt + {length} requested = {room} exceeds n_ctx {self.n_ctx}"
            )

        return {
            **NEUTRAL,
            "n_predict": length,
            "n_probs": top_n,
            "top_k": top_k,
            "temperature": params["temperature"],
            **{k: params[k] for k in ("top_p", "min_p") if k in params},
            "seed": seed,
            "cache_prompt": self.cache_prompt,
        }


# ---- the repairs -------------------------------------------------------------------


def ends_mid_character(data: bytes) -> bool:
    """Whether the bytes end with an under-filled multi-byte sequence.

    **Measured, and narrower than "does the path decode".** llama.cpp refuses a prompt
    whose bytes *end* mid-character -- `The` + `F0 9F` answers HTTP 500 -- but accepts one
    carrying a completed invalid sequence with valid bytes after it, and accepts a stray
    continuation byte even in last position (`The` + `9C` answers 200). So the predicate
    asks about the tail alone, and a path that does not decode end to end is not thereby
    unreachable.
    """
    for back in range(1, min(4, len(data)) + 1):
        byte = data[-back]
        if byte < 0x80:
            return False  # ASCII: nothing is pending
        if byte < 0xC0:
            continue  # a continuation byte; keep looking back for its lead
        need = 2 if byte < 0xE0 else 3 if byte < 0xF0 else 4 if byte < 0xF8 else 0
        return back < need  # an invalid lead (need 0) is garbage the server accepts
    return False


def terminator_for(stop_type: str) -> str:
    """`stop_type` separates `eos` from `limit`, which is why the native endpoint is the
    one this talks to. Nothing else is expected: this adapter does not expose `stop`, so
    `word` cannot arise, and `none` means a generation loop that never started."""
    if stop_type in ("eos", "limit"):
        return stop_type
    raise AssertionError(f"unexpected stop_type {stop_type!r} from a request with no stop strings")


def walk(tokens: list[int], groups: list[dict], vocabulary: GgufVocabulary) -> list[Position]:
    """Put the real token sequence back together with the rankings reported for it.

    `tokens` is what the model emitted. `completion_probabilities` is that sequence
    regrouped onto character boundaries: the server accumulates generated text and emits a
    record only once the accumulation is valid UTF-8, so a character split across several
    tokens yields **one** entry carrying the whole group's bytes but the **last**
    fragment's id, logprob and alternatives.

    So each group is consumed by spelling tokens until they equal the bytes it reports,
    and the ranking lands on the last token of the group. The interior ones are
    declinations -- positions with no distribution, which the core records as an absent
    ranked edge and never as an estimate.

    A control token reports empty bytes when generated even though the vocabulary spells
    it in full, so a group with no bytes is matched on its id instead.
    """
    positions: list[Position] = []
    at = 0
    for group in groups:
        want = bytes(group["bytes"])
        taken: list[int] = []
        while at < len(tokens):
            taken.append(tokens[at])
            at += 1
            if want:
                if vocabulary.spell(taken) == want:
                    break
            elif taken[-1] == group["id"]:
                break
        else:
            raise AssertionError(
                f"ran out of tokens matching group {group['id']} ({want!r}); "
                f"tokens={tokens} groups={[g['id'] for g in groups]}"
            )
        if taken[-1] != group["id"]:
            raise AssertionError(
                f"group spelling {want!r} ends at token {taken[-1]}, "
                f"but the server reports id {group['id']}"
            )
        positions += [Position(token, None) for token in taken[:-1]]
        positions.append(
            Position(
                group["id"],
                tuple(Ranked(alt["id"], alt["logprob"]) for alt in group["top_logprobs"]),
            )
        )
    # Anything after the last group was emitted but never accounted for in text.
    positions += [Position(token, None) for token in tokens[at:]]
    return positions
