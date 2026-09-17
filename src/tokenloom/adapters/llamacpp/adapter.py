"""The llama.cpp adapter: the four operations, and the repairs behind them.

An adapter absorbs its backend's faults rather than passing them through. This one has
four to absorb, all recorded in this package's `README.md`, and every one of them produces a
record that is *quietly wrong* rather than an error:

1. `completion_probabilities` is the generated sequence regrouped onto character
   boundaries, not the sequence itself. `walk` puts the two back together.
2. `n_probs` above the vocabulary size is silently clamped. Refused.
3. A prompt plus a requested length that will not fit is silently truncated -- and the
   response still says `stop_type: limit`, which in the core means "it drew the requested
   length". Refused before it can happen, and cross-checked after.
4. The server's default sampler chain joins any request that does not name one, so a
   request naming `top_k` and `temperature` would also get `min_p`, `top_p` and repetition
   penalties nobody asked for. Every request names its own chain, and every parameter set
   is checked against what the server reports resolving.
"""

from __future__ import annotations

import math
from pathlib import Path

from ...core import Generation, Position, Ranked, Source, Token
from .client import LlamaCppClient, ServerError
from .vocab import GgufVocabulary

#: What a caller may name. Anything else is refused rather than ignored: obligation 6
#: forbids substituting a default for a parameter the backend does not understand.
#:
#: Sampling parameters keep the field's names; what governs the *record* is `record_`.
KNOWN = frozenset(
    {
        "length",
        "record_rows",
        "record_mass",
        "top_k",
        "temperature",
        "top_p",
        "min_p",
        "cache_prompt",
        "seed",
    }
)

#: The samplers this adapter exposes, in the order the server applies them. A request's
#: chain is built from the ones the caller named, so naming a sampler and activating it are
#: the same act and one left out is left out of the chain.
SAMPLERS = ("top_k", "top_p", "min_p", "temperature")

#: Required is what something other than the caller would otherwise decide. Leave
#: `temperature` unnamed and a chain without it draws at 1.0; leave `cache_prompt` unnamed
#: and the server picks a cache state, which moves the logprobs; leave `record_rows` or
#: `record_mass` unnamed and *this adapter* would be deciding what the store keeps for
#: good.
#:
#: `top_k` is not here. A chain holds what the caller named, so omitting it omits it from
#: the chain rather than letting the server's own value apply, and requiring it would
#: protect nothing.
#:
#: `seed` is deliberately **not** here, and that is not an oversight to repair. A seed is
#: not a policy: there is no value the server imposes and none it substitutes, so a caller
#: who does not ask for reproducibility has had nothing adjusted. `docs/ADAPTER.md` states
#: what it costs -- a stochastic act naming no seed cannot be replayed, and nothing in the
#: record marks it as one that cannot.
REQUIRED = ("length", "record_rows", "record_mass", "temperature", "cache_prompt")

#: Set on every request because the `samplers` list does not gate them: `mirostat` replaces
#: the chain wholesale when it is non-zero, and `dynatemp_range` lives inside the chain's
#: `temperature` entry. Both are measured; `README.md` has the rest.
UNGATED = {"mirostat": 0, "dynatemp_range": 0.0}

#: `0xFFFFFFFF` is llama.cpp's "choose one for me". A seed it would replace is a seed it
#: cannot honour, and an adapter whose backend cannot seed its sampler refuses.
MAX_SEED = 2**32 - 2

#: Reported for a key the server did not echo at all, which is a disagreement like any
#: other. A sentinel rather than `None`, so that a genuine null would still be compared.
MISSING = "<not reported>"


class Refused(Exception):
    """Carried out of the checks and turned into a `refused` act by `generate`."""


