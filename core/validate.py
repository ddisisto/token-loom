"""The load-time validator: eight checks, two of which have a scope that matters.

Getting a scope wrong here is worse than omitting the check, because it either
fires on correct trees or stays silent on broken ones. The pair to watch is
coverage:

- **Strong** (checks every run, deleted included) -- every byte of a complete
  span is covered exactly once, contiguously. This is what the operations
  preserve; nothing may lose or duplicate a piece.
- **Prefix** (live runs only) -- the live pieces of a span cover a contiguous
  prefix from byte 0, possibly none of it. This is the form that survives
  delete, which can only ever strip a span's tail.

The prefix form cannot actually fail on a tree that passes the strong one. A
span's pieces lie along a single root-to-leaf path in order, and deletion takes
whole subtrees, so the live subset is always a prefix of that chain. It is kept
anyway, as a standing guard on `delete`: an implementation that stopped
cascading would show up here and nowhere else.

`PHASE-1.md` has the reasoning, including why a vacuum would retire the strong
form rather than satisfy it.
"""
from __future__ import annotations

from core.store import BulkStore, spelled
from core.tree import COUNTERFACTUAL, HUMAN, KINDS, SAMPLED, Tree


class Invalid(Exception):
    """Raised on load. The message lists every problem, not just the first."""

    def __init__(self, problems: list[str]):
        self.problems = problems
        super().__init__(f'{len(problems)} problem(s):\n  ' + '\n  '.join(problems))


def validate(tree: Tree, store: BulkStore | None = None) -> list[str]:
    """Every problem found, as readable strings. Empty means the tree is sound."""
    problems: list[str] = []
    live = tree.live_runs()

    _check_links(tree, problems)
    # the remaining structural checks assume ids resolve, so stop if they do not
    if problems:
        return problems

    _check_pieces(tree, problems)
    _check_chain(tree, problems)
    _check_coverage(tree, live, problems)
    _check_spans(tree, problems)
    if store is not None:
        _check_tokens(tree, store, problems)
    return problems


def _check_links(tree: Tree, problems: list[str]) -> None:
    """3. Parent and child agree, ids resolve, and everything hangs off the root."""
    if tree.root not in tree.runs:
        problems.append(f'root {tree.root} is not a run')
        return
    for run in tree.runs.values():
        if run.parent is not None and run.parent not in tree.runs:
            problems.append(f'{run.id}: parent {run.parent} does not exist')
        for child in run.children:
            if child not in tree.runs:
                problems.append(f'{run.id}: child {child} does not exist')
            elif tree.runs[child].parent != run.id:
                problems.append(f'{run.id}: child {child} names parent '
                                f'{tree.runs[child].parent}')
        for piece in run.pieces:
            if piece.span not in tree.spans:
                problems.append(f'{run.id}: piece names missing span {piece.span}')
    if problems:
        return

    for run in tree.runs.values():
        if run.parent is not None and run.id not in tree.runs[run.parent].children:
            problems.append(f'{run.id}: parent {run.parent} does not list it')
    if tree.runs[tree.root].parent is not None:
        problems.append(f'root {tree.root} has a parent')

    reached = tree.live_runs() | _dead_subtrees(tree)
    for run_id in tree.runs:
        if run_id not in reached:
            problems.append(f'{run_id}: not reachable from the root')

    for span_id in tree.deleted:
        if span_id not in tree.runs:
            problems.append(f'deleted names missing run {span_id}')


def _dead_subtrees(tree: Tree) -> set[str]:
    """Every run under a deleted subtree root -- reachable, but not live."""
    found: set[str] = set()
    stack = [r for r in tree.deleted if r in tree.runs]
    while stack:
        current = stack.pop()
        if current in found:
            continue
        found.add(current)
        stack.extend(tree.runs[current].children)
    return found


def _check_pieces(tree: Tree, problems: list[str]) -> None:
    """1. Every piece range is inside its span, and empty means in flight."""
    for run in tree.runs.values():
        for piece in run.pieces:
            span = tree.spans[piece.span]
            limit = span.length if span.complete else 0
            if not 0 <= piece.start <= piece.end <= limit:
                problems.append(
                    f'{run.id}: piece {tuple(piece)} outside {piece.span} '
                    f'(0..{limit})')
            elif piece.length == 0:
                # legal only for a span with no bytes: one in flight, or one
                # aborted before its first token arrived. Either way the run
                # cannot have grown past it, so it is the last piece.
                if span.length != 0:
                    problems.append(
                        f'{run.id}: empty piece on {piece.span}, which has bytes')
                elif piece is not run.pieces[-1]:
                    problems.append(
                        f'{run.id}: empty piece on {piece.span} is not last')


