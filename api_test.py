#!/usr/bin/env python
"""Headless check that the API says what it means. No model, no browser.

The same posture as `core_test.py`, one layer up: everything here runs with
nothing serving on 8081, because a contract that can only be exercised against
a GPU is a contract nobody checks. Generation is reached through a stand-in
server that returns the records a real one returns -- which is not a mock of
llama-server so much as the smallest thing that satisfies the two methods
`core/session.py` actually calls.

Three kinds of check, and the last is the one worth having:

- the encoding, with no HTTP in the way -- positions, the b64 escape, runs
- the routes, through a real client, including the errors
- **what is absent.** `PATCH` not existing is a decision, and a decision that
  nothing tests is one a later convenience quietly reverses.

Usage: python api_test.py
"""
import base64
import os
import shutil
import sys
import tempfile

from fastapi.testclient import TestClient

import api.server as server
from api import wire
from core import Counterfactual, Position, Result, Token, create_tree
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


def raises(kind, fn, *args):
    try:
        fn(*args)
    except kind:
        return True
    except Exception:
        return False
    return False


# -- the stand-in ----------------------------------------------------------

SYMBOL = '🜁'.encode()          # three tokens under Qwen2.5, none valid alone
FRAGMENT = '中'.encode()[:2]    # what a byte-fallback alternative looks like


class Stand_in:
    """A server that answers `describe` and `complete`, and nothing else.

    Those are the only two methods `Session` reaches, which is itself worth
    asserting: if this ever needs a third, the core has grown a dependency on
    the transport that the adapter boundary was supposed to hold.

    The scripts below return whole characters from `complete`, because a real
    server cannot do otherwise -- it accumulates until its bytes decode. The
    byte fragments in this file therefore arrive the way they arrive in
    practice: as counterfactuals, and through a branch.
    """

    def __init__(self, script):
        self.script = script
        self.calls = []

    def describe(self) -> dict:
        return {'model': 'stand-in', 'n_ctx': 4096}

    def alive(self) -> bool:
        return True

    def complete(self, prompt: bytes, settings: dict, seed: int) -> Result:
        self.calls.append((prompt, seed))
        tokens, counterfactuals, reason = self.script(len(self.calls) - 1)
        return Result(tokens, counterfactuals, reason, len(prompt))


def two_siblings(call: int):
    """Two continuations that agree for one token and then part.

    Sibling agreement is the only quantitative read the instrument has, so the
    fixture has to contain some -- a script where every call returns the same
    thing would make `divergence` untestable and look like it passed.
    """
    shared = Token(0, 11, b' the', -0.20)
    if call == 0:
        return ([shared, Token(1, 12, b' sea', -0.51)],
                [Counterfactual(1, 0, 12, b' sea', -0.51),
                 Counterfactual(1, 1, 13, b' sky', -1.80),
                 # a byte-fallback alternative: the model ranked half a
                 # character, which is the case b64 on the wire exists for
                 Counterfactual(1, 2, 99, FRAGMENT, -6.40)],
                'length')
    return ([shared, Token(1, 14, b' wind', -0.83)],
            [Counterfactual(1, 0, 14, b' wind', -0.83)], 'eos')


# -- the encoding, with no HTTP in the way ---------------------------------

