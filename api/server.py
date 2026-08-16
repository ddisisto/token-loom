"""The routes. One tree, one process, one writer.

    uv run --group web python -m api.server data/demo

Read `api/__init__.py` first for the three shapes this rests on. What is
decided *here*, and each of these is a decision rather than an implementation
detail:

**Generation blocks, and that is not a defect yet.** `Session.generate` is an
ordinary blocking call -- the worker thread went with tkinter -- so a batch of
eight at length 32 holds its request open for tens of seconds. Streaming is
deferred entire (`BEYOND-MVP.md`) and the format support it needs is already
in, so the shape that replaces this later is additive. Handlers are `def`
rather than `async def`, which is what puts them on FastAPI's threadpool
instead of stalling the event loop for every other request.

**One writer lock, and reads do not take it.** Every mutation serialises,
including the model call inside `generate`. Reads run underneath, which means a
read during generation sees in-flight spans -- provenance written, bytes not
yet arrived. That is the state `FORMAT.md` decision 8 exists for and the honest
thing to show; it is also exactly what the placeholder forks in a future
streaming UI will render.

**Every mutation answers with the whole tree.** The alternative -- return the
created span and let the client patch its copy -- puts a second implementation
of the tree's structure in the client and a desync bug behind every operation.
The tree file is small by construction, the bulk data is deliberately
elsewhere, and the client already parses this exact shape from `GET /api/tree`.
When a tree is large enough for that to hurt, the fix is a delta endpoint, not
a client-side model.

**No save, no save-as, no sessions.** Save is not a user action any more:
`core/session.py` writes the tree after every mutation and once per
continuation inside a batch, which is the save ordering that makes a crash
mid-generation legible. `ROADMAP.md` says these "carry over in function" and
they do -- the function of save is served by that ordering, and the function of
save-as is copying a directory, which is a shell command rather than an
endpoint. Creating a tree stays `loom.py new`.

**No `PATCH`.** Per `FORMAT.md` decision 2, and it does not reappear as a
convenience: delete cascades, authoring creates, and carrying old text into an
authoring box is the client's business.

Nothing here guards against a *second process* writing the same directory --
see the two-writer thread in `CLAUDE-HANDOVER.md`. One writer is what this
process promises about itself, not what it enforces on the filesystem.
"""
from __future__ import annotations

import argparse
import os
import threading

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from api import wire
from core import Incomplete, Invalid, Server, Truncated
from core.session import Session

app = FastAPI(title='token loom')

# The one open tree, and the lock every mutation takes. Module-level because
# the process serves exactly one tree -- there is nothing to key them by, and a
# registry would be the session model creeping back in through the door marked
# "just in case".
SESSION: Session | None = None
WRITING = threading.Lock()


def held() -> Session:
    """The open session, or a 503 if the process has not got one.

    Reachable only before startup finishes or after a failed open, and worth an
    answer rather than an `AttributeError` in the log.
    """
    if SESSION is None:
        raise HTTPException(503, 'no tree is open')
    return SESSION


def generating() -> Session:
    """The same, and a model server attached.

    Separate because the failures are different: a process with no tree cannot
    answer anything, and a process with no model server answers every read.
    Composing a prompt with no model running is a property the format has --
    bytes exist before any tokenizer does -- so it is not an error until
    something asks for generation.
    """
    session = held()
    if session.server is None:
        raise HTTPException(503, 'no model server attached')
    return session


def state(session: Session, **extra) -> dict:
    """The whole tree, plus whatever the mutation wants to name."""
    return dict(wire.tree_json(session.tree, session.store), **extra)


# -- request bodies --------------------------------------------------------

class At(BaseModel):
    """A position in a body: `{"span": "s3", "offset": 9}`, or null for root.

    `at` is `None` by default *and* `None` is the root, which reads like a trap
    and is not one: the root is where an initial prompt goes, so a body with no
    address means the only position a tree is guaranteed to have.
    """
    at: dict | str | None = None


class Author(At):
    """`{"at": ..., "text": "..."}` -- the text is a string, and encodes UTF-8.

    Bytes that are not valid UTF-8 cannot be authored over JSON, and that is
    accepted: the case exists in the core (a paste, a file) but a client that
    needs it can send base64 when something actually wants to.
    """
    text: str


class Generate(At):
    """`{"at": ..., "n": 1, "settings": {...}}` -- full parameters per call.

    Full, not partial, and not merged with server-side state: this is what
    makes the request the whole record of what produced a span, and what keeps
    the headless path and the UI the same client. `GET /api/settings` exists so
    a client can find out what the server would fill in, not so the server can
    fill it in later.
    """
    n: int = 1
    settings: dict


