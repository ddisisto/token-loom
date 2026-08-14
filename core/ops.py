"""The six operations. Everything in Phase 2 and 3 is built from these.

`split` is the one the others are made of: generating from a mid-run position,
branching to a counterfactual, and moving a slice end all reduce to it. It is
also the only operation that changes the shape of an existing run, and it does
so without opening a single span -- dividing a list of integers, relinking, and
leaving every absolute offset exactly where it was.

Generation is two calls, not one, because decision 2 splits a span across the
model call: `begin_generation` writes provenance and returns spans with no
bytes, and `complete` fills the byte record in when they arrive. Between them
the tree is saved, which is what makes a crash mid-generation legible.
"""
from __future__ import annotations

from core.store import ABORTED, BulkStore, Token, spelled
from core.tree import (COUNTERFACTUAL, HUMAN, SAMPLED, Piece, Position, Run,
                       Span, Tree, char_boundary, next_id, now)


def absolute(tree: Tree, pos: Position) -> int:
    run = tree.runs[pos.run]
    if not 0 <= pos.offset <= run.length:
        raise ValueError(f'{pos.offset} is outside {pos.run} (0..{run.length})')
    return run.start + pos.offset


def at(tree: Tree, run_id: str, offset: int) -> Position:
    """Resolve an absolute offset to a position on the path ending at `run_id`.

    This is the lookup decision 1 calls for: durable references hold absolute
    offsets, and runs are found from them rather than the other way round.
    """
    for candidate in tree.ancestry(run_id):
        run = tree.runs[candidate]
        if run.start <= offset <= run.end:
            return Position(candidate, offset - run.start)
    raise ValueError(f'{offset} is not on the path to {run_id}')


# -- the primitive ---------------------------------------------------------

def split(tree: Tree, pos: Position) -> str:
    """Return the run whose end is exactly this position, dividing one if need be.

    Idempotent at an existing boundary, and canonical: the end of a run and
    offset 0 of its child are the same position, and both answer with the same
    run. Callers can therefore treat the result as "the run to hang something
    off" without caring how the position was named.
    """
    run = tree.runs[pos.run]
    if not 0 <= pos.offset <= run.length:
        raise ValueError(f'{pos.offset} is outside {pos.run} (0..{run.length})')

    if pos.offset == 0 and run.parent is not None:
        return run.parent
    if pos.offset == run.length:
        return run.id

    prefix: list[Piece] = []
    suffix: list[Piece] = []
    seen = 0
    for piece in run.pieces:
        if seen + piece.length <= pos.offset:
            prefix.append(piece)
        elif seen >= pos.offset:
            suffix.append(piece)
        else:
            cut = piece.start + (pos.offset - seen)
            prefix.append(Piece(piece.span, piece.start, cut))
            suffix.append(Piece(piece.span, cut, piece.end))
        seen += piece.length

    # the prefix keeps the id, so no ancestor's child list changes
    new_id = tree.new_run_id()
    tree.runs[new_id] = Run(new_id, run.id, run.start + pos.offset,
                            suffix, run.children)
    for child in run.children:
        tree.runs[child].parent = new_id
    run.pieces = prefix
    run.children = [new_id]

    # `selected` is the one thing in the file keyed by a run id, and this is
    # exactly the hazard decision 1 warns about: it would still resolve, but to
    # a run that no longer reaches that far.
    chosen = tree.selected
    if chosen and chosen['run'] == run.id and chosen['offset'] > pos.offset:
        tree.selected = {'run': new_id, 'offset': chosen['offset'] - pos.offset}

    # the prefix is the run that now ends at the position
    return run.id


def _attach(tree: Tree, anchor_id: str, n: int) -> list[str]:
    """Where n new spans land: the anchor itself, or n fresh children.

    One span continuing from a tip extends that run -- which is how a single
    run comes to reference several spans at different temperatures, and is
    worth keeping expressible. Anything else branches. The root never extends:
    it holds no bytes by design, so that several initial prompts can sit under
    it as siblings.
    """
    anchor = tree.runs[anchor_id]
    if n == 1 and anchor_id != tree.root and not anchor.children:
        return [anchor_id]
    start = anchor.end
    ids = []
    for _ in range(n):
        run_id = tree.new_run_id()
        tree.runs[run_id] = Run(run_id, anchor_id, start)
        anchor.children.append(run_id)
        ids.append(run_id)
    return ids


