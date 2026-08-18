#!/usr/bin/env python
"""Headless check that the format holds -- the worked example, round-tripped.

Two halves, and the second is the one that matters. Round-tripping proves the
format can be written and read back. Breaking it seven ways proves the validator
would have noticed: a validator that has never rejected anything is untested,
and this one exists to catch exactly the mistakes that are invisible by eye.

Every byte length below is computed from a literal rather than written down.
Arithmetic in a test is code too, and nothing checks it.

Usage: python core_test.py
"""
import json
import os
import shutil
import sys
import tempfile

from core import (BulkStore, Position, Tree, address_at, author,
                  begin_generation, branch_counterfactual, complete,
                  create_tree, delete, divergence, open_tree, restore, runs,
                  save, slice_at, token_offsets, validate)
from core.store import ABORTED, Counterfactual, LENGTH, Token
from core.tree import Span

TS = '2026-08-12-10.00.00'

# the worked example from FORMAT.md: one authored prompt, a batch of two
# continuations, a counterfactual branch inside the second, and one call left
# in flight. Five spans and no structure beside them.
PROMPT = b'The sea was'
CALM = [(1001, b' calm'), (1002, b' for'), (1003, b' days')]
CLEAR = [(1001, b' calm'), (1004, b' and'), (1005, b' clear')]
STILL = b' still'
# ' calm' + ' and' is where the counterfactual branch lands
CUT = len(CLEAR[0][1]) + len(CLEAR[1][1])

TOKENS = {'s2': CALM, 's3': CLEAR, 's4': [(2058, STILL)]}
COUNTERFACTUALS = {
    ('s3', 2): [(1005, b' clear', -0.92), (2058, STILL, -2.31),
                (1006, b' bright', -3.10)],
}


def spelled(rows):
    return b''.join(raw for _, raw in rows)


def worked_example():
    tree = Tree.empty(base_seed=90210)
    tree.tree_id = 'worked-example'
    tree.params['p1'] = {'temperature': 0.9, 'top_p': 1, 'top_n': 3,
                         'length': 3, 'stop': [],
                         'model': 'qwen2.5-7b-base', 'tokenizer': 'qwen2.5',
                         'n_ctx': 16384, 'prompt_length': 6000}
    # a second call at different conditions, so the fixture holds what a sweep
    # holds: two batches that are two experiments rather than one repeated
    tree.params['p2'] = dict(tree.params['p1'], temperature=1.3)
    root = Position('s1', len(PROMPT))
    for span in [
        Span('s1', 'given', None, PROMPT, TS),
        Span('s2', 'sampled', root, spelled(CALM), TS, params='p1', seed=90211,
             batch='b1', index=0, slice_start=Position('s1', 0)),
        Span('s3', 'sampled', root, spelled(CLEAR), TS, params='p1', seed=90212,
             batch='b1', index=1, slice_start=Position('s1', 0)),
        # branches inside s3, which is not cut
        Span('s4', 'counterfactual', Position('s3', CUT), STILL, TS,
             origin={'span': 's3', 'index': 2, 'token_id': 2058}),
        # in flight: provenance written, byte record still empty
        Span('s5', 'sampled', Position('s3', len(spelled(CLEAR))), None, TS,
             params='p2', seed=90213, batch='b2', index=0,
             slice_start=Position('s1', 0)),
    ]:
        tree.add(span)
    tree.selected = Position('s3', len(spelled(CLEAR)))
    return tree


def fill_store(store):
    for span, rows in TOKENS.items():
        store.add_tokens(span, [Token(i, tid, raw, -1.0 - i)
                                for i, (tid, raw) in enumerate(rows)])
    for (span, idx), ranked in COUNTERFACTUALS.items():
        store.add_counterfactuals(
            span, [Counterfactual(idx, rank, *row)
                   for rank, row in enumerate(ranked)])
    for span in ('s2', 's3'):
        store.set_terminator(span, LENGTH)


# --------------------------------------------------------------------------

PASS, FAIL = 0, 0


def check(name, ok, detail=''):
    global PASS, FAIL
    if ok:
        PASS += 1
        print(f'  ok    {name}')
    else:
        FAIL += 1
        print(f'  FAIL  {name}{"  -- " + detail if detail else ""}')


def expect_problem(name, mangle, matching, store=None):
    """Break the worked example one way, and confirm the validator says so."""
    tree = worked_example()
    mangle(tree)
    problems = validate(tree, store)
    check(name, any(matching in p for p in problems),
          f'got {problems or "no problems"}')


SETTINGS = {'temperature': 0.9, 'top_p': 1, 'top_n': 3, 'length': 4,
            'stop': [], 'model': 'qwen2.5-7b-base', 'tokenizer': 'qwen2.5',
            'n_ctx': 16384, 'prompt_length': 6000}

OPENING = b'The lighthouse keeper wrote:'
WAS_CALM = [(11, b' the'), (12, b' sea'), (13, b' was'), (14, b' calm')]
WAS_WILD = [(11, b' the'), (12, b' sea'), (13, b' was'), (15, b' wild')]
ROUGH = b' rough'


def toks(parts):
    return [Token(i, tid, raw, -1.0 - i) for i, (tid, raw) in enumerate(parts)]