class Branch(BaseModel):
    """`{"span": "s3", "index": 2, "rank": 1}` -- a counterfactual by rank.

    By rank rather than by token id because rank is what the store is keyed on
    and what the client saw; two entries with the same id at one index cannot
    exist.
    """
    span: str
    index: int
    rank: int


# -- reads -----------------------------------------------------------------

@app.get('/api/tree')
def read_tree() -> dict:
    """Structure, spans, params, deletions, live extents and derived runs."""
    session = held()
    return wire.tree_json(session.tree, session.store)


@app.get('/api/path')
def read_path(to: str) -> dict:
    """The bytes from the root to a position, as text: `?to=s3+9`.

    Answers with the same escape as a span: a path ending inside a character
    has no string form, which is reachable by pointing at an offset mid-token.
    """
    session = held()
    pos = wire.parse_position(session.tree, to)
    raw = session.text(pos)
    return {'at': wire.position_json(pos), 'text': wire.text_json(raw),
            'bytes': len(raw)}


@app.get('/api/span/{span_id}/tokens')
def read_tokens(span_id: str) -> list[dict]:
    """The token overlay for one span, with counterfactuals."""
    session = held()
    if span_id not in session.tree.spans:
        raise wire.Unknown(f'no span {span_id}')
    return wire.tokens_json(session.store, span_id)


@app.get('/api/batches')
def read_batches() -> list[dict]:
    """Every generation call, with its origin and its interned parameters."""
    session = held()
    return wire.batches_json(session.tree, session.store)


@app.get('/api/batches/{batch}/divergence')
def read_divergence(batch: str, depths: str = '1,3,10') -> dict:
    """How far the siblings of one call agree, as a profile over token depth."""
    session = held()
    spans = wire.batch_spans(session.tree, batch)
    try:
        wanted = tuple(int(d) for d in depths.split(',') if d)
    except ValueError:
        raise wire.Malformed(f'depths must be numbers: {depths!r}') from None
    return {'batch': batch, 'spans': spans,
            'divergence': wire.divergence_json(session.store, spans,
                                               wanted or (1, 3, 10))}


@app.get('/api/params')
def read_params() -> dict:
    """The intern table, whole. It is small and every span points into it."""
    return held().tree.params


@app.get('/api/slice')
def read_slice(at: str, length: int) -> dict:
    """What a generation from `at` would send: `{start, end, text, bytes}`.

    The read Phase 3's viewport is built on, and it is worth having before the
    viewport exists: it is the only way to see what was actually in context,
    and the start it reports is the nudged one -- the slice that would be used,
    not the one that was asked for.
    """
    session = held()
    pos = wire.parse_position(session.tree, at)
    start, end, raw = session.slice(pos, length)
    return {'start': wire.position_json(start), 'end': wire.position_json(end),
            'text': wire.text_json(raw), 'bytes': len(raw)}


@app.get('/api/settings')
def read_settings() -> dict:
    """The parameter set a client should start from, with the server's own
    facts filled in.

    `model` and `n_ctx` are properties of what is serving rather than of what
    the user asked for, and both are recorded per span. This is the only place
    the API knows them; a generate request carries them like any other
    parameter.
    """
    return generating().settings()


# -- writes ----------------------------------------------------------------

@app.post('/api/author')
def do_author(body: Author) -> dict:
    """Append a given span at a position. Returns the tree and the new span."""
    session = held()
    with WRITING:
        pos = wire.position_from_json(session.tree, body.at)
        span = session.author(pos, body.text.encode())
        return state(session, created=[span.id])


@app.post('/api/generate')
def do_generate(body: Generate) -> dict:
    """Record the intent, save, then call the model once per continuation.

    Blocks for the whole batch, holding the writer lock. A reader watching
    `/api/tree` sees the spans appear in flight and fill in one at a time,
    because `Session.generate` saves per continuation -- an interrupted batch
    keeps what landed.
    """
    session = generating()
    with WRITING:
        pos = wire.position_from_json(session.tree, body.at)
        spans = session.generate(pos, dict(body.settings), body.n)
        return state(session, created=[s.id for s in spans])


@app.post('/api/branch')
def do_branch(body: Branch) -> dict:
    """Take a token the model ranked but did not sample, and branch there.

    No generation and nothing divided: the alternative was recorded when the
    span was. This is the operation the counterfactual storage exists to pay
    for.
    """
    session = held()
    with WRITING:
        if body.span not in session.tree.spans:
            raise wire.Unknown(f'no span {body.span}')
        span = session.branch(body.span, body.index, body.rank)
        return state(session, created=[span.id])


