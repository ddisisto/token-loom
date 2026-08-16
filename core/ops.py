"""The five operations. Everything in Phase 2 and 3 is built from these.

There used to be six, and the sixth -- `split` -- was the one the others were
made of. It existed to manufacture a node boundary at a mid-run position,
because a branch could only hang off a node. With a span carrying the address
it continues from, a branch mid-span is a child anchored at an offset and there
is nothing to divide: `author`, `begin_generation` and `branch_counterfactual`
each collapse to constructing one span.

Generation is still two calls, not one, because decision 2 splits a span across
the model call: `begin_generation` writes provenance and returns spans with no
bytes, and `complete` fills the byte record in when they arrive. Between them
the tree is saved, which is what makes a crash mid-generation legible.
"""
from __future__ import annotations

from core.store import ABORTED, BulkStore, Token, spelled
from core.tree import (COUNTERFACTUAL, GIVEN, SAMPLED, Position, Span, Tree,
                       char_boundary, next_id, now)


def check(tree: Tree, pos: Position | None) -> None:
    """Is this a position at all? Raises rather than answering.

    `None` is the root and is always addressable. Anything else must name a
    span that exists, at an offset within the bytes it has -- which for a span
    still in flight is only offset 0.
    """
    if pos is None:
        return
    span = tree.spans.get(pos.span)
    if span is None:
        raise KeyError(pos.span)
    if not 0 <= pos.offset <= span.length:
        raise ValueError(f'{pos.offset} is outside {pos.span} '
                         f'(0..{span.length})')


# -- authoring and generation ---------------------------------------------

def author(tree: Tree, pos: Position | None, text: bytes) -> Span:
    """Append a given span. No tokens: whatever model reads it tokenises it.

    `given` rather than `authored` because the bytes need not have been typed:
    a paste, a file and another model's transcript all arrive here, and what
    they have in common is that they came from outside this tree's generation.
    """
    if not text:
        raise ValueError('an empty authored span would be a no-op')
    check(tree, pos)
    return tree.add(Span(tree.new_span_id(), GIVEN, parent=pos, text=text,
                         created=now()))


def begin_generation(tree: Tree, pos: Position | None, settings: dict,
                     n: int = 1) -> list[Span]:
    """Write the intent: one batch, n spans with provenance and no bytes.

    All n share a parent address, which is what "n continuations from one
    position" means -- and having said it once, the structure says it too. The
    caller saves the tree before calling the model. That ordering is what keeps
    a crash legible, and what guarantees no bulk row can ever name a span the
    tree has not heard of.
    """
    if n < 1:
        raise ValueError(f'n must be at least 1, got {n}')
    check(tree, pos)

    params = tree.intern(settings)
    batch = next_id({s.batch for s in tree.spans.values() if s.batch}, 'b')
    # base seed plus call index, so siblings differ and the tree still replays
    call = sum(1 for s in tree.spans.values() if s.seed is not None)
    # resolved through slice_at, so the span records the same start the prompt
    # was actually built from -- including the nudge to a character boundary
    slice_start, _, _ = slice_at(tree, pos, settings['prompt_length'])

    spans = []
    for i in range(n):
        spans.append(tree.add(
            Span(tree.new_span_id(), SAMPLED, parent=pos, created=now(),
                 params=params, seed=tree.base_seed + call + i, batch=batch,
                 index=i, slice_start=slice_start)))
    return spans


def complete(tree: Tree, store: BulkStore, span_id: str, tokens: list[Token],
             reason: str, counterfactuals=None) -> Span:
    """Fill in a span's byte record. Filled in, never overwritten.

    Nothing structural happens here, and nothing but the text grows: a span
    records its attachment when it is created and the bytes arrive into a shape
    already fixed.
    """
    span = tree.spans[span_id]
    if span.complete:
        raise ValueError(f'{span_id} is already complete')
    if tokens:
        store.add_tokens(span_id, tokens)
    if counterfactuals:
        store.add_counterfactuals(span_id, counterfactuals)
    span.text = spelled(tokens)
    store.set_terminator(span_id, reason)
    return span


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
        span.text = spelled(store.tokens(span.id))
        store.set_terminator(span.id, ABORTED)
        closed.append(span.id)
    return closed


# -- deletion --------------------------------------------------------------

def delete(tree: Tree, pos: Position) -> None:
    """Soft, and it cascades. The bulk store is untouched.

    `pos` means *nothing continues past here*: the span's own bytes from that
    offset on stop being reached, and so does everything anchored at or after
    it. One address covers both of the things this has to express -- deleting a
    whole fork while its sibling survives is the offset-0 case, and truncating
    mid-span is every other case.

    Nothing is rewritten and no span is opened: a deleted subtree keeps every
    byte it recorded. Generated tokens cost real GPU time, so destroying them
    on a keystroke is the wrong default.

    **The list is not pruned, and must not be.** An entry that a wider cut
    already covers looks redundant and is not: dropping it makes `restore` on
    the wider one resurrect a subtree that was deleted separately and never
    restored. The redundant entry is precisely what remembers that. Nor is
    there anything to buy by pruning -- `Tree.live` takes the least cut per
    span and is total over any set of addresses, including ones that nest.
    Deleting something already unreachable is still a no-op, which is what
    keeps the list from growing on repeated calls.
    """
    if pos is None:
        raise ValueError('the root cannot be deleted')
    check(tree, pos)
    if not tree.resolves(pos):
        return                       # already under a deletion
    tree.deleted.append(pos)