def operations(workdir):
    """The five, on a tree built entirely by hand. No model involved."""
    path = os.path.join(workdir, 'ops')
    tree, store = create_tree(path, base_seed=500)

    # ids are minted as one past the highest in use, so the first span is s0.
    # The worked example's s1..s5 are illustrative names, not a convention.
    print('\nauthor and generate')
    prompt = author(tree, None, OPENING)
    check('the first prompt is a root span, with no node to hang it off',
          prompt.parent is None and tree.children_of(None) == [(0, 's0')])
    check('the given span carries no parameters and no seed',
          prompt.params is None and prompt.seed is None)

    tip = tree.tip('s0')
    spans = begin_generation(tree, tip, SETTINGS, n=2)
    check('n continuations share one parent address, which is what n means',
          {s.parent for s in spans} == {tip} and tip == Position('s0', len(OPENING)))
    check('one batch, distinct seeds derived from the base',
          {s.batch for s in spans} == {'b0'}
          and [s.seed for s in spans] == [500, 501])
    check('in flight: provenance, no bytes, and its own attachment',
          all(not s.complete and s.parent == tip for s in spans))
    check('the intent record validates before any token exists',
          not validate(tree, store), str(validate(tree, store)))
    check('both continuations share one interned parameter set',
          {s.params for s in spans} == {'p0'} and len(tree.params) == 1)

    complete(tree, store, 's1', toks(WAS_CALM), LENGTH)
    complete(tree, store, 's2', toks(WAS_WILD), LENGTH)
    check('completion fills the byte record and nothing else',
          tree.spans['s1'].text == spelled(WAS_CALM)
          and tree.spans['s1'].seed == 500
          and tree.spans['s1'].parent == tip)
    check('generated paths read back whole',
          tree.path_bytes(tree.tip('s2')) == OPENING + spelled(WAS_WILD),
          repr(tree.path_bytes(tree.tip('s2'))))
    check('validates after generation', not validate(tree, store),
          str(validate(tree, store)))

    print('\nbranch to a counterfactual')
    store.add_counterfactuals('s1', [
        Counterfactual(3, 0, 14, b' calm', -0.3),
        Counterfactual(3, 1, 16, ROUGH, -1.8),
        Counterfactual(3, 2, 17, b' still', -2.4)])
    offsets = token_offsets(store, 's1')
    check('token offsets accumulate from the rows',
          offsets == [0, 4, 8, 12, 17], str(offsets))

    branched = branch_counterfactual(tree, store, 's1', 3, rank=1)
    check('it anchors at the byte its token starts on, dividing nothing',
          branched.parent == Position('s1', offsets[3]))
    check('the counterfactual branch reads as the road not taken',
          tree.path_bytes(tree.tip('s3'))
          == OPENING + spelled(WAS_CALM[:3]) + ROUGH,
          repr(tree.path_bytes(tree.tip('s3'))))
    check('it carries the token id, not the rank',
          branched.origin == {'span': 's1', 'index': 3, 'token_id': 16})
    check('and no parameters, having never been a generation call',
          branched.params is None and branched.seed is None)
    check('the span it left keeps every byte it had',
          tree.spans['s1'].text == spelled(WAS_CALM))
    check('and still reads whole down its own line',
          tree.path_bytes(tree.tip('s1')) == OPENING + spelled(WAS_CALM))
    check('validates after branching', not validate(tree, store),
          str(validate(tree, store)))

    print('\ncontinue at a tip, and slice')
    more = begin_generation(tree, tree.tip('s3'), SETTINGS, n=1)
    check('the seed keeps counting past the spans already generated',
          more[0].seed == 502)
    complete(tree, store, 's4', toks([(20, b' indeed')]), LENGTH)
    check('one continuation at a tip is just another child',
          tree.spans['s4'].parent == Position('s3', len(ROUGH)))
    check('and the path runs through both spans',
          tree.path_bytes(tree.tip('s4'))
          == OPENING + spelled(WAS_CALM[:3]) + ROUGH + b' indeed')

    whole = tree.path_bytes(tree.tip('s3'))
    start, end, text = slice_at(tree, tree.tip('s3'), 20)
    check('a slice is two addresses and the bytes they name',
          (start, end, text) == (Position('s0', len(whole) - 20),
                                 tree.tip('s3'), whole[-20:]),
          f'{(start, end)} {text!r}')
    check('the start address agrees with the offset it came from',
          tree.absolute(start) == len(whole) - 20)
    start, _, text = slice_at(tree, tree.tip('s3'), 1000)
    check('and clamps at the root rather than running off it',
          start == Position('s0', 0) and text == whole)

    # `None` is the whole path and is the default. It has to be its own answer
    # rather than a big number: a number that happens to cover the path today
    # is one that interns, so raising it later records a change of framing that
    # did not happen. And `0` keeps its own meaning rather than becoming the
    # spelling for this -- an empty prompt is reachable, and the only reason
    # nothing runs it is that the MVP requires a character in the seed.
    unbounded = slice_at(tree, tree.tip('s3'), None)
    check('no length at all is the whole path, root-anchored',
          unbounded == (Position('s0', 0), tree.tip('s3'), whole),
          str(unbounded))
    check('and is the same slice a length large enough to cover it gives',
          unbounded == slice_at(tree, tree.tip('s3'), 1000))
    start, _, text = slice_at(tree, tree.tip('s3'), 0)
    check('while zero is an empty prompt, which is a different question',
          text == b'' and start == tree.tip('s3'), f'{start} {text!r}')
    check('an absolute offset resolves back to an address',
          address_at(tree, tree.tip('s3'), 30) == Position('s1', 2),
          str(address_at(tree, tree.tip('s3'), 30)))
    check('at a span boundary it names the earlier tip, canonically',
          address_at(tree, tree.tip('s3'), len(OPENING))
          == Position('s0', len(OPENING)))

    print('\ndelete')
    delete(tree, Position('s2', 0))
    live = tree.live()
    check('deleting a fork whole takes it out of the live set', 's2' not in live)
    check('its sibling is untouched', 's1' in live)
    check('the span keeps every byte it recorded',
          tree.spans['s2'].text == spelled(WAS_WILD))
    check('its tokens are still in the bulk store',
          len(store.tokens('s2')) == len(WAS_WILD))
    check('validates after deleting', not validate(tree, store),
          str(validate(tree, store)))

    delete(tree, Position('s1', offsets[3]))
    live = tree.live()
    check('truncating mid-span keeps its head reachable',
          live.get('s1') == offsets[3])
    check('and drops what was anchored at the cut', 's3' not in live)
    check('while the span itself is untouched',
          tree.spans['s1'].text == spelled(WAS_CALM))
    check('a deleted address is a prefix bound, not a coverage claim',
          tree.path_bytes(Position('s1', live['s1']))
          == OPENING + spelled(WAS_CALM[:3]))
    check('an independent earlier deletion is not disturbed by a later one',
          set(tree.deleted) == {Position('s2', 0), Position('s1', offsets[3])},
          str(tree.deleted))

    # entries may cover each other, and must: dropping the narrower one would
    # make restoring the wider one resurrect a subtree deleted separately
    delete(tree, Position('s1', 2))
    check('a wider cut is kept beside the narrower one it covers',
          Position('s1', offsets[3]) in tree.deleted
          and Position('s1', 2) in tree.deleted, str(tree.deleted))
    check('and liveness takes the least of them', tree.live().get('s1') == 2)
    delete(tree, Position('s1', 6))
    check('while a cut already inside a dead region is a no-op',
          Position('s1', 6) not in tree.deleted, str(tree.deleted))
    restore(tree, Position('s1', 2))
    check('undoing the wider one leaves the narrower one still deleting',
          tree.live().get('s1') == offsets[3] and 's3' not in tree.live())

    restore(tree, Position('s1', offsets[3]))
    check('and delete is reversible, being soft', 's3' in tree.live())
    check('validates throughout', not validate(tree, store),
          str(validate(tree, store)))

    print('\nthe cursor is an address, and no operation moves it')
    # The invariant, not the value: a recorded address stays the same address.
    # It holds by construction -- a span is written once and never cut, so
    # nothing an operation does can move a position out from under a cursor,
    # and there is no fix-up code anywhere to go wrong. This asserts it anyway,
    # because "by construction" is a claim about code that can be edited.
    tree.selected = Position('s1', 6)
    was, address = tree.absolute(tree.selected), tree.selected
    author(tree, tree.tip('s4'), b' -- or so he said')
    check('authoring elsewhere leaves it exactly where it was',
          tree.selected == address)
    flight = {s.id for s in begin_generation(tree, Position('s1', 2), SETTINGS, n=2)}
    check('branching inside the very span it points into leaves it alone',
          tree.selected == address)
    branch_counterfactual(tree, store, 's1', 3, rank=2)
    check('so does a counterfactual anchored past it', tree.selected == address)
    check('and the absolute offset it names is unchanged',
          tree.absolute(tree.selected) == was)

    delete(tree, Position('s1', 0))
    check('deleting out from under it does not invalidate the address',
          tree.selected == address and tree.path_bytes(tree.selected)
          == OPENING + spelled(WAS_CALM)[:6])
    check('it just stops resolving to anything live -- a display concern',
          not tree.resolves(tree.selected))
    restore(tree, Position('s1', 0))
    check('and resolves again once the delete is undone',
          tree.resolves(tree.selected))

    print('\nslice start is recorded resolved, its length interned')
    near = begin_generation(tree, tree.tip('s2'), {**SETTINGS,
                                                  'prompt_length': 12}, 1)
    tail = tree.path_bytes(tree.tip('s2'))
    check('a restricted context resolves to an address on its own path',
          tree.absolute(near[0].slice_start) == len(tail) - 12,
          str(near[0].slice_start))
    check('the length interns; the resolved address does not',
          tree.params[near[0].params]['prompt_length'] == 12
          and 'slice_start' not in tree.params[near[0].params])
    check('a different framing at the same position is a new parameter set',
          near[0].params != 'p0' and len(tree.params) == 2)
    complete(tree, store, near[0].id, toks([(21, b' still')]), LENGTH)

    print('\nthe whole thing survives a round trip')
    save(path, tree)
    store.close()
    back, store = open_tree(path)
    check('reloads and validates', not validate(back, store),
          str(validate(back, store)))
    # the two calls above were never completed, so this exercises recovery:
    # the reload is legitimately not byte-identical, and saying it is would
    # hide the one thing worth checking here
    check('the calls left in flight come back aborted',
          all(back.spans[s].text == b'' and store.terminator(s) == 'aborted'
              for s in flight), str(flight))
    check('keeping the attachment they were created with',
          all(back.spans[s].parent == tree.spans[s].parent for s in flight))
    check('and every other span is byte-identical',
          {k: v for k, v in back.to_json()['spans'].items() if k not in flight}
          == {k: v for k, v in tree.to_json()['spans'].items()
              if k not in flight})
    check('with the same cursor, parameters and deletions',
          (back.selected, back.params, back.deleted)
          == (tree.selected, tree.params, tree.deleted))
    store.close()