def encoding(workdir):
    print('\nthe encoding, on its own')
    path = os.path.join(workdir, 'wire')
    tree, store = create_tree(path, base_seed=1)
    from core import author
    s0 = author(tree, None, b'The sea was')
    s1 = author(tree, tree.tip(s0.id), b' calm')

    check('a bare span means its tip, which is where writing continues',
          wire.parse_position(tree, s0.id) == Position(s0.id, 11))
    check('an offset addresses inside it',
          wire.parse_position(tree, f'{s0.id}+4') == Position(s0.id, 4))
    check('and `.` is the root, which is a position and not a span',
          wire.parse_position(tree, '.') is None)
    check('a span the tree does not have is Unknown',
          raises(wire.Unknown, wire.parse_position, tree, 's99'))
    check('an offset past the bytes it has is Malformed',
          raises(wire.Malformed, wire.parse_position, tree, f'{s0.id}+99'))
    check('and so is an offset that is not a number',
          raises(wire.Malformed, wire.parse_position, tree, f'{s0.id}+x'))
    check('an empty address is refused rather than read as the cursor',
          raises(wire.Malformed, wire.parse_position, tree, ''))

    check('the object spelling round-trips through the string one',
          wire.position_from_json(tree, {'span': s1.id, 'offset': 3})
          == wire.parse_position(tree, f'{s1.id}+3'))
    check('null is the root in a body too',
          wire.position_from_json(tree, None) is None)
    check('and an object naming no span is Malformed, not a KeyError',
          raises(wire.Malformed, wire.position_from_json, tree, {'offset': 0}))

    check('bytes that decode go out as a string',
          wire.text_json(b'The sea was') == 'The sea was')
    check('bytes that do not carry the file escape onto the wire',
          wire.text_json(FRAGMENT)
          == {'b64': base64.b64encode(FRAGMENT).decode('ascii')},
          str(wire.text_json(FRAGMENT)))
    check('and bytes that have not arrived are null, which means in flight',
          wire.text_json(None) is None)

    # a run tree has no identity anywhere in it, at any depth
    node = wire.runs_json(tree, tree.live(), (None, 0, False))
    def keys(n):
        return set(n) | {k for c in n['children'] for k in keys(c)}
    check('a run carries composition and no identity',
          keys(node) == {'pieces', 'width', 'children'}, str(keys(node)))
    check('its pieces name spans and byte ranges, not run positions',
          node['pieces'] == [{'span': s0.id, 'begin': 0, 'end': 11},
                             {'span': s1.id, 'begin': 0, 'end': 5}],
          str(node['pieces']))
    store.close()


# -- the routes ------------------------------------------------------------