class LlamaCppAdapter:
    """One vocabulary, one server, one model."""

    def __init__(
        self,
        source: Source,
        vocabulary: GgufVocabulary,
        client: LlamaCppClient,
    ) -> None:
        self.source = source
        self.vocabulary = vocabulary
        self.client = client
        self.n_ctx = client.props().n_ctx

    @classmethod
    def connect(
        cls,
        gguf_path: str | Path,
        *,
        source_name: str,
        base_url: str = "http://localhost:8081",
        vocabulary_name: str | None = None,
    ) -> LlamaCppAdapter:
        client = LlamaCppClient(base_url)
        vocabulary = GgufVocabulary.cached(gguf_path, vocabulary_name or source_name)
        return cls(Source("model", source_name), vocabulary, client)

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

    def generate(self, ids: list[int], params: dict) -> Generation:
        """Draw from `ids`, or refuse. Met or refused, never adjusted."""
        try:
            payload = self._request(ids, params)
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

        self._check(payload, answer, len(ids))
        if answer.get("truncated"):
            raise AssertionError(
                "the server truncated a request that was checked for room; "
                f"asked {params['length']}, drew {answer.get('tokens_predicted')}"
            )

        positions = walk(answer["tokens"], answer["completion_probabilities"], self.vocabulary)
        return Generation(
            terminator_for(answer["stop_type"]),
            tuple(bound(positions, params["record_mass"])),
        )

    def _request(self, ids: list[int], params: dict) -> dict:
        """Every refusal, in one place. Each is decidable from the request and this
        adapter's own configuration, which is why there is no second way to decline."""
        unknown = set(params) - KNOWN
        if unknown:
            raise Refused(f"parameters this backend does not understand: {sorted(unknown)}")
        missing = [key for key in REQUIRED if key not in params]
        if missing:
            raise Refused(f"parameters this backend requires: {missing}")

        length = params["length"]
        rows, mass = params["record_rows"], params["record_mass"]
        if not isinstance(params["cache_prompt"], bool):
            raise Refused(f"cache_prompt must be a bool, not {params['cache_prompt']!r}")
        if not isinstance(rows, int) or isinstance(rows, bool) or rows < 2:
            raise Refused(f"record_rows must be an integer of at least 2; asked {rows!r}")
        if "top_k" in params:
            top_k = params["top_k"]
            if not isinstance(top_k, int) or isinstance(top_k, bool) or top_k < 1:
                raise Refused(f"top_k must be a positive integer, not {top_k!r}")
            if rows < top_k:
                raise Refused(
                    "record_rows must cover a top_k the request named; "
                    f"asked record_rows {rows}, top_k {top_k}"
                )
        if rows > len(self.vocabulary):
            # The server reports the whole vocabulary and calls it n_probs; that is a
            # parameter adjusted rather than met.
            raise Refused(
                f"record_rows {rows} exceeds the vocabulary ({len(self.vocabulary)}); "
                "the server would clamp it silently"
            )
        if isinstance(mass, bool) or not isinstance(mass, int | float) or not 0.0 < mass <= 1.0:
            raise Refused(f"record_mass must be a probability in (0, 1]; not {mass!r}")
        if "seed" in params:
            seed = params["seed"]
            if not isinstance(seed, int) or isinstance(seed, bool) or not 0 <= seed <= MAX_SEED:
                raise Refused(
                    f"seed must be an integer in 0..{MAX_SEED}; {seed!r} cannot be honoured"
                )
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

        named = [sampler for sampler in SAMPLERS if sampler in params]
        return {
            **UNGATED,
            "samplers": named,
            "n_predict": length,
            # The ceiling is what the server is asked for; `record_mass` cuts what comes
            # back, and the server has no way to express it.
            "n_probs": rows,
            **{sampler: params[sampler] for sampler in named},
            **({"seed": params["seed"]} if "seed" in params else {}),
            "cache_prompt": params["cache_prompt"],
        }

    def _check(self, payload: dict, answer: dict, prompt_length: int) -> None:
        """Every parameter this adapter set, against what the server reports resolving.

        **What comes back is what the server accepted, not everything it then did**, so
        this is a net under the refusals and not a replacement for them: a request for
        200000 rows echoes back as 200000 and returns 152064. The row count is therefore
        checked against what came back rather than against the echo.

        `cache_prompt` is the one parameter not echoed at all. Its effect is visible
        instead in `timings.prompt_n`, which is the whole prompt exactly when the cache is
        off.
        """
        settings = answer.get("generation_settings", {})
        settings = settings.get("params", settings)
        wrong = [
            f"{key}: sent {value!r}, resolved {settings.get(key, MISSING)!r}"
            for key, value in payload.items()
            if key != "cache_prompt" and not resolved_as(value, settings.get(key, MISSING))
        ]
        widest = max(
            (len(group["top_logprobs"]) for group in answer.get("completion_probabilities", ())),
            default=0,
        )
        if widest > payload["n_probs"]:
            wrong.append(f"n_probs: sent {payload['n_probs']}, and a position reports {widest}")
        if not payload["cache_prompt"]:
            evaluated = answer.get("timings", {}).get("prompt_n")
            if evaluated != prompt_length:
                wrong.append(
                    f"cache_prompt: sent False, and {evaluated} of {prompt_length} "
                    "prompt tokens were evaluated"
                )
        if wrong:
            raise AssertionError(
                "the server did not resolve what this adapter set: " + "; ".join(wrong)
            )


# ---- comparing what came back --------------------------------------------------------


def resolved_as(sent, got) -> bool:
    """Whether what the server reports is what was sent.

    Floats come back at the single precision the server holds them in -- `0.8` reports as
    `0.800000011920929` -- so they are compared to that and not for equality. Bools are
    compared by identity, since `0` and `False` are equal in Python and are different
    answers here.
    """
    if isinstance(sent, bool) or isinstance(got, bool):
        return sent is got
    if isinstance(sent, float) or isinstance(got, float):
        return isinstance(got, int | float) and math.isclose(
            sent, got, rel_tol=1e-6, abs_tol=1e-9
        )
    return sent == got


# ---- the recording bounds ------------------------------------------------------------


def reaches(ranking: tuple[Ranked, ...], mass: float) -> int:
    """How many rows it takes for the probabilities to reach `mass`.

    The whole ranking when they never do -- which `mass` of 1.0 always is, since the
    reported values sum to less than one by the mass of the vocabulary not reported.
    """
    running = 0.0
    for k, row in enumerate(ranking, start=1):
        running += math.exp(row.logprob)
        if running >= mass:
            return k
    return len(ranking)


def bound(positions: list[Position], mass: float) -> list[Position]:
    """Cut each position's ranking to `record_mass`, two rows, and the token drawn --
    whichever of the three reaches furthest.

    The `record_rows` ceiling is already applied: it is what `n_probs` asked the server
    for. A position the backend declined to rank is passed through untouched.
    """
    out: list[Position] = []
    for position in positions:
        if position.ranking is None:
            out.append(position)
            continue
        keep = max(reaches(position.ranking, mass), 2)
        for index, row in enumerate(position.ranking):
            if row.token_id == position.token_id:
                keep = max(keep, index + 1)
                break
        out.append(Position(position.token_id, tuple(position.ranking[:keep])))
    return out


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