def driver(workdir):
    """Everything the command line does that needs no model.

    Thin glue, but glue that rots quietly: position parsing and the derived-run
    rendering have no other caller, so nothing else would notice them breaking.
    """
    import io
    import contextlib
    import loom

    print('\nthe command line')
    path = os.path.join(workdir, 'cli')

    def run(*argv):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = loom.main(['-d', path, *argv])
        return code, out.getvalue()

    code, out = run('new', '--seed', '77')
    check('new creates a tree', code == 0 and 'base seed 77' in out, out)
    code, out = run('show')
    check('an empty tree renders as empty rather than raising',
          code == 0 and '(empty)' in out, out)

    code, out = run('author', 'The sea was')
    check('author works on a fresh tree, whose cursor is the root',
          code == 0 and "'The sea was'" in out, out)

    # author leaves the cursor at the tip, so the mark lands at the very end --
    # which is the common case and has to read as "here", not as a stray glyph
    code, out = run('show')
    check('show renders the derived run and its text',
          's0+0  0..11  Gs0' in out and f"'The sea was{loom.CURSOR}'" in out, out)

    code, out = run('read', 's0')
    check('read prints the path', out.strip() == 'The sea was', out)

    code, out = run('cursor', 's0+4')
    check('a position is a span and an offset into it',
          's0+4' in out and 'absolute 4' in out, out)

    code, out = run('slice', '--prompt-length', '6')
    check('slice reports two addresses and the bytes between them',
          's0+0..s0+4' in out and out.endswith('The \n'), repr(out))

    # 'The sea was'[:7] is 'The sea', so the branch reads with one space
    code, out = run('author', ' still', 's0+7')
    check('authoring mid-span needs no boundary made first',
          code == 0 and "' still'" in out, out)
    code, out = run('show')
    check('and the branch shows up where it was anchored',
          's0+7' in out and 'Gs1' in out, out)
    code, out = run('read', 's1')
    check('the branch reads as the shorter path',
          out.strip() == 'The sea still', out)
    code, out = run('read', 's0')
    check('while the span it branched off still reads whole',
          out.strip() == 'The sea was', out)

    code, out = run('delete', 's1+0')
    check('delete reports what is left', 's1+0 deleted' in out, out)
    code, out = run('show')
    check('a deleted branch is not rendered', 'Gs1' not in out, out)
    code, out = run('show', '-a')
    check('unless asked for', 'Gs1' in out and '(deleted)' in out, out)
    code, out = run('restore', 's1+0')
    check('restore puts it back', 's1+0 restored' in out, out)

    check('a bad span id is refused rather than traced',
          _exits(run, 'tokens', 'nope'))
    check('a bad position is refused too', _exits(run, 'read', 's99'))
    check('and so is a malformed offset', _exits(run, 'cursor', 's0+x'))

    check('creating a tree over an existing one is refused, not traced',
          _exits(run, 'new'))

    # a file from another format reaches the CLI as a ValueError out of the
    # loader, which is a traceback unless something catches it
    stale = os.path.join(path, 'tree.json')
    d = json.loads(open(stale).read())
    d['format'] = 'token-loom/0'
    open(stale, 'w').write(json.dumps(d))
    check('and so is a tree this format does not read',
          _exits(run, 'show'))

    several_roots(workdir)
    derived_runs(workdir)
    capping_the_render(workdir)
    sibling_divergence(workdir)
    entry_alignment()
    merged_records()


def cli_reads(path):
    """`batches`, `params` and the cursor mark, against the worked example.

    Run here rather than in `driver` because they need a tree that has been
    generated into, and `driver` only authors. The worked example has two
    batches, one of them in flight, which is the awkward case: a batch whose
    span has no bytes and no terminator still has to list.
    """
    import io
    import contextlib
    import loom

    print('\nreading a batch back as the experiment it was')

    def run(*argv):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = loom.main(['-d', path, *argv])
        return code, out.getvalue()

    code, out = run('batches')
    check('both batches list', code == 0 and 'b1' in out and 'b2' in out, out)
    check('the siblings of one call are shown together, in batch order',
          out.index('[0] s2') < out.index('[1] s3'), out)
    check('with the seeds that distinguish them',
          '90211' in out and '90212' in out, out)
    check('and the parameters they shared', "'temperature': 0.9" in out, out)
    # s5 was in flight and `open_tree` recovered it, so it lists as aborted
    check('a recovered span lists with its terminator, not as a gap',
          'aborted' in out, out)
    check('a counterfactual span is in no batch', 's4' not in out, out)

    code, out = run('batches', 'b1')
    check('one batch can be asked for alone',
          code == 0 and 'b1' in out and 'b2' not in out, out)
    check('a batch that does not exist is refused', _exits(run, 'batches', 'b9'))

    # the level between one call and the whole tree: interning is by value, so
    # one key is one set of conditions however many calls were made under it.
    # Both directions are checked because a filter that returns everything
    # passes the first on its own
    code, out = run('batches', '--params', 'p1')
    check('batches select down to one set of conditions',
          code == 0 and 'b1' in out and 'b2' not in out, out)
    code, out = run('batches', '--params', 'p2')
    check('and the other conditions select the other call',
          code == 0 and 'b2' in out and 'b1' not in out, out)
    check('an unknown parameter set is refused',
          _exits(run, 'batches', '--params', 'p9'))

    code, out = run('params')
    check('the intern table lists, with how many spans use each entry',
          code == 0 and 'p1' in out and 'span(s)' in out, out)
    check('and the values, one per line rather than as a dict dump',
          'temperature' in out and 'prompt_length' in out, out)

    # the cursor is at the tip of s3, which is the end of its run
    code, out = run('show')
    check('the cursor marks its place inside the text, not just at the line end',
          loom.CURSOR in out, out)
    check('and still flags which run it is in', '←' in out, out)


