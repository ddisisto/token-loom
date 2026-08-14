"""The token core: a tree is a directory, and its two halves cannot be separated.

    data/<name>/tree.json      structure, spans, interned parameters
    data/<name>/bulk.sqlite    per-token records

Opening one runs the validator and applies the load-time rule for in-flight
spans, which is what keeps "maybe still running" from being a state a span can
sit in forever.
"""
from __future__ import annotations

import os

from core.ops import (absolute, at, author, begin_generation,
                      branch_counterfactual, complete, delete, descendants,
                      locate, prefix_bytes, recover, restore, slice_at, split,
                      token_offsets, widen)
from core.store import (ABORTED, CONTEXT, LENGTH, STOP, BulkStore,
                        Counterfactual, Token, spelled)
from core.tree import (COUNTERFACTUAL, FORMAT, HUMAN, SAMPLED, Piece, Position,
                       Run, Span, Tree)
from core.validate import Invalid, validate

TREE_FILE = 'tree.json'
BULK_FILE = 'bulk.sqlite'

__all__ = [
    # format
    'Tree', 'Run', 'Span', 'Piece', 'Position', 'BulkStore', 'Token',
    'Counterfactual', 'FORMAT', 'HUMAN', 'SAMPLED', 'COUNTERFACTUAL',
    'LENGTH', 'STOP', 'CONTEXT', 'ABORTED', 'spelled',
    # the six operations, and what they are built from
    'author', 'begin_generation', 'complete', 'split', 'delete', 'slice_at',
    'branch_counterfactual', 'restore', 'recover', 'widen',
    'absolute', 'at', 'locate', 'prefix_bytes', 'token_offsets', 'descendants',
    # files
    'open_tree', 'create_tree', 'save', 'validate', 'Invalid',
]


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
