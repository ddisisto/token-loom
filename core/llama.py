"""Generation against llama.cpp's own server, on its native endpoint.

Local only, which the roadmap settles for the MVP. `inference.py` is not in the
path: it was written around the OpenAI-compatible surface and a capability
table describing how providers differ, and almost none of that survives contact
with one local server. What it does instead -- echo handling, `drop_params`,
provider routing, a placeholder API key the client refuses to work without --
is machinery for a problem this does not have.

The deciding argument is upstream of the endpoint choice, though: **no hosted
provider can feed the token core anyway.** It needs per-token ids, bytes and
logprobs on a raw continuation, and no OpenRouter provider returns logprobs on
its completions endpoint. Preserving hosted reach would preserve nothing usable.

Both endpoints return an identical token payload -- `{id, token, bytes,
logprob, top_logprobs}` -- so the native one is chosen for what it adds around
that: `stop_type` separating end-of-text from a stop string from a limit, and
`tokens_evaluated` for free. See `FORMAT.md`.
"""
from __future__ import annotations

from typing import NamedTuple

import requests

from core.store import (ABORTED, CONTEXT, EOS, LENGTH, STOP, Counterfactual,
                        Token)

DEFAULT_BASE = 'http://127.0.0.1:8081'


class Truncated(Exception):
    """The prompt does not fit the server's context, so nothing was generated.

    Fatal rather than a warning, for the reason it always was: a span whose
    `slice_start` claimed bytes the model never saw would be a lie in exactly
    the way immutable bytes exist to prevent, and the recorded conditions are
    the whole product.

    What changed is where it comes from. This was written watching the
    `truncated` flag in the response, on the assumption that the server cuts an
    over-long prompt down and generates from what is left. Measured against
    llama.cpp b10221, it does not: an over-long prompt is refused outright with
    HTTP 400 and `exceed_context_size_error`, and no generation happens at all.
    So this is raised from the refusal, and the flag means something else --
    see `_reason`.
    """


class Incomplete(Exception):
    """The response lost bytes the model had already produced.

    llama-server accumulates generated *text* and only emits a token's record
    once that text is valid UTF-8. A character whose encoding spans several
    tokens is therefore held back until the token that completes it. If the
    `n_predict` budget expires first, the held-back fragments are never flushed
    and their bytes are gone from the response entirely -- while
    `tokens_predicted` still counts them and `stop_type` still says `limit`.

    Fatal for the same reason as `Truncated`: a span whose bytes are a strict
    prefix of what the model emitted, recorded as having stopped at a length
    limit, is a lie of exactly the kind immutable bytes exist to prevent. It is
    rare -- zero of 72 measured on English prompts -- and reliably reachable
    with astral-plane characters, where a retry at a different length usually
    clears it.
    """


class Result(NamedTuple):
    tokens: list[Token]
    counterfactuals: list[Counterfactual]
    reason: str
    prompt_tokens: int


