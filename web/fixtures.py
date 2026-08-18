"""Tree responses for `web_test.mjs`, built by the code that serves them.

    uv run python web/fixtures.py

Prints `{name: <the body of GET /api/tree>}` as JSON on stdout. The node test
runs this and asserts against what comes out.

**Generated rather than written down, and that is the point.** A fixture typed
by hand into the test encodes what its author believed the server sends, so a
misunderstanding of the wire format would be asserted rather than caught --
which is the one failure a client-side test of derived values exists to
prevent. These go through `wire.tree_json`, so the shapes are the real ones and
a change to them breaks the test rather than passing it.

No model server: `begin_generation` and `complete` are called directly with
token rows made up here, exactly as `core_test.py` does. What matters to the
front end is the structure and the bytes, and neither needs a GPU.

The cases are chosen for what is hard rather than for what is common:

- `plain` -- a fork of two, one taken, and a live fork at the tip.
- `flight` -- a batch where one continuation has landed, one is still in
  flight, and one completed with no bytes. All three have to be cards.
- `counterfactual` -- the path routed onto a branch taken mid-span, so the
  fork's two children both name spans the path passes through. The case
  `stepsOnto` exists for.
- `wide` -- multi-byte characters at a fork boundary, where a byte offset and
  a string index part company.
- `fragment` -- a branch onto a byte-fallback token, which has no string form.
  The reading surface refuses this tree; the fixture is what it refuses.
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api import wire                                             # noqa: E402
from core import (ABORTED, BulkStore, Counterfactual, EOS, LENGTH,  # noqa: E402
                  Position, Token, author, begin_generation,
                  branch_counterfactual, complete, create_tree)

SETTINGS = {'temperature': 0.9, 'top_p': 1, 'top_n': 3, 'length': 4,
            'stop': [], 'model': 'qwen2.5-7b-base', 'tokenizer': 'qwen2.5',
            'n_ctx': 16384, 'prompt_length': None}


def toks(parts):
    return [Token(i, tid, raw, -1.0 - i) for i, (tid, raw) in enumerate(parts)]


def plain(tree, store):
    """Seed, a batch of two, one confirmed, another batch at the new tip."""
    seed = author(tree, None, b'The lighthouse keeper wrote:')
    first, second = begin_generation(tree, tree.tip(seed.id), SETTINGS, n=2)
    complete(tree, store, first.id, toks([(11, b' the'), (12, b' sea')]), LENGTH)
    complete(tree, store, second.id, toks([(11, b' the'), (21, b' gulls')]), LENGTH)

    onward = begin_generation(tree, tree.tip(first.id), SETTINGS, n=2)
    complete(tree, store, onward[0].id, toks([(31, b' was'), (32, b' calm')]), LENGTH)
    complete(tree, store, onward[1].id, toks([(31, b' was'), (41, b' rough')]), LENGTH)
    tree.selected = tree.tip(first.id)


def flight(tree, store):
    """One landed, one still generating, one that produced nothing.

    The second and third are the two zero-width states, and they are different
    answers: a placeholder that will fill, and a generation that will not.
    """
    seed = author(tree, None, b'A list of three things:')
    landed, running, nothing = begin_generation(tree, tree.tip(seed.id),
                                               SETTINGS, n=3)
    complete(tree, store, landed.id, toks([(11, b' salt'), (12, b' water')]), LENGTH)
    complete(tree, store, nothing.id, [], ABORTED)
    tree.selected = tree.tip(seed.id)


def counterfactual(tree, store):
    """A branch taken mid-span, with the path routed onto it.

    Both children of the resulting fork name spans the path passes through --
    the branch itself, and the span it was taken from, which is its parent. A
    client deciding by span identity picks the wrong one half the time.
    """
    seed = author(tree, None, b'The sea was')
    span = begin_generation(tree, tree.tip(seed.id), SETTINGS, n=1)[0]
    complete(tree, store, span.id,
             toks([(11, b' calm'), (12, b' and'), (13, b' clear')]), EOS,
             [Counterfactual(2, 0, 21, b' bright', -0.92),
              Counterfactual(2, 1, 22, b' cold', -2.31)])
    taken = branch_counterfactual(tree, store, span.id, 2, 0)
    tree.selected = tree.tip(taken.id)


def wide(tree, store):
    """Characters wider than a byte, on both sides of a fork.

    Every offset on the wire is a byte offset and every string index here is a
    UTF-16 code unit. These differ by 2 per emoji and by 2 per accented
    character, so a client slicing by the wrong one is visibly wrong.
    """
    seed = author(tree, None, 'Le phare — gardien du détroit 🜁'.encode())
    first, second = begin_generation(tree, tree.tip(seed.id), SETTINGS, n=2)
    complete(tree, store, first.id,
             toks([(11, ' était'.encode()), (12, ' calme'.encode())]), LENGTH)
    complete(tree, store, second.id,
             toks([(11, ' était'.encode()), (21, ' 🜃 froid'.encode())]), LENGTH)
    tree.selected = tree.tip(first.id)


def fragment(tree, store):
    """A branch onto a byte-fallback token: bytes with no string form.

    Qwen2.5 spells an astral-plane character in several tokens, none of them
    valid UTF-8 alone, so a counterfactual at one of them makes a span that
    cannot be a string. `loom.py` keeps this; the reading surface refuses it.
    """
    seed = author(tree, None, b'The sigil was ')
    span = begin_generation(tree, tree.tip(seed.id), SETTINGS, n=1)[0]
    glyph = '🜁'.encode()
    # three tokens over four bytes, none of them valid UTF-8 alone, which is
    # what Qwen2.5 measurably does with this glyph. The span as a whole spells
    # the character; only the branch below is a fragment, and a sampled span
    # that ended mid-character would be a shape generation cannot produce.
    complete(tree, store, span.id,
             toks([(11, glyph[0:1]), (12, glyph[1:3]), (13, glyph[3:4])]), EOS,
             [Counterfactual(1, 0, 91, b'\x9f\x9c', -1.20)])
    taken = branch_counterfactual(tree, store, span.id, 1, 0)
    tree.selected = tree.tip(taken.id)


def expected(tree):
    """What the core says, for the client's derivations to be checked against.

    `path` is the whole active path as the core assembles it, which is the one
    number that matters: a client walking run pieces has to arrive at the same
    string, and arithmetic in a test is code that nothing checks. It is `null`
    where the path has no string form, which is itself the thing to assert.
    """
    raw = tree.path_bytes(tree.selected)
    try:
        text = raw.decode()
    except UnicodeDecodeError:
        text = None
    return {'path': text, 'bytes': len(raw),
            'flight': sorted(s.id for s in tree.spans.values()
                             if not s.complete),
            'selected': wire.position_json(tree.selected)}


CASES = {'plain': plain, 'flight': flight, 'counterfactual': counterfactual,
         'wide': wide, 'fragment': fragment}


def main() -> int:
    workdir = tempfile.mkdtemp(prefix='loom-fixtures-')
    try:
        out = {}
        for name, build in CASES.items():
            tree, store = create_tree(os.path.join(workdir, name), base_seed=90210)
            tree.tree_id = f'fixture-{name}'
            build(tree, store)
            out[name] = {'tree': wire.tree_json(tree, store),
                         'expect': expected(tree)}
            store.close()
        json.dump(out, sys.stdout, indent=1, sort_keys=True)
        sys.stdout.write('\n')
    finally:
        shutil.rmtree(workdir, ignore_errors=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