def _check_chain(tree: Tree, problems: list[str]) -> None:
    """2. Absolute offsets accumulate down the tree, and the root starts at 0."""
    if tree.runs[tree.root].start != 0:
        problems.append(f'root {tree.root} starts at '
                        f'{tree.runs[tree.root].start}, not 0')
    for run in tree.runs.values():
        if run.parent is None:
            continue
        expected = tree.runs[run.parent].end
        if run.start != expected:
            problems.append(f'{run.id}: starts at {run.start}, but '
                            f'{run.parent} ends at {expected}')


def _tiles(pieces, limit: int) -> str | None:
    """Do these ranges cover [0, limit) exactly once, contiguously?"""
    at = 0
    for piece in sorted(pieces, key=lambda p: p.start):
        if piece.start < at:
            return f'overlap at {piece.start}'
        if piece.start > at:
            return f'gap at {at}..{piece.start}'
        at = piece.end
    if at != limit:
        return f'covers {at} of {limit} bytes'
    return None


def _check_coverage(tree: Tree, live: set[str], problems: list[str]) -> None:
    """4 and 5. The two coverage forms, each over the run set it holds for."""
    for span in tree.spans.values():
        if not span.complete:
            continue

        every = [p for _, _, p in tree.pieces_of(span.id)]
        fault = _tiles(every, span.length)
        if fault:
            problems.append(f'{span.id}: strong coverage -- {fault}')

        reachable = [p for _, _, p in tree.pieces_of(span.id, runs=live)]
        if reachable:
            covered = sum(p.length for p in reachable)
            fault = _tiles(reachable, covered)
            if fault:
                problems.append(f'{span.id}: prefix coverage -- {fault}')
            elif min(p.start for p in reachable) != 0:
                problems.append(f'{span.id}: live pieces do not start at byte 0')


def _check_spans(tree: Tree, problems: list[str]) -> None:
    """6 and 7. A span's own numbers, and where it says it sits."""
    for span in tree.spans.values():
        if span.kind not in KINDS:
            problems.append(f'{span.id}: unknown kind {span.kind!r}')
        if (span.text is None) != (span.end is None):
            problems.append(f'{span.id}: text and extent end disagree about '
                            f'whether it is in flight')
        elif span.complete and span.end - span.start != span.length:
            problems.append(f'{span.id}: extent {[span.start, span.end]} is '
                            f'{span.end - span.start} bytes, text is {span.length}')

        # 7. extent[0] against the run chain, via the piece holding byte 0
        anchors = [(run_id, offset) for run_id, offset, piece
                   in tree.pieces_of(span.id) if piece.start == 0]
        if not anchors:
            if span.complete:
                problems.append(f'{span.id}: no piece covers byte 0')
        else:
            run_id, offset = anchors[0]
            if offset != span.start:
                problems.append(f'{span.id}: says it starts at {span.start}, but '
                                f'its first piece sits at {offset} in {run_id}')


def _check_tokens(tree: Tree, store: BulkStore, problems: list[str]) -> None:
    """8 and 9. A span's text is what its tokens spell, and sampling terminates."""
    terminated = store.terminated()
    for span in tree.spans.values():
        rows = store.tokens(span.id)

        if span.kind == HUMAN:
            if rows:
                problems.append(f'{span.id}: human span has {len(rows)} token rows')
            continue

        if span.kind == COUNTERFACTUAL and len(rows) != 1:
            problems.append(f'{span.id}: counterfactual span has {len(rows)} '
                            f'token rows, expected 1')

        # 9. only a sampled span was ever in flight, so only it terminates
        if span.kind == SAMPLED and span.complete and span.id not in terminated:
            problems.append(f'{span.id}: complete but has no terminator')
        if not span.complete:
            continue  # in flight: its rows are still arriving

        if [t.idx for t in rows] != list(range(len(rows))):
            problems.append(f'{span.id}: token indices are not contiguous from 0')
            continue
        written = spelled(rows)
        if written != span.text:
            problems.append(f'{span.id}: text is {span.text!r} but its tokens '
                            f'spell {written!r}')
