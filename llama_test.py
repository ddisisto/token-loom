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

from core import (CONTEXT, EOS, LENGTH, STOP, Position, Server, Truncated,
                  spelled, validate)
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

        stop_strings(f'{workdir}/stop', server)
        deep_chain(f'{workdir}/deep', server)
        context_limit(f'{workdir}/ctx', server)

        print(f'\n{PASS} passed, {FAIL} failed')
        return 1 if FAIL else 0
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


def stop_strings(path, server):
    """`STOP` as a distinct terminator, which nothing else here reaches.

    Measured while writing this, and the reason the assertion below is about
    the *invariant* rather than about the text: **llama-server drops as many
    trailing entries from `completion_probabilities` as the stop string has
    tokens**, whatever actually matched. When the stop string is a token
    sequence at a token boundary -- the ordinary case, and both cases here --
    those are exactly the tokens that spelled it, so `content` and the overlay
    agree and the span ends cleanly before the match.

    When it is not, they disagree and the overlay is the shorter of the two.
    Stopping a Qwen2.5 continuation on `'ecember'` returns `content` of
    `' in D'` and *no entries at all*, because `'ecember'` is two tokens and
    only two were produced. The span is then well-formed and empty: the bytes
    the model emitted before the match have no token records, so there is
    nowhere in the format to put them. That is a real loss of model output, it
    is silent, and it is not something the core can currently detect from a
    completed span -- only by comparing against `content`, which nothing does.
    Recorded here rather than asserted, because what to do about it is a
    decision and not a bug fix.
    """
    print('\nstop strings terminate as stop, and the span ends before the match')
    session = Session.create(path, base_seed=4242, server=server)

    # a prompt per case, each chosen so the stop string is near-certain within
    # the length: prose reaches a full stop, a numbered list reaches a newline
    cases = [('.', 'a period',
              b'The lighthouse keeper wrote: It was a cold'),
             ('\n', 'a newline',
              b'Three rules for keeping a lighthouse:\n1.')]

    for stop, label, text in cases:
        prompt = session.author(None, text)
        settings = session.settings(length=64, top_n=3, temperature=0.7,
                                    stop=[stop])
        span = session.generate(session.tip(prompt.id), settings, n=1)[0]
        reason = session.store.terminator(span.id)
        check(f'{label}: terminated as stop rather than length',
              reason == STOP, f'{reason} on {span.text!r}')
        if reason != STOP:
            continue
        check(f'{label}: the stop string is not in the span',
              stop.encode() not in span.text, repr(span.text))
        check(f'{label}: the tokens still spell the span exactly',
              spelled(session.store.tokens(span.id)) == span.text)
        print(f'  {span.id}: {span.text!r}')

    check('the tree validates with stopped spans in it',
          not validate(session.tree, session.store),
          str(validate(session.tree, session.store)))
    session.close()


def deep_chain(path, server, depth=40):
    """Spans as numerous as tokens -- the sizing assumption, actually walked.

    `ancestry` walks span by span, so a chain of single-token generations is
    the shape every derived quantity is worst-case on: `absolute`, `path_bytes`
    and the slice all traverse the whole chain. This is a correctness check
    rather than a timing one; that it also finishes quickly is incidental.
    """
    print(f'\na chain of {depth} single-token generations')
    session = Session.create(path, base_seed=1234, server=server)
    settings = session.settings(length=1, top_n=3, temperature=0.9)

    prompt = session.author(None, b'Once upon a time')
    chain, pos = [], session.tip(prompt.id)
    for _ in range(depth):
        span = session.generate(pos, settings, n=1)[0]
        chain.append(span)
        pos = session.tip(span.id)

    check('every step is one span', len(chain) == depth)
    check('each hangs off the tip of the one before',
          all(later.parent == Position(earlier.id, earlier.length)
              for earlier, later in zip(chain, chain[1:])))
    check('each carries exactly one token',
          all(len(session.store.tokens(s.id)) == 1 for s in chain))

    # computed, not eyeballed: the path is the prompt plus every span's bytes
    expected = prompt.text + b''.join(s.text for s in chain)
    check('the path is the prompt and every span in order',
          session.text(pos) == expected,
          f'{len(session.text(pos))} bytes against {len(expected)}')
    check('the derived absolute offset agrees with the byte count',
          session.tree.absolute(pos) == len(expected))
    check('ancestry is one step per span, plus the prompt',
          len(session.tree.ancestry(pos)) == depth + 1)
    check('the slice from the tip reaches back to the prompt',
          session.slice(pos, 10_000)[2] == expected)
    check('it validates', not validate(session.tree, session.store),
          str(validate(session.tree, session.store)))
    print(f'  {len(expected)} bytes over {depth + 1} spans: '
          f'{session.text(pos)[:70]!r}')
    session.close()