def restore(tree: Tree, pos: Position) -> None:
    """Undo a delete. Soft delete is what makes this a list operation."""
    if pos in tree.deleted:
        tree.deleted.remove(pos)


# -- reading ---------------------------------------------------------------

def address_at(tree: Tree, pos: Position | None, target: int
               ) -> Position | None:
    """The address of a root-relative byte offset, on the path ending at `pos`.

    The inverse of `Tree.absolute`, and needed because a slice length is a
    count of bytes while a slice start has to be an address. At a boundary
    between two spans it answers with the earlier span's tip rather than the
    later one's byte 0 -- the same point, named canonically, so two callers
    computing the same slice record the same start.
    """
    chain = tree.ancestry(pos)
    seen = 0
    for step in chain:
        if target <= seen + step.offset:
            return Position(step.span, target - seen)
        seen += step.offset
    return chain[-1] if chain else None


def slice_at(tree: Tree, pos: Position | None, length: int
             ) -> tuple[Position | None, Position | None, bytes]:
    """The prompt: `(start, end, bytes)`, clamped at the root.

    Recorded as bounds rather than as text, which is only sound because bytes
    are immutable -- the bounds keep meaning what they meant when written. Both
    bounds are addresses, so they survive export of a subtree, where a
    root-relative offset would not.

    The start is nudged forward to a character boundary when subtracting a byte
    length lands inside one. That is a real case rather than a precaution: a
    token can be a fragment of a character, so byte offsets genuinely address
    positions no string starts at. Snapping *here* rather than at the point of
    sending is what keeps `slice_start` on the span honest -- it records the
    slice that was actually used, not the one that was asked for.
    """
    prefix = tree.path_bytes(pos)
    at = char_boundary(prefix, max(0, len(prefix) - length))
    return address_at(tree, pos, at), pos, prefix[at:]


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


def divergence(store: BulkStore, span_ids: list[str],
               depths=(1, 3, 10)) -> dict | None:
    """How far a set of siblings agree, as a profile over token depth.

    A read, not an operation: it stores nothing and changes nothing, and every
    number it returns is recomputed from token rows already held. It lives here
    rather than in the CLI because it is missing from the API too -- comparing
    sibling token sequences is the only quantitative handle the instrument has
    on where a prompt tends to go, and a client that cannot do it is short of
    the floor rather than short of a convenience.

    `lock(k)` is the largest fraction of siblings sharing their first `k`
    tokens. The denominator is always the full sibling count, so a span with
    fewer than `k` tokens joins no group and lowers every lock it cannot
    reach -- which is the conservative reading, and the one that cannot make
    agreement look higher than it was.

    `distinct` does *not* filter by length, because a short sequence is a
    distinct path rather than a missing one. The asymmetry is deliberate: a
    span too short to share a prefix has still gone somewhere of its own.
    """
    seqs = [tuple(t.token_id for t in store.tokens(s)) for s in span_ids]
    n = len(seqs)
    if not n:
        return None
    longest = max(len(s) for s in seqs)

    lock = {}
    for k in depths:
        reaching = [s[:k] for s in seqs if len(s) >= k]
        counts = {}
        for prefix in reaching:
            counts[prefix] = counts.get(prefix, 0) + 1
        lock[k] = (max(counts.values()) / n) if counts else 0.0

    common = 0
    for i in range(min(len(s) for s in seqs)):
        if len({s[i] for s in seqs}) != 1:
            break
        common += 1

    distinct = [len({s[:d] for s in seqs}) for d in range(1, longest + 1)]
    fully = next((d for d, c in enumerate(distinct, 1) if c == n), None)

    return {'n': n, 'lock': lock, 'common': common, 'distinct': distinct,
            'fully_distinct_at': fully,
            'short': {k: sum(1 for s in seqs if len(s) < k) for k in depths}}


def branch_counterfactual(tree: Tree, store: BulkStore, span_id: str,
                          index: int, rank: int) -> Span:
    """Take a token the model ranked but did not sample, and branch there.

    No generation: the alternative was already recorded when the span was, so
    this is the payoff that makes storing counterfactuals worth their size.
    `parent` and `origin` overlap deliberately -- `origin` says which
    counterfactual, `parent` says where it attaches -- and the validator holds
    them to agreeing.
    """
    ranked = [c for c in store.counterfactuals(span_id, index) if c.rank == rank]
    if not ranked:
        raise ValueError(f'{span_id}[{index}] has no counterfactual at rank {rank}')
    choice = ranked[0]

    offsets = token_offsets(store, span_id)
    if index >= len(offsets) - 1:
        raise ValueError(f'{span_id} has no token {index}')

    span = tree.add(Span(
        tree.new_span_id(), COUNTERFACTUAL,
        parent=Position(span_id, offsets[index]),
        text=choice.bytes, created=now(),
        origin={'span': span_id, 'index': index, 'token_id': choice.token_id}))
    store.add_tokens(span.id, [Token(0, choice.token_id, choice.bytes,
                                     choice.logprob)])
    return span
