"""A tree, its store, and a server -- held together with the save ordering.

The operations in `ops.py` are deliberately ignorant of files and of models.
This is where those meet: it owns the directory, and it owns the rule that the
tree is saved *between* recording an intent and making the call. That ordering
is not bookkeeping. It is what makes a crash mid-generation legible, and what
guarantees no bulk row can name a span the tree has not heard of.

Owning the directory is also what makes this the place the two-writer guard
lives. A session opened for writing takes an exclusive lock on the directory
and holds it until it closes; a session opened for reading takes none, writes
nothing, and is refused by nothing. `core/lock.py` has the mechanism and the
reasoning, including why the sqlite store cannot stand in for it.

The split is a property of the *session*, not of each call. Nothing here
serialises a read against a write within one process -- the API answers
`GET /api/tree` under a running generation, and that stays true.
"""
from __future__ import annotations

import os

from core.llama import Server
from core.lock import DirectoryLock, Locked
from core.ops import (author, begin_generation, branch_counterfactual, complete,
                      delete, recover, restore, slice_at)
from core.store import BulkStore
from core.tree import Position, Span, Tree, id_order
from core.validate import Invalid, validate

__all__ = ['Session', 'Locked', 'TREE_FILE', 'BULK_FILE']

TREE_FILE = 'tree.json'
BULK_FILE = 'bulk.sqlite'


