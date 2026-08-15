#!/usr/bin/env python
"""token loom, from the command line.

The deliverable that makes the core usable rather than merely complete, and the
posture the project claims: anything that only works by clicking is half-built.
Everything the web front end will do in Phase 2 is doable here first, which is
what makes replacing that front end survivable.

    loom.py new                          start a tree
    loom.py author 'The sea was'         add text at the cursor
    loom.py gen -n 4 --length 40         four continuations from the cursor
    loom.py show                         the tree
    loom.py read s4                      one path, whole
    loom.py tokens s2                    the overlay: logprobs, alternatives
    loom.py branch s2 3 1                take the road not taken
    loom.py delete s5+9                  soft, and it cascades

The tree directory comes from -d, or $LOOM_TREE, or ./data/tree. A **position**
is `span` for that span's tip, `span+offset` for a byte offset within it, or
`.` for the root -- the point before any span, where an initial prompt goes.
With no position given, commands use the cursor.

There is no `split`. A branch mid-span is a child anchored at an offset, so
there is nothing to divide and no boundary to make first. Runs still exist in
what `show` prints, as a maximal stretch with no branch point in it, but they
are computed from the spans rather than stored -- which is why their labels are
positions rather than ids of their own.
"""
from __future__ import annotations

import argparse
import os
import sys

from core import Invalid, Position, Server, Truncated, validate
from core.ops import token_offsets
from core.session import Session

DEFAULT_DIR = os.environ.get('LOOM_TREE', 'data/tree')


# -- rendering -------------------------------------------------------------

def show_text(raw: bytes, limit: int | None = 60) -> str:
    """Bytes as something readable, without pretending they always decode."""
    text = raw.decode('utf-8', errors='replace')
    if limit is not None and len(text) > limit:
        text = text[:limit - 1] + '…'
    return repr(text)


def kind_mark(kind: str) -> str:
    return {'human': 'H', 'sampled': 'S', 'counterfactual': 'C'}.get(kind, '?')


def fmt(pos: Position | None) -> str:
    """A position, in the syntax that would be typed back in."""
    return '·' if pos is None else f'{pos.span}+{pos.offset}'


def outline(tree, reach: dict[str, int], span_id: str | None, offset: int,
            resuming: bool) -> tuple[list[tuple[str, int, int]], list[tuple]]:
    """One derived run from a starting point: its pieces, and where it forks.

    A run is a maximal stretch with no branch point in it. This computes that
    list and throws it away on every render, which is the whole of what "runs
    are derived" means in practice -- the boundaries carry no meaning of their
    own, so there is nothing to keep.

    `resuming` says the children anchored exactly at `offset` have already been
    emitted by the fork that sent us here. Without it a span with a branch at
    byte 0 -- which `branch s 0 r` produces -- would either lose that branch or
    fork into itself forever.
    """
    pieces: list[tuple[str, int, int]] = []
    while True:
        if span_id is None:
            roots = [c for _, c in tree.children_of(None) if c in reach]
            if len(roots) != 1:
                return pieces, [(c, 0, False) for c in roots]
            span_id, offset, resuming = roots[0], 0, False
            continue

        limit = reach[span_id]
        kids = [(off, c) for off, c in tree.children_of(span_id) if c in reach]
        cuts = sorted({off for off, _ in kids
                       if off < limit and (off > offset
                                           or (off == offset and not resuming))})
        if cuts:
            here = cuts[0]
            pieces.append((span_id, offset, here))
            forks = [(c, 0, False) for off, c in kids if off == here]
            forks.append((span_id, here, True))   # the span carries on past it
            return pieces, forks

        pieces.append((span_id, offset, limit))
        onward = [c for off, c in kids if off == limit]
        if len(onward) == 1:
            # one continuation is not a branch: the run simply extends, which
            # is how it comes to cover several spans at different temperatures
            span_id, offset, resuming = onward[0], 0, False
            continue
        return pieces, [(c, 0, False) for c in onward]


