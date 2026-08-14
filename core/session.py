"""A tree, its store, and a server -- held together with the save ordering.

The operations in `ops.py` are deliberately ignorant of files and of models.
This is where those meet: it owns the directory, and it owns the rule that the
tree is saved *between* recording an intent and making the call. That ordering
is not bookkeeping. It is what makes a crash mid-generation legible, and what
guarantees no bulk row can name a span the tree has not heard of.
"""
from __future__ import annotations

import os

from core.llama import Server
from core.ops import (author, begin_generation, branch_counterfactual, complete,
                      delete, prefix_bytes, recover, restore, slice_at, split)
from core.store import BulkStore
from core.tree import Position, Span, Tree
from core.validate import Invalid, validate

TREE_FILE = 'tree.json'
BULK_FILE = 'bulk.sqlite'


class Session:
    def __init__(self, path: str, tree: Tree, store: BulkStore,
                 server: Server | None = None):
        self.path = path
        self.tree = tree
        self.store = store
        self.server = server

    # -- lifecycle ---------------------------------------------------------

    @classmethod
    def create(cls, path: str, base_seed: int | None = None,
               server: Server | None = None) -> Session:
        if os.path.exists(os.path.join(path, TREE_FILE)):
            raise FileExistsError(f'{path} already holds a tree')
        os.makedirs(path, exist_ok=True)
        session = cls(path, Tree.empty(base_seed),
                      BulkStore(os.path.join(path, BULK_FILE)), server)
        session.save()
        return session

    @classmethod
    def open(cls, path: str, server: Server | None = None,
             strict: bool = True) -> Session:
        tree = Tree.load(os.path.join(path, TREE_FILE))
        store = BulkStore(os.path.join(path, BULK_FILE))
        session = cls(path, tree, store, server)
        if recover(tree, store):
            session.save()
        problems = validate(tree, store)
        if problems and strict:
            store.close()
            raise Invalid(problems)
        return session

    def save(self) -> None:
        self.tree.save(os.path.join(self.path, TREE_FILE))

    def close(self) -> None:
        self.store.close()

    def __enter__(self) -> Session:
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    # -- editing -----------------------------------------------------------

    def author(self, pos: Position, text: bytes) -> Span:
        span = author(self.tree, pos, text)
        self.save()
        return span

    def branch(self, span_id: str, index: int, rank: int) -> Span:
        span = branch_counterfactual(self.tree, self.store, span_id, index, rank)
        self.save()
        return span

    def delete(self, run_id: str) -> None:
        delete(self.tree, run_id)
        self.save()

    def restore(self, run_id: str) -> None:
        restore(self.tree, run_id)
        self.save()

    # -- generation --------------------------------------------------------

    def settings(self, **over) -> dict:
        """A parameter set, with the server's own facts filled in.

        `model` and `n_ctx` are properties of what is serving rather than of
        what the user asked for, and both are recorded per span: reproducibility
        is conditions-level, and "hit the context limit" means nothing without
        knowing which limit.
        """
        if self.server is None:
            raise RuntimeError('no server attached to this session')
        base = {'temperature': 0.9, 'top_p': 1, 'top_n': 3, 'length': 32,
                'stop': [], 'prompt_length': 6000}
        base.update(self.server.describe())
        base.setdefault('tokenizer', base.get('model'))
        base.update(over)
        return base

    def generate(self, pos: Position, settings: dict, n: int = 1) -> list[Span]:
        """Record the intent, save, then call the model once per continuation.

        `n` is sequential by construction: llama-server takes one prompt per
        request. That is the best case for its prompt cache -- identical prefix,
        repeated immediately -- so the cost is generation n times and prompt
        processing once.
        """
        if self.server is None:
            raise RuntimeError('no server attached to this session')

        anchor = split(self.tree, pos)
        tip = Position(anchor, self.tree.runs[anchor].length)
        start, _, prompt = slice_at(self.tree, tip, settings['prompt_length'])

        spans = begin_generation(self.tree, tip, settings, n)
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

    def slice(self, pos: Position, length: int) -> tuple[int, int, bytes]:
        return slice_at(self.tree, pos, length)

    def text(self, run_id: str) -> bytes:
        return self.tree.path_bytes(run_id)

    def tip(self, run_id: str) -> Position:
        return Position(run_id, self.tree.runs[run_id].length)

    def leaves(self) -> list[str]:
        live = self.tree.live_runs()
        return [r for r in sorted(live)
                if not (set(self.tree.runs[r].children) & live)]
