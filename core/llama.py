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
    """The server silently cut the prompt to fit its context.

    Fatal rather than a warning. The span's `slice_start` would claim bytes the
    model never saw, which makes the record a lie in exactly the way immutable
    bytes exist to prevent -- and the recorded conditions are the whole product.
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
            'cache_prompt': True,
        }
        r = requests.post(f'{self.base}/completion', json=body,
                          timeout=self.timeout)
        r.raise_for_status()
        return self._read(r.json(), settings)

    @staticmethod
    def _read(payload: dict, settings: dict) -> Result:
        if payload.get('truncated'):
            raise Truncated(
                f"the server truncated a prompt of "
                f"{payload.get('tokens_evaluated')} tokens; the recorded slice "
                f"would not be what the model saw")

        entries = payload.get('completion_probabilities') or []
        tokens = [Token(i, e['id'], bytes(e['bytes']), e['logprob'])
                  for i, e in enumerate(entries)]
        counterfactuals = [
            Counterfactual(i, rank, c['id'], bytes(c['bytes']), c['logprob'])
            for i, e in enumerate(entries)
            for rank, c in enumerate(e.get('top_logprobs') or [])]

        return Result(tokens, counterfactuals,
                      _reason(payload, settings), payload.get('tokens_evaluated', 0))


def _reason(payload: dict, settings: dict) -> str:
    """Which wall the generation hit.

    `stop_type: limit` covers both "produced everything asked for" and "ran out
    of context", so the roadmap calls for deriving the difference. The cheapest
    derivation is not the arithmetic it suggests: if nothing stopped it and it
    produced fewer tokens than requested, context exhaustion is the only thing
    left that could have.
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