def routes(workdir):
    print('\nthe routes, through a client')
    path = os.path.join(workdir, 'served')
    tree, store = create_tree(path, base_seed=90210)
    store.close()

    stand_in = Stand_in(two_siblings)
    session = Session.open(path, server=stand_in)
    server.SESSION = session
    client = TestClient(server.app)

    body = client.get('/api/tree').json()
    check('an empty tree is empty rather than absent',
          body['spans'] == {} and body['selected'] is None
          and body['runs']['width'] == 0, str(body)[:120])
    check('and it says which format it is, on every read',
          body['format'] == 'token-loom/1.1', body['format'])

    made = client.post('/api/author',
                       json={'at': None, 'text': 'The lighthouse keeper wrote:'})
    body = made.json()
    root = body['created'][0]
    check('authoring at the root needs no span to hang it off',
          made.status_code == 200 and body['spans'][root]['parent'] is None)
    check('a given span carries no parameters and no seed',
          body['spans'][root]['kind'] == 'given'
          and body['spans'][root]['params'] is None
          and body['spans'][root]['seed'] is None)
    check('the mutation answers with the whole tree, not just what it made',
          set(body) >= {'spans', 'params', 'runs', 'live', 'created'})

    print('\ngeneration, against the stand-in')
    settings = client.get('/api/settings').json()
    check('the settings a client starts from carry the server, not the user',
          settings['model'] == 'stand-in' and settings['n_ctx'] == 4096,
          str(settings))
    settings.update(length=2, top_n=3, temperature=0.9)

    at = {'span': root, 'offset': len('The lighthouse keeper wrote:')}
    body = client.post('/api/generate',
                       json={'at': at, 'n': 2, 'settings': settings}).json()
    made = body['created']
    check('n continuations from one position are one batch',
          len(made) == 2
          and {body['spans'][s]['batch'] for s in made} == {'b0'},
          str([body['spans'][s] for s in made]))
    check('with seeds derived from the base, so siblings differ',
          [body['spans'][s]['seed'] for s in made] == [90210, 90211],
          str([body['spans'][s]['seed'] for s in made]))
    check('both are complete and both say why they stopped',
          [body['spans'][s]['terminator'] for s in made] == ['length', 'eos'],
          str([body['spans'][s]['terminator'] for s in made]))
    check('the slice they were given is recorded as an address',
          body['spans'][made[0]]['slice_start'] == {'span': root, 'offset': 0},
          str(body['spans'][made[0]]['slice_start']))
    check('and the prompt the stand-in saw is the path, not the request',
          stand_in.calls[0][0] == b'The lighthouse keeper wrote:',
          repr(stand_in.calls[0][0]))

    tokens = client.get(f'/api/span/{made[0]}/tokens').json()
    check('the overlay converts back to byte offsets, which are the anchor',
          [(t['idx'], t['begin'], t['end']) for t in tokens]
          == [(0, 0, 4), (1, 4, 8)], str(tokens))
    check('a token carries its id and its logprob',
          tokens[1]['token_id'] == 12 and tokens[1]['logprob'] == -0.51)
    check('and its alternatives, ranked as the model ranked them',
          [c['rank'] for c in tokens[1]['counterfactuals']] == [0, 1, 2])
    check('the first token has no alternatives and says so with an empty list',
          tokens[0]['counterfactuals'] == [])

    print('\nthe reads a client cannot recompute')
    diverge = client.get('/api/batches/b0/divergence').json()
    check('siblings that agree for one token lock at depth 1 and not at 3',
          diverge['divergence']['lock']['1'] == 1.0
          and diverge['divergence']['lock']['3'] == 0.0,
          str(diverge['divergence']))
    check('and the common prefix is the depth before they part',
          diverge['divergence']['common'] == 1, str(diverge['divergence']))
    check('a batch that does not exist is 404, not an empty profile',
          client.get('/api/batches/b9/divergence').status_code == 404)

    batches = client.get('/api/batches').json()
    check('a batch names its origin and its interned parameters',
          len(batches) == 1 and batches[0]['params'] == 'p0'
          and batches[0]['from'] == at, str(batches))

    body = client.get('/api/slice', params={'at': f'{made[0]}', 'length': 12}).json()
    check('a slice reports the start it would use, nudged to a boundary',
          body['bytes'] == 12 and body['start']['span'] == root,
          str(body))
    whole = client.get('/api/slice', params={'at': f'{made[0]}'}).json()
    check('and omitting the length asks for the whole path, not for nothing',
          whole['start'] == {'span': root, 'offset': 0}
          and whole['bytes'] == len(client.get(
              '/api/path', params={'to': f'{made[0]}'}).json()['text']),
          str(whole))
    check('which is what the settings a client starts from ask for',
          'prompt_length' in settings and settings['prompt_length'] is None,
          str(settings))

    print('\nbranching to a counterfactual')
    body = client.post('/api/branch',
                       json={'span': made[0], 'index': 1, 'rank': 2}).json()
    branched = body['created'][0]
    check('it anchors at the byte its token starts on, dividing nothing',
          body['spans'][branched]['parent'] == {'span': made[0], 'offset': 4},
          str(body['spans'][branched]))
    check('a branch onto a byte-fallback token has no string form on the wire',
          isinstance(body['spans'][branched]['text'], dict)
          and 'b64' in body['spans'][branched]['text'],
          str(body['spans'][branched]['text']))
    check('and the path through it is bytes, so it says so the same way',
          isinstance(client.get('/api/path',
                                params={'to': branched}).json()['text'], dict))
    check('its origin names the counterfactual it came from',
          body['spans'][branched]['origin']
          == {'span': made[0], 'index': 1, 'token_id': 99},
          str(body['spans'][branched]['origin']))

    print('\ndeletion, and what it leaves behind')
    body = client.post('/api/delete', json={'at': {'span': made[1], 'offset': 0}}).json()
    check('a deleted span stops being reachable',
          made[1] not in body['live'] and made[1] in body['spans'])
    check('while its sibling is untouched',
          made[0] in body['live'])
    check('and the branch under the survivor survives with it',
          branched in body['live'], str(body['live']))
    body = client.post('/api/restore', json={'at': {'span': made[1], 'offset': 0}}).json()
    check('restore is a list operation, which is what soft delete buys',
          made[1] in body['live'])

    print('\nthe cursor, which is written down')
    body = client.put('/api/cursor', json={'at': f'{made[0]}+4'}).json()
    check('a cursor set in one spelling reads back in the other',
          body['selected'] == {'span': made[0], 'offset': 4}, str(body['selected']))
    check('and it survives a reopen, because it is in the tree file',
          Session.open(path).tree.selected == Position(made[0], 4))

    return session, client, root, made, branched


