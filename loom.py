#!/usr/bin/env python
"""token loom, from the command line.

The deliverable that makes Phase 1 usable rather than merely complete, and the
posture the project claims: anything that only works by clicking is half-built.
Everything the web front end will do in Phase 2 is doable here first, which is
what makes replacing that front end survivable.

    loom.py new                          start a tree
    loom.py author 'The sea was'         add text at the cursor
    loom.py gen -n 4 --length 40         four continuations from the cursor
    loom.py show                         the tree
    loom.py read r4                      one path, whole
    loom.py tokens s2                    the overlay: logprobs, alternatives
    loom.py branch s2 3 1                take the road not taken
    loom.py split r2:9                   make a branch point mid-run
    loom.py delete r5                    soft, and it cascades

The tree directory comes from -d, or $LOOM_TREE, or ./data/tree. A **position**
is `run` for that run's tip, `run:offset` for a byte offset within it, or
`run@absolute` for an absolute offset resolved along that run's path. With no
position given, commands use the cursor -- which is `selected` in the file, and
the one thing there keyed by a run id.
"""
from __future__ import annotations

import argparse
import os
import sys

from core import Invalid, Position, Server, Truncated, at, split, validate
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


def show(session: Session, verbose: bool = False) -> None:
    tree = session.tree
    live = tree.live_runs()
    cursor = tree.selected or {}

    def walk(run_id: str, indent: str, last: bool, root: bool = False) -> None:
        run = tree.runs[run_id]
        joint = '' if root else ('└─ ' if last else '├─ ')
        dead = '' if run_id in live else '  (deleted)'
        here = ' ←' if cursor.get('run') == run_id else ''
        spans = ' '.join(f'{kind_mark(tree.spans[p.span].kind)}{p.span}'
                         for p in run.pieces) or '·'
        print(f'{indent}{joint}{run_id}  {run.start}..{run.end}  {spans}{dead}{here}')

        body = indent + ('   ' if last or root else '│  ')
        if run.pieces:
            print(f'{body}  {show_text(tree.run_bytes(run_id), None if verbose else 68)}')
        children = run.children
        for i, child in enumerate(children):
            walk(child, body, i == len(children) - 1)

    walk(tree.root, '', True, root=True)

    problems = validate(tree, session.store)
    print(f'\n{len(tree.runs)} runs, {len(tree.spans)} spans, '
          f'{len(tree.params)} parameter sets, {len(live)} live')
    if problems:
        print(f'INVALID: {len(problems)} problem(s)')
        for p in problems:
            print(f'  {p}')


def show_tokens(session: Session, span_id: str) -> None:
    """The overlay against the anchor: what each token is, and where it sits."""
    span = session.tree.spans[span_id]
    store = session.store
    tokens = store.tokens(span_id)
    offsets = token_offsets(store, span_id)

    detail = [f'{span.kind}', f'extent {span.start}..{span.end}']
    if span.params:
        detail.append(span.params)
    if span.seed is not None:
        detail.append(f'seed {span.seed}')
    if span.batch:
        detail.append(f'batch {span.batch}[{span.index}]')
    if span.slice_start is not None:
        detail.append(f'slice from {span.slice_start}')
    reason = store.terminator(span_id)
    detail.append(reason or 'IN FLIGHT')
    print(f'{span_id}  ' + '  '.join(detail))
    if span.origin:
        o = span.origin
        print(f'  from {o["span"]}[{o["index"]}] token {o["token_id"]}')
    if span.params:
        print(f'  {session.tree.params[span.params]}')
    print()

    if not tokens:
        print('  (no tokens)')
        return

    print(f'  {"byte":>6} {"id":>7}  {"token":<16} {"logprob":>9}   alternatives')
    for token in tokens:
        # absolute byte offset, so it lines up with everything else printed
        byte = span.start + offsets[token.idx]
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

def known_run(session: Session, run_id: str) -> str:
    if run_id not in session.tree.runs:
        raise SystemExit(f'no run {run_id!r}; see `show`')
    return run_id


