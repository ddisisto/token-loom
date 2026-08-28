"""The vocabulary, read from the GGUF.

**The server has no route to per-token bytes.** `/detokenize` answers a fragment id with
the replacement character rather than the bytes, and it does so with HTTP 200 -- the
response is lossy rather than an error, which is exactly the shape of fault that produces
a record that is quietly wrong. `docs/SERVER.md` records the measurement.

So bytes come from `tokenizer.ggml.tokens` in the model file, which holds every entry in
byte-level BPE encoding. Applying the GPT-2 byte decoder gives real bytes for every id,
fragments and control tokens included, and that is obligation 2 met exactly: what the
vocabulary says, never what a generation said about an occurrence.
"""

from __future__ import annotations

import functools
import os
import struct
from pathlib import Path

#: Inflating 152064 entries out of a GGUF costs about five seconds, which is fine once and
#: not fine on every command. The cache is keyed on the model file's size and mtime, so a
#: different or rebuilt model file misses rather than answering wrongly.
CACHE_MAGIC = b"token-loom/vocab-1"


@functools.cache
def _byte_decoder() -> dict[str, int]:
    """GPT-2's byte<->unicode table, inverted.

    The printable ASCII range and two Latin-1 runs map to themselves; the remaining 68
    byte values are displaced to U+0100 upward so that every byte has a printable
    character. Inverting it turns a stored token back into the bytes it spells.
    """
    printable = (
        list(range(ord("!"), ord("~") + 1))
        + list(range(0xA1, 0xAC + 1))
        + list(range(0xAE, 0xFF + 1))
    )
    codes = list(printable)
    spare = 0
    for byte in range(256):
        if byte not in printable:
            printable.append(byte)
            codes.append(256 + spare)
            spare += 1
    return {chr(code): byte for byte, code in zip(printable, codes, strict=True)}


class GgufVocabulary:
    """Every id the model has, with the bytes it spells.

    Inflated once at construction rather than answered per call. The core is indifferent
    -- "whether an adapter answers per call or from a vocabulary it inflated once is its
    own business" -- and a local file makes the choice easy.
    """

    def __init__(self, gguf_path: str | Path, name: str, *, cache: Path | None = None) -> None:
        self.path = Path(gguf_path)
        self._name = name
        if cache is not None and (spelled := _read_cache(cache, self.path)) is not None:
            self._bytes = spelled
            return
        self._bytes = self._inflate()
        if cache is not None:
            _write_cache(cache, self.path, self._bytes)

    @classmethod
    def cached(cls, gguf_path: str | Path, name: str) -> GgufVocabulary:
        """The ordinary way in: inflate once, then load from the cache in milliseconds."""
        gguf_path = Path(gguf_path)
        root = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "token-loom"
        root.mkdir(parents=True, exist_ok=True)
        return cls(gguf_path, name, cache=root / f"{gguf_path.stem}.vocab")

    def _inflate(self) -> list[bytes]:
        from gguf import GGUFReader

        reader = GGUFReader(self.path)
        field = reader.fields.get("tokenizer.ggml.tokens")
        if field is None:
            raise ValueError(f"{self.path} carries no tokenizer.ggml.tokens")
        decoder = _byte_decoder()
        spelled: list[bytes] = []
        for index in field.data:
            encoded = bytes(field.parts[index]).decode("utf-8")
            try:
                spelled.append(bytes(decoder[char] for char in encoded))
            except KeyError as exc:  # pragma: no cover -- a vocabulary in another encoding
                raise ValueError(
                    f"id {len(spelled)} spells {encoded!r}, which is not byte-level BPE"
                ) from exc
        return spelled

    @property
    def name(self) -> str:
        return self._name

    def __len__(self) -> int:
        return len(self._bytes)

    def bytes_for(self, token_id: int) -> bytes:
        """What that id spells, exactly, for every id the adapter can emit.

        An id it cannot answer for cannot be stored at all, so this raises rather than
        returning a placeholder. There is no unknown-bytes case anywhere in this format.
        """
        try:
            return self._bytes[token_id]
        except IndexError:
            raise KeyError(f"id {token_id} is not in {self._name} ({len(self)} entries)") from None

    def spell(self, ids: list[int]) -> bytes:
        """A path's bytes, from its ids alone. This is what a reader will do."""
        return b"".join(self.bytes_for(i) for i in ids)


# ---- the cache ---------------------------------------------------------------------
#
# Count, then that many lengths, then every token's bytes end to end. One read and two
# slices; no pickle, so a corrupt or stale file is a miss rather than a hazard.


def _stamp(gguf: Path) -> bytes:
    info = gguf.stat()
    return struct.pack("<QQ", info.st_size, int(info.st_mtime_ns))


def _read_cache(cache: Path, gguf: Path) -> list[bytes] | None:
    try:
        raw = cache.read_bytes()
    except OSError:
        return None
    head = len(CACHE_MAGIC) + 16
    if len(raw) < head + 4 or raw[: len(CACHE_MAGIC)] != CACHE_MAGIC:
        return None
    if raw[len(CACHE_MAGIC) : head] != _stamp(gguf):
        return None  # a different or rebuilt model file
    (count,) = struct.unpack_from("<I", raw, head)
    widths = struct.unpack_from(f"<{count}I", raw, head + 4)
    body = memoryview(raw)[head + 4 + 4 * count :]
    out, at = [], 0
    for width in widths:
        out.append(bytes(body[at : at + width]))
        at += width
    return out if at == len(body) else None


def _write_cache(cache: Path, gguf: Path, spelled: list[bytes]) -> None:
    payload = (
        CACHE_MAGIC
        + _stamp(gguf)
        + struct.pack("<I", len(spelled))
        + struct.pack(f"<{len(spelled)}I", *(len(b) for b in spelled))
        + b"".join(spelled)
    )
    tmp = cache.with_suffix(".tmp")
    try:
        tmp.write_bytes(payload)
        tmp.replace(cache)  # atomic, so a reader never sees a half-written cache
    except OSError:
        pass  # a cache that cannot be written is not an error