def context_limit(path, server, port=8082):
    """`CONTEXT`, the one terminator that is derived rather than reported.

    `stop_type: limit` covers both walls, so the core reads "nothing stopped it
    and it produced fewer tokens than were asked for" as context exhaustion.
    Being derived makes it the easiest to get silently wrong, and nothing else
    reaches it: at 16k context an ordinary prompt never comes close.

    Writing this found that it had never been reached at all. The response's
    `truncated` flag was being treated as "the server cut the prompt" and
    raised on, when it actually means generation hit the context wall -- so the
    only path to `CONTEXT` raised instead of recording. Both halves are covered
    below: the wall, and the genuinely over-long prompt that the server refuses
    outright rather than truncating.

    Forcing it needs a server with a small `--ctx-size`, which is a different
    server than the rest of this file uses. `scripts/llama-server.sh` takes
    `CTX` and `PORT` from the environment, so:

        CTX=512 PORT=8082 scripts/llama-server.sh --n-gpu-layers 0

    Skipped, not failed, when nothing is listening there -- it is the one check
    here that cannot run against the ordinary setup.
    """
    small = Server(f'http://127.0.0.1:{port}')
    print(f'\nthe context limit, against a small-context server on {port}')
    if not small.alive():
        print(f'  (nothing on {port}; skipped -- see the docstring)')
        return

    n_ctx = small.describe()['n_ctx']
    session = Session.create(path, base_seed=777, server=small)

    # Fill three quarters of the context, then ask for more tokens than the
    # remaining quarter can hold. Sized in tokens, not bytes: the phrase is
    # eight short words and each is comfortably one token for this vocabulary.
    # Three quarters rather than all of it because a prompt that does not fit
    # is a different outcome entirely -- the server truncates it and the core
    # raises `Truncated` rather than generating at all.
    filler = ('the sea and the sky and the wind ' * (n_ctx * 3 // 4 // 8)).encode()
    prompt = session.author(None, filler)
    asked = n_ctx  # more than can possibly fit alongside the prompt
    settings = session.settings(length=asked, top_n=3, temperature=0.9,
                                prompt_length=len(filler))
    span = session.generate(session.tip(prompt.id), settings, n=1)[0]

    produced = len(session.store.tokens(span.id))
    reason = session.store.terminator(span.id)
    check('it stopped short of what was asked for', produced < asked,
          f'{produced} of {asked}')
    check('and is recorded as context rather than length', reason == CONTEXT,
          f'{reason} after {produced} of {asked} tokens')
    check('it validates', not validate(session.tree, session.store),
          str(validate(session.tree, session.store)))
    print(f'  n_ctx {n_ctx}: asked {asked}, produced {produced}, {reason}')

    # and the other half: asking for a length that does fit must still be
    # LENGTH, or the derivation is just reporting context exhaustion always
    room = n_ctx - len(session.store.tokens(span.id)) - 1
    settings = session.settings(length=max(1, room // 4), top_n=3,
                                temperature=0.9, prompt_length=len(filler))
    short = session.generate(session.tip(prompt.id), settings, n=1)[0]
    short_reason = session.store.terminator(short.id)
    check('a length that fits is still recorded as length',
          short_reason in (LENGTH, EOS, STOP),
          f'{short_reason} after {len(session.store.tokens(short.id))} of '
          f'{settings["length"]} tokens')

    # a prompt longer than the context is refused outright, not truncated --
    # so it is a typed error and no span records bytes the model never saw
    over = ('the sea and the sky and the wind ' * (n_ctx // 4)).encode()
    big = session.author(None, over)
    refused = False
    try:
        session.generate(session.tip(big.id),
                         session.settings(length=8, top_n=3,
                                          prompt_length=len(over)), n=1)
    except Truncated as e:
        refused = True
        print(f'  refused, as it should be: {e}')
    check('a prompt longer than the context is refused, not silently cut',
          refused)
    session.close()


def _descending(values):
    return all(a >= b for a, b in zip(values, values[1:]))


def _shared(a: bytes, b: bytes) -> int:
    n = 0
    while n < min(len(a), len(b)) and a[n] == b[n]:
        n += 1
    return n


if __name__ == '__main__':
    sys.exit(main())