class Session:
    """A tree directory held open, for reading or for writing.

    `write` is the whole of the read/write distinction, and it is one flag
    rather than two classes because everything it changes is a refusal:

    - a writing session takes the directory lock and holds it until `close`
    - a reading session takes no lock, so any number of them coexist with each
      other and with the one writer
    - a reading session refuses to `save`, which is the single choke point every
      mutation here goes through -- there is no path that writes without it
    - a reading session does not run in-flight recovery either, since closing a
      span out as `aborted` is a write to both halves of the directory

    Not running recovery is the one visible difference in what a reader sees: a
    span another process is generating right now reads as in flight, which is
    what it is. The validator has no objection to one -- its rows are still
    arriving, and check 7 only asks a *complete* span for a terminator.
    """

    def __init__(self, path: str, tree: Tree, store: BulkStore,
                 server: Server | None = None,
                 lock: DirectoryLock | None = None):
        self.path = path
        self.tree = tree
        self.store = store
        self.server = server
        self.lock = lock

    # -- lifecycle ---------------------------------------------------------

    @classmethod
    def create(cls, path: str, base_seed: int | None = None,
               server: Server | None = None) -> Session:
        """A new tree directory, held for writing. There is no reading a tree
        that does not exist yet, so there is no flag here."""
        if os.path.exists(os.path.join(path, TREE_FILE)):
            raise FileExistsError(f'{path} already holds a tree')
        os.makedirs(path, exist_ok=True)
        lock = DirectoryLock(path)
        lock.acquire()
        try:
            session = cls(path, Tree.empty(base_seed),
                          BulkStore(os.path.join(path, BULK_FILE)), server, lock)
            session.save()
        except BaseException:
            lock.release()
            raise
        return session

    @classmethod
    def open(cls, path: str, server: Server | None = None,
             strict: bool = True, write: bool = True) -> Session:
        """Open a tree directory. Writing by default, and locked if so.

        The lock is taken *before* the file is read, so what is validated is
        what no one else can be rewriting underneath. `Locked` propagates: the
        callers that own a command line turn it into a message and an exit
        code, because "someone else has this tree" is a fact about the world
        rather than a fault in the caller.
        """
        lock = DirectoryLock(path) if write else None
        if lock is not None:
            lock.acquire()          # FileNotFoundError if there is no directory
        try:
            tree = Tree.load(os.path.join(path, TREE_FILE))
            store = BulkStore(os.path.join(path, BULK_FILE))
        except BaseException:
            if lock is not None:
                lock.release()
            raise

        session = cls(path, tree, store, server, lock)
        try:
            # recovery writes to both halves, so a reader leaves it for a writer
            if write and recover(tree, store):
                session.save()
            problems = validate(tree, store)
            if problems and strict:
                raise Invalid(problems)
        except BaseException:
            session.close()
            raise
        return session

    def save(self) -> None:
        """The single choke point every mutation goes through.

        Refusing here rather than on each operation is deliberate: a new
        operation added to this class cannot forget to be refused, because the
        thing it has to do to take effect is the thing that checks.
        """
        if self.lock is None:
            raise Locked(f'{self.path} was opened for reading; a session that '
                         f'holds no lock on the directory does not write to it')
        self.tree.save(os.path.join(self.path, TREE_FILE))

    def close(self) -> None:
        self.store.close()
        if self.lock is not None:
            self.lock.release()

    def __enter__(self) -> Session:
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    # -- editing -----------------------------------------------------------

    def author(self, pos: Position | None, text: bytes) -> Span:
        span = author(self.tree, pos, text)
        self.save()
        return span

    def branch(self, span_id: str, index: int, rank: int) -> Span:
        span = branch_counterfactual(self.tree, self.store, span_id, index, rank)
        self.save()
        return span

    def delete(self, pos: Position) -> None:
        delete(self.tree, pos)
        self.save()

    def restore(self, pos: Position) -> None:
        restore(self.tree, pos)
        self.save()

    # -- generation --------------------------------------------------------

    def settings(self, **over) -> dict:
        """A parameter set, with the server's own facts filled in.

        `model` and `n_ctx` are properties of what is serving rather than of
        what the user asked for, and both are recorded per span: reproducibility
        is conditions-level, and "hit the context limit" means nothing without
        knowing which limit.

        `prompt_length` defaults to `None` -- the whole path. The number it
        replaced was arbitrary, and arbitrary is the wrong kind of default for
        a recorded parameter: a caller who never thought about framing had one
        chosen for them and it went onto every span they made. Sending the whole
        path is the choice that makes no claim, and where it does not fit, the
        server refuses outright rather than quietly reading less than the
        reader can see. Narrowing the slice stays available and stays
        deliberate, which is what studying framing as a change of basis asks
        of it.
        """
        if self.server is None:
            raise RuntimeError('no server attached to this session')
        base = {'temperature': 0.9, 'top_p': 1, 'top_n': 3, 'length': 32,
                'stop': [], 'prompt_length': None}
        base.update(self.server.describe())
        base.setdefault('tokenizer', base.get('model'))
        base.update(over)
        return base

    def generate(self, pos: Position | None, settings: dict, n: int = 1
                 ) -> list[Span]:
        """Record the intent, save, then call the model once per continuation.

        `n` is sequential by construction: llama-server takes one prompt per
        request. That is the best case for its prompt cache -- identical prefix,
        repeated immediately -- so the cost is generation n times and prompt
        processing once.
        """
        if self.server is None:
            raise RuntimeError('no server attached to this session')

        # no anchoring step, and nothing made first: the position is the position
        start, _, prompt = slice_at(self.tree, pos, settings['prompt_length'])
        if not prompt:
            # the adapter refuses this too, and says why. It is caught again
            # here because the refusal has to land *before* the provenance is
            # written: generating at the root with nothing authored is an
            # ordinary slip, and one junk span left in flight per slip is a
            # worse answer than the error
            raise ValueError(
                'the prompt is empty: there is nothing to continue from. '
                'Author a given first')

        spans = begin_generation(self.tree, pos, settings, n)
        assert spans[0].slice_start == start, 'the prompt is not the recorded slice'
        self.save()

        for span in spans:
            result = self.server.complete(prompt, settings, span.seed)
            complete(self.tree, self.store, span.id, result.tokens,
                     result.reason, result.counterfactuals)
            # saved per continuation, so an interrupted batch keeps what landed
            self.save()
        return spans

    # -- reading -----------------------------------------------------------

    def slice(self, pos: Position | None, length: int
              ) -> tuple[Position | None, Position | None, bytes]:
        return slice_at(self.tree, pos, length)

    def text(self, pos: Position | None) -> bytes:
        return self.tree.path_bytes(pos)

    def tip(self, span_id: str) -> Position:
        return self.tree.tip(span_id)

    def leaves(self) -> list[str]:
        """Live spans that nothing live continues from.

        A span cut by a deletion address can still be a leaf while holding
        bytes past the cut -- the tree stops reaching them, which is exactly
        the distinction soft delete exists to keep.
        """
        reach = self.tree.live()
        return [span_id for span_id in sorted(reach, key=id_order)
                if not any(child in reach
                           for _, child in self.tree.children_of(span_id))]