# -- authoring and generation ---------------------------------------------

def author(tree: Tree, pos: Position, text: bytes) -> Span:
    """Append a human span. No tokens: whatever model reads it tokenises it."""
    if not text:
        raise ValueError('an empty authored span would be a no-op')
    anchor = split(tree, pos)
    start = tree.runs[anchor].end
    span = Span(tree.new_span_id(), HUMAN, start=start, end=start + len(text),
                text=text, created=now())
    tree.spans[span.id] = span
    run_id = _attach(tree, anchor, 1)[0]
    tree.runs[run_id].pieces.append(Piece(span.id, 0, len(text)))
    return span


def begin_generation(tree: Tree, pos: Position, settings: dict, n: int = 1
                     ) -> list[Span]:
    """Write the intent: one batch, n spans with provenance and no bytes.

    The caller saves the tree before calling the model. That ordering is what
    keeps a crash legible, and what guarantees no bulk row can ever name a span
    the tree has not heard of.
    """
    if n < 1:
        raise ValueError(f'n must be at least 1, got {n}')
    anchor = split(tree, pos)
    start = tree.runs[anchor].end

    params = tree.intern(settings)
    batch = next_id({s.batch for s in tree.spans.values() if s.batch}, 'b')
    # base seed plus call index, so siblings differ and the tree still replays
    call = sum(1 for s in tree.spans.values() if s.seed is not None)
    # resolved through slice_at, so the span records the same start the prompt
    # was actually built from -- including the nudge to a character boundary
    slice_start, _, _ = slice_at(tree, Position(anchor, tree.runs[anchor].length),
                                 settings['prompt_length'])

    spans = []
    for i, run_id in enumerate(_attach(tree, anchor, n)):
        span = Span(tree.new_span_id(), SAMPLED, start=start, created=now(),
                    params=params, seed=tree.base_seed + call + i, batch=batch,
                    index=i, slice_start=slice_start)
        tree.spans[span.id] = span
        tree.runs[run_id].pieces.append(Piece(span.id, 0, 0))
        spans.append(span)
    return spans


def complete(tree: Tree, store: BulkStore, span_id: str, tokens: list[Token],
             reason: str, counterfactuals=None) -> Span:
    """Fill in a span's byte record. Filled in, never overwritten."""
    span = tree.spans[span_id]
    if span.complete:
        raise ValueError(f'{span_id} is already complete')
    if tokens:
        store.add_tokens(span_id, tokens)
    if counterfactuals:
        store.add_counterfactuals(span_id, counterfactuals)
    text = spelled(tokens)
    span.text = text
    span.end = span.start + len(text)
    widen(tree, span_id, len(text))
    store.set_terminator(span_id, reason)
    return span


def widen(tree: Tree, span_id: str, length: int) -> None:
    """Grow a span's placeholder piece to the bytes that actually landed.

    Widened in place rather than replaced: the piece is the link between an
    in-flight span and its run, and it exists from the moment the span does.
    """
    for run in tree.runs.values():
        for i, piece in enumerate(run.pieces):
            if piece.span == span_id:
                run.pieces[i] = Piece(span_id, piece.start, piece.start + length)
                return


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
        widen(tree, span.id, len(text))
        store.set_terminator(span.id, ABORTED)
        closed.append(span.id)
    return closed


# -- deletion --------------------------------------------------------------

def descendants(tree: Tree, run_id: str) -> set[str]:
    """`run_id` and everything under it."""
    found: set[str] = set()
    stack = [run_id]
    while stack:
        current = stack.pop()
        if current in found:
            continue
        found.add(current)
        stack.extend(tree.runs[current].children)
    return found


def delete(tree: Tree, run_id: str) -> None:
    """Soft, and it cascades. The bulk store is untouched.

    Nothing is rewritten and no span is opened: a deleted subtree stops being
    reachable and keeps every byte it recorded. Generated tokens cost real GPU
    time, so destroying them on a keystroke is the wrong default.
    """
    if run_id == tree.root:
        raise ValueError('the root cannot be deleted')
    if run_id not in tree.runs:
        raise KeyError(run_id)
    if run_id not in tree.live_runs():
        return  # already under a deleted root

    # keep `deleted` to maximal roots only, so liveness stays one walk
    under = descendants(tree, run_id)
    tree.deleted = [d for d in tree.deleted if d not in under]
    tree.deleted.append(run_id)

    chosen = tree.selected
    if chosen and chosen['run'] in under:
        parent = tree.runs[run_id].parent
        tree.selected = {'run': parent, 'offset': tree.runs[parent].length}