def build(tree, reach: dict[str, int], start: tuple) -> dict:
    """The derived run tree, ready to print.

    A run of zero width is not a run -- it is a fork point, which is what a
    branch anchored at byte 0 of a span that also continues produces. Its
    branches are spliced into its parent's, so the display shows the fork where
    it is rather than inventing a node with no text in it.
    """
    pieces, forks = outline(tree, reach, *start)
    children: list[dict] = []
    for fork in forks:
        child = build(tree, reach, fork)
        children.extend(child['children'] if not child['width'] else [child])
    return {'pieces': pieces,
            'width': sum(end - begin for _, begin, end in pieces),
            'children': children}


def show(session: Session, verbose: bool = False, everything: bool = False) -> None:
    tree = session.tree
    reach = ({s.id: s.length for s in tree.spans.values()} if everything
             else tree.live())
    dead = set(tree.spans) - set(tree.live())
    cursor = tree.selected
    marked = False

    def walk(node: dict, indent: str, last: bool, root: bool = False) -> None:
        nonlocal marked
        pieces = node['pieces']
        joint = '' if root else ('└─ ' if last else '├─ ')

        if node['width']:
            head = Position(pieces[0][0], pieces[0][1])
            at = tree.absolute(head)
            marks = ' '.join(f'{kind_mark(tree.spans[s].kind)}{s}'
                             for s, _, _ in pieces)
            gone = '  (deleted)' if pieces[0][0] in dead else ''
            # a cursor on a run boundary belongs to both; the earlier one wins,
            # which is the same canonical choice `address_at` makes
            here = ''
            if not marked and cursor and any(
                    s == cursor.span and begin <= cursor.offset <= end
                    for s, begin, end in pieces):
                here, marked = ' ←', True
            print(f'{indent}{joint}{fmt(head)}  {at}..{at + node["width"]}  '
                  f'{marks}{gone}{here}')

            body = indent + ('   ' if last or root else '│  ')
            text = b''.join(tree.spans[s].text[begin:end]
                            for s, begin, end in pieces if tree.spans[s].text)
            print(f'{body}  {show_text(text, None if verbose else 68)}')
        else:
            body = indent

        for i, child in enumerate(node['children']):
            walk(child, body, i == len(node['children']) - 1)

    root = build(tree, reach, (None, 0, False))
    if not root['width'] and not root['children']:
        print('(empty)')
    else:
        walk(root, '', True, root=True)

    problems = validate(tree, session.store)
    print(f'\n{len(tree.spans)} spans, {len(dead)} unreachable, '
          f'{len(tree.params)} interned')
    if dead and not everything:
        print('  (`show -a` renders the deleted ones too)')
    if problems:
        print(f'INVALID: {len(problems)} problem(s)')
        for p in problems:
            print(f'  {p}')