def several_roots(workdir):
    """More than one span with `parent: null`, which the format permits.

    `EMPTY_TREE` is literally empty and an initial prompt is an ordinary given
    span with no parent, so nothing stops there being several -- and `show`
    has to splice the zero-width root rather than render it as a run of its
    own. That was a claim from reading `outline`, not from running it.

    Not a flow to build on: the MVP composes one prompt with separators rather
    than authoring siblings. It is checked because the format allows it, and an
    allowed shape that crashes the only renderer is a fault either way.
    """
    import io
    import contextlib
    import loom

    print('\nseveral root prompts')
    path = os.path.join(workdir, 'roots')

    def at_root(*argv):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = loom.main(['-d', path, *argv])
        return code, out.getvalue()

    at_root('new', '--seed', '5')
    for text in ('First.', 'Second!', 'Third?'):
        at_root('author', text, '.')

    code, out = at_root('show')
    check('all three roots render', code == 0
          and all(m in out for m in ('Gs0', 'Gs1', 'Gs2')), out)
    check('none of them is nested under another',
          out.count('├─ ') + out.count('└─ ') == 3, out)
    check('the zero-width root is spliced, not drawn as a run',
          '·' not in out and '3 spans' in out, out)

    # each root is its own origin: absolute offsets restart rather than running
    # on from the sibling before it, which is what "no parent" has to mean
    code, out = at_root('read', 's1')
    check('a root reads as itself alone', out.strip() == 'Second!', out)
    code, out = at_root('cursor', 's2+0')
    check('and starts at absolute 0 like every other root',
          'absolute 0' in out, out)

    # deleting one root leaves the others, which the cut-per-span rule gives
    at_root('delete', 's1+0')
    code, out = at_root('show')
    check('deleting one root leaves its siblings',
          'Gs0' in out and 'Gs2' in out and 'Gs1' not in out, out)
    # soft delete, so the span is still there and merely unreachable
    check('and the count says unreachable rather than gone',
          '3 spans, 1 unreachable' in out, out)


def entry_alignment():
    """`_align`, on payloads shaped like the ones that caused it to exist.

    Pure, so it runs with no model. Which matters more than convenience here:
    the case it exists for needs a character whose UTF-8 spans several tokens,
    and that is reachable from a live server only by getting the model to emit
    one. A constructed payload reaches it on purpose.

    A mis-alignment is the dangerous failure -- it does not crash, it silently
    relabels every record after the slip. So the negative cases matter as much
    as the positive one, and all of them raise rather than guessing.
    """
    from core.llama import Incomplete, _align

    print('\naligning entries against the sampled sequence')

    # one character of three tokens in the middle: the server emits one entry
    # for it, carrying the group's bytes and the *last* fragment's id
    tokens = [10, 20, 21, 22, 30]
    entries = [{'id': 10}, {'id': 22}, {'id': 30}]
    groups, tail = _align(entries, tokens, len(tokens))

    check('an unmerged entry stands for exactly its own token',
          groups[0] == [10] and groups[2] == [30], str(groups))
    check('a merged entry stands for the whole group it completes',
          groups[1] == [20, 21, 22], str(groups))
    check('and the groups partition the sampled sequence, losing nothing',
          [t for g in groups for t in g] == tokens, str(groups))
    check('nothing is left over when the budget did not expire mid-character',
          tail == [], str(tail))

    # the same, cut short: the fragments of the last character never flushed
    groups, tail = _align([{'id': 10}], [10, 20, 21], 3)
    check('tokens past the last entry are the dropped tail',
          groups == [[10]] and tail == [20, 21], f'{groups} {tail}')

    check('an entry whose id is nowhere in the sequence raises',
          _raises(Incomplete, _align, [{'id': 99}], [10, 20], 2))
    check('a tokens array disagreeing with the reported count raises',
          _raises(Incomplete, _align, [{'id': 10}], [10, 20], 5))
    check('no entries at all leaves the whole sequence unclaimed',
          _align([], [10, 20], 2) == ([], [10, 20]))


def merged_records():
    """What `_read` writes for a merged entry, which is deliberately less.

    The entry's bytes are the whole character and are right. Its id, logprob
    and alternatives describe only the final fragment, so recording them beside
    those bytes would assert a correspondence that does not hold. Absent is the
    honest record, and the test is that the absence is there on purpose rather
    than by omission.
    """
    from core.llama import Incomplete, Server

    print('\nwhat a merged entry is allowed to claim')

    def entry(tid, raw, logprob, alts):
        return {'id': tid, 'bytes': list(raw), 'logprob': logprob,
                'top_logprobs': [{'id': a, 'bytes': list(b), 'logprob': lp}
                                 for a, b, lp in alts]}

    payload = {
        'tokens': [10, 20, 21, 22, 30],
        'tokens_predicted': 5,
        'tokens_evaluated': 7,
        'stop_type': 'limit',
        'completion_probabilities': [
            entry(10, b'A', -0.1, [(10, b'A', -0.1), (11, b'B', -1.0)]),
            entry(22, '\U0001f701'.encode(), -0.5, [(22, b'\x81', -0.5)]),
            entry(30, b'C', -0.2, [(30, b'C', -0.2)]),
        ],
    }
    result = Server._read(payload, {'length': 5})
    merged = result.tokens[1]

    check('a merged row keeps the bytes, which are the whole character',
          merged.bytes == '\U0001f701'.encode()
          and len(merged.bytes) == 4, repr(merged.bytes))
    check('and claims neither an id nor a logprob it does not have',
          merged.token_id is None and merged.logprob is None, str(merged))
    check('an unmerged row is untouched by any of this',
          result.tokens[0].token_id == 10
          and result.tokens[0].logprob == -0.1, str(result.tokens[0]))
    check('the alternatives to a fragment are dropped, not relabelled',
          {c.idx for c in result.counterfactuals} == {0, 2}
          and len(result.counterfactuals) == 3,
          str([(c.idx, c.rank) for c in result.counterfactuals]))
    check('the span still spells what the model produced',
          b''.join(t.bytes for t in result.tokens)
          == 'A\U0001f701C'.encode(),
          repr(b''.join(t.bytes for t in result.tokens)))
    # the whole character arrived, so three tokens became one row and the row
    # count is below tokens_predicted without anything having been lost
    check('a merge shortens the record without shortening the text',
          len(result.tokens) == 3 and payload['tokens_predicted'] == 5)

    payload['tokens'] = [10, 20, 21, 22, 30, 40, 41]
    payload['tokens_predicted'] = 7
    check('but a budget that expired mid-character is refused, not recorded',
          _raises(Incomplete, Server._read, payload, {'length': 7}))

    # a stop match leaves a tail deliberately -- the server drops the matched
    # text so it is not part of the span. Refusing that would make stop strings
    # unusable, and this distinction is the one the live test caught
    payload['stop_type'] = 'word'
    stopped = Server._read(payload, {'length': 7})
    check('a tail left by a stop match is expected, not an incomplete response',
          [t.idx for t in stopped.tokens] == [0, 1, 2], str(stopped.tokens))
    check('and the span still ends before the match',
          b''.join(t.bytes for t in stopped.tokens) == 'A\U0001f701C'.encode())