class Server:
    """One llama-server, addressed natively."""

    def __init__(self, base: str = DEFAULT_BASE, timeout: int = 600):
        self.base = base.rstrip('/')
        self.timeout = timeout

    # -- what the server is ------------------------------------------------

    def props(self) -> dict:
        r = requests.get(f'{self.base}/props', timeout=10)
        r.raise_for_status()
        return r.json()

    def describe(self) -> dict:
        """The parts of a parameter set that come from the server, not the user.

        `n_ctx` is recorded with every span because "hit the context limit" is
        uninterpretable without knowing which limit -- it is a serving choice,
        and `--parallel` divides it.
        """
        props = self.props()
        settings = props.get('default_generation_settings', {})
        return {'model': props.get('model_alias'),
                'n_ctx': settings.get('n_ctx')}

    def alive(self) -> bool:
        try:
            return requests.get(f'{self.base}/health',
                                timeout=3).json().get('status') == 'ok'
        except requests.RequestException:
            return False

    # -- generation --------------------------------------------------------

    def complete(self, prompt: bytes, settings: dict, seed: int) -> Result:
        """One continuation, as the records the core stores.

        `prompt` is bytes because everything in the core is, and is decoded
        here -- the one place that has to. A slice start is nudged to a
        character boundary when it is resolved, so the only way this can fail
        is a generation point deliberately placed inside a character.
        """
        if settings['top_n'] < 1:
            # n_probs=0 returns no `completion_probabilities` at all, and with
            # it go the per-token bytes -- not just the counterfactuals. There
            # is no token overlay to store without them, so this is a hard
            # requirement rather than a default worth quietly applying.
            raise ValueError(
                'top_n must be at least 1: llama-server returns per-token '
                'bytes and logprobs only alongside counterfactuals')
        try:
            text = prompt.decode('utf-8')
        except UnicodeDecodeError as e:
            raise ValueError(
                'the prompt ends inside a character, so it has no string form. '
                'A token can be a fragment of a character, so a branch point '
                'at a token boundary is not always at a character boundary -- '
                f'{e}') from e

        body = {
            'prompt': text,
            'n_predict': settings['length'],
            'temperature': settings['temperature'],
            'top_p': settings['top_p'],
            'n_probs': settings['top_n'],
            'stop': list(settings['stop']),
            'seed': seed,
            'return_tokens': True,
            # on, and it costs byte-exact replay of an individual span. A full
            # cache hit evaluates no prompt tokens, which changes the reduction
            # order enough to perturb the logits, which occasionally flips a
            # near-tie: the same slice, seed and parameters can reproduce a
            # *different* continuation warm than cold. Measured, not assumed.
            #
            # It was off for a while on the reasoning that recorded conditions
            # should reproduce their span. What that missed is that the cache is
            # a pure function of the prompt tokens -- no seed reaches it -- so
            # the perturbation is unbiased numerical noise and the *distribution*
            # is unchanged to within it. Warm and cold are two draws from the
            # same distribution, not one right and one wrong. What is lost is
            # bitwise replay, which was already conditional on the same build
            # and the same GPU, and which the research thread has traded for the
            # prompt processing. See BEYOND-MVP.md for the ways back to it
            'cache_prompt': True,
        }
        r = requests.post(f'{self.base}/completion', json=body,
                          timeout=self.timeout)
        if r.status_code == 400:
            # the one refusal worth a typed error rather than an HTTPError:
            # the prompt is longer than the context and nothing was generated
            error = (r.json().get('error') or {}) if _is_json(r) else {}
            if error.get('type') == 'exceed_context_size_error':
                raise Truncated(
                    f"{error.get('n_prompt_tokens')} prompt tokens do not fit "
                    f"a context of {error.get('n_ctx')}; shorten the slice with "
                    f"--prompt-length, or serve with a larger --ctx-size")
        r.raise_for_status()
        return self._read(r.json(), settings)

    @staticmethod
    def _read(payload: dict, settings: dict) -> Result:
        entries = payload.get('completion_probabilities') or []
        groups, tail = _align(entries, payload.get('tokens') or [],
                              payload.get('tokens_predicted', 0))
        # a stop match leaves a tail on purpose: the server erases trailing
        # entries by the stop string's token count so the match itself is not
        # part of the span. That is the intended behaviour and this is not the
        # place to second-guess it -- the known fault there is that the erase
        # is by token count while the match is on text, so a stop string off a
        # token boundary takes real bytes with it. Undecidable from here, and
        # fixed properly only by matching on token ids
        if tail and payload.get('stop_type') != 'word':
            raise Incomplete(
                f'the response is {len(tail)} token(s) short of the '
                f'{payload.get("tokens_predicted", 0)} it reports: a character '
                f'split across tokens was still incomplete when the length '
                f'budget ran out, so its bytes never arrived. Retrying at a '
                f'different --length usually clears it')

        tokens, counterfactuals = [], []
        for i, (entry, group) in enumerate(zip(entries, groups)):
            # a merged entry stands for a group, and its id, logprob and
            # alternatives describe only that group's *last* fragment. Storing
            # the fragment's id beside the group's bytes would assert a
            # correspondence that does not hold, so both are recorded absent
            merged = len(group) > 1
            tokens.append(Token(i, None if merged else entry['id'],
                                bytes(entry['bytes']),
                                None if merged else entry['logprob']))
            if merged:
                # alternatives to a byte fragment, at a position whose sampled
                # value is a whole character. There is nowhere in the format to
                # say that, so they are dropped rather than mislabelled
                continue
            counterfactuals.extend(
                Counterfactual(i, rank, c['id'], bytes(c['bytes']), c['logprob'])
                for rank, c in enumerate(entry.get('top_logprobs') or []))

        return Result(tokens, counterfactuals,
                      _reason(payload, settings), payload.get('tokens_evaluated', 0))


