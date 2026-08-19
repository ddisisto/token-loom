"""The load-time validator: eight checks, four structural.

Eight is fewer than a validator over this data usually needs, and the reason is
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

Check 8 is the exception to all of the above, and the reason it arrived late.
It is the one place where there *are* two records of the same fact -- the tree
says which spans exist, the bulk store says which spans have rows -- because
the two live in different files and only one of them is rewritten whole. That
is exactly the seam two writers tear.
"""
from __future__ import annotations

from core.ops import token_offsets
from core.store import BulkStore, spelled
from core.tree import COUNTERFACTUAL, GIVEN, KINDS, SAMPLED, Tree, id_order


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
        _check_orphans(tree, store, problems)
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

        if span.kind == GIVEN:
            if rows:
                problems.append(f'{span.id}: given span has {len(rows)} token rows')
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


def _check_orphans(tree: Tree, store: BulkStore, problems: list[str]) -> None:
    """8. No bulk row names a span the tree has no record of.

    This is the half that catches damage already done, where the directory lock
    only prevents new damage. Two processes writing one directory clobber
    `tree.json` whole; the bulk store is append-only and survives, so what a
    torn tree leaves behind is rows for spans that are no longer named anywhere.

    **A soft-deleted span is not one of them**, and getting that wrong would
    fire this on every tree that has ever had a delete. Delete marks addresses
    in `tree.deleted` and removes nothing from `tree.spans`; the store is not
    touched at all. So a deleted subtree's rows are named by spans that are
    still present, and the membership test below sees them. The condition is
    *absent from the tree entirely*, which soft delete never produces and only a
    lost write can.

    **What this catches that check 6 does not, and the reverse.** They divide
    the same accident. When a re-minted id lands on rows from the span it
    replaced, check 6 compares the new span's `text` against what its rows spell
    and objects -- but only where the two disagree, so stale *counterfactual*
    ranks at indices the new span also has slip past it, and so does a whole
    span whose bytes happen to match. This check does not look at bytes at all:
    it asks whether anyone still claims the rows. It therefore catches the tree
    losing spans the store remembers, which check 6 cannot see because it walks
    the tree and a lost span is not there to walk. Neither is a weaker form of
    the other, and a tree that fails only one of them says which direction the
    damage went.

    Token rows are the whole population asked about, and `spans_with_tokens` is
    why: `ops.complete` writes tokens for every span that gets rows, and writes
    them before the counterfactuals and the terminator. A span with
    counterfactual rows and no token rows is not a state any operation produces,
    so widening the query would add a scan for a case that cannot arise -- and
    if one ever did, check 6 would already be objecting that the span's text and
    its tokens disagree.
    """
    for span_id in sorted(store.spans_with_tokens() - set(tree.spans),
                          key=id_order):
        problems.append(f'{span_id}: the bulk store holds token rows for it, '
                        f'but the tree has no such span')


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
