#!/usr/bin/env python
"""Headless check that generation lands in the core intact. Needs the server.

`core_test.py` proves the format and the operations on hand-written tokens.
This proves the one thing it cannot: that what llama-server actually returns
survives the round trip -- ids, bytes, logprobs, counterfactuals and the reason
a span stopped -- and that the token overlay lines up with the byte anchor.

Usage: scripts/llama-server.sh, then python llama_test.py
"""
import shutil
import sys
import tempfile

from core import EOS, LENGTH, Position, Server, spelled, validate
from core.ops import token_offsets
from core.session import Session

PASS, FAIL = 0, 0


def check(name, ok, detail=''):
    global PASS, FAIL
    if ok:
        PASS += 1
        print(f'  ok    {name}')
    else:
        FAIL += 1
        print(f'  FAIL  {name}{"  -- " + detail if detail else ""}')


def main():
    server = Server()
    if not server.alive():
        print('llama-server is not answering on', server.base)
        print('start it with scripts/llama-server.sh')
        return 2

    workdir = tempfile.mkdtemp(prefix='token-loom-live-')
    try:
        print('the server describes itself')
        described = server.describe()
        print('  ', described)
        check('model and context size come back',
              described['model'] and described['n_ctx'])

        session = Session.create(f'{workdir}/tree', base_seed=90210,
                                 server=server)
        settings = session.settings(length=8, top_n=3, temperature=0.9)

        print('\ngenerate two continuations from one prompt')
        prompt = session.author(None, b'The lighthouse keeper wrote:')
        spans = session.generate(session.tip(prompt.id), settings, n=2)
        check('both completed', all(s.complete for s in spans))
        check('distinct seeds', spans[0].seed != spans[1].seed)
        check('one batch', spans[0].batch == spans[1].batch)
        check('the tree validates against its store',
              not validate(session.tree, session.store),
              str(validate(session.tree, session.store)))

        for span in spans:
            tokens = session.store.tokens(span.id)
            print(f'  {span.id}: {span.text!r}')
            check(f'{span.id}: tokens spell the span exactly',
                  spelled(tokens) == span.text)
            check(f'{span.id}: every token carries an id and bytes',
                  all(t.token_id is not None and t.bytes for t in tokens))
            check(f'{span.id}: it hangs off the prompt it was given',
                  span.parent == session.tip(prompt.id))
            check(f'{span.id}: terminated as length',
                  session.store.terminator(span.id) in (LENGTH, EOS),
                  session.store.terminator(span.id))
            cfs = session.store.counterfactuals(span.id)
            check(f'{span.id}: counterfactuals at every position',
                  {c.idx for c in cfs} == set(range(len(tokens))),
                  f'{len({c.idx for c in cfs})} of {len(tokens)}')
            check(f'{span.id}: counterfactuals are ranked by logprob',
                  all(_descending([c.logprob for c in cfs if c.idx == i])
                      for i in range(len(tokens))))

        print('\nthe token overlay lines up with the byte anchor')
        span = spans[0]
        offsets = token_offsets(session.store, span.id)
        check('offsets end at the span length', offsets[-1] == len(span.text))
        check('every token boundary is a byte offset in the span',
              all(0 <= o <= len(span.text) for o in offsets))

        print('\nbranch to a counterfactual the model did not take')
        cfs = session.store.counterfactuals(span.id, 1)
        taken = session.store.tokens(span.id)[1].token_id
        alternative = next((c for c in cfs if c.token_id != taken), None)
        branch_tip = None
        if alternative is None:
            print('  (no distinct alternative at index 1; skipped)')
        else:
            sampled_path = session.text(session.tip(span.id))
            branched = session.branch(span.id, 1, alternative.rank)
            branch_tip = session.tip(branched.id)
            check('the branch carries the token id it chose',
                  branched.origin['token_id'] == alternative.token_id)
            check('it anchors at the byte the token starts on',
                  branched.parent == Position(span.id, offsets[1]))
            check('the sampled path is untouched beside it',
                  session.text(session.tip(span.id)) == sampled_path)
            check('the two agree up to the divergence and not past it',
                  _shared(sampled_path, session.text(branch_tip))
                  == session.tree.absolute(branched.parent))
            check('and still validates',
                  not validate(session.tree, session.store),
                  str(validate(session.tree, session.store)))
            print(f'  took     {sampled_path!r}')
            print(f'  not took {session.text(branch_tip)!r}')

        print('\ncontinue from the branch, then reload from disk')
        session.generate(branch_tip or session.tip(spans[0].id), settings, n=1)
        before = {s: session.tree.path_bytes(session.tree.tip(s))
                  for s in session.leaves()}
        session.close()

        back = Session.open(f'{workdir}/tree', server=server)
        check('reloads and validates', not validate(back.tree, back.store),
              str(validate(back.tree, back.store)))
        check('nothing is left in flight',
              all(s.complete for s in back.tree.spans.values()))
        check('every path survives byte for byte',
              {s: back.tree.path_bytes(back.tree.tip(s))
               for s in back.leaves()} == before)
        for leaf in back.leaves():
            print(f'  {leaf}: '
                  f'{back.tree.path_bytes(back.tree.tip(leaf)).decode()!r}')
        back.close()

        print(f'\n{PASS} passed, {FAIL} failed')
        return 1 if FAIL else 0
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


def _descending(values):
    return all(a >= b for a, b in zip(values, values[1:]))


def _shared(a: bytes, b: bytes) -> int:
    n = 0
    while n < min(len(a), len(b)) and a[n] == b[n]:
        n += 1
    return n


if __name__ == '__main__':
    sys.exit(main())
