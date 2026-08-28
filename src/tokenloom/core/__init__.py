"""The core: the tree, and nothing about any backend.

`docs/CORE.md` is what this implements and it is locked. Nothing in here names a backend,
and no backend's limitation is a rule in here.
"""

from .check import Corrupt, Violation, verify, violations
from .ports import USER, Adapter, Generation, Position, Ranked, Source, Token, Vocabulary
from .schema import MARKER, OPS, TERMINATORS
from .store import Rejected, Store, StoreError, canonical

__all__ = [
    "MARKER",
    "OPS",
    "TERMINATORS",
    "USER",
    "Adapter",
    "Corrupt",
    "Generation",
    "Position",
    "Ranked",
    "Rejected",
    "Source",
    "Store",
    "StoreError",
    "Token",
    "Violation",
    "Vocabulary",
    "canonical",
    "violations",
    "verify",
]
