"""The value types the core passes around, and the adapter surface it calls.

`docs/ADAPTER.md` states three operations for one vocabulary. The core knows nothing else
about a backend: `create` needs `tokenize`, every stored id needs `bytes_for`, and only
`generate` calls a model.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass(frozen=True, slots=True)
class Source:
    """Who produced a node. The empty name is the unnamed user and belongs to nothing else."""

    kind: str  # 'user' | 'model'
    name: str = ""

    def __post_init__(self) -> None:
        if self.kind not in ("user", "model"):
            raise ValueError(f"source kind must be 'user' or 'model', not {self.kind!r}")
        # INV-SOURCE-NAMED, refused at the door rather than caught by the checker.
        if self.kind == "model" and not self.name:
            raise ValueError("a model source must be named")

    def __str__(self) -> str:
        return f"{self.kind}:{self.name}" if self.name else self.kind


USER = Source("user", "")


@dataclass(frozen=True, slots=True)
class Token:
    """An id together with the bytes it spells. The bytes are the vocabulary's answer."""

    id: int
    bytes: bytes


@dataclass(frozen=True, slots=True)
class Ranked:
    """One alternative at a position, as the source presented it."""

    token_id: int
    logprob: float


@dataclass(frozen=True, slots=True)
class Position:
    """One drawn token, and what else was ranked where it was drawn.

    `ranking` is `None` for a declination -- a position the backend could give no
    distribution for. The core records that as an absent ranked edge and never as an
    estimate, so `None` and an empty tuple are not the same thing and the empty tuple is
    not legal.
    """

    token_id: int
    ranking: tuple[Ranked, ...] | None

    def __post_init__(self) -> None:
        if self.ranking is not None and not self.ranking:
            raise ValueError("an empty ranking is not a declination; pass None")


@dataclass(frozen=True, slots=True)
class Generation:
    """What a `generate` came back with: what was drawn, and how it ended.

    A refusal is this object with terminator `refused` and no positions -- the adapter's
    answer arrives on the same path as a model's, which is what lets the core write the
    terminator in one place.
    """

    terminator: str
    positions: tuple[Position, ...] = ()
    reason: str | None = None  # the adapter's word to its caller; the core stores none of it


@runtime_checkable
class Vocabulary(Protocol):
    """What `create` needs, and what every stored id is spelled by. No model is called."""

    @property
    def name(self) -> str:
        """Names the vocabulary a tree is in. Advisory; the `vocab` table is what enforces."""

    def tokenize(self, text: bytes, *, special: bool = False) -> list[Token]:
        """The ids that spell those bytes, in order, each with its own bytes.

        `special` selects the second reading of a control token's literal spelling. It is
        never the default: authored text is plain bytes, and a user who quotes
        `<|endoftext|>` does not inject it.
        """

    def bytes_for(self, token_id: int) -> bytes:
        """What that id spells, exactly. The vocabulary's answer, never an occurrence's."""


@runtime_checkable
class Adapter(Vocabulary, Protocol):
    """A vocabulary that can also be asked to generate."""

    @property
    def source(self) -> Source:
        """The model whose draws these are. Must separate anything that must not merge."""

    def generate(self, ids: list[int], params: dict, seed: int) -> Generation:
        """Draw from the path `ids`, or refuse. Met or refused, never adjusted."""

    def will_evaluate(self, ids: list[int]) -> bool:
        """Whether the backend would accept this path. Asking is not declining: this
        writes nothing, stands in for no refusal, and the real request still goes through
        `generate`. Its shape is unsettled in `docs/ADAPTER.md`; this is the first draw."""