def _raises(kind, fn, *args):
    try:
        fn(*args)
    except kind:
        return True
    return False


def sibling_divergence(workdir):
    """`divergence`, against sequences whose answers are fixed by construction.

    This is the project's first derived *measurement* rather than derived
    display, which puts it in the category the method notes warn about: nothing
    disagrees with a number, so a wrong one is indistinguishable from a right
    one until something reaches it on purpose.

    So the fixture is four sequences chosen to pin every branch at once -- two
    that agree for nine tokens and part on the tenth, one that leaves after
    three, and one too short to reach most depths at all. The short one is the
    case the asymmetry is about: it must lower `lock` (it shares no prefix it
    cannot reach) while still counting as a distinct path (it went somewhere).
    """
    print('\nsibling divergence, as a number')
    store = BulkStore(os.path.join(workdir, 'divergence.sqlite'))

    seqs = {
        'a': [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
        'b': [1, 2, 3, 4, 5, 6, 7, 8, 9, 11],   # parts from a at index 9
        'c': [1, 2, 3, 20, 21, 22, 23, 24, 25, 26],   # parts at index 3
        'd': [1, 2],                            # too short for depth 3 and 10
    }
    for span, ids in seqs.items():
        store.add_tokens(span, [Token(i, tid, bytes([65 + i]), -1.0)
                                for i, tid in enumerate(ids)])

    d = divergence(store, list(seqs))
    n = len(seqs)

    # every expectation below is computed from `seqs`, not written down
    def sharing(k):
        reaching = [tuple(s[:k]) for s in seqs.values() if len(s) >= k]
        return max(reaching.count(p) for p in reaching) / n if reaching else 0.0

    check('lock counts the largest agreeing subset over every sibling',
          all(abs(d['lock'][k] - sharing(k)) < 1e-9 for k in (1, 3, 10)),
          f'{d["lock"]} vs {[sharing(k) for k in (1, 3, 10)]}')
    check('a sibling too short to reach a depth lowers the lock there',
          d['lock'][3] == 3 / 4 and d['short'][3] == 1, str(d))
    check('and is still counted as a path of its own',
          d['distinct'][2] == 2, str(d['distinct']))

    # the invariants, which hold for any input and catch what values cannot
    check('lock never rises with depth',
          d['lock'][1] >= d['lock'][3] >= d['lock'][10], str(d['lock']))
    check('distinct paths never fall with depth',
          all(x <= y for x, y in zip(d['distinct'], d['distinct'][1:])),
          str(d['distinct']))
    check('the common prefix is exactly the depth before paths appear',
          all(c == 1 for c in d['distinct'][:d['common']])
          and d['distinct'][d['common']] > 1, str(d))
    check('fully distinct is the first depth where every sibling is alone',
          d['fully_distinct_at'] == 10
          and d['distinct'][d['fully_distinct_at'] - 1] == n, str(d))
    check('the common prefix stops at the shortest sibling',
          d['common'] == 2 and min(len(s) for s in seqs.values()) == 2, str(d))

    # siblings that never part have no depth at which they are all distinct,
    # which is a missing answer rather than a large one
    for span in ('e', 'f'):
        store.add_tokens(span, [Token(i, t, b'x', -1.0)
                                for i, t in enumerate([7, 7, 7])])
    same = divergence(store, ['e', 'f'])
    check('identical siblings report no full-distinction depth, not a number',
          same['fully_distinct_at'] is None and same['lock'][1] == 1.0,
          str(same))
    check('and asking past their length is answered, not raised',
          same['lock'][10] == 0.0 and same['short'][10] == 2, str(same))

    check('an empty sibling set is None rather than a division by zero',
          divergence(store, []) is None)
    store.close()


def derived_runs(workdir):
    """The run decomposition itself, not what a renderer prints of it.

    `runs` moved out of `loom.py` when the API turned out to need the identical
    read, and everything that covered it before went through printed output --
    which tests the printing at least as much as the derivation. These assert
    the structure, and the central one is an invariant rather than a value:
    **the pieces partition the live bytes.** Every reachable byte appears in
    exactly one piece of exactly one run, which is what makes a run tree a way
    of reading the span tree rather than a second copy of it.
    """
    print('\nthe derived run tree')
    path = os.path.join(workdir, 'runs')
    tree, store = create_tree(path, base_seed=7)

    # s0 forks at byte 4 and continues; s1 extends it; s2 is the branch, and
    # s3 hangs off s2's byte 0 -- the case that needs the `resuming` flag
    s0 = author(tree, None, b'ABCDEFGH')
    s1 = author(tree, tree.tip(s0.id), b'IJ')
    s2 = author(tree, Position(s0.id, 4), b'XY')
    s3 = author(tree, Position(s2.id, 0), b'Z')

    def pieces_of(node):
        return [node['pieces']] + [p for c in node['children']
                                   for p in pieces_of(c)]

    def widths(node):
        return sorted(c['width'] for c in node['children'])

    def partitions(tree):
        """Every live byte in exactly one piece, and nothing dead in any."""
        reach = tree.live()
        seen: dict[str, list] = {}
        for run in pieces_of(runs(tree, reach, (None, 0, False))):
            for span, begin, end in run:
                seen.setdefault(span, []).extend(range(begin, end))
        for span, limit in reach.items():
            if sorted(seen.get(span, [])) != list(range(limit)):
                return False, f'{span}: {sorted(seen.get(span, []))} vs 0..{limit}'
        extra = set(seen) - set(reach)
        return (not extra), f'unreachable spans in the render: {extra}'

    top = runs(tree, tree.live(), (None, 0, False))
    check('a run stops at the first branch point in it',
          top['pieces'] == [(s0.id, 0, 4)], str(top['pieces']))
    check('and one continuation is not a branch, so the run crosses spans',
          [c['pieces'] for c in top['children'] if c['width'] == 6]
          == [[(s0.id, 4, 8), (s1.id, 0, 2)]], str(top['children']))

    # s3 is anchored at byte 0 of s2, which also continues. That is a fork
    # point rather than a run, and it is spliced into its parent's children --
    # so nothing of width 0 survives to be drawn or laid out
    check('a branch at byte 0 is a fork point, not a run of no width',
          widths(top) == [1, 2, 6], str(widths(top)))
    check('and both sides of that fork reach the tree',
          [p for run in pieces_of(top) for p in run].count((s2.id, 0, 2)) == 1
          and (s3.id, 0, 1) in [p for run in pieces_of(top) for p in run],
          str(pieces_of(top)))

    ok, detail = partitions(tree)
    check('the pieces partition every live byte, exactly once', ok, detail)

    # Zero width and no children is the other way to have no bytes, and it is
    # not a fork point: a span in flight, and a span completed with none. The
    # partition invariant above cannot see the difference between "kept, and
    # covers no bytes" and "absent" -- both give an empty range -- so these ask
    # the structure directly. Reached on purpose, because ordinary use of the
    # CLI renders trees whose generations have all finished.
    flight, empty = begin_generation(tree, tree.tip(s1.id), SETTINGS, n=2)
    complete(tree, store, empty.id, [], ABORTED)

    def named(node):
        return {span for run in pieces_of(node) for span, _, _ in run}

    top = runs(tree, tree.live(), (None, 0, False))
    onward = [c for c in top['children'] if c['width'] == 6][0]
    check('a span in flight is a node of no width rather than no node',
          flight.id in named(top), str(pieces_of(top)))
    check('and so is one completed with no bytes at all',
          empty.id in named(top), str(pieces_of(top)))
    check('the run they continue from forks into exactly the two of them',
          [c['pieces'] for c in onward['children']]
          == [[(flight.id, 0, 0)], [(empty.id, 0, 0)]], str(onward['children']))
    check('and neither acquires children by being kept',
          all(not c['children'] for c in onward['children']),
          str(onward['children']))
    check('while the byte-0 fork point is still spliced, not drawn',
          widths(top) == [1, 2, 6], str(widths(top)))

    ok, detail = partitions(tree)
    check('the partition still holds with two spans holding no bytes',
          ok, detail)

    # a deletion cuts a span mid-way, and the partition has to follow it --
    # this is the case where a piece's end is a cut rather than a length
    delete(tree, Position(s0.id, 6))
    ok, detail = partitions(tree)
    check('and still do so once a deletion bisects a span', ok, detail)
    check('the cut span keeps its bytes while the tree stops reaching them',
          tree.spans[s0.id].length == 8 and tree.live()[s0.id] == 6,
          f'{tree.spans[s0.id].length} {tree.live().get(s0.id)}')

    store.close()


def capping_the_render(workdir):
    """`show <position>` and `show --depth n`, which are cuts over the display.

    Neither changes what is reachable, so neither can crash in an obvious way:
    the failure mode is a miscount, which ordinary use does not surface. The
    one that did happen, and is the reason this exists: a zero-width node
    prints nothing, so it must not consume a level either -- otherwise
    `--depth 1` means "the roots" on a tree with several and "the roots and
    their forks" on a tree with one, and only the second tree is ever tested.

    So the fixture has both shapes at once: two roots, one of which forks.
    """
    import io
    import contextlib
    import loom

    print('\ncapping what the render prints')
    path = os.path.join(workdir, 'depth')

    def run(*argv):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = loom.main(['-d', path, *argv])
        return code, out.getvalue()

    run('new', '--seed', '5')
    run('author', 'One.', '.')          # s0, a root
    run('author', 'Two.', '.')          # s1, another
    run('author', ' left', 's0')        # s2, at s0's tip
    run('author', ' right', 's0')       # s3, at the same tip -- so s0 forks

    code, out = run('show')
    check('uncapped, the fork under a root renders',
          code == 0 and 'Gs2' in out and 'Gs3' in out, out)

    code, out = run('show', '--depth', '0')
    check('--depth 0 stops at the roots, not one level short of them',
          code == 0 and 'Gs0' in out and 'Gs1' in out and 'Gs2' not in out, out)
    check('and the elision counts the runs it stood in for',
          '2 more run(s)' in out, out)

    code, out = run('show', '--depth', '1')
    check('--depth 1 reaches the forks below a root',
          'Gs2' in out and 'Gs3' in out and 'more run(s)' not in out, out)
    # the cap is display-only, so the summary underneath still counts the tree
    check('a depth limit hides runs rather than unreaching them',
          '4 spans, 0 unreachable' in run('show', '--depth', '0')[1], out)

    code, out = run('show', 's0+0')
    check('a subtree renders from a position, without its siblings',
          code == 0 and 'Gs0' in out and 'Gs2' in out and 'Gs1' not in out, out)

    run('delete', 's1+0')
    check('a subtree rooted at an unreachable span is refused, not a traceback',
          _exits(run, 'show', 's1+0'))
    code, out = run('show', '-a', 's1+0')
    check('and renders under -a, which is what the refusal points at',
          code == 0 and 'Gs1' in out, out)


def _exits(run, *argv):
    try:
        run(*argv)
    except SystemExit:
        return True
    except KeyError:
        return False
    return False


def main():
    workdir = tempfile.mkdtemp(prefix='token-loom-')
    path = os.path.join(workdir, 'example')
    try:
        print('round trip')
        os.makedirs(path)
        tree = worked_example()
        store = BulkStore(os.path.join(path, 'bulk.sqlite'))
        fill_store(store)
        save(path, tree)
        store.close()

        # in flight at rest: nothing generating, so s5 must load as aborted
        reloaded, store = open_tree(path)
        check('validates clean', not validate(reloaded, store),
              str(validate(reloaded, store)))
        check('s5 recovered as aborted', store.terminator('s5') == 'aborted')
        check('s5 completed empty, keeping its attachment',
              reloaded.spans['s5'].text == b''
              and reloaded.spans['s5'].parent == Position('s3', len(spelled(CLEAR))))

        print('\nstructure survives the round trip')
        check('path bytes, s2 -- the unbranched continuation',
              reloaded.path_bytes(reloaded.tip('s2'))
              == PROMPT + spelled(CALM), repr(reloaded.path_bytes(reloaded.tip('s2'))))
        check('path bytes, s3 -- the branched one, still whole',
              reloaded.path_bytes(reloaded.tip('s3')) == PROMPT + spelled(CLEAR))
        check('path bytes, s4 -- the counterfactual branch',
              reloaded.path_bytes(reloaded.tip('s4'))
              == PROMPT + spelled(CLEAR)[:CUT] + STILL,
              repr(reloaded.path_bytes(reloaded.tip('s4'))))
        check('s3 keeps all fifteen bytes, referenced as a range by nothing',
              reloaded.spans['s3'].text == spelled(CLEAR)
              and len(spelled(CLEAR)) == 15)
        check('sibling branches share an absolute offset',
              reloaded.absolute(Position('s2', 0))
              == reloaded.absolute(Position('s3', 0)) == len(PROMPT))
        check('and are told apart by their span alone',
              Position('s2', 0) != Position('s3', 0))
        check('the branch point is where its origin token starts',
              token_offsets(store, 's3')[2] == CUT
              and reloaded.spans['s4'].parent == Position('s3', CUT))
        check('what branches from s3 is two children at two offsets',
              reloaded.children_of('s3') == [(CUT, 's4'),
                                             (len(spelled(CLEAR)), 's5')])
        check('counterfactuals keyed by id',
              [c.token_id for c in store.counterfactuals('s3', 2)]
              == [1005, 2058, 1006])
        # the two entries differ in one field, which is the case that a
        # by-identity implementation and a by-value one disagree about
        check('interning is by value, not identity',
              reloaded.intern(reloaded.params['p1']) == 'p1'
              and reloaded.intern(reloaded.params['p2']) == 'p2'
              and len(reloaded.params) == 2)
        store.close()

        print('\nthe marker, and the key the marker cannot stand in for')
        marker = json.loads(open(os.path.join(path, 'tree.json')).read())
        check('the format marker is what this format is called',
              marker['format'] == 'token-loom/1.1', marker['format'])
        check('a root writes its parent as null rather than omitting it',
              'parent' in marker['spans']['s1']
              and marker['spans']['s1']['parent'] is None,
              repr(marker['spans']['s1'].get('parent', '<absent>')))

        # The shape this replaced kept structure in runs and pieces, so its
        # spans have no `parent` at all -- and it called itself `token-loom/1`
        # too, since it never went live and the number was reclaimed. The
        # marker therefore cannot tell the two apart. Reading `parent` as
        # required is the whole of what does: with `.get()` every span of such
        # a file loads as a root, and the result validates.
        stale = json.loads(json.dumps(marker))
        del stale['spans']['s2']['parent']
        try:
            Tree.from_json(stale)
            check('a span with no parent is refused', False,
                  'it loaded, and every span would have been a root')
        except ValueError as e:
            check('a span with no parent is refused, loudly', 'parent' in str(e),
                  str(e))

        print('\ndeleting bisects a span, never opens one')
        tree = worked_example()
        tree.deleted = [Position('s3', CUT)]
        problems = validate(tree)
        check('a truncating address leaves the tree valid', not problems,
              str(problems))
        check('s3 still holds its bytes', tree.spans['s3'].text == spelled(CLEAR))
        check('the tree reaches only its head', tree.live().get('s3') == CUT)
        check('s4 goes with it, being anchored at the cut',
              's4' not in tree.live())
        check('s5 goes with it too, being anchored past it',
              's5' not in tree.live())
        check('s2 survives its sibling', 's2' in tree.live())

        # `Tree.live` answers with one offset per span, so "the live part is a
        # prefix from byte 0" is the shape of the answer rather than a property
        # of it. What is worth checking is that reading up to that offset gives
        # the bytes it should, which is the claim the shape is there to support.
        check('a live extent is a prefix from byte 0 by construction',
              tree.path_bytes(Position('s3', tree.live()['s3']))
              == PROMPT + spelled(CLEAR)[:CUT])
        tree.deleted = [Position('s3', 0)]
        check('deleting the head takes the whole span out of reach',
              's3' not in tree.live() and 's4' not in tree.live())

        print('\noffsets are bytes, not characters')
        # The whole model is anchored on byte offsets, and every one of them
        # here is a Python len() -- which counts characters. On ASCII the two
        # agree and nothing above would notice the difference. This is the
        # cheapest place to find out, and the only one that fires early.
        # 'café — ' is 7 characters and 10 bytes: é is 2, the em dash is 3
        accented = 'café — '
        wide = Tree.empty(base_seed=1)
        wide.params['p1'] = dict(worked_example().params['p1'])
        wide.add(Span('s1', 'given', None, accented.encode(), TS))
        wide.add(Span('s2', 'sampled', Position('s1', len(accented.encode())),
                      b'yes', TS, params='p1', seed=2, batch='b1', index=0,
                      slice_start=Position('s1', 0)))
        check('a 7-character prompt is 10 bytes',
              len(accented) == 7 and wide.spans['s1'].length == 10)
        check('the continuation anchors at byte 10, not character 7',
              wide.spans['s2'].parent == Position('s1', 10)
              and not validate(wide), str(validate(wide)))
        wide_path = os.path.join(workdir, 'wide')
        os.makedirs(wide_path)
        wstore = BulkStore(os.path.join(wide_path, 'bulk.sqlite'))
        wstore.add_tokens('s2', [Token(0, 7, b'yes', -0.4)])
        wstore.set_terminator('s2', LENGTH)
        save(wide_path, wide)
        wstore.close()
        wide_back, wstore = open_tree(wide_path)
        check('multi-byte text survives the round trip',
              wide_back.path_bytes(wide_back.tip('s2')).decode()
              == accented + 'yes',
              repr(wide_back.path_bytes(wide_back.tip('s2'))))
        wstore.close()

        print('\nbytes with no string form')
        # Measured, not hypothetical: Qwen2.5 tokenises this symbol into three
        # tokens, none valid UTF-8 alone. A length limit inside one leaves a
        # span JSON has no string for.
        symbol = '🜁'.encode()
        cut = Tree.empty(base_seed=3)
        cut.params['p0'] = dict(worked_example().params['p1'])
        cut.add(Span('s0', 'given', None, b'sign: ', TS))
        cut.add(Span('s1', 'sampled', Position('s0', 6), symbol[:3], TS,
                     params='p0', seed=3, batch='b0', index=0,
                     slice_start=Position('s0', 0)))
        check('a partial character is three bytes, not one',
              len(symbol) == 4 and cut.spans['s1'].length == 3)
        rendered = cut.to_json()['spans']['s1']['text']
        check('it serialises as an object rather than a string',
              isinstance(rendered, dict) and 'b64' in rendered, str(rendered))
        check('and the readable spans are unaffected',
              cut.to_json()['spans']['s0']['text'] == 'sign: ')

        cut_path = os.path.join(workdir, 'cut')
        os.makedirs(cut_path)
        cstore = BulkStore(os.path.join(cut_path, 'bulk.sqlite'))
        cstore.add_tokens('s1', [Token(0, 99, symbol[:3], -5.0)])
        cstore.set_terminator('s1', LENGTH)
        save(cut_path, cut)
        cstore.close()
        cut_back, cstore = open_tree(cut_path)
        check('the bytes survive the round trip exactly',
              cut_back.spans['s1'].text == symbol[:3])
        check('and the tree still validates against its tokens',
              not validate(cut_back, cstore), str(validate(cut_back, cstore)))
        cstore.close()

        print('\nand the operations that can reach that case')
        # The span above was hand-built, which proves the serialisation and
        # nothing about the paths into it. These are the paths: authoring, and
        # branching to a counterfactual. Generation is *not* one of them --
        # llama-server accumulates until its bytes decode, so a sampled span
        # cannot end mid-character and this shape is unreachable from a model
        # call. A path believed to work because nothing contradicts it is how
        # `CONTEXT` stayed dead code, so both live ones are reached on purpose.
        reach_path = os.path.join(workdir, 'reach')
        reach, rstore = create_tree(reach_path, base_seed=5)
        conditions = dict(worked_example().params['p1'])

        # 1. authoring. `author` takes bytes, and bytes arrive from a file or a
        # paste as well as from a keyboard -- the CLI encodes a `str` and so
        # cannot produce this, but the CLI is not the only client.
        typed = author(reach, None, b'sign: ')
        pasted = author(reach, reach.tip(typed.id), symbol[:3])
        check('an authored fragment serialises as an object',
              isinstance(reach.to_json()['spans'][pasted.id]['text'], dict),
              str(reach.to_json()['spans'][pasted.id]['text']))

        # 2. branching to a counterfactual, which is the case that arises
        # without anyone arranging it: the bytes come from the model's own
        # vocabulary, where a byte-fallback token is a fragment of a character
        # by construction. The sampled span it hangs off is whole, as every
        # sampled span is; the branch takes one alternative and stops there.
        alt = '中'.encode()[:2]
        sampled = begin_generation(reach, reach.tip(typed.id), conditions, 1)[0]
        complete(reach, rstore, sampled.id,
                 [Token(0, 601, symbol[:3], -0.20),
                  Token(1, 602, symbol[3:], -0.05)], LENGTH,
                 [Counterfactual(0, 0, 601, symbol[:3], -0.20),
                  Counterfactual(0, 1, 603, alt, -2.60)])
        check('the sampled span it branches from is whole, as sampled spans are',
              sampled.text == symbol and sampled.text.decode() == '🜁')
        taken = branch_counterfactual(reach, rstore, sampled.id, 0, 1)
        check('a counterfactual branch onto a byte-fallback token is a fragment',
              taken.text == alt and taken.length == 2)
        check('and it too serialises as an object',
              isinstance(reach.to_json()['spans'][taken.id]['text'], dict),
              str(reach.to_json()['spans'][taken.id]['text']))

        save(reach_path, reach)
        rstore.close()
        reach_back, rstore = open_tree(reach_path)
        check('both survive the round trip byte for byte',
              (reach_back.spans[pasted.id].text,
               reach_back.spans[taken.id].text) == (symbol[:3], alt))
        check('the tree validates with two spans that have no string form',
              not validate(reach_back, rstore), str(validate(reach_back, rstore)))
        # the point of the format: an address is an address regardless of
        # whether the bytes it names can be printed. The branch hangs at offset
        # 0 of the sampled span -- it replaces that token rather than following
        # it -- so the path holds the prompt and the alternative and nothing of
        # what was actually sampled.
        check('and a fragment span is addressable like any other',
              reach_back.path_bytes(reach_back.tip(taken.id)) == b'sign: ' + alt,
              repr(reach_back.path_bytes(reach_back.tip(taken.id))))
        rstore.close()

        print('\na slice start that lands inside a character')
        # prompt_length is in bytes, so subtracting it lands wherever it lands
        mixed = 'abécd'
        edge = Tree.empty(base_seed=4)
        edge.add(Span('s0', 'given', None, mixed.encode(), TS))
        check('the text is 5 characters in 6 bytes',
              len(mixed) == 5 and edge.spans['s0'].length == 6)
        start, end, text = slice_at(edge, edge.tip('s0'), 3)
        check('the start nudges forward off the continuation byte',
              (start, end, text) == (Position('s0', 4), Position('s0', 6), b'cd'),
              f'{(start, end)} {text!r}')
        check('and what it returns is decodable, which is the point',
              text.decode() == 'cd')
        start, _, text = slice_at(edge, edge.tip('s0'), 4)
        check('a start already on a boundary is left alone',
              start == Position('s0', 2) and text == 'écd'.encode(),
              f'{start} {text!r}')

        # before the validator section, which deliberately breaks the store on
        # disk and leaves it broken
        cli_reads(path)

        print('\nthe validator rejects')
        example_store = BulkStore(os.path.join(path, 'bulk.sqlite'))
        expect_problem(
            '1. a parent naming a span that does not exist',
            lambda t: setattr(t.spans['s3'], 'parent', Position('s99', 0)),
            'does not exist')
        expect_problem(
            '1. a parent offset past the bytes its span has',
            lambda t: setattr(t.spans['s3'], 'parent', Position('s1', 99)),
            'anchored at 99')
        expect_problem(
            '2. a parent chain that cycles',
            lambda t: (setattr(t.spans['s2'], 'parent', Position('s3', 0)),
                       setattr(t.spans['s3'], 'parent', Position('s2', 0))),
            'cycles')
        expect_problem(
            '3. an unknown provenance kind',
            lambda t: setattr(t.spans['s2'], 'kind', 'invented'),
            'unknown kind')
        expect_problem(
            '3. a counterfactual with no origin',
            lambda t: setattr(t.spans['s4'], 'origin', None),
            'no origin')
        expect_problem(
            '3. a slice starting on a branch the span is not on',
            lambda t: setattr(t.spans['s3'], 'slice_start', Position('s2', 0)),
            'not on its path')
        expect_problem(
            '4. a deletion address naming a missing span',
            lambda t: t.deleted.append(Position('s99', 0)),
            'deleted names missing span')
        expect_problem(
            '4. a deletion address past the bytes its span has',
            lambda t: t.deleted.append(Position('s3', 99)),
            'deleted at 99')
        expect_problem(
            '5. a counterfactual anchored where its origin does not say',
            lambda t: setattr(t.spans['s4'], 'parent', Position('s3', 5)),
            f'but token 2 starts at {CUT}', example_store)
        expect_problem(
            '5. a counterfactual branching off a span its origin does not name',
            lambda t: setattr(t.spans['s4'], 'parent', Position('s2', 5)),
            'its origin names', example_store)
        expect_problem(
            '6. text its tokens do not spell',
            lambda t: setattr(t.spans['s3'], 'text', b' calm and CLEAR'),
            'spell', example_store)
        expect_problem(
            '6. a given span carrying token rows',
            lambda t: setattr(t.spans['s2'], 'kind', 'given'),
            'given span has', example_store)
        example_store.db.execute("DELETE FROM terminators WHERE span = 's3'")
        example_store.db.commit()
        expect_problem(
            '7. a sampled span with no terminator',
            lambda t: None, 'no terminator', example_store)
        example_store.close()

        operations(workdir)
        driver(workdir)

        print(f'\n{PASS} passed, {FAIL} failed')
        return 1 if FAIL else 0
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


if __name__ == '__main__':
    sys.exit(main())