def _align(entries: list[dict], tokens: list[int], predicted: int
           ) -> tuple[list[list[int]], list[int]]:
    """Which sampled tokens each returned entry stands for.

    `completion_probabilities` is not the sampled sequence. It is that sequence
    regrouped onto character boundaries: llama-server accumulates generated
    text and emits a record only once the accumulation is valid UTF-8, so a
    character split across several tokens produces *one* entry, carrying the
    whole group's bytes but the last fragment's id, logprob and alternatives.
    `tokens` -- requested through `return_tokens` and, until this existed,
    thrown away -- is the real sequence.

    So the two are alignable and the alignment costs nothing: an entry's `id`
    is its group's final token, so walking `tokens` and consuming up to and
    including that id recovers each group. Whatever remains after the last
    entry is what the server dropped.

    Measured on Qwen2.5 at b10221: no merging at all on English prompts, and
    every astral-plane character merged, since none of its tokens is valid
    UTF-8 alone. The counts are the check -- an entry id that never appears, or
    a `tokens` array that disagrees with `tokens_predicted`, means the walk has
    lost its place, and a mis-alignment silently mislabels every record after
    it. Raising is the only honest answer to that.
    """
    if not entries:
        return [], list(tokens)
    if len(tokens) != predicted:
        raise Incomplete(
            f'the response reports {predicted} tokens predicted but returns '
            f'{len(tokens)} of them, so no alignment against '
            f'`completion_probabilities` can be trusted')

    groups, at = [], 0
    for entry in entries:
        start = at
        while at < len(tokens) and tokens[at] != entry['id']:
            at += 1
        if at == len(tokens):
            raise Incomplete(
                f'token {entry["id"]} heads no group in the sampled sequence: '
                f'entry {len(groups)} of {len(entries)} cannot be aligned, and '
                f'an unverified alignment mislabels everything after it')
        at += 1
        groups.append(tokens[start:at])
    return groups, tokens[at:]


def _is_json(response) -> bool:
    return response.headers.get('content-type', '').startswith('application/json')


def _reason(payload: dict, settings: dict) -> str:
    """Which wall the generation hit.

    `stop_type: limit` covers both "produced everything asked for" and "ran out
    of context", so the roadmap calls for deriving the difference. The cheapest
    derivation is not the arithmetic it suggests: if nothing stopped it and it
    produced fewer tokens than requested, context exhaustion is the only thing
    left that could have.

    The derivation was unreachable until it was tested. `truncated` in the
    response does not mean the prompt was cut -- it means *generation* hit the
    context wall, which is this exact case, and it was being raised on. So
    every context exhaustion became a fatal error and `CONTEXT` was never once
    recorded. Measured against llama.cpp b10221 at `--ctx-size 512`, with a
    385-token prompt: asking for 512 tokens yields 127 and `truncated: true`,
    asking for 120 yields 120 and `truncated: false`, and the boundary sits
    exactly where prompt + predicted reaches `n_ctx`.

    The flag and the derivation agreed in every case measured. The derivation
    is what is used, because it needs nothing from the server beyond the counts
    that any completions endpoint reports.
    """
    stop_type = payload.get('stop_type')
    if stop_type == 'eos':
        return EOS
    if stop_type == 'word':
        return STOP
    if stop_type == 'limit':
        produced = payload.get('tokens_predicted', 0)
        return LENGTH if produced >= settings['length'] else CONTEXT
    return ABORTED
