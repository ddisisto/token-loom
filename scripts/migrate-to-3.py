#!/usr/bin/env python3
"""Move a tree from `token-loom/nodes-2` to `token-loom/3`.

    uv run python scripts/migrate-to-3.py data/continuations [...]
    uv run python scripts/migrate-to-3.py --dry-run data/logozoa

One marker to the next, once, so that nothing in this project carries the old one. What
changes on disk is two columns removed -- `edges.rank` and `acts.rank` -- and the marker in
`tree.json`. Everything else is copied across unchanged.

**Nothing is recovered.** A node whose covering edge was never written stays uncovered: what
a draw past the recording bounds was worth was discarded when the generation landed, and no
reading of the rows can put it back. The count is reported so that a tree says how much of
itself predates obligation 7.

The new database is built from `schema.py`'s DDL rather than altered in place, which is what
makes it exactly the schema this reader writes -- an `ALTER TABLE` would leave the old
PRIMARY KEY behind and nothing would say so. The original is kept beside the new one as
`bulk.sqlite.nodes-2` until it is deleted by hand.
"""

from __future__ import annotations

import argparse
import fcntl
import json
import shutil
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from tokenloom.core import Store  # noqa: E402
from tokenloom.core.check import violations  # noqa: E402
from tokenloom.core.schema import BULK_FILE, DDL, LOCK_FILE, MARKER, TREE_FILE  # noqa: E402

WAS = "token-loom/nodes-2"
KEPT = BULK_FILE + ".nodes-2"

#: Every table, with the columns the new schema keeps, named rather than starred so that a
#: column arriving on either side is a failure here and not a silent reordering.
COPY = {
    "vocab": "token_id, bytes",
    "sources": "id, kind, name",
    "nodes": "id, parent, token_id, source, deleted",
    "edges": "node, source, token_id, logprob",
    "params": "id, json",
    "acts": "id, op, actor, origin, tip, created, model, params, terminator",
}


def claim(path: Path):
    """The store's own claim, taken the same way: one `flock`, without blocking, so a tree
    a writer still holds is refused rather than migrated underneath them."""
    (path / LOCK_FILE).touch()
    fd = (path / LOCK_FILE).open("a+b")
    try:
        fcntl.flock(fd.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        fd.close()
        raise SystemExit(f"{path}: another writer holds this tree") from None
    return fd


def uncovered(conn: sqlite3.Connection) -> int:
    """Nodes a model produced with no covering edge at their parent.

    Counted before and after, and it has to be the same number: the migration moves rows and
    recovers none. Only model-sourced nodes, since an authored token was never drawn and its
    absence from a ranking is the ordinary case rather than a shortfall.
    """
    return conn.execute(
        """
        SELECT COUNT(*) FROM nodes n
          JOIN sources s ON s.id = n.source AND s.kind = 'model'
          LEFT JOIN edges e
            ON e.node = n.parent AND e.source = n.source AND e.token_id = n.token_id
         WHERE n.parent IS NOT NULL AND e.node IS NULL
        """
    ).fetchone()[0]


def report(path: Path, conn: sqlite3.Connection) -> tuple[dict[str, int], int]:
    """What is there, said once, so a dry run and a real one say the same thing."""
    counts = {table: conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
              for table in COPY}
    short = uncovered(conn)
    print(f"{path}: " + ", ".join(f"{n} {t}" for t, n in counts.items()))
    if short:
        print(f"{path}: {short} nodes have no covering edge, and stay that way")
    return counts, short


def migrate(path: Path, dry_run: bool) -> int:
    tree = json.loads((path / TREE_FILE).read_text())
    if tree.get("marker") == MARKER:
        print(f"{path}: already {MARKER}")
        return 0
    if tree.get("marker") != WAS:
        print(f"{path}: marker {tree.get('marker')!r} is not {WAS!r}; not touching it")
        return 1

    if dry_run:
        # No claim: reading takes none, and a tree someone is serving should still be able
        # to say what a migration would find in it.
        old = sqlite3.connect(f"file:{path / BULK_FILE}?mode=ro", uri=True)
        report(path, old)
        old.close()
        return 0

    held = claim(path)
    try:
        old = sqlite3.connect(path / BULK_FILE)
        # Folded into the database and the sidecar removed, before anything is moved. The
        # swap moves one file, so a `-wal` left beside it would be read by the *new*
        # database under the same name -- and deleting it instead would take content the
        # kept copy still needs. Checkpointing is the only move that loses neither.
        old.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        before, short = report(path, old)
        old.close()

        fresh = path / (BULK_FILE + ".new")
        fresh.unlink(missing_ok=True)
        conn = sqlite3.connect(fresh)
        conn.execute("PRAGMA journal_mode = WAL")
        conn.executescript(DDL)
        conn.execute("ATTACH DATABASE ? AS was", (str(path / BULK_FILE),))
        for table, columns in COPY.items():
            conn.execute(f"INSERT INTO {table} ({columns}) SELECT {columns} FROM was.{table}")
        after = {table: conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                 for table in COPY}
        conn.commit()
        conn.execute("DETACH DATABASE was")

        if after != before:
            conn.close()
            fresh.unlink()
            raise SystemExit(f"{path}: row counts changed {before} -> {after}; nothing written")
        if uncovered(conn) != short:
            conn.close()
            fresh.unlink()
            raise SystemExit(f"{path}: coverage moved; nothing written")
        bad = violations(conn)
        conn.close()
        if bad:
            fresh.unlink()
            raise SystemExit(f"{path}: the migrated store fails {bad[0]}; nothing written")

        # The old database is moved rather than removed: the swap is the point of no return
        # and it should leave something to go back to.
        for stray in (f"{BULK_FILE}-wal", f"{BULK_FILE}-shm"):
            if (path / stray).exists():
                raise SystemExit(f"{path}: {stray} survived the checkpoint; nothing written")
        shutil.move(path / BULK_FILE, path / KEPT)
        shutil.move(fresh, path / BULK_FILE)
        tree["marker"] = MARKER
        (path / TREE_FILE).write_text(json.dumps(tree, indent=2) + "\n")
    finally:
        fcntl.flock(held.fileno(), fcntl.LOCK_UN)
        held.close()

    # Opened for writing, which verifies, so the tree is checked by the reader that will use
    # it and not only by the checker this script called.
    Store.open(path, write=True).close()
    print(f"{path}: now {MARKER}; the old database is {KEPT}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="migrate-to-3.py", description=__doc__)
    parser.add_argument("trees", type=Path, nargs="+")
    parser.add_argument("--dry-run", action="store_true",
                        help="say what is there and write nothing")
    args = parser.parse_args(argv)
    return max(migrate(tree, args.dry_run) for tree in args.trees)


if __name__ == "__main__":
    raise SystemExit(main())
