"""The bulk store: per-span, per-token records, in sqlite.

Generic over record type by construction -- a new kind of per-span record is a
new table here, not a new mechanism. Tokens are its first tenant, not its
definition, and embeddings are the concrete case that made this a constraint
rather than a preference (see `BEYOND-MVP.md`).

Two properties the rest of the core leans on:

- **Append-only.** Delete is soft and never reaches here; a deleted subtree
  keeps its rows. Reclaiming them is a vacuum, deferred, and constrained.
- **The terminator is the done-signal.** A span with no terminator row is in
  flight. Nothing else records termination, so there is no second value to
  disagree with and no window where the two differ.
"""
from __future__ import annotations

import sqlite3
from typing import Iterable, NamedTuple

from util.util import timestamp

# why a span stopped. `aborted` is what a process that died leaves behind, and
# is applied at load rather than written by the generation that failed.
LENGTH = 'length'
STOP = 'stop'
CONTEXT = 'context'
ABORTED = 'aborted'
REASONS = (LENGTH, STOP, CONTEXT, ABORTED)

SCHEMA = [
    """CREATE TABLE IF NOT EXISTS tokens (
         span TEXT NOT NULL, idx INTEGER NOT NULL,
         token_id INTEGER, bytes BLOB NOT NULL, logprob REAL,
         PRIMARY KEY (span, idx)
       ) WITHOUT ROWID""",
    """CREATE TABLE IF NOT EXISTS counterfactuals (
         span TEXT NOT NULL, idx INTEGER NOT NULL, rank INTEGER NOT NULL,
         token_id INTEGER, bytes BLOB NOT NULL, logprob REAL,
         PRIMARY KEY (span, idx, rank)
       ) WITHOUT ROWID""",
    """CREATE TABLE IF NOT EXISTS terminators (
         span TEXT PRIMARY KEY, reason TEXT NOT NULL, written TEXT NOT NULL
       ) WITHOUT ROWID""",
]


class Token(NamedTuple):
    idx: int
    token_id: int | None
    bytes: bytes
    logprob: float | None


class Counterfactual(NamedTuple):
    idx: int
    rank: int
    token_id: int | None
    bytes: bytes
    logprob: float | None


class BulkStore:
    def __init__(self, path: str):
        self.path = path
        self.db = sqlite3.connect(path)
        self.db.execute('PRAGMA journal_mode=WAL')
        self.db.execute('PRAGMA synchronous=NORMAL')
        for statement in SCHEMA:
            self.db.execute(statement)
        self.db.commit()

    def close(self) -> None:
        self.db.close()

    def __enter__(self) -> BulkStore:
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    # -- tokens ----------------------------------------------------------

    def add_tokens(self, span: str, tokens: Iterable[Token]) -> None:
        self.db.executemany(
            'INSERT OR REPLACE INTO tokens VALUES (?, ?, ?, ?, ?)',
            [(span, t.idx, t.token_id, t.bytes, t.logprob) for t in tokens])
        self.db.commit()

    def tokens(self, span: str) -> list[Token]:
        rows = self.db.execute(
            'SELECT idx, token_id, bytes, logprob FROM tokens '
            'WHERE span = ? ORDER BY idx', (span,))
        return [Token(*row) for row in rows]

    def spans_with_tokens(self) -> set[str]:
        return {row[0] for row in self.db.execute('SELECT DISTINCT span FROM tokens')}

    # -- counterfactuals -------------------------------------------------

    def add_counterfactuals(self, span: str, cfs: Iterable[Counterfactual]) -> None:
        self.db.executemany(
            'INSERT OR REPLACE INTO counterfactuals VALUES (?, ?, ?, ?, ?, ?)',
            [(span, c.idx, c.rank, c.token_id, c.bytes, c.logprob) for c in cfs])
        self.db.commit()

    def counterfactuals(self, span: str, idx: int | None = None
                        ) -> list[Counterfactual]:
        if idx is None:
            rows = self.db.execute(
                'SELECT idx, rank, token_id, bytes, logprob FROM counterfactuals '
                'WHERE span = ? ORDER BY idx, rank', (span,))
        else:
            rows = self.db.execute(
                'SELECT idx, rank, token_id, bytes, logprob FROM counterfactuals '
                'WHERE span = ? AND idx = ? ORDER BY rank', (span, idx))
        return [Counterfactual(*row) for row in rows]

    # -- terminators -----------------------------------------------------

    def set_terminator(self, span: str, reason: str) -> None:
        if reason not in REASONS:
            raise ValueError(f'unknown termination reason {reason!r}')
        self.db.execute('INSERT OR REPLACE INTO terminators VALUES (?, ?, ?)',
                        (span, reason, timestamp()))
        self.db.commit()

    def terminator(self, span: str) -> str | None:
        row = self.db.execute(
            'SELECT reason FROM terminators WHERE span = ?', (span,)).fetchone()
        return row[0] if row else None

    def terminated(self) -> set[str]:
        return {row[0] for row in self.db.execute('SELECT span FROM terminators')}


def spelled(tokens: Iterable[Token]) -> bytes:
    """The bytes a span's token rows spell out -- its text, by definition.

    Bytes rather than a decoded string on purpose. This is what a span's `text`
    is checked against and what recovery rebuilds it from, and both have to be
    exact: byte-level BPE can emit a token that is half a UTF-8 character, so
    decoding here would move a question about serialisation into the middle of
    the core. It belongs at the edge, and lives in `Span.to_json`.
    """
    return b''.join(t.bytes for t in tokens)