def parse_position(session: Session, text: str | None) -> Position:
    tree = session.tree
    if not text:
        cursor = tree.selected
        if not cursor:
            raise SystemExit('no cursor set; give a position, or see `show`')
        return Position(cursor['run'], cursor['offset'])
    try:
        if '@' in text:
            run, _, offset = text.partition('@')
            return at(tree, known_run(session, run), int(offset))
        if ':' in text:
            run, _, offset = text.partition(':')
            return Position(known_run(session, run), int(offset))
    except ValueError as e:
        raise SystemExit(f'{text}: {e}')
    return session.tip(known_run(session, text))


def set_cursor(session: Session, pos: Position) -> None:
    session.tree.selected = {'run': pos.run, 'offset': pos.offset}
    session.save()


def run_of(session: Session, span_id: str) -> str:
    """The last run a span reaches, which a split may have moved it into."""
    return max(session.tree.pieces_of(span_id), key=lambda item: item[2].start)[0]


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

    sub.add_parser('show', help='the tree').add_argument(
        '-v', '--verbose', action='store_true', help='untruncated text')

    p = sub.add_parser('read', help='one path, whole')
    p.add_argument('run', nargs='?')

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

    sub.add_parser('split', help='make a branch point').add_argument('position')
    sub.add_parser('delete', help='soft delete, cascading').add_argument('run')
    sub.add_parser('restore', help='undo a delete').add_argument('run')
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

    try:
        return dispatch(session, args)
    finally:
        session.close()


def dispatch(session: Session, args) -> int:
    tree = session.tree

    if args.command == 'show':
        show(session, args.verbose)

    elif args.command == 'read':
        run = args.run or (tree.selected or {}).get('run')
        if not run:
            print('leaves:', ' '.join(session.leaves()))
            return 0
        known_run(session, run)
        sys.stdout.write(tree.path_bytes(run).decode('utf-8', errors='replace'))
        sys.stdout.write('\n')

    elif args.command == 'tokens':
        if args.span not in tree.spans:
            raise SystemExit(f'no span {args.span!r}')
        show_tokens(session, args.span)

    elif args.command == 'author':
        pos = parse_position(session, args.position)
        span = session.author(pos, args.text.encode('utf-8'))
        set_cursor(session, session.tip(run_of(session, span.id)))
        print(f'{span.id}  {span.start}..{span.end}  '
              f'{show_text(span.text)}')

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
            print(f'{span.id}  {run_of(session, span.id)}  '
                  f'{session.store.terminator(span.id):>7}  '
                  f'{show_text(span.text, 70)}')
        set_cursor(session, session.tip(run_of(session, spans[0].id)))

    elif args.command == 'branch':
        if args.span not in tree.spans:
            raise SystemExit(f'no span {args.span!r}')
        span = session.branch(args.span, args.index, args.rank)
        set_cursor(session, session.tip(run_of(session, span.id)))
        print(f'{span.id}  {span.start}..{span.end}  {show_text(span.text)}')
        print(show_text(tree.path_bytes(run_of(session, span.id)), 100))

    elif args.command == 'split':
        pos = parse_position(session, args.position)
        before = set(tree.runs)
        anchor = split(tree, pos)
        session.save()
        made = set(tree.runs) - before
        print(f'{anchor} ends at {tree.runs[anchor].end}'
              + (f'; {made.pop()} holds the rest' if made else '; already a boundary'))

    elif args.command == 'delete':
        try:
            session.delete(known_run(session, args.run))
        except ValueError as e:
            raise SystemExit(str(e))
        print(f'{args.run} deleted; {len(tree.live_runs())} runs live')

    elif args.command == 'restore':
        session.restore(known_run(session, args.run))
        print(f'{args.run} restored; {len(tree.live_runs())} runs live')

    elif args.command == 'cursor':
        pos = parse_position(session, args.position)
        set_cursor(session, pos)
        print(f'cursor at {pos.run}:{pos.offset} '
              f'(absolute {tree.runs[pos.run].start + pos.offset})')

    elif args.command == 'slice':
        pos = parse_position(session, args.position)
        start, end, text = session.slice(pos, args.prompt_length)
        print(f'{start}..{end}  {end - start} bytes')
        sys.stdout.write(text.decode('utf-8', errors='replace'))
        sys.stdout.write('\n')

    return 0


if __name__ == '__main__':
    sys.exit(main())
