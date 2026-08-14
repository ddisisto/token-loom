#!/usr/bin/env python
"""Headless check that the format holds -- the worked example, round-tripped.

Two halves, and the second is the one that matters. Round-tripping proves the
format can be written and read back. Breaking it nine ways proves the validator
would have noticed: a validator that has never rejected anything is untested,
and this one exists to catch exactly the mistakes that are invisible by eye.

Usage: python core_test.py
"""
import os
import shutil
import sys
import tempfile

from core import (BulkStore, Invalid, Position, Tree, at, author,
                  begin_generation, branch_counterfactual, complete,
                  create_tree, delete, locate, open_tree, restore, save,
                  slice_at, split, validate)
from core.store import Counterfactual, LENGTH, Token
from core.tree import Piece, Run, Span

TS = '2026-08-12-10.00.00'

# the worked example from PHASE-1.md: a root, one authored prompt, a batch of
# two continuations, a counterfactual branch off the second, and one call left
# in flight.
TOKENS = {
    's2': [(1001, b' calm', -0.51), (1002, b' for', -1.24), (1003, b' days', -0.83)],
    's3': [(1001, b' calm', -0.51), (1004, b' and', -1.11), (1005, b' clear', -0.92)],
    's4': [(2058, b' still', -2.31)],
}
COUNTERFACTUALS = {
    ('s3', 2): [(1005, b' clear', -0.92), (2058, b' still', -2.31),
                (1006, b' bright', -3.10)],
}


def worked_example():
    tree = Tree.empty(base_seed=90210)
    tree.tree_id = 'worked-example'
    tree.params['p1'] = {'temperature': 0.9, 'top_p': 1, 'top_n': 3,
                         'length': 3, 'stop': [],
                         'model': 'qwen2.5-7b-base', 'tokenizer': 'qwen2.5',
                         'n_ctx': 16384, 'prompt_length': 6000}

    tree.spans = {
        's1': Span('s1', 'human', 0, 11, b'The sea was', TS),
        's2': Span('s2', 'sampled', 11, 25, b' calm for days', TS,
                   params='p1', seed=90211, batch='b1', index=0, slice_start=0),
        's3': Span('s3', 'sampled', 11, 26, b' calm and clear', TS,
                   params='p1', seed=90212, batch='b1', index=1, slice_start=0),
        's4': Span('s4', 'counterfactual', 20, 26, b' still', TS,
                   origin={'span': 's3', 'index': 2, 'token_id': 2058}),
        # in flight: provenance written, byte record still empty
        's5': Span('s5', 'sampled', 26, None, None, TS,
                   params='p1', seed=90213, batch='b2', index=0, slice_start=0),
    }
    tree.runs = {
        'r0': Run('r0', None, 0, [], ['r1']),
        'r1': Run('r1', 'r0', 0, [Piece('s1', 0, 11)], ['r2', 'r3']),
        'r2': Run('r2', 'r1', 11, [Piece('s2', 0, 14)], []),
        # the split divided r3's piece list; s3 itself was never opened
        'r3': Run('r3', 'r1', 11, [Piece('s3', 0, 9)], ['r4', 'r5']),
        'r4': Run('r4', 'r3', 20, [Piece('s3', 9, 15)], ['r6']),
        'r5': Run('r5', 'r3', 20, [Piece('s4', 0, 6)], []),
        # the placeholder piece is what links s5 to the run it will land in
        'r6': Run('r6', 'r4', 26, [Piece('s5', 0, 0)], []),
    }
    tree.selected = {'run': 'r4', 'offset': 6}
    return tree


def fill_store(store):
    for span, rows in TOKENS.items():
        store.add_tokens(span, [Token(i, *row) for i, row in enumerate(rows)])
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


def expect_problem(name, mangle, matching):
    """Break the worked example one way, and confirm the validator says so."""
    tree = worked_example()
    mangle(tree)
    problems = validate(tree)
    hit = [p for p in problems if matching in p]
    check(name, bool(hit), f'got {problems or "no problems"}')


SETTINGS = {'temperature': 0.9, 'top_p': 1, 'top_n': 3, 'length': 4,
            'stop': [], 'model': 'qwen2.5-7b-base', 'tokenizer': 'qwen2.5',
            'n_ctx': 16384, 'prompt_length': 6000}