def show_tokens(session: Session, span_id: str) -> None:
    """The overlay against the anchor: what each token is, and where it sits."""
    tree = session.tree
    span = tree.spans[span_id]
    store = session.store
    tokens = store.tokens(span_id)
    offsets = token_offsets(store, span_id)
    base = tree.absolute(span.parent)

    detail = [f'{span.kind}', f'at {fmt(span.parent)}',
              f'{base}..{base + span.length}']
    if span.params:
        detail.append(span.params)
    if span.seed is not None:
        detail.append(f'seed {span.seed}')
    if span.batch:
        detail.append(f'batch {span.batch}[{span.index}]')
    if span.slice_start is not None:
        detail.append(f'slice from {fmt(span.slice_start)}')
    reason = store.terminator(span_id)
    detail.append(reason or 'IN FLIGHT')
    print(f'{span_id}  ' + '  '.join(detail))
    if span.origin:
        o = span.origin
        print(f'  from {o["span"]}[{o["index"]}] token {o["token_id"]}')
    if span.params:
        print(f'  {tree.params[span.params]}')
    print()

    if not tokens:
        print('  (no tokens)')
        return

    print(f'  {"byte":>6} {"id":>7}  {"token":<16} {"logprob":>9}   alternatives')
    for token in tokens:
        # absolute byte offset, so it lines up with everything else printed
        byte = base + offsets[token.idx]
        alts = []
        for c in store.counterfactuals(span_id, token.idx):
            taken = '*' if c.token_id == token.token_id else ' '
            alts.append(f'{taken}{show_text(c.bytes, 12)}({c.logprob:.2f})')
        logprob = '' if token.logprob is None else f'{token.logprob:9.4f}'
        print(f'  {byte:>6} {token.token_id:>7}  '
              f'{show_text(token.bytes, 14):<16} {logprob}   {" ".join(alts)}')
    print('\n  * marks the alternative that was actually sampled; it is not '
          'always ranked first,\n    and at higher temperatures it is often '
          'not in the list at all.')


# -- positions -------------------------------------------------------------

def known_span(session: Session, span_id: str) -> str:
    if span_id not in session.tree.spans:
        raise SystemExit(f'no span {span_id!r}; see `show`')
    return span_id


def parse_position(session: Session, text: str | None) -> Position | None:
    """`span`, `span+offset`, or `.` for the root. Empty means the cursor."""
    if not text:
        return session.tree.selected
    if text == '.':
        return None
    if '+' in text:
        span_id, _, offset = text.partition('+')
        try:
            return Position(known_span(session, span_id), int(offset))
        except ValueError as e:
            raise SystemExit(f'{text}: {e}')
    return session.tip(known_span(session, text))


def set_cursor(session: Session, pos: Position | None) -> None:
    session.tree.selected = pos
    session.save()


# -- commands --------------------------------------------------------------

def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog='loom.py', description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('-d', '--dir', default=DEFAULT_DIR,
                        help=f'tree directory (default {DEFAULT_DIR})')
    parser.add_argument('--server', default=None, help='llama-server base URL')
    sub = parser.add_subparsers(dest='command', required=True)

    p = sub.add_parser('new', help='create a tree')
    p.add_argument('--seed', type=int, default=None, help='base seed')

    p = sub.add_parser('show', help='the tree')
    p.add_argument('-v', '--verbose', action='store_true', help='untruncated text')
    p.add_argument('-a', '--all', action='store_true', help='deleted subtrees too')

    p = sub.add_parser('read', help='one path, whole')
    p.add_argument('position', nargs='?')

    sub.add_parser('tokens', help='the token overlay for a span').add_argument('span')

    p = sub.add_parser('author', help='add human text at a position')
    p.add_argument('text')
    p.add_argument('position', nargs='?')

    p = sub.add_parser('gen', help='generate from a position')
    p.add_argument('position', nargs='?')
    p.add_argument('-n', type=int, default=1, help='continuations')
    p.add_argument('--length', type=int, default=32, help='tokens')
    p.add_argument('--temp', type=float, default=0.9)
    p.add_argument('--top-p', type=float, default=1.0)
    p.add_argument('--top-n', type=int, default=3, help='counterfactuals, min 1')
    p.add_argument('--prompt-length', type=int, default=6000, help='bytes')
    p.add_argument('--stop', action='append', default=[])

    p = sub.add_parser('branch', help='take a counterfactual')
    p.add_argument('span')
    p.add_argument('index', type=int)
    p.add_argument('rank', type=int)

    sub.add_parser('delete', help='soft delete, cascading').add_argument('position')
    sub.add_parser('restore', help='undo a delete').add_argument('position')
    sub.add_parser('cursor', help='move the cursor').add_argument('position')

    p = sub.add_parser('slice', help='the prompt a position would send')
    p.add_argument('position', nargs='?')
    p.add_argument('--prompt-length', type=int, default=6000)

    args = parser.parse_args(argv)
    server = Server(args.server) if args.server else Server()

    if args.command == 'new':
        session = Session.create(args.dir, base_seed=args.seed, server=server)
        print(f'{args.dir}: tree {session.tree.tree_id}, '
              f'base seed {session.tree.base_seed}')
        session.close()
        return 0

    try:
        session = Session.open(args.dir, server=server)
    except FileNotFoundError:
        raise SystemExit(f'no tree at {args.dir}; `loom.py -d {args.dir} new` first')
    except Invalid as e:
        raise SystemExit(f'{args.dir} did not validate:\n{e}')
    except ValueError as e:
        # a wrong format marker, or a span from a shape that kept its structure
        # somewhere else. Both are "this file is not ours", and both used to
        # arrive as a traceback from inside the loader.
        raise SystemExit(f'{args.dir} is not a tree this reads: {e}')

    try:
        return dispatch(session, args)
    finally:
        session.close()


