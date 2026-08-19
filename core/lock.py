"""One writer per tree directory, enforced by the kernel.

`Tree.save` rewrites `tree.json` whole, so two processes writing one directory
do not interleave -- the later save simply destroys the earlier one's spans.
Worse, span ids are minted one past the highest *in the tree*, so a re-minted
`s7` silently inherits the dead `s7`'s rows in the bulk store. Neither is
detectable afterwards from the tree alone.

The lock is `flock` on the **directory's own file descriptor**: `os.open` it,
`LOCK_EX | LOCK_NB`, hold the descriptor for the life of the process. Four
properties, all measured rather than assumed:

- **Nothing is created.** No lock file to gitignore, to leave stale, or to
  commit by accident -- and `experiments/` trees are committed, so a stray file
  appearing inside one is a real nuisance rather than a theoretical one.
- **The kernel releases it, including on SIGKILL.** A crashed writer leaves no
  cleanup for the next one to do. Measured: a child holding the lock, killed
  with SIGKILL, and the next acquire succeeded.
- **It is about the directory rather than either file in it.** A lock taken on
  `tree.json` would be orphaned by the very `os.replace` that save performs --
  the successor file is a different inode. Measured: renaming a file *into* the
  locked directory leaves the lock held.
- **A second descriptor conflicts even in the same process.** flock locks the
  open file description, and two `os.open` calls make two of those. So the
  guard also catches one process opening one tree twice for writing, which is
  the same bug arriving by a shorter route.

**The sqlite store does not serve as the lock, and this is settled.** Three
reasons in order of decisiveness: the file destroyed is `tree.json`, which
sqlite has no visibility into at all; `store.py` commits after every write and
sqlite's locks are per-transaction rather than per-connection, so holding the
connection open grants nothing in between; and the store runs
`journal_mode=WAL`, which exists precisely so readers and writers do not block
each other. The one variant that would give process-lifetime exclusion,
`PRAGMA locking_mode = EXCLUSIVE`, blocks readers -- and a reader must never be
blocked, since `loom.py show` against a tree a server has open is exactly the
case the read/write split exists for.

**Reads take no lock at all.** Not a shared one: a shared lock would still have
to be released, would still make a reader something a writer can notice, and
buys nothing here -- `Tree.save` is atomic by rename, so a reader either sees
the whole old file or the whole new one. What a reader must not do is *write*,
and `Session` enforces that at `save` rather than here.

Nothing in this module is per-operation. The lock is taken once when a tree is
opened for writing and released when the session closes; within one process,
concurrent reads and a running generation are the API's business and this does
not serialise them.

The raw `open_tree`/`create_tree` in `core/__init__.py` stay unlocked on
purpose: they hand back a tree and a store and have no lifetime to hold a lock
for. `Session` is the thing that owns a directory over time, so `Session` is
where the lock lives.
"""
from __future__ import annotations

import fcntl
import os


class Locked(Exception):
    """Another process already has this tree directory open for writing."""


class DirectoryLock:
    """An exclusive flock on a directory, held from `acquire` to `release`.

    Re-entrant by count in the single sense that matters -- `release` on an
    unheld lock is a no-op -- so a caller unwinding a half-built session does
    not have to know how far it got.
    """

    def __init__(self, path: str):
        self.path = path
        self.fd: int | None = None

    @property
    def held(self) -> bool:
        return self.fd is not None

    def acquire(self) -> None:
        """Take it, or raise `Locked`. Never blocks.

        Blocking would turn "someone else has this tree" into "this command
        hangs", which is the worse of the two failures by a wide margin: the
        holder keeps it for its whole life, so waiting is waiting for a person
        to quit a server.
        """
        if self.held:
            return
        fd = os.open(self.path, os.O_RDONLY)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            os.close(fd)
            raise Locked(
                f'{self.path} is open for writing by another process; only one '
                f'writer at a time. Reads are unaffected -- `loom.py -d '
                f'{self.path} show` works while a server holds it.')
        self.fd = fd

    def release(self) -> None:
        if self.fd is None:
            return
        fd, self.fd = self.fd, None
        # closing releases; the explicit LOCK_UN says so to the reader
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)

    def __enter__(self) -> DirectoryLock:
        self.acquire()
        return self

    def __exit__(self, *exc) -> None:
        self.release()
