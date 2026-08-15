#!/usr/bin/env python
"""Build `data/demo/` -- the tree `PLAYBOOKS.md` walks through.

Each playbook is one **root prompt** in a single tree, which is what the format
permits and what keeps five independent experiments in one directory. Reading
them back afterwards is the point: `loom.py show`, `batches` and `params` are
how a recorded experiment becomes legible.

The tree is committed, so this is the record of how it was made rather than
something a reader has to run. Rebuild it with:

    python demo.py --force

Needs `scripts/llama-server.sh` on 8081. Seeds derive from a fixed base, so a
rebuild against the same model and build is reproducible at the conditions
level -- not bit level, which no GPU offers and nothing here claims.
"""
from __future__ import annotations

import argparse
import shutil
import sys

from core import Server
from core.session import Session

BASE_SEED = 31415
DEFAULT_PATH = 'data/demo'


def heading(n: int, title: str, question: str) -> None:
    print(f'\n{"=" * 72}\n{n}. {title}\n   {question}\n{"=" * 72}')


def report(session: Session, spans) -> None:
    for span in spans:
        reason = session.store.terminator(span.id) or 'IN FLIGHT'
        text = (span.text or b'').decode('utf-8', errors='replace')
        print(f'  {span.id:<5} {reason:>7}  {text[:64]!r}')


# -- the playbooks ---------------------------------------------------------

def broad_sampling(session: Session):
    """Eight continuations from one position, identical conditions.

    The base move, and the one the whole structure is arranged around: the
    only thing separating these eight is the seed. What they have in common is
    the prior showing through.
    """
    heading(1, 'Broad sampling', 'where does the prior go from one position?')
    prompt = session.author(None, b'The lighthouse keeper wrote in his log:')
    settings = session.settings(temperature=0.9, length=32, top_n=3)
    spans = session.generate(session.tip(prompt.id), settings, n=8)
    report(session, spans)
    return prompt


def temperature_gate(session: Session):
    """The same position, three times, at three temperatures.

    Three batches and three interned parameter sets, which is exactly what
    makes this a comparison rather than three unrelated generations -- `params`
    lists what differed and `batches` shows what it did.
    """
    heading(2, 'Temperature', 'what does temperature gate access to?')
    prompt = session.author(None, b'There are three kinds of silence. The first is')
    for temperature in (0.2, 0.8, 1.3):
        settings = session.settings(temperature=temperature, length=28, top_n=3)
        print(f'\n  --temp {temperature}')
        report(session, session.generate(session.tip(prompt.id), settings, n=3))
    return prompt


def framing(session: Session):
    """One continuation point, two amounts of prefix visible.

    `prompt_length` is a recorded parameter, not a viewport setting, so these
    are two different experiments at the same position rather than one
    experiment viewed twice. The span records the address the slice actually
    started at, which is what `show`'s `slice from` reads back.
    """
    heading(3, 'Framing', 'what changes when the model sees less of the same prefix?')
    long_prefix = (
        b'A note on method. The instrument records what a model does when it is '
        b'iterated against itself: which continuations recur, how much of the '
        b'prior has to be visible before they do, and whether anything survives '
        b'being passed forward repeatedly. Nothing here is a claim about meaning. '
        b'It is a record of what came back, under conditions written down beside '
        b'it. The first thing worth saying about the results is')
    prompt = session.author(None, long_prefix)
    for prompt_length in (40, len(long_prefix) + 64):
        settings = session.settings(temperature=0.8, length=28, top_n=3,
                                    prompt_length=prompt_length)
        start, _, sent = session.slice(session.tip(prompt.id), prompt_length)
        print(f'\n  --prompt-length {prompt_length}: {len(sent)} bytes sent, '
              f'from {start.span}+{start.offset}')
        report(session, session.generate(session.tip(prompt.id), settings, n=2))
    return prompt


def road_not_taken(session: Session):
    """Branch to a token the model ranked but did not sample, then continue.

    No generation is needed for the branch itself -- the alternative was
    recorded when the span was, which is the payoff that makes storing
    counterfactuals worth their size. What costs a call is finding out where
    that one token leads.
    """
    heading(4, 'The road not taken', 'how far does one token propagate?')
    prompt = session.author(None, b'She opened the door and found')
    settings = session.settings(temperature=0.9, length=36, top_n=3)
    span = session.generate(session.tip(prompt.id), settings, n=1)[0]
    report(session, [span])

    # the interesting positions are where the sampled token was *not* rank 0 --
    # measured at about a third of them at this temperature
    chosen = None
    for token in session.store.tokens(span.id)[2:]:
        ranked = session.store.counterfactuals(span.id, token.idx)
        if ranked and ranked[0].token_id != token.token_id:
            was = next((c.rank for c in ranked if c.token_id == token.token_id),
                       None)
            chosen = (token, ranked[0], was)
            break
    if chosen is None:
        print('  (every token was rank 0; nothing to branch to)')
        return prompt

    token, alternative, was = chosen
    where = 'not in the top 3 at all' if was is None else f'rank {was}'
    print(f'\n  token {token.idx}: sampled {token.bytes!r}, {where}; '
          f'rank 0 was {alternative.bytes!r}')
    branched = session.branch(span.id, token.idx, 0)
    print(f'  branched as {branched.id} at {branched.parent.span}+'
          f'{branched.parent.offset}')
    report(session, session.generate(session.tip(branched.id), settings, n=1))
    return prompt


def retransmission(session: Session):
    """Generate from the tip repeatedly, seeing only a short sliding window.

    A short `prompt_length` means each step reads only the tail of what the
    step before produced, so the text is passed forward through the model again
    and again with the beginning falling out of view. Whether anything survives
    that is one of the questions the instrument exists for.
    """
    heading(5, 'Retransmission', 'does anything survive being passed forward?')
    prompt = session.author(None, b'Begin with a plain sentence about the weather.')
    settings = session.settings(temperature=0.9, length=24, top_n=3,
                                prompt_length=120)
    pos = session.tip(prompt.id)
    for step in range(8):
        span = session.generate(pos, settings, n=1)[0]
        text = (span.text or b'').decode('utf-8', errors='replace')
        print(f'  {step}: {span.id:<5} {text[:64]!r}')
        pos = session.tip(span.id)
    return prompt


PLAYBOOKS = [broad_sampling, temperature_gate, framing, road_not_taken,
             retransmission]


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('-d', '--dir', default=DEFAULT_PATH)
    parser.add_argument('--force', action='store_true',
                        help='delete and rebuild an existing demo tree')
    parser.add_argument('--server', default=None)
    args = parser.parse_args(argv)

    server = Server(args.server) if args.server else Server()
    if not server.alive():
        print(f'llama-server is not answering on {server.base}; '
              f'see scripts/llama-server.sh')
        return 2

    if args.force:
        shutil.rmtree(args.dir, ignore_errors=True)
    try:
        session = Session.create(args.dir, base_seed=BASE_SEED, server=server)
    except FileExistsError:
        print(f'{args.dir} already holds a tree; --force to rebuild')
        return 1

    print(f'{args.dir}: {server.describe()}')
    try:
        for playbook in PLAYBOOKS:
            playbook(session)
    finally:
        session.close()

    print(f'\n{len(session.tree.spans)} spans, '
          f'{len(session.tree.params)} parameter sets. '
          f'`loom.py -d {args.dir} show` reads it back.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
