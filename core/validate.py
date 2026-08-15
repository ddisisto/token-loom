"""The load-time validator: seven checks, four structural.

Seven is fewer than a validator over this data usually needs, and the reason is
worth stating once here. A span carries its own attachment, so there is exactly
one representation of where each byte sits. Most of what a validator does is
hold two representations to agreeing, and there is no second one:

- **that every byte of a span is covered exactly once** has nothing to tile
- **that the live part of a span is a contiguous prefix** is the shape
  `Tree.live` answers in, and no other shape is available
- **that a stored absolute offset agrees with its parent's** has nothing
  stored, since `Tree.absolute` derives it

Nor can a span disagree with itself about being in flight: `text` is the only
field that says so and `Span.complete` reads it.

What is checkable here instead is that an *address* lies on the path it claims
to -- check 3's slice clause and check 5. An absolute offset could only be
checked against arithmetic; an address can be checked against the tree.
"""
from __future__ import annotations

from core.ops import token_offsets
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

    _check_parents(tree, problems)
    # everything below walks ancestry, so stop if addresses do not resolve
    if problems:
        return problems

    _check_spans(tree, problems)
    _check_deleted(tree, problems)
    if store is not None:
        _check_tokens(tree, store, problems)
    return problems


def _check_parents(tree: Tree, problems: list[str]) -> None:
    """1 and 2. Every parent address resolves, and no chain runs forever."""
    for span in tree.spans.values():
        parent = span.parent
        if parent is None:
            continue
        if parent.span not in tree.spans:
            problems.append(f'{span.id}: parent {parent.span} does not exist')
        else:
            limit = tree.spans[parent.span].length
            if not 0 <= parent.offset <= limit:
                problems.append(
                    f'{span.id}: anchored at {parent.offset} in {parent.span}, '
                    f'which has {limit} bytes')
    if problems:
        return

    # 2. one pass over all chains, memoised, so a deep tree stays linear
    settled: set[str] = set()
    for start in tree.spans.values():
        walked: list[str] = []
        visiting: set[str] = set()
        current = start
        while current is not None and current.id not in settled:
            if current.id in visiting:
                problems.append(f'{current.id}: parent chain cycles')
                break
            visiting.add(current.id)
            walked.append(current.id)
            current = (tree.spans[current.parent.span]
                       if current.parent is not None else None)
        settled.update(walked)


def _check_spans(tree: Tree, problems: list[str]) -> None:
    """3. A span's own record, and where it says its prompt started.

    The slice clause is the one that earns its keep. A slice start is an
    address, so it can be held to lying on the span's own ancestry -- naming a
    span on some other branch is a bug a root-relative offset could not express,
    let alone catch.
    """
    for span in tree.spans.values():
        if span.kind not in KINDS:
            problems.append(f'{span.id}: unknown kind {span.kind!r}')
        if span.kind == COUNTERFACTUAL and not span.origin:
            problems.append(f'{span.id}: counterfactual span has no origin')

        if span.slice_start is None:
            continue
        start = span.slice_start
        # the slice ends at the generation point, so it lies along the path to
        # this span's parent -- itself included, up to the offset used
        path = {step.span: step.offset for step in tree.ancestry(span.parent)}
        if start.span not in path:
            problems.append(f'{span.id}: slice starts in {start.span}, which is '
                            f'not on its path')
        elif start.offset > path[start.span]:
            problems.append(f'{span.id}: slice starts at {start.offset} in '
                            f'{start.span}, past the {path[start.span]} bytes '
                            f'of it on the path')


def _check_deleted(tree: Tree, problems: list[str]) -> None:
    """4. Every deletion address resolves."""
    for pos in tree.deleted:
        if pos.span not in tree.spans:
            problems.append(f'deleted names missing span {pos.span}')
        else:
            limit = tree.spans[pos.span].length
            if not 0 <= pos.offset <= limit:
                problems.append(f'deleted at {pos.offset} in {pos.span}, which '
                                f'has {limit} bytes')


def _check_tokens(tree: Tree, store: BulkStore, problems: list[str]) -> None:
    """5, 6 and 7. Provenance against the bulk store."""
    terminated = store.terminated()
    for span in tree.spans.values():
        rows = store.tokens(span.id)

        if span.kind == HUMAN:
            if rows:
                problems.append(f'{span.id}: human span has {len(rows)} token rows')
            continue

        if span.kind == COUNTERFACTUAL:
            if len(rows) != 1:
                problems.append(f'{span.id}: counterfactual span has {len(rows)} '
                                f'token rows, expected 1')
            _check_origin(tree, store, span, problems)

        # 7. only a sampled span was ever in flight, so only it terminates
        if span.kind == SAMPLED and span.complete and span.id not in terminated:
            problems.append(f'{span.id}: complete but has no terminator')
        if not span.complete:
            continue  # in flight: its rows are still arriving

        # 6. the check that earns its keep three times over -- it is the only
        # thing that would catch byte-fallback tokens being mishandled, what
        # makes a `text` field and a `bytes` blob safe to hold the same
        # information, and what a future vacuum has to pass
        if [t.idx for t in rows] != list(range(len(rows))):
            problems.append(f'{span.id}: token indices are not contiguous from 0')
            continue
        written = spelled(rows)
        if written != span.text:
            problems.append(f'{span.id}: text is {span.text!r} but its tokens '
                            f'spell {written!r}')


def _check_origin(tree: Tree, store: BulkStore, span, problems: list[str]) -> None:
    """5. A counterfactual attaches exactly where its origin says it does.

    The two records are written together and overlap deliberately: `origin`
    says which counterfactual was taken, `parent` says where it hangs. Nothing
    else would notice them drifting apart.
    """
    origin, parent = span.origin, span.parent
    if not origin or parent is None:
        return
    source, index = origin.get('span'), origin.get('index')
    if source != parent.span:
        problems.append(f'{span.id}: branches off {parent.span} but its origin '
                        f'names {source}')
        return
    offsets = token_offsets(store, source)
    if index is None or index >= len(offsets) - 1:
        problems.append(f'{span.id}: origin names token {index} of {source}, '
                        f'which has {max(len(offsets) - 1, 0)}')
    elif offsets[index] != parent.offset:
        problems.append(f'{span.id}: anchored at {parent.offset} in {source}, '
                        f'but token {index} starts at {offsets[index]}')