@app.post('/api/delete')
def do_delete(body: At) -> dict:
    """Soft, cascading, and reversible. Nothing is rewritten and no bytes go."""
    session = held()
    with WRITING:
        pos = wire.position_from_json(session.tree, body.at)
        if pos is None:
            raise wire.Malformed('the root cannot be deleted')
        session.delete(pos)
        return state(session)


@app.post('/api/restore')
def do_restore(body: At) -> dict:
    """Undo a delete -- a list operation, which is what soft delete buys."""
    session = held()
    with WRITING:
        pos = wire.position_from_json(session.tree, body.at)
        if pos is None:
            raise wire.Malformed('the root is never deleted')
        session.restore(pos)
        return state(session)


@app.put('/api/cursor')
def set_cursor(body: At) -> dict:
    """Move `selected`. Stored in the tree, so it survives a restart.

    A mutation rather than a read because it is written down. Whether the front
    end should keep its own selection instead is a client question; the field
    exists because the CLI needs somewhere to point.
    """
    session = held()
    with WRITING:
        session.tree.selected = wire.position_from_json(session.tree, body.at)
        session.save()
        return state(session)


# -- errors ----------------------------------------------------------------

def install_error_handlers(app: FastAPI) -> None:
    """The core raises `KeyError` and `ValueError`; HTTP wants 404 and 400.

    Mapped once here rather than caught per route, because every route reaches
    the same two through `ops.check`: an unknown span is 404, an offset outside
    a span is 400, and a generation the model server refused is 502 -- its
    prompt did not fit, or its response lost bytes it had already produced.
    Nothing else is translated -- an unexpected exception should be a 500 with a
    traceback in the log, not a tidy message that hides a bug.

    `KeyError` before `ValueError` is not arbitrary: `wire.Unknown` is a
    `KeyError` and `wire.Malformed` is a `ValueError`, and the plain versions
    out of `core/` mean the same two things.
    """
    def problem(status: int, exc: Exception) -> JSONResponse:
        detail = exc.args[0] if exc.args else exc.__class__.__name__
        return JSONResponse({'detail': str(detail)}, status_code=status)

    @app.exception_handler(KeyError)
    def unknown(request: Request, exc: KeyError):
        return problem(404, exc)

    @app.exception_handler(ValueError)
    def malformed(request: Request, exc: ValueError):
        return problem(400, exc)

    @app.exception_handler(Truncated)
    def truncated(request: Request, exc: Truncated):
        return problem(502, exc)

    @app.exception_handler(Incomplete)
    def incomplete(request: Request, exc: Incomplete):
        return problem(502, exc)


install_error_handlers(app)


# -- lifecycle -------------------------------------------------------------

def open_tree(path: str, base: str | None = None, model: bool = True) -> Session:
    """Open one tree, with a model server attached unless told otherwise.

    A tree that fails validation is a refusal rather than a warning: the
    validator's checks are the load-time contract, and a server that serves a
    tree it knows is broken hands the problem to every client at once.
    `loom.py` is the repair tool -- it can open with `strict=False`.

    In-flight spans left by a dead process are closed as `aborted` by
    `Session.open` before the first request is served, which is decision 8's
    load-time rule and is why "maybe still running" is not a state the API can
    report.
    """
    server = Server(base) if base else Server()
    return Session.open(path, server=server if model else None)


def serve(session: Session, host: str, port: int) -> None:
    global SESSION
    SESSION = session
    uvicorn.run(app, host=host, port=port)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog='api.server', description=__doc__.split('\n')[0])
    parser.add_argument('dir', nargs='?',
                        default=os.environ.get('LOOM_TREE', 'data/tree'))
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=8080)
    parser.add_argument('--server', default=None, help='llama-server base URL')
    parser.add_argument('--no-model', action='store_true',
                        help='serve the reads with no llama-server at all')
    args = parser.parse_args(argv)

    try:
        session = open_tree(args.dir, args.server, model=not args.no_model)
    except FileNotFoundError:
        print(f'{args.dir} holds no tree; `loom.py -d {args.dir} new` makes one')
        return 2
    except Invalid as e:
        print(f'{args.dir} does not validate, so it is not served:\n{e}')
        return 2

    print(f'{args.dir}: {len(session.tree.spans)} spans, '
          f'{len(session.tree.params)} interned')
    try:
        serve(session, args.host, args.port)
    finally:
        session.close()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
