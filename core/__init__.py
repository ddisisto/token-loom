"""The token core: a tree is a directory, and its two halves cannot be separated.

    data/<name>/tree.json      structure, spans, interned parameters
    data/<name>/bulk.sqlite    per-token records

Opening one runs the validator and applies the load-time rule for in-flight
spans, which is what keeps "maybe still running" from being a state a span can
sit in forever.
"""
from __future__ import annotations

import os

from core.store import ABORTED, BulkStore, spelled
from core.tree import (COUNTERFACTUAL, FORMAT, HUMAN, SAMPLED, Piece, Run,
                       Span, Tree)
from core.validate import Invalid, validate

TREE_FILE = 'tree.json'
BULK_FILE = 'bulk.sqlite'

__all__ = ['Tree', 'Run', 'Span', 'Piece', 'BulkStore', 'Invalid', 'validate',
           'open_tree', 'create_tree', 'save', 'recover', 'FORMAT',
           'HUMAN', 'SAMPLED', 'COUNTERFACTUAL']


def create_tree(path: str, base_seed: int | None = None
                ) -> tuple[Tree, BulkStore]:
    """A new tree directory. Fails rather than overwriting an existing one."""
    if os.path.exists(os.path.join(path, TREE_FILE)):
        raise FileExistsError(f'{path} already holds a tree')
    os.makedirs(path, exist_ok=True)
    tree = Tree.empty(base_seed)
    store = BulkStore(os.path.join(path, BULK_FILE))
    tree.save(os.path.join(path, TREE_FILE))
    return tree, store


def open_tree(path: str, strict: bool = True, repair: bool = True
              ) -> tuple[Tree, BulkStore]:
    """Load, recover anything left in flight, and validate.

    `strict=False` returns a tree that failed validation instead of raising,
    which is what a repair tool needs and nothing else should want.
    """
    tree = Tree.load(os.path.join(path, TREE_FILE))
    store = BulkStore(os.path.join(path, BULK_FILE))

    if repair and recover(tree, store):
        tree.save(os.path.join(path, TREE_FILE))

    problems = validate(tree, store)
    if problems and strict:
        store.close()
        raise Invalid(problems)
    return tree, store


def save(path: str, tree: Tree) -> None:
    tree.save(os.path.join(path, TREE_FILE))


def recover(tree: Tree, store: BulkStore) -> list[str]:
    """Close out spans left in flight by a process that is gone.

    Reaching this point means nothing is generating -- generation is blocking,
    so an in-flight span found at load time belongs to a run that ended. Each
    is completed from whatever token rows made it and marked `aborted`, which
    is the whole of decision 8: in flight is a state, and it has an exit.

    Returns the span ids it closed, so the caller knows whether to save.
    """
    closed = []
    terminated = store.terminated()
    for span in tree.spans.values():
        if span.complete or span.id in terminated:
            continue
        text = spelled(store.tokens(span.id))
        span.text = text
        span.end = span.start + len(text)
        _widen(tree, span.id, len(text))
        store.set_terminator(span.id, ABORTED)
        closed.append(span.id)
    return closed


def _widen(tree: Tree, span_id: str, length: int) -> None:
    """Grow a span's placeholder piece to the bytes that actually landed.

    Widened in place rather than replaced: the piece is the link between an
    in-flight span and its run, and it exists from the moment the span does.
    """
    for run in tree.runs.values():
        for i, piece in enumerate(run.pieces):
            if piece.span == span_id:
                run.pieces[i] = Piece(span_id, piece.start, piece.start + length)
                return
