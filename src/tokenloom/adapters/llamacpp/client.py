"""A thin client over llama.cpp's **native** `/completion` endpoint.

Not the OpenAI-compatible one: both return an identical token payload, and the native one
adds `stop_type`, which separates `eos` from `limit` where the compatible layer flattens
both into `finish_reason: stop`.

Nothing here interprets. Repair belongs in `adapter.py`, so that what this returns is what
the server said and the difference between the two is legible.
"""

from __future__ import annotations

from dataclasses import dataclass

import httpx


class ServerError(Exception):
    """The server answered, and it was not an answer."""

    def __init__(self, status: int, body: str) -> None:
        super().__init__(f"HTTP {status}: {body[:300]}")
        self.status = status
        self.body = body


@dataclass(frozen=True, slots=True)
class Props:
    n_ctx: int
    model_alias: str
    model_path: str


class LlamaCppClient:
    def __init__(self, base_url: str = "http://localhost:8081", timeout: float = 600.0) -> None:
        self.base_url = base_url.rstrip("/")
        self._http = httpx.Client(base_url=self.base_url, timeout=timeout)

    def close(self) -> None:
        self._http.close()

    def _post(self, path: str, payload: dict) -> dict:
        response = self._http.post(path, json=payload)
        if response.status_code != 200:
            raise ServerError(response.status_code, response.text)
        return response.json()

    def props(self) -> Props:
        data = self._http.get("/props").json()
        return Props(
            n_ctx=data["default_generation_settings"]["n_ctx"],
            model_alias=data.get("model_alias", ""),
            model_path=data.get("model_path", ""),
        )

    def tokenize(self, text: str, *, special: bool) -> list[dict]:
        """`/tokenize` with `with_pieces`, which returns per-token bytes exactly.

        A piece comes back as a JSON string when it decodes and a JSON *array of ints*
        when it does not, so authored text tokenises into ids carrying real bytes even
        where a token is a fragment of a character.

        `parse_special` selects the reading: `<|endoftext|>` as one id, or as the ordinary
        tokens that spell those thirteen characters. Both spell the same bytes.
        """
        return self._post(
            "/tokenize", {"content": text, "with_pieces": True, "parse_special": special}
        )["tokens"]

    def completion(self, ids: list[int], payload: dict) -> dict:
        """A prompt as an array of token ids, evaluated verbatim.

        The server does not re-tokenise an id array -- the same text as two different id
        sequences gives two different continuations -- which is what makes replay the
        path this format can take.

        `return_tokens` is not optional here: `completion_probabilities` is that sequence
        regrouped onto character boundaries, and `tokens` is the real one.
        """
        return self._post(
            "/completion",
            {"prompt": ids, "return_tokens": True, "stream": False, **payload},
        )
