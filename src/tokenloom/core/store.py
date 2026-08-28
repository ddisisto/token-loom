"""The store: the three acts, the two state edits, and everything that writes.

Reading is `reads.py`; checking is `check.py`. What is enforced here is what the core
*rejects* -- and a rejection leaves no trace, so it must happen before anything is written.
"""

from __future__ import annotations

import fcntl
import json
import secrets
import sqlite3
from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

from . import check, reads
from .ports import Adapter, Generation, Source, Vocabulary
from .schema import (
    BULK_FILE,
    DDL,
    LOCK_FILE,
    MARKER,
    TERMINATORS,
    TERMINATORS_WITHOUT_TIP,
    TREE_FILE,
)


class StoreError(Exception):
    """The store will not do this."""


class Rejected(StoreError):
    """The core declined before writing anything. Rejection leaves no trace.

    Distinct from a refusal, which is the *adapter's* answer and is recorded as an act
    with terminator `refused`. Only a `generate` can record its own undoing.
    """


def _now() -> str:
    t = datetime.now(UTC)
    return f"{t:%Y-%m-%dT%H:%M:%S}.{t.microsecond // 1000:03d}Z"


def canonical(params: Mapping) -> str:
    """Canonical serialisation: keys sorted, no insignificant whitespace.

    Two spellings of one request intern to one row, which is the whole reason it exists.
    """
    return json.dumps(params, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


class Store:
    """One tree, in one directory.

    A reader takes no lock. A writer takes the `flock` for the whole of an act, the model
    call included, and its first write after acquiring records abandoned acts -- so
    opening a tree for writing can modify it.
    """

    def __init__(self, path: Path, conn: sqlite3.Connection, tree: dict, *, write: bool) -> None:
        self.path = path
        self.conn = conn
        self.tree = tree
        self.writable = write

    # ---- opening -------------------------------------------------------------------

    @classmethod
    def initialise(cls, path: str | Path, vocabulary: str) -> Store:
        path = Path(path)
        path.mkdir(parents=True, exist_ok=False)
        tree = {
            "marker": MARKER,
            "created": f"{datetime.now(UTC):%Y-%m-%dT%H:%M:%SZ}",
            "vocabulary": vocabulary,
        }
        (path / TREE_FILE).write_text(json.dumps(tree, indent=2) + "\n")
        (path / LOCK_FILE).touch()
        conn = _connect(path / BULK_FILE)
        conn.executescript(DDL)
        conn.commit()
        conn.close()
        return cls.open(path, write=True)

    @classmethod
    def open(cls, path: str | Path, *, write: bool = False, verify: bool = True) -> Store:
        path = Path(path)
        tree = json.loads((path / TREE_FILE).read_text())
        # A reader that does not recognise `marker` stops.
        if tree.get("marker") != MARKER:
            raise StoreError(f"unrecognised marker {tree.get('marker')!r}; this reader stops")
        store = cls(path, _connect(path / BULK_FILE), tree, write=write)
        if write:
            # A store that fails an invariant is not repaired silently: a reader reports
            # it, and a writer will not write.
            if verify:
                check.verify(store.conn)
            (path / LOCK_FILE).touch()
            with store._locked():
                pass  # acquiring is what sweeps
        return store

    def close(self) -> None:
        self.conn.close()

    def __enter__(self) -> Store:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    @property
    def vocabulary(self) -> str:
        return self.tree["vocabulary"]

    # ---- the lock ------------------------------------------------------------------

    @contextmanager
    def _locked(self) -> Iterator[None]:
        """Held for the whole of an act, the model call included. A stale lock blocks and
        nothing breaks it."""
        if not self.writable:
            raise StoreError("this store was opened for reading")
        fd = (self.path / LOCK_FILE).open("a+")
        try:
            fcntl.flock(fd.fileno(), fcntl.LOCK_EX)
            self._sweep()
            yield
        finally:
            fcntl.flock(fd.fileno(), fcntl.LOCK_UN)
            fd.close()

    @contextmanager
    def _writing(self) -> Iterator[None]:
        """One transaction. Anything that raises leaves the store as it was."""
        try:
            yield
            self.conn.commit()
        except BaseException:
            self.conn.rollback()
            raise

    def _sweep(self) -> None:
        """Record abandoned acts. Acquiring the lock means no other writer is live, so
        every generation still in flight is one whose writer is gone."""
        with self._writing():
            self.conn.execute(
                "UPDATE acts SET terminator = 'aborted' "
                "WHERE op = 'generate' AND terminator IS NULL"
            )

    # ---- interning -----------------------------------------------------------------

    def find_source(self, source: Source) -> int | None:
        row = self.conn.execute(
            "SELECT id FROM sources WHERE kind = ? AND name = ?", (source.kind, source.name)
        ).fetchone()
        return row[0] if row else None

    def source_id(self, source: Source) -> int:
        found = self.find_source(source)
        if found is not None:
            return found
        return self.conn.execute(
            "INSERT INTO sources (kind, name) VALUES (?, ?)", (source.kind, source.name)
        ).lastrowid

    def params_id(self, params: Mapping) -> int:
        text = canonical(params)
        row = self.conn.execute("SELECT id FROM params WHERE json = ?", (text,)).fetchone()
        if row:
            return row[0]
        return self.conn.execute("INSERT INTO params (json) VALUES (?)", (text,)).lastrowid

    def put_token(self, token_id: int, data: bytes) -> None:
        """`vocab` writes verify.

        An id already present must spell what the vocabulary says now, or the write fails.
        This is the only check that reaches outside the store, and it catches a store
        opened against the wrong vocabulary at the first id the two disagree on.
        """
        row = self.conn.execute(
            "SELECT bytes FROM vocab WHERE token_id = ?", (token_id,)
        ).fetchone()
        if row is None:
            self.conn.execute(
                "INSERT INTO vocab (token_id, bytes) VALUES (?, ?)", (token_id, data)
            )
        elif bytes(row[0]) != data:
            raise StoreError(
                f"vocabulary disagrees at id {token_id}: store has {bytes(row[0])!r}, "
                f"vocabulary says {data!r}"
            )

    # ---- nodes ---------------------------------------------------------------------

    def _merge_node(self, parent: int | None, token_id: int, source_id: int) -> int:
        """Merging is checked, not assumed: looked up by the merge key first, reused if
        it exists. Roots are exempt -- the merge key does not reach them."""
        if parent is not None:
            row = self.conn.execute(
                "SELECT id FROM nodes WHERE parent = ? AND token_id = ? AND source = ?",
                (parent, token_id, source_id),
            ).fetchone()
            if row:
                return row[0]
        return self.conn.execute(
            "INSERT INTO nodes (parent, token_id, source) VALUES (?, ?, ?)",
            (parent, token_id, source_id),
        ).lastrowid

    def _extend_ranking(self, node: int, source_id: int, ranking: Sequence) -> None:
        """A ranking extends and is never truncated or rewritten.

        Only tokens not already recorded are contributed, appended at continuing ranks.
        Rows already present keep their values, so anything derived from a ranking -- a
        node's logprob above all -- never changes retroactively. It follows that rank
        means the k-th alternative recorded here, not the model's k-th choice: a token
        that would outrank a stored one is appended below it regardless.
        """
        rows = self.conn.execute(
            "SELECT rank, token_id FROM edges WHERE node = ? AND source = ?", (node, source_id)
        ).fetchall()
        seen = {token_id for _, token_id in rows}
        next_rank = max((rank for rank, _ in rows), default=-1) + 1
        for ranked in ranking:
            if ranked.token_id in seen:
                continue
            seen.add(ranked.token_id)
            self.conn.execute(
                "INSERT INTO edges (node, source, rank, token_id, logprob) VALUES (?, ?, ?, ?, ?)",
                (node, source_id, next_rank, ranked.token_id, ranked.logprob),
            )
            next_rank += 1

    def _require_live(self, node: int | None) -> None:
        """Liveness constrains where an act starts, not what it produces."""
        if node is None:
            return
        if not reads.node_exists(self.conn, node):
            raise Rejected(f"no node {node}")
        if not reads.is_live(self.conn, node):
            raise Rejected(f"node {node} is not live; an act begins at a live node")

    # ---- the acts ------------------------------------------------------------------

    def create(
        self,
        at: int | None,
        text: bytes | str,
        *,
        vocabulary: Vocabulary,
        source: Source,
        special: bool = False,
    ) -> int:
        """Bytes in, tokens out. One act, and nodes for the tokens.

        The text is tokenised, the resulting nodes are reassembled exactly as a derived
        read will reassemble them, and the result is compared against what was authored.
        A mismatch rejects the act -- and so does a `create` that would add no tokens.
        """
        if isinstance(text, str):
            text = text.encode("utf-8")
        try:
            text.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise Rejected(f"authored bytes must be valid UTF-8: {exc}") from exc
        if not text:
            raise Rejected("a create that would add no tokens is rejected")

        tokens = vocabulary.tokenize(text, special=special)
        if not tokens:
            raise Rejected("a create that would add no tokens is rejected")
        # Reassembled from the vocabulary, never from the tokeniser's own report of an
        # occurrence -- the reassembly is what a reader will do, so it is the thing that
        # has to hold.
        spelled = [vocabulary.bytes_for(t.id) for t in tokens]
        if b"".join(spelled) != text:
            raise Rejected(
                f"round trip does not hold: {text!r} tokenises to "
                f"{[t.id for t in tokens]}, which spells {b''.join(spelled)!r}"
            )

        with self._locked(), self._writing():
            self._require_live(at)
            source_id = self.source_id(source)
            cur = at
            for token, data in zip(tokens, spelled, strict=True):
                self.put_token(token.id, data)
                cur = self._merge_node(cur, token.id, source_id)
            return self._write_act("create", source_id, origin=at, tip=cur)

    def realise(self, node: int, source: Source, rank: int, *, actor: Source) -> int:
        """The ranked edge at `(node, source, rank)`, taken. One write and no call.

        The act's source is who acted; the node carries the source of the model that
        ranked the edge, which is why the act needs no column for the edge's source.
        """
        with self._locked(), self._writing():
            self._require_live(node)
            edge_source = self.find_source(source)
            if edge_source is None:
                raise Rejected(f"no source {source} in this store")
            row = self.conn.execute(
                "SELECT token_id FROM edges WHERE node = ? AND source = ? AND rank = ?",
                (node, edge_source, rank),
            ).fetchone()
            if row is None:
                raise Rejected(f"no ranked edge at node {node}, source {source}, rank {rank}")
            tip = self._merge_node(node, row[0], edge_source)
            return self._write_act(
                "realise", self.source_id(actor), origin=node, tip=tip, rank=rank
            )

    def generate(
        self,
        at: int | None,
        params: Mapping,
        *,
        adapter: Adapter,
        seed: int | None = None,
    ) -> tuple[int, Generation]:
        """Two writes, and the model call between them.

        The act, its parameters and its seed are committed *before* the model is called,
        so no node can ever belong to an act the store has not heard of, and an act with
        no terminator is a generation in flight. The nodes, the ranked edges and the
        terminator land in the second write -- and a refusal comes back on the same path
        as an answer, into that same second write.
        """
        length = params.get("length")
        if not isinstance(length, int) or isinstance(length, bool) or length <= 0:
            raise Rejected(f"`length` must be a positive integer, not {length!r}")
        params = dict(params)
        if seed is None:
            # Conservatively inside every plausible backend's range, so the core never
            # mints a seed a backend would read as a sentinel.
            seed = secrets.randbelow(2**31)

        with self._locked():
            with self._writing():
                self._require_live(at)
                source_id = self.source_id(adapter.source)
                ids = reads.path_token_ids(self.conn, at) if at is not None else []
                act = self._write_act(
                    "generate", source_id, origin=at, tip=None,
                    params=self.params_id(params), seed=seed,
                )
            # provenance is committed; the transaction is closed across the model call

            try:
                answer = adapter.generate(ids, params, seed)
            except BaseException:
                with self._writing():
                    self.conn.execute(
                        "UPDATE acts SET terminator = 'failed' WHERE id = ?", (act,)
                    )
                raise

            with self._writing():
                self._land(act, answer, at, source_id, length, adapter)
        return act, answer

    def _land(
        self,
        act: int,
        answer: Generation,
        at: int | None,
        source_id: int,
        length: int,
        vocabulary: Vocabulary,
    ) -> None:
        """The second write: nodes, ranked edges, tip and terminator."""
        if answer.terminator not in TERMINATORS:
            raise StoreError(f"unknown terminator {answer.terminator!r}")
        if answer.terminator in TERMINATORS_WITHOUT_TIP and answer.positions:
            raise StoreError(
                f"a {answer.terminator} generation wrote nothing but reported "
                f"{len(answer.positions)} tokens"
            )
        if answer.terminator in ("eos", "limit") and not answer.positions:
            raise StoreError(f"terminator {answer.terminator!r} always names a tip")
        if len(answer.positions) > length:
            raise StoreError(
                f"generation drew {len(answer.positions)} tokens for a length of {length}"
            )
        if answer.terminator == "limit" and len(answer.positions) != length:
            raise StoreError(
                "terminator `limit` means it drew the requested length; "
                f"drew {len(answer.positions)} of {length}"
            )

        cur = at
        for position in answer.positions:
            # A ranking belongs to the node the position was computed at -- the one the
            # previous token landed on. A root-beginning generation has no such node for
            # position 0, and that distribution has nowhere in this format to go.
            if position.ranking is not None and cur is not None:
                for ranked in position.ranking:
                    self.put_token(ranked.token_id, vocabulary.bytes_for(ranked.token_id))
                self._extend_ranking(cur, source_id, position.ranking)
            self.put_token(position.token_id, vocabulary.bytes_for(position.token_id))
            cur = self._merge_node(cur, position.token_id, source_id)
        self.conn.execute(
            "UPDATE acts SET tip = ?, terminator = ? WHERE id = ?",
            (cur if answer.positions else None, answer.terminator, act),
        )

    # ---- state edits ---------------------------------------------------------------

    def delete(self, node: int) -> None:
        """One write, on that node alone. Descendants are untouched; liveness is derived
        by walking the ancestry. Deleting what is already effectively deleted is legal,
        and is what makes undelete work. Not an act, and not recorded in `acts`."""
        self._set_deleted(node, 1)

    def undelete(self, node: int) -> None:
        """Clears it. Live again only if its ancestry is. Not an act."""
        self._set_deleted(node, None)

    def _set_deleted(self, node: int, value: int | None) -> None:
        with self._locked(), self._writing():
            if not reads.node_exists(self.conn, node):
                raise Rejected(f"no node {node}")
            self.conn.execute("UPDATE nodes SET deleted = ? WHERE id = ?", (value, node))

    # ---- acts ----------------------------------------------------------------------

    def _write_act(
        self,
        op: str,
        source_id: int,
        *,
        origin: int | None,
        tip: int | None,
        params: int | None = None,
        seed: int | None = None,
        rank: int | None = None,
        terminator: str | None = None,
    ) -> int:
        return self.conn.execute(
            "INSERT INTO acts (op, source, origin, tip, created, params, seed, terminator, rank) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (op, source_id, origin, tip, _now(), params, seed, terminator, rank),
        ).lastrowid


def _connect(db: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db)
    conn.execute("PRAGMA journal_mode = WAL")  # a reader takes no lock and is not blocked
    conn.execute("PRAGMA synchronous = FULL")
    return conn