# -- the errors, and the absences ------------------------------------------

def refusals(session, client, root, made):
    print('\nwhat the API refuses')
    check('an unknown span is 404',
          client.get('/api/span/s99/tokens').status_code == 404)
    check('an offset past the bytes a span has is 400',
          client.get('/api/path', params={'to': f'{root}+999'}).status_code == 400)
    check('an unparseable address is 400, not a traceback',
          client.get('/api/path', params={'to': f'{root}+x'}).status_code == 400)
    check('deleting the root is refused rather than cascading over everything',
          client.post('/api/delete', json={'at': None}).status_code == 400)
    check('branching to a rank that was never recorded is 400',
          client.post('/api/branch',
                      json={'span': made[0], 'index': 1, 'rank': 9}
                      ).status_code == 400)
    check('and branching inside a span that has no such token is 400',
          client.post('/api/branch',
                      json={'span': made[0], 'index': 9, 'rank': 0}
                      ).status_code == 400)
    check('a refusal says what was wrong, in a field a client can read',
          'detail' in client.get('/api/span/s99/tokens').json())

    print('\nwhat the API does not have')
    check('there is no edit endpoint, per decision 2',
          client.patch(f'/api/node/{root}', json={'text': 'no'}).status_code
          in (404, 405))
    check('nor a node-shaped read of any kind',
          client.get(f'/api/node/{root}').status_code == 404)
    check('nor sessions to open, activate or close',
          client.post('/api/sessions/open', json={}).status_code == 404)
    check('nor a save, because saving is not a thing a client does',
          client.post('/api/save', json={}).status_code == 404)
    paths = {r.path for r in server.app.routes if hasattr(r, 'path')}
    check('and no route mentions a node at all',
          not any('node' in p for p in paths), str(sorted(paths)))


def no_model(workdir):
    """Every read works with nothing serving; only generation does not.

    The property is the format's rather than the API's -- bytes exist before
    any tokenizer does, so a prompt can be composed with no model running -- and
    this is where it either survives contact with a transport or quietly stops
    being true.
    """
    print('\nwith no model attached')
    path = os.path.join(workdir, 'modelless')
    tree, store = create_tree(path, base_seed=3)
    store.close()
    session = Session.open(path, server=None)
    server.SESSION = session
    client = TestClient(server.app)

    check('a tree with no server behind it still reads',
          client.get('/api/tree').status_code == 200)
    check('and still takes text, which is what composing a prompt is',
          client.post('/api/author',
                      json={'at': None, 'text': 'Compose me'}).status_code == 200)
    check('asking what the model is answers 503 rather than guessing',
          client.get('/api/settings').status_code == 503)
    check('and generating answers 503 rather than half-writing a span',
          client.post('/api/generate',
                      json={'at': None, 'n': 1, 'settings': {}}).status_code == 503)
    check('nothing was recorded by the attempt',
          len(client.get('/api/tree').json()['spans']) == 1)
    session.close()


def main():
    workdir = tempfile.mkdtemp(prefix='api-test-')
    try:
        encoding(workdir)
        session, client, root, made, _ = routes(workdir)
        refusals(session, client, root, made)
        session.close()
        no_model(workdir)
    finally:
        shutil.rmtree(workdir, ignore_errors=True)

    print(f'\n{PASS} passed, {FAIL} failed')
    return 1 if FAIL else 0


if __name__ == '__main__':
    sys.exit(main())