def restore(tree: Tree, run_id: str) -> None:
    """Undo a delete. Soft delete is what makes this a list operation."""
    if run_id in tree.deleted:
        tree.deleted.remove(run_id)


# -- reading ---------------------------------------------------------------

def prefix_bytes(tree: Tree, pos: Position) -> bytes:
    """Every byte from the root to this position, along its path."""
    ancestry = tree.ancestry(pos.run)
    before = b''.join(tree.run_bytes(r) for r in ancestry[:-1])
    return before + tree.run_bytes(pos.run)[:pos.offset]


def slice_at(tree: Tree, pos: Position, length: int) -> tuple[int, int, bytes]:
    """The prompt: `(start, end, bytes)`, clamped at the root.

    Recorded as bounds rather than as text, which is only sound because bytes
    are immutable -- the bounds keep meaning what they meant when written.

    The start is nudged forward to a character boundary when subtracting a byte
    length lands inside one. That is a real case rather than a precaution: a
    token can be a fragment of a character, so byte offsets genuinely address
    positions no string starts at. Snapping *here* rather than at the point of
    sending is what keeps `slice_start` on the span honest -- it records the
    slice that was actually used, not the one that was asked for.
    """
    end = absolute(tree, pos)
    prefix = prefix_bytes(tree, pos)
    start = char_boundary(prefix, max(0, end - length))
    return start, end, prefix[start:]


def locate(tree: Tree, span_id: str, offset: int) -> Position:
    """Where a byte of a span sits in the tree, as a position.

    A span's pieces lie along one root-to-leaf path, so this is unambiguous --
    but a split may have put the offset in a different run than the one the
    span started in, which is the whole reason it needs looking up.
    """
    span = tree.spans[span_id]
    if not 0 <= offset <= span.length:
        raise ValueError(f'{offset} is outside {span_id} (0..{span.length})')
    pieces = sorted(tree.pieces_of(span_id), key=lambda item: item[2].start)
    for run_id, piece_at, piece in pieces:
        # the last piece owns the span's far end, which no range contains
        if piece.start <= offset < piece.end or (offset == span.length
                                                 and piece.end == offset):
            run = tree.runs[run_id]
            return Position(run_id, piece_at - run.start + (offset - piece.start))
    raise ValueError(f'{span_id} has no piece covering {offset}')


def token_offsets(store: BulkStore, span_id: str) -> list[int]:
    """The byte offset each token of a span starts at, plus the span's length.

    Byte offsets are the anchor and token indices are the overlay; this is the
    conversion between them, and it is a per-span read rather than a stored
    field precisely because the overlay is derived.
    """
    offsets = [0]
    for token in store.tokens(span_id):
        offsets.append(offsets[-1] + len(token.bytes))
    return offsets


def branch_counterfactual(tree: Tree, store: BulkStore, span_id: str,
                          index: int, rank: int) -> Span:
    """Take a token the model ranked but did not sample, and branch there.

    No generation: the alternative was already recorded when the span was, so
    this is the payoff that makes storing counterfactuals worth their size.
    """
    ranked = [c for c in store.counterfactuals(span_id, index) if c.rank == rank]
    if not ranked:
        raise ValueError(f'{span_id}[{index}] has no counterfactual at rank {rank}')
    choice = ranked[0]

    offsets = token_offsets(store, span_id)
    if index >= len(offsets) - 1:
        raise ValueError(f'{span_id} has no token {index}')
    anchor = split(tree, locate(tree, span_id, offsets[index]))
    start = tree.runs[anchor].end

    span = Span(tree.new_span_id(), COUNTERFACTUAL, start=start,
                end=start + len(choice.bytes), text=choice.bytes, created=now(),
                origin={'span': span_id, 'index': index,
                        'token_id': choice.token_id})
    tree.spans[span.id] = span
    run_id = _attach(tree, anchor, 1)[0]
    tree.runs[run_id].pieces.append(Piece(span.id, 0, len(choice.bytes)))
    store.add_tokens(span.id, [Token(0, choice.token_id, choice.bytes,
                                     choice.logprob)])
    return span
