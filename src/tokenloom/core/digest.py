"""The digest a stamp carries, transcribed from `docs/CORE.md`'s *What the digest is*.

The encoding is part of the format rather than this implementation's business, so it is
written against the document's words and not against what is convenient here: a digest two
implementations compute differently names nothing.

**What is covered is what is there and not what this knows of.** The tables and columns come
off the store, so a tree carrying a column this version predates is still digested whole and
two implementations reading one tree agree. What comes from the document is the *order* --
which tables go first, and which key each is walked in -- because that is the part a file
cannot answer and two implementations would otherwise answer differently.
"""

from __future__ import annotations

import hashlib
import sqlite3
import struct

#: The key each table's rows are walked in, in the order `docs/CORE.md`'s *On disk* declares the
#: tables. `stamps` is absent: a stamp cannot attest itself, and that is the only exception.
KEYS: dict[str, tuple[str, ...]] = {
    "vocab": ("token_id",),
    "sources": ("id",),
    "nodes": ("id",),
    "edges": ("node", "source", "token_id"),
    "params": ("id",),
    "acts": ("id",),
}

NULL = b""  #: A null contributes nothing, and neither does its column's name.
INTEGER, REAL, TEXT, BLOB, ROW = b"\x01", b"\x02", b"\x03", b"\x04", b"\x05"


def frame(value) -> bytes:
    """One value, tagged by type and framed so that no two values write one byte string.

    Lengths are counted so that text cannot run into what follows it, and a real is its
    IEEE-754 bits rather than any rendering of them -- the one place a decimal would make two
    equal trees differ, or two different ones agree, depending on how it rounded.
    """
    if value is None:
        return NULL
    if isinstance(value, bool):  # before int: SQLite has no bool, so one here is a bug
        raise TypeError("a bool is not a value this format stores")
    if isinstance(value, int):
        return INTEGER + value.to_bytes(8, "big", signed=True)
    if isinstance(value, float):
        return REAL + struct.pack(">d", value)
    if isinstance(value, str):
        data = value.encode("utf-8")
        return TEXT + len(data).to_bytes(8, "big") + data
    if isinstance(value, bytes | memoryview):
        data = bytes(value)
        return BLOB + len(data).to_bytes(8, "big") + data
    raise TypeError(f"no framing for {type(value).__name__}")


def of(conn: sqlite3.Connection) -> str:
    """The digest of everything this store observed. 64 lowercase hex characters.

    One pass per table and no sort beyond the key's own index. The column names are framed
    once per table rather than once per value, and rows are accumulated into a buffer that is
    handed to the hash in blocks -- which is most of the cost, since the hashing itself is a
    fraction of walking the rows in Python.
    """
    out = hashlib.blake2b(digest_size=32)
    buffer = bytearray()
    for table in _tables(conn):
        columns = [r[1] for r in conn.execute(f"PRAGMA table_info({table})")]
        key = KEYS.get(table) or _key(conn, table) or columns
        # A table with no rows contributes nothing, not even its name, so the name is written
        # only once a row has been seen. A table absent altogether is that same nothing: an
        # older tree simply lacks it, which is not a change anything may turn on.
        named = False
        rows = conn.execute(
            f"SELECT {', '.join(columns)} FROM {table} ORDER BY {', '.join(key)}"
        )
        framed = [frame(name) for name in columns]
        for row in rows:
            if not named:
                buffer += frame(table)
                named = True
            buffer += ROW
            for name, value in zip(framed, row, strict=True):
                if value is None:
                    continue
                buffer += name
                buffer += frame(value)
            if len(buffer) > 1 << 20:
                out.update(buffer)
                buffer.clear()
    out.update(buffer)
    return out.hexdigest()


def _tables(conn: sqlite3.Connection) -> list[str]:
    """Every table the store holds but `stamps`: the ones the format names first, in the order
    *On disk* declares them, then anything else by name so that two readers agree on where it
    went."""
    held = {
        r[0]
        for r in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
        if not r[0].startswith("sqlite_") and r[0] != "stamps"
    }
    named = [table for table in KEYS if table in held]
    return named + sorted(held - set(named))


def _key(conn: sqlite3.Connection, table: str) -> list[str]:
    """A table this format does not name is walked in its own primary key order. Empty where
    it declares none, and the caller then falls back to every column, which is an order and
    is all that is needed of it."""
    pk = [(r[5], r[1]) for r in conn.execute(f"PRAGMA table_info({table})") if r[5]]
    return [name for _, name in sorted(pk)]