def dispatch(session: Session, args) -> int:
    tree = session.tree

    if args.command == 'show':
        show(session, args.verbose, args.all)

    elif args.command == 'read':
        pos = parse_position(session, args.position)
        if pos is None:
            print('leaves:', ' '.join(session.leaves()) or '(none)')
            return 0
        sys.stdout.write(tree.path_bytes(pos).decode('utf-8', errors='replace'))
        sys.stdout.write('\n')

    elif args.command == 'tokens':
        show_tokens(session, known_span(session, args.span))

    elif args.command == 'author':
        pos = parse_position(session, args.position)
        span = session.author(pos, args.text.encode('utf-8'))
        set_cursor(session, session.tip(span.id))
        print(f'{span.id}  at {fmt(span.parent)}  {show_text(span.text)}')

    elif args.command == 'gen':
        pos = parse_position(session, args.position)
        settings = session.settings(
            temperature=args.temp, top_p=args.top_p, top_n=args.top_n,
            length=args.length, stop=args.stop,
            prompt_length=args.prompt_length)
        if not session.server.alive():
            raise SystemExit(f'llama-server is not answering on '
                             f'{session.server.base}; see scripts/llama-server.sh')
        try:
            spans = session.generate(pos, settings, n=args.n)
        except Truncated as e:
            raise SystemExit(f'refused: {e}')
        for span in spans:
            print(f'{span.id}  {session.store.terminator(span.id):>7}  '
                  f'{show_text(span.text, 70)}')
        set_cursor(session, session.tip(spans[0].id))

    elif args.command == 'branch':
        known_span(session, args.span)
        try:
            span = session.branch(args.span, args.index, args.rank)
        except ValueError as e:
            raise SystemExit(str(e))
        set_cursor(session, session.tip(span.id))
        print(f'{span.id}  at {fmt(span.parent)}  {show_text(span.text)}')
        print(show_text(tree.path_bytes(session.tip(span.id)), 100))

    elif args.command in ('delete', 'restore'):
        pos = parse_position(session, args.position)
        if pos is None:
            raise SystemExit('the root cannot be deleted')
        try:
            getattr(session, args.command)(pos)
        except ValueError as e:
            raise SystemExit(str(e))
        print(f'{fmt(pos)} {args.command}d; {len(tree.live())} spans live')

    elif args.command == 'cursor':
        pos = parse_position(session, args.position)
        set_cursor(session, pos)
        print(f'cursor at {fmt(pos)} (absolute {tree.absolute(pos)})')

    elif args.command == 'slice':
        pos = parse_position(session, args.position)
        start, end, text = session.slice(pos, args.prompt_length)
        print(f'{fmt(start)}..{fmt(end)}  {len(text)} bytes')
        sys.stdout.write(text.decode('utf-8', errors='replace'))
        sys.stdout.write('\n')

    return 0


if __name__ == '__main__':
    sys.exit(main())
