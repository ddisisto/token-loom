#!/usr/bin/env python
"""token loom, from the command line.

The deliverable that makes the core usable rather than merely complete, and the
posture the project claims: anything that only works by clicking is half-built.
Everything the web front end will do in Phase 2 is doable here first, which is
what makes replacing that front end survivable.

    loom.py new                          start a tree
    loom.py author 'The sea was'         add text at the cursor
    loom.py gen -n 4 --length 40         four continuations from the cursor
    loom.py gen -n 20 --stay             twenty more, cursor left in place
    loom.py show                         the tree
    loom.py show s2 --depth 1            one subtree, one level of forks
    loom.py read s4                      one path, whole
    loom.py tokens s2                    the overlay: logprobs, alternatives
    loom.py branch s2 3 1                take the road not taken
    loom.py batches --params p1          generation calls, one condition
    loom.py diverge                      how far the siblings of a call agree
    loom.py params                       the interned parameter sets
    loom.py delete s5+9                  soft, and it cascades

The tree directory comes from -d, or $LOOM_TREE, or ./data/tree. A **position**
is `span` for that span's tip, `span+offset` for a byte offset within it, or
`.` for the root -- the point before any span, where an initial prompt goes.
With no position given, commands use the cursor, which `show` marks inline.

A tree has **one writer at a time**. The commands that change something take an
exclusive lock on the directory and refuse if a server or another `loom.py`
already holds it; the commands that only look take no lock at all, so reading a
tree an API is serving is always available and never waits.

`gen` moves the cursor to the first span it made, which is what walking forward
wants and the opposite of what sampling one position repeatedly wants; `--stay`
is the second reading. Between them, `show <position> --depth n` and
`batches --params <key>` are how a sweep stays readable -- a run of twenty
siblings is three lines of tree and one line of batch, not twenty of each.

The numbers `branch` takes are the two `tokens` prints beside each alternative:
the token's `idx` down the left, and the alternative's rank at the front of its
column.

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

from core import (Incomplete, Invalid, Locked, Position, Server, Truncated,
                  validate)
from core.ops import divergence, runs, token_offsets
from core.session import Session
from core.tree import id_order

DEFAULT_DIR = os.environ.get('LOOM_TREE', 'data/tree')

# Which commands only look. The list is here rather than derived from what a
# handler happens to call, because "does this write" is a fact about the command
# a person typed and has to be knowable before the tree is opened -- the lock is
# taken at open time or not at all. Anything absent is treated as a writer,
# which is the safe direction to be wrong in: a new command refuses to run
# beside a server until someone decides it is a read.
READS = frozenset({'show', 'read', 'tokens', 'batches', 'diverge', 'params',
                   'slice'})


# -- rendering -------------------------------------------------------------

CURSOR = '‸'


def show_text(raw: bytes, limit: int | None = 60) -> str:
    """Bytes as something readable, without pretending they always decode."""
    text = raw.decode('utf-8', errors='replace')
    if limit is not None and len(text) > limit:
        text = text[:limit - 1] + '…'
    return repr(text)


def show_marked(raw: bytes, at: int, limit: int | None = 60) -> str:
    """The same, with the cursor marked at byte `at` and kept in view.

    Two things make this less trivial than inserting a character. The mark is
    at a *byte* offset and the output is characters, so the split happens on
    the bytes and each side is decoded separately -- which is also what keeps a
    cursor sitting inside a character from corrupting the half it is not in.

    And the mark has to survive truncation, or marking the position is exactly
    the thing that gets cut. So the window slides to hold it: text is shown
    from the start until the cursor would fall off the end, and from around the
    cursor after that. An elision on either side says which happened.
    """
    at = max(0, min(at, len(raw)))
    head = raw[:at].decode('utf-8', errors='replace')
    tail = raw[at:].decode('utf-8', errors='replace')
    if limit is None or len(head) + len(tail) <= limit:
        return repr(head + CURSOR + tail)

    # keep a third of the window ahead of the cursor when it is deep in the run
    keep = max(0, len(head) - (limit - limit // 3))
    left = ('…' + head[keep + 1:]) if keep else head
    room = limit - len(left)
    right = tail if len(tail) <= room else tail[:max(0, room - 1)] + '…'
    return repr(left + CURSOR + right)


def kind_mark(kind: str) -> str:
    return {'given': 'G', 'sampled': 'S', 'counterfactual': 'C'}.get(kind, '?')


def fmt(pos: Position | None) -> str:
    """A position, in the syntax that would be typed back in."""
    return '·' if pos is None else f'{pos.span}+{pos.offset}'


def run_count(node: dict) -> int:
    """Runs in a subtree, so an elision can say what it is standing in for."""
    return bool(node['width']) + sum(run_count(c) for c in node['children'])


def show(session: Session, verbose: bool = False, everything: bool = False,
         start: Position | None = None, depth: int | None = None) -> None:
    """The tree, or a subtree of it, or the top few levels of either.

    `start` and `depth` are what sits between `batches` (one call) and the
    whole tree. A sweep of six temperature bands off one prompt is hundreds of
    siblings under one node: unreadable rendered whole, and not what `batches`
    groups by either. Rooting the render at a position and capping how far it
    forks are the two cuts that make it legible, and both are pure display --
    nothing here changes what is reachable.

    So the cap is applied while walking rather than while building. The run
    tree is computed in full either way, which keeps the summary underneath
    honest about the whole tree: a depth limit hides runs, it does not make
    them stop existing.
    """
    tree = session.tree
    reach = ({s.id: s.length for s in tree.spans.values()} if everything
             else tree.live())
    dead = set(tree.spans) - set(tree.live())
    cursor = tree.selected
    marked = False

    def walk(node: dict, indent: str, last: bool, root: bool = False,
             level: int = 0) -> None:
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
            here, cursor_byte = '', None
            if not marked and cursor:
                seen = 0
                for s, begin, end in pieces:
                    if s == cursor.span and begin <= cursor.offset <= end:
                        cursor_byte = seen + cursor.offset - begin
                        break
                    seen += end - begin
                if cursor_byte is not None:
                    here, marked = ' ←', True
            print(f'{indent}{joint}{fmt(head)}  {at}..{at + node["width"]}  '
                  f'{marks}{gone}{here}')

            body = indent + ('   ' if last or root else '│  ')
            text = b''.join(tree.spans[s].text[begin:end]
                            for s, begin, end in pieces if tree.spans[s].text)
            limit = None if verbose else 68
            print(f'{body}  ' + (show_marked(text, cursor_byte, limit)
                                 if cursor_byte is not None
                                 else show_text(text, limit)))
        else:
            body = indent

        # zero width is a fork point rather than a run: it neither occupies a
        # level nor can be the thing a level cuts below, so the cap skips it
        # entirely and applies to its children as if they were the top
        if node['width'] and depth is not None and level >= depth \
                and node['children']:
            hidden = sum(run_count(c) for c in node['children'])
            print(f'{body}   … {hidden} more run(s) below; '
                  f'--depth {depth + 1} goes one further')
            return

        # a zero-width node is a fork point rather than a run -- it prints
        # nothing, so it must not consume a level either, or `--depth 1` means
        # one thing on a tree with a single root and another on a tree with five
        for i, child in enumerate(node['children']):
            walk(child, body, i == len(node['children']) - 1,
                 level=level + bool(node['width']))

    if start is not None and start.span not in reach:
        raise SystemExit(f'{fmt(start)} is not reachable; `show -a` renders '
                         f'the deleted ones too')
    begin = ((None, 0, False) if start is None
             else (start.span, start.offset, False))
    root = runs(tree, reach, begin)
    if not root['width'] and not root['children']:
        print('(empty)' if start is None else f'(nothing below {fmt(start)})')
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

    # `idx` and the rank prefixes are the two numbers `branch` takes. Printing
    # the alternatives without them meant counting columns to use the command.
    print(f'  {"idx":>4} {"byte":>6} {"id":>7}  {"token":<16} {"logprob":>9}'
          f'   alternatives, by rank')
    for token in tokens:
        # absolute byte offset, so it lines up with everything else printed
        byte = base + offsets[token.idx]
        alts = []
        for c in store.counterfactuals(span_id, token.idx):
            taken = '*' if c.token_id == token.token_id else ' '
            alts.append(f'{c.rank}{taken}{show_text(c.bytes, 12)}'
                        f'({c.logprob:.2f})')
        logprob = '' if token.logprob is None else f'{token.logprob:9.4f}'
        # a merged row stands for several tokens of one character, so it has no
        # single id or logprob to print -- the absence is the record, not a gap
        ident = '  merged' if token.token_id is None else f'{token.token_id:>7}'
        print(f'  {token.idx:>4} {byte:>6} {ident}  '
              f'{show_text(token.bytes, 14):<16} {logprob:>9}   {" ".join(alts)}')
    print(f'\n  each alternative reads <rank><taken>, so `branch {span_id} '
          f'<idx> <rank>` takes one.')
    print('  * marks the alternative that was actually sampled; it is not '
          'always ranked first,\n    and at higher temperatures it is often '
          'not in the list at all.')


def show_batches(session: Session, batch_id: str | None = None,
                 params_key: str | None = None) -> None:
    """A batch read back as the experiment it was.

    The batch id was pulled forward into Phase 1 precisely so the siblings of
    one call would be linkable afterwards, and nothing read it. This is that
    payoff: one call, its parameters, and what each continuation did with the
    same conditions and a different seed.

    `params_key` groups a level up from that. Interning is by value, so one key
    *is* one set of conditions however many calls were made under it -- which
    makes "every batch at this temperature" a selection the tree already knows
    how to make, rather than something a sweep has to keep track of itself.
    """
    tree, store = session.tree, session.store
    batches: dict[str, list] = {}
    for span in sorted(tree.spans.values(), key=lambda s: id_order(s.id)):
        if span.batch:
            batches.setdefault(span.batch, []).append(span)

    if batch_id is not None:
        if batch_id not in batches:
            raise SystemExit(f'no batch {batch_id!r}; see `batches`')
        batches = {batch_id: batches[batch_id]}
    if params_key is not None:
        if params_key not in tree.params:
            raise SystemExit(f'no parameter set {params_key!r}; see `params`')
        batches = {name: spans for name, spans in batches.items()
                   if spans[0].params == params_key}
        if not batches:
            print(f'(no batches under {params_key})')
            return
    if not batches:
        print('(no batches; nothing has been generated)')
        return

    live = tree.live()
    for name, spans in batches.items():
        spans.sort(key=lambda s: (s.index if s.index is not None else 0))
        head = spans[0]
        detail = [f'{len(spans)} span(s)', f'from {fmt(head.parent)}']
        if head.params:
            detail.append(head.params)
        print(f'{name}  ' + '  '.join(detail))
        if head.params:
            print(f'  {tree.params[head.params]}')
        for span in spans:
            reason = store.terminator(span.id) or 'IN FLIGHT'
            gone = '' if span.id in live else '  (deleted)'
            print(f'  [{span.index}] {span.id:<5} seed {span.seed:<8} '
                  f'{reason:>7}{gone}  {show_text(span.text or b"", 46)}')
        print()


def show_divergence(session: Session, batch_id: str | None = None,
                    params_key: str | None = None, profile: bool = False
                    ) -> None:
    """Sibling agreement as a number, per batch.

    The first quantitative read in the project, and the reason it is worth
    having is in RESEARCH.md: everything else there was read by eye off `show`.
    A batch is the natural unit because its spans are the siblings of one call
    -- same position, same conditions, different seed -- which is exactly the
    set the measure is defined over.

    `lock(k)` is the largest fraction sharing their first k tokens. The ratio
    lock(10)/lock(3) is the one to watch: it separates siblings that agree and
    keep agreeing from siblings that agree on an opening and then scatter, and
    those are different phenomena that a single lock number reports alike.
    """
    tree, store = session.tree, session.store
    batches: dict[str, list] = {}
    for span in sorted(tree.spans.values(), key=lambda s: id_order(s.id)):
        if span.batch:
            batches.setdefault(span.batch, []).append(span)

    if batch_id is not None:
        if batch_id not in batches:
            raise SystemExit(f'no batch {batch_id!r}; see `batches`')
        batches = {batch_id: batches[batch_id]}
    if params_key is not None:
        if params_key not in tree.params:
            raise SystemExit(f'no parameter set {params_key!r}; see `params`')
        batches = {name: spans for name, spans in batches.items()
                   if spans[0].params == params_key}
    if not batches:
        print('(no batches to compare)')
        return

    if not profile:
        print(f'{"batch":<6} {"n":>3} {"temp":>5} {"from":>8}  '
              f'{"lock1":>5} {"lock3":>5} {"lock10":>6} {"10/3":>5}  '
              f'{"common":>6} {"distinct@":>9}')
    for name, spans in sorted(batches.items(), key=lambda kv: id_order(kv[0])):
        spans.sort(key=lambda s: (s.index if s.index is not None else 0))
        head = spans[0]
        d = divergence(store, [s.id for s in spans])
        temp = (tree.params[head.params].get('temperature')
                if head.params else None)
        # undefined rather than zero when the frame itself never formed: a
        # ratio against a lock of nothing is not a small number, it is no number
        ratio = (d['lock'][10] / d['lock'][3]) if d['lock'][3] else None

        if profile:
            print(f'{name}  n={d["n"]}  temp {temp}  from {fmt(head.parent)}'
                  + (f'  {head.params}' if head.params else ''))
            print(f'  lock(1) {d["lock"][1]:.2f}  lock(3) {d["lock"][3]:.2f}  '
                  f'lock(10) {d["lock"][10]:.2f}  '
                  + ('10/3 —' if ratio is None else f'10/3 {ratio:.2f}'))
            print(f'  common prefix {d["common"]} token(s), '
                  + ('fully distinct at depth '
                     f'{d["fully_distinct_at"]}' if d['fully_distinct_at']
                     else 'never fully distinct'))
            print('  distinct paths by depth: '
                  + ' '.join(str(c) for c in d['distinct']))
            if any(d['short'].values()):
                print('  too short to reach a depth: '
                      + ', '.join(f'{k}:{v}' for k, v in d['short'].items()
                                  if v))
            print()
        else:
            print(f'{name:<6} {d["n"]:>3} {str(temp):>5} '
                  f'{fmt(head.parent):>8}  '
                  f'{d["lock"][1]:>5.2f} {d["lock"][3]:>5.2f} '
                  f'{d["lock"][10]:>6.2f} '
                  + ('    —' if ratio is None else f'{ratio:>5.2f}')
                  + f'  {d["common"]:>6} '
                  + f'{str(d["fully_distinct_at"] or "—"):>9}')


def show_params(session: Session) -> None:
    """The intern table, which was visible one span at a time and no other way.

    Interning is by value, so two entries here are two genuinely different sets
    of conditions -- which makes this the list of experiments the tree holds,
    not merely a storage detail.
    """
    tree = session.tree
    if not tree.params:
        print('(nothing interned; parameters arrive with the first generation)')
        return

    users: dict[str, int] = {}
    for span in tree.spans.values():
        if span.params:
            users[span.params] = users.get(span.params, 0) + 1

    # every key that any entry sets, so the columns line up across entries that
    # differ in which optional parameters they carry
    fields = sorted({k for v in tree.params.values() for k in v})
    for key in sorted(tree.params, key=id_order):
        print(f'{key}  {users.get(key, 0)} span(s)')
        for field in fields:
            value = tree.params[key].get(field)
            if value is not None:
                print(f'  {field:<14} {value!r}')
        print()


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

    p = sub.add_parser('show', help='the tree, or a subtree of it')
    p.add_argument('position', nargs='?', help='root the render here')
    p.add_argument('-v', '--verbose', action='store_true', help='untruncated text')
    p.add_argument('-a', '--all', action='store_true', help='deleted subtrees too')
    p.add_argument('--depth', type=int, default=None,
                   help='stop forking after this many levels')

    p = sub.add_parser('read', help='one path, whole')
    p.add_argument('position', nargs='?')

    sub.add_parser('tokens', help='the token overlay for a span').add_argument('span')

    p = sub.add_parser('batches', help='generation calls, as experiments')
    p.add_argument('batch', nargs='?', help='one batch, or all of them')
    p.add_argument('--params', default=None,
                   help='only batches run under this parameter set; see `params`')

    p = sub.add_parser('diverge', help='how far the siblings of a call agree')
    p.add_argument('batch', nargs='?', help='one batch, or all of them')
    p.add_argument('--params', default=None,
                   help='only batches run under this parameter set')
    p.add_argument('--profile', action='store_true',
                   help='the full depth profile rather than one row each')

    sub.add_parser('params', help='the interned parameter sets')

    p = sub.add_parser('author', help='add given text at a position')
    p.add_argument('text')
    p.add_argument('position', nargs='?')

    p = sub.add_parser('gen', help='generate from a position')
    p.add_argument('position', nargs='?')
    p.add_argument('-n', type=int, default=1, help='continuations')
    p.add_argument('--length', type=int, default=32, help='tokens')
    p.add_argument('--temp', type=float, default=0.9)
    p.add_argument('--top-p', type=float, default=1.0)
    p.add_argument('--top-n', type=int, default=3, help='counterfactuals, min 1')
    p.add_argument('--prompt-length', type=int, default=None,
                   help='bytes of path to send; the whole of it if omitted')
    p.add_argument('--stop', action='append', default=[])
    p.add_argument('--stay', action='store_true',
                   help='leave the cursor at the generation point')

    p = sub.add_parser('branch', help='take a counterfactual')
    p.add_argument('span')
    p.add_argument('index', type=int)
    p.add_argument('rank', type=int)

    sub.add_parser('delete', help='soft delete, cascading').add_argument('position')
    sub.add_parser('restore', help='undo a delete').add_argument('position')
    sub.add_parser('cursor', help='move the cursor').add_argument('position')

    p = sub.add_parser('slice', help='the prompt a position would send')
    p.add_argument('position', nargs='?')
    p.add_argument('--prompt-length', type=int, default=None)

    args = parser.parse_args(argv)
    server = Server(args.server) if args.server else Server()

    if args.command == 'new':
        try:
            session = Session.create(args.dir, base_seed=args.seed,
                                     server=server)
        except Locked as e:
            raise SystemExit(str(e))
        except FileExistsError:
            # refusing is right -- a tree is not overwritable and the bulk
            # store beside it would survive the tree file being replaced. Only
            # the traceback was wrong
            raise SystemExit(f'{args.dir} already holds a tree; move it aside, '
                             f'or `-d` somewhere else')
        print(f'{args.dir}: tree {session.tree.tree_id}, '
              f'base seed {session.tree.base_seed}')
        session.close()
        return 0

    try:
        session = Session.open(args.dir, server=server,
                               write=args.command not in READS)
    except Locked as e:
        # the one refusal that is about the world rather than about the tree:
        # nothing here is wrong, someone else simply has it
        raise SystemExit(str(e))
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
        show(session, args.verbose, args.all,
             parse_position(session, args.position) if args.position else None,
             args.depth)

    elif args.command == 'read':
        pos = parse_position(session, args.position)
        if pos is None:
            print('leaves:', ' '.join(session.leaves()) or '(none)')
            return 0
        sys.stdout.write(tree.path_bytes(pos).decode('utf-8', errors='replace'))
        sys.stdout.write('\n')

    elif args.command == 'tokens':
        show_tokens(session, known_span(session, args.span))

    elif args.command == 'batches':
        show_batches(session, args.batch, args.params)

    elif args.command == 'diverge':
        show_divergence(session, args.batch, args.params, args.profile)

    elif args.command == 'params':
        show_params(session)

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
        except Incomplete as e:
            # the spans of this batch that landed are kept and closed out as
            # aborted on the next load, which is what in-flight recovery is for
            raise SystemExit(f'abandoned mid-batch: {e}')
        for span in spans:
            print(f'{span.id}  {session.store.terminator(span.id):>7}  '
                  f'{show_text(span.text, 70)}')
        # walking forward wants the cursor on what was just made; sampling in
        # place wants it left where the sampling is happening, or every repeat
        # has to name the position again. `session.generate` has already saved
        # per continuation, so staying put needs no write of its own
        if args.stay:
            if pos != tree.selected:
                set_cursor(session, pos)
        else:
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
