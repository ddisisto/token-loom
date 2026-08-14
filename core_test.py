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

from core import BulkStore, Invalid, Tree, open_tree, recover, save, validate
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

        print(f'\n{PASS} passed, {FAIL} failed')
        return 1 if FAIL else 0
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


if __name__ == '__main__':
    sys.exit(main())
