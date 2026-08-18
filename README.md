# token loom

A fork of [socketteer/loom](https://github.com/socketteer/loom), diverged far enough to need
its own name. Loom wove text blocks; this weaves tokens.

The tree is a **trie over bytes**, with tokens as a per-span overlay. Branching is an
operation on a *position* — `(span, byte offset)` — rather than on a node, so continuing from
the middle of a generation costs exactly what continuing from its end costs, and nothing is
ever cut, copied or edited in place.

It is an instrument for studying what a model does when iterated against itself: which
continuations recur, how temperature gates access to them, how much of the prior has to be
visible before they appear, and whether anything survives being passed forward repeatedly.
The interactive tree is one way of looking at that, not the only one — headless and batch
use are first-class, and anything that only works by clicking is half-built.

## Where to start

| | |
| --- | --- |
| [PLAYBOOKS.md](PLAYBOOKS.md) | **start here** — five ways of using it, worked end to end against a real model |
| [RESEARCH.md](RESEARCH.md) | the questions, what is currently believed about each, and what to run next |
| [experiments/](experiments/) | the record — one file per experiment, registered before the run and answered after |
| [ROADMAP.md](ROADMAP.md) | the build path — where the interface is going, and what is out of scope |
| [FRONTEND.md](FRONTEND.md) | the front end: what it is for, and the constraints that hold it to it |
| [INTERACTION.md](INTERACTION.md) | the front end: what is on the screen and what each action does |
| [FORMAT.md](FORMAT.md) | the on-disk format, and the reasoning behind each choice |
| [BEYOND-MVP.md](BEYOND-MVP.md) | wants that reach past the MVP, and the constraints they impose now |

There are **two threads**: building the interface, and using the instrument. They share a
core, a format and a set of conventions, and diverge only in direction — `ROADMAP.md` leads
one, `RESEARCH.md` the other.

## Running it

Local inference only, for now. `scripts/llama-server.sh` serves Qwen2.5-7B **base** on port
8081 — base rather than Instruct because a chat-templated reply is a different object than a
continuation of the prior, and this is built for the second.

    scripts/llama-server.sh          # in one terminal
    python loom.py new
    python loom.py author 'The sea was'
    python loom.py gen -n 4 --length 40
    python loom.py show

`loom.py --help` documents the rest. There is a committed demo tree that needs no model at
all:

    python loom.py -d data/demo show

The same tree is also servable over HTTP, one tree per process — and the same process serves
the reading surface, on the same origin:

    scripts/api.sh data/demo        # then http://127.0.0.1:8080/ , or GET /api/tree

`python core_test.py` and `python api_test.py` run with no model, and `node web/web_test.mjs`
checks the client's derivations with no browser; `python llama_test.py` needs the server.

## State

Phase 1 landed the token core: built, tested, and driven from the command line, which is the
**reference client** rather than a scratch tool. Phase 2 landed the API — `api/` is a clean
replacement rather than a port, speaking positions rather than node ids, and the old browser
front end and the whole OpenAI-compatible path retired with it.

Phase 3 is the front end, and it is **built and not yet lived in**. A given goes in at the
root and everything after that is navigation: the surface supplies continuations at the rate
they are read, and the reader chooses among them. The model's context is the whole active
path, so what can be scrolled through is what the model was given — one object, looked at by
both. [FRONTEND.md](FRONTEND.md) has the concept and the constraints,
[INTERACTION.md](INTERACTION.md) has the screen.

`web/` is ES modules and no build step, served by the API off its own origin. It works end to
end against a live model and renders in a real browser, but nobody has yet read anything
through it for an hour, which is the stage that found the faults planning and testing did not
in every phase before this one.

The tkinter app and the browser UI are both gone; the tag `pre-token-core` preserves the last
commit where the browser UI was the whole instrument, and `git show pre-token-core:README.md`
has its documentation.