PROMPT = b'The lighthouse keeper wrote:'
CALM = [(11, b' the'), (12, b' sea'), (13, b' was'), (14, b' calm')]
WILD = [(11, b' the'), (12, b' sea'), (13, b' was'), (15, b' wild')]


def toks(parts):
    return [Token(i, tid, raw, -1.0 - i) for i, (tid, raw) in enumerate(parts)]


def operations(workdir):
    """The six, on a tree built entirely by hand. No model involved."""
    path = os.path.join(workdir, 'ops')
    tree, store = create_tree(path, base_seed=500)

    # ids are minted as one past the highest in use, so the first span is s0.
    # The worked example's s1..s5 are illustrative names, not a convention.
    print('\nauthor and generate')
    prompt = author(tree, Position('r0', 0), PROMPT)
    check('authoring under the empty root makes a child, not bytes on it',
          tree.runs['r0'].pieces == [] and tree.runs['r1'].pieces
          == [Piece('s0', 0, 28)])
    check('the human span carries no parameters and no seed',
          prompt.params is None and prompt.seed is None)

    spans = begin_generation(tree, Position('r1', 28), SETTINGS, n=2)
    check('n continuations become n child runs',
          tree.runs['r1'].children == ['r2', 'r3'])
    check('one batch, distinct seeds derived from the base',
          {s.batch for s in spans} == {'b0'}
          and [s.seed for s in spans] == [500, 501])
    check('in flight: provenance, no bytes, an empty piece as the link',
          all(not s.complete for s in spans)
          and tree.runs['r2'].pieces == [Piece('s1', 0, 0)])
    check('the intent record validates before any token exists',
          not validate(tree, store), str(validate(tree, store)))
    check('both continuations share one interned parameter set',
          {s.params for s in spans} == {'p0'} and len(tree.params) == 1)

    complete(tree, store, 's1', toks(CALM), LENGTH)
    complete(tree, store, 's2', toks(WILD), LENGTH)
    check('completion widens the placeholder piece',
          tree.runs['r2'].pieces == [Piece('s1', 0, 17)])
    check('the byte record is filled in, not the provenance',
          tree.spans['s1'].text == b' the sea was calm'
          and tree.spans['s1'].seed == 500)
    check('generated paths read back whole',
          tree.path_bytes('r3') == PROMPT + b' the sea was wild',
          repr(tree.path_bytes('r3')))
    check('validates after generation', not validate(tree, store),
          str(validate(tree, store)))

    print('\nsplit')
    before = {r: tree.runs[r].start for r in tree.runs}
    # deliberately mid-token: ' was' spans bytes 8..12, and this cuts at 9.
    # Byte offsets are the anchor, so a run boundary need not be a token one.
    anchor = split(tree, Position('r2', 9))
    check('the prefix keeps the run id', anchor == 'r2')
    check('the suffix is a new run holding the rest',
          tree.runs['r2'].pieces == [Piece('s1', 0, 9)]
          and tree.runs['r4'].pieces == [Piece('s1', 9, 17)])
    check('splitting changes no absolute offset',
          all(tree.runs[r].start == start for r, start in before.items()))
    check('the span was never opened -- it still holds all seventeen bytes',
          tree.spans['s1'].text == b' the sea was calm')
    check('the text either side of the split is unchanged',
          tree.path_bytes('r4') == PROMPT + b' the sea was calm')
    check('children relink to the suffix', tree.runs['r2'].children == ['r4'])

    count = len(tree.runs)
    check('idempotent at the boundary it just made',
          split(tree, Position('r2', 9)) == 'r2' and len(tree.runs) == count)
    check('offset 0 of a run answers with its parent',
          split(tree, Position('r4', 0)) == 'r2' and len(tree.runs) == count)
    check('validates after splitting', not validate(tree, store),
          str(validate(tree, store)))

    print('\nbranch to a counterfactual')
    store.add_counterfactuals('s1', [
        Counterfactual(3, 0, 14, b' calm', -0.3),
        Counterfactual(3, 1, 16, b' rough', -1.8),
        Counterfactual(3, 2, 17, b' still', -2.4)])
    check('a token index resolves to the run a split moved it into',
          locate(tree, 's1', 12) == Position('r4', 3),
          str(locate(tree, 's1', 12)))

    branched = branch_counterfactual(tree, store, 's1', 3, rank=1)
    check('the counterfactual branch reads as the road not taken',
          tree.path_bytes('r6') == PROMPT + b' the sea was rough',
          repr(tree.path_bytes('r6')))
    check('it carries the token id, not the rank',
          branched.origin == {'span': 's1', 'index': 3, 'token_id': 16})
    check('and no parameters, having never been a generation call',
          branched.params is None and branched.seed is None)
    check('the sampled continuation survives beside it',
          tree.path_bytes('r5') == PROMPT + b' the sea was calm')
    check('validates after branching', not validate(tree, store),
          str(validate(tree, store)))

    print('\ncontinue at a tip, and slice')
    more = begin_generation(tree, Position('r6', 6), SETTINGS, n=1)
    check('one continuation at a tip extends the run rather than branching',
          tree.runs['r6'].children == []
          and [p.span for p in tree.runs['r6'].pieces] == ['s3', 's4'],
          str([p.span for p in tree.runs['r6'].pieces]))
    check('the seed keeps counting past the spans already generated',
          more[0].seed == 502)
    complete(tree, store, 's4', toks([(20, b' indeed')]), LENGTH)
    check('a run may reference several spans',
          tree.path_bytes('r6') == PROMPT + b' the sea was rough indeed')

    start, end, text = slice_at(tree, Position('r6', 6), 20)
    check('a slice is bounds and the bytes they name',
          (start, end) == (26, 46) and text == b'e: the sea was rough',
          f'{(start, end)} {text!r}')
    start, end, text = slice_at(tree, Position('r6', 6), 1000)
    check('and clamps at the root rather than running off it',
          start == 0 and text == PROMPT + b' the sea was rough')
    check('an absolute offset resolves back to a position',
          at(tree, 'r6', 30) == Position('r2', 2))

    print('\ndelete')
    delete(tree, 'r5')
    live = tree.live_runs()
    check('the deleted run is out of the live set', 'r5' not in live)
    check('its sibling is untouched', 'r6' in live)
    check('the span keeps every byte it recorded',
          tree.spans['s1'].text == b' the sea was calm')
    check('its tokens are still in the bulk store',
          len(store.tokens('s1')) == 4)
    check('validates after deleting', not validate(tree, store),
          str(validate(tree, store)))

    print('\nselected is the one thing in the file keyed by a run id')
    # Which makes it the standing demonstration of decision 1: after a split
    # the old id still resolves, but to a run that no longer reaches that far.
    # The absolute offset is what has to survive, not the pair naming it.
    tree.selected = {'run': 'r6', 'offset': 10}
    was = tree.runs['r6'].start + 10
    split(tree, Position('r6', 4))
    check('a split past the cursor moves it to the suffix',
          tree.selected == {'run': 'r7', 'offset': 6}, str(tree.selected))
    check('and the absolute offset it named is unchanged',
          tree.runs[tree.selected['run']].start + tree.selected['offset'] == was)

    delete(tree, 'r7')
    check('deleting out from under the cursor leaves it somewhere live',
          tree.selected['run'] in tree.live_runs(), str(tree.selected))
    restore(tree, 'r7')
    check('and delete is reversible, being soft', 'r7' in tree.live_runs())
    check('validates throughout', not validate(tree, store),
          str(validate(tree, store)))

    print('\nslice start is recorded resolved, its length interned')
    near = begin_generation(tree, Position('r3', 17), {**SETTINGS,
                                                       'prompt_length': 12}, 1)
    check('a restricted context resolves to an offset on the span',
          near[0].slice_start == 33, str(near[0].slice_start))
    check('the length interns; the resolved offset does not',
          tree.params[near[0].params]['prompt_length'] == 12
          and 'slice_start' not in tree.params[near[0].params])
    check('a different framing at the same position is a new parameter set',
          near[0].params != 'p0' and len(tree.params) == 2)
    complete(tree, store, near[0].id, toks([(21, b' still')]), LENGTH)

    print('\nthe whole thing survives a round trip')
    save(path, tree)
    store.close()
    back, store = open_tree(path)
    check('reloads and validates', not validate(back, store))
    check('structure is identical', back.to_json() == tree.to_json())
    # r6 was split since, so the full continuation now ends at its suffix --
    # which is the point: run ids narrow, absolute offsets do not
    check('and still reads the same',
          back.path_bytes('r7') == PROMPT + b' the sea was rough indeed',
          repr(back.path_bytes('r7')))
    store.close()


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
        check('validates clean', not validate(reloaded, store))
        check('s5 recovered as aborted', store.terminator('s5') == 'aborted')
        check('s5 completed empty', reloaded.spans['s5'].text == b''
              and reloaded.spans['s5'].end == 26)

        print('\nstructure survives the round trip')
        check('run bytes, r3', reloaded.run_bytes('r3') == b' calm and',
              repr(reloaded.run_bytes('r3')))
        check('path bytes, r2 -- the unbranched continuation',
              reloaded.path_bytes('r2') == b'The sea was calm for days',
              repr(reloaded.path_bytes('r2')))
        check('path bytes, r4 -- through the split',
              reloaded.path_bytes('r4') == b'The sea was calm and clear',
              repr(reloaded.path_bytes('r4')))
        check('path bytes, r5 -- the counterfactual branch',
              reloaded.path_bytes('r5') == b'The sea was calm and still',
              repr(reloaded.path_bytes('r5')))
        check('s3 keeps all fifteen bytes across two runs',
              reloaded.spans['s3'].text == b' calm and clear')
        check('two runs reference s3',
              len(list(reloaded.pieces_of('s3'))) == 2)
        check('sibling branches share an offset',
              reloaded.runs['r3'].end == reloaded.runs['r5'].start == 20)
        check('counterfactuals keyed by id',
              [c.token_id for c in store.counterfactuals('s3', 2)]
              == [1005, 2058, 1006])
        check('interning is by value, not identity',
              reloaded.intern(reloaded.params['p1']) == 'p1'
              and len(reloaded.params) == 1)
        store.close()

        print('\ndeleting bisects a run, never a span')
        tree = worked_example()
        tree.deleted = ['r4']
        problems = validate(tree)
        check('a deleted tail leaves the tree valid', not problems,
              str(problems))
        check('s3 still holds its bytes', tree.spans['s3'].text == b' calm and clear')
        check('r4 is gone from the live set', 'r4' not in tree.live_runs())
        check('r6 goes with it -- cascade', 'r6' not in tree.live_runs())
        check('r5 survives its sibling', 'r5' in tree.live_runs())

        # prefix coverage, asserted positively: it cannot be made to fail
        # through delete, because delete takes whole subtrees. Kept as a guard
        # on the operation rather than on the file -- see validate.py.
        live = tree.live_runs()
        reachable = [p for _, _, p in tree.pieces_of('s3', runs=live)]
        check('s3 is reachable only as a prefix of itself',
              [tuple(p) for p in reachable] == [('s3', 0, 9)],
              str([tuple(p) for p in reachable]))
        tree.deleted = ['r3']
        check('deleting the head takes the whole span out of reach',
              not list(tree.pieces_of('s3', runs=tree.live_runs())))

        print('\noffsets are bytes, not characters')
        # The whole model is anchored on byte offsets, and every one of them
        # here is a Python len() -- which counts characters. On ASCII the two
        # agree and nothing above would notice the difference. This is the
        # cheapest place to find out, and the only one that fires early.
        # 'café — ' is 7 characters and 10 bytes: é is 2, the em dash is 3
        wide = Tree.empty(base_seed=1)
        wide.spans = {
            's1': Span('s1', 'human', 0, 10, 'café — '.encode(), TS),
            's2': Span('s2', 'sampled', 10, 13, b'yes', TS,
                       params='p1', seed=2, batch='b1', index=0, slice_start=0),
        }
        wide.params['p1'] = dict(tree.params['p1'])
        wide.runs = {
            'r0': Run('r0', None, 0, [], ['r1']),
            'r1': Run('r1', 'r0', 0, [Piece('s1', 0, 10)], ['r2']),
            'r2': Run('r2', 'r1', 10, [Piece('s2', 0, 3)], []),
        }
        check('a 7-character prompt is 10 bytes',
              len('café — ') == 7 and wide.spans['s1'].length == 10)
        check('the continuation starts at byte 10, not character 7',
              not [p for p in validate(wide) if 'starts at' in p],
              str(validate(wide)))
        wide_path = os.path.join(workdir, 'wide')
        os.makedirs(wide_path)
        wstore = BulkStore(os.path.join(wide_path, 'bulk.sqlite'))
        wstore.add_tokens('s2', [Token(0, 7, b'yes', -0.4)])
        wstore.set_terminator('s2', LENGTH)
        save(wide_path, wide)
        wstore.close()
        wide_back, wstore = open_tree(wide_path)
        check('multi-byte text survives the round trip',
              wide_back.path_bytes('r2').decode() == 'café — yes',
              repr(wide_back.path_bytes('r2')))
        wstore.close()

        print('\nbytes with no string form')
        # Measured, not hypothetical: Qwen2.5 tokenises this symbol into three
        # tokens, none valid UTF-8 alone. A length limit inside one leaves a
        # span JSON has no string for.
        symbol = '🜁'.encode()
        cut = Tree.empty(base_seed=3)
        cut.params['p0'] = dict(tree.params['p1'])
        cut.spans = {
            's0': Span('s0', 'human', 0, 6, b'sign: ', TS),
            's1': Span('s1', 'sampled', 6, 9, symbol[:3], TS, params='p0',
                       seed=3, batch='b0', index=0, slice_start=0),
        }
        cut.runs = {
            'r0': Run('r0', None, 0, [], ['r1']),
            'r1': Run('r1', 'r0', 0, [Piece('s0', 0, 6)], ['r2']),
            'r2': Run('r2', 'r1', 6, [Piece('s1', 0, 3)], []),
        }
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

        print('\na slice start that lands inside a character')
        # prompt_length is in bytes, so subtracting it lands wherever it lands
        edge = Tree.empty(base_seed=4)
        edge.spans = {'s0': Span('s0', 'human', 0, 6, 'abécd'.encode(), TS)}
        edge.runs = {
            'r0': Run('r0', None, 0, [], ['r1']),
            'r1': Run('r1', 'r0', 0, [Piece('s0', 0, 6)], []),
        }
        check('the text is 5 characters in 6 bytes',
              len('abécd') == 5 and edge.spans['s0'].length == 6)
        start, end, text = slice_at(edge, Position('r1', 6), 3)
        check('the start nudges forward off the continuation byte',
              (start, end, text) == (4, 6, b'cd'), f'{(start, end)} {text!r}')
        check('and what it returns is decodable, which is the point',
              text.decode() == 'cd')
        start, _, text = slice_at(edge, Position('r1', 6), 4)
        check('a start already on a boundary is left alone',
              start == 2 and text == 'écd'.encode(), f'{start} {text!r}')

        print('\nthe validator rejects')
        expect_problem(
            '1. a piece range past the end of its span',
            lambda t: t.runs['r4'].pieces.__setitem__(0, Piece('s3', 9, 99)),
            'outside s3')
        expect_problem(
            '1. an empty piece on a span that has bytes',
            lambda t: t.runs['r2'].pieces.append(Piece('s2', 14, 14)),
            'which has bytes')
        expect_problem(
            '2. a broken offset chain',
            lambda t: setattr(t.runs['r4'], 'start', 19),
            'starts at 19')
        expect_problem(
            '3. a child whose parent disowns it',
            lambda t: t.runs['r3'].children.remove('r5'),
            'does not list it')
        expect_problem(
            '4. strong coverage: a span byte no piece reaches',
            lambda t: t.runs['r4'].pieces.__setitem__(0, Piece('s3', 10, 15)),
            'strong coverage')
        expect_problem(
            '6. an extent that disagrees with its text',
            lambda t: setattr(t.spans['s2'], 'end', 24),
            'text is 14')
        expect_problem(
            '7. a span that says it sits somewhere it does not',
            lambda t: setattr(t.spans['s4'], 'start', 21),
            'says it starts at 21')

        # 8 and 9 need the store, so they do not fit expect_problem
        for name, mangle, matching in [
            ('8. text its tokens do not spell',
             lambda t: setattr(t.spans['s3'], 'text', b' calm and CLEAR'), 'spell'),
            ('9. a sampled span with no terminator',
             lambda t: None, 'no terminator'),
        ]:
            broken = worked_example()
            mangle(broken)
            side = os.path.join(workdir, 'broken', name[:2])
            os.makedirs(side)
            store = BulkStore(os.path.join(side, 'bulk.sqlite'))
            fill_store(store)
            if matching == 'no terminator':
                store.db.execute("DELETE FROM terminators WHERE span = 's3'")
                store.db.commit()
            problems = validate(broken, store)
            check(name, any(matching in p for p in problems),
                  f'got {problems or "no problems"}')
            store.close()

        operations(workdir)

        print(f'\n{PASS} passed, {FAIL} failed')
        return 1 if FAIL else 0
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


if __name__ == '__main__':
    sys.exit(main())
