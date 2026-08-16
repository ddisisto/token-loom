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
"""
from __future__ import annotations

from fastapi import FastAPI
from pydantic import BaseModel

from core.session import Session

app = FastAPI(title='token loom')

# The one open tree, and the lock every mutation takes. Module-level because
# the process serves exactly one tree -- there is nothing to key them by, and a
# registry would be the session model creeping back in through the door marked
# "just in case".
SESSION: Session | None = None


def held() -> Session:
    """The open session, or a 503 if the process has not got one.

    Reachable only before startup finishes or after a failed open, and worth an
    answer rather than an `AttributeError` in the log.
    """
    raise NotImplementedError


# -- request bodies --------------------------------------------------------

class At(BaseModel):
    """A position in a body: `{"span": "s3", "offset": 9}`, or null for root."""


class Author(BaseModel):
    """`{"at": ..., "text": "..."}` -- the text is a string, and encodes UTF-8.

    Bytes that are not valid UTF-8 cannot be authored over JSON, and that is
    accepted: the case exists in the core (a paste, a file) but a client that
    needs it can send base64 when something actually wants to.
    """


class Generate(BaseModel):
    """`{"at": ..., "n": 1, "settings": {...}}` -- full parameters per call.

    Full, not partial, and not merged with server-side state: this is what
    makes the request the whole record of what produced a span, and what keeps
    the headless path and the UI the same client. `GET /api/settings` exists so
    a client can find out what the server would fill in, not so the server can
    fill it in later.
    """


class Branch(BaseModel):
    """`{"span": "s3", "index": 2, "rank": 1}` -- a counterfactual by rank.

    By rank rather than by token id because rank is what the store is keyed on
    and what the client saw; two entries with the same id at one index cannot
    exist.
    """


# -- reads -----------------------------------------------------------------

@app.get('/api/tree')
def read_tree() -> dict:
    """Structure, spans, params, deletions, live extents and derived runs."""
    raise NotImplementedError


@app.get('/api/path')
def read_path(to: str) -> dict:
    """The bytes from the root to a position, as text: `?to=s3+9`.

    Answers with the same escape as a span: a path ending inside a character
    has no string form, which is reachable by pointing at an offset mid-token.
    """
    raise NotImplementedError


@app.get('/api/span/{span_id}/tokens')
def read_tokens(span_id: str) -> list[dict]:
    """The token overlay for one span, with counterfactuals."""
    raise NotImplementedError


@app.get('/api/batches')
def read_batches() -> list[dict]:
    """Every generation call, with its origin and its interned parameters."""
    raise NotImplementedError


@app.get('/api/batches/{batch}/divergence')
def read_divergence(batch: str, depths: str = '1,3,10') -> dict:
    """How far the siblings of one call agree, as a profile over token depth."""
    raise NotImplementedError


@app.get('/api/params')
def read_params() -> dict:
    """The intern table, whole. It is small and every span points into it."""
    raise NotImplementedError


@app.get('/api/slice')
def read_slice(at: str, length: int) -> dict:
    """What a generation from `at` would send: `{start, end, text, bytes}`.

    The read Phase 3's viewport is built on, and it is worth having before the
    viewport exists: it is the only way to see what was actually in context,
    and the start it reports is the nudged one -- the slice that would be used,
    not the one that was asked for.
    """
    raise NotImplementedError


@app.get('/api/settings')
def read_settings() -> dict:
    """The parameter set a client should start from, with the server's own
    facts filled in.

    `model` and `n_ctx` are properties of what is serving rather than of what
    the user asked for, and both are recorded per span. This is the only place
    the API knows them; a generate request carries them like any other
    parameter.
    """
    raise NotImplementedError


# -- writes ----------------------------------------------------------------

@app.post('/api/author')
def do_author(body: Author) -> dict:
    """Append a given span at a position. Returns the tree and the new span."""
    raise NotImplementedError


@app.post('/api/generate')
def do_generate(body: Generate) -> dict:
    """Record the intent, save, then call the model once per continuation.

    Blocks for the whole batch, holding the writer lock. A reader watching
    `/api/tree` sees the spans appear in flight and fill in one at a time,
    because `Session.generate` saves per continuation -- an interrupted batch
    keeps what landed.
    """
    raise NotImplementedError


@app.post('/api/branch')
def do_branch(body: Branch) -> dict:
    """Take a token the model ranked but did not sample, and branch there.

    No generation and nothing divided: the alternative was recorded when the
    span was. This is the operation the counterfactual storage exists to pay
    for.
    """
    raise NotImplementedError


@app.post('/api/delete')
def do_delete(body: At) -> dict:
    """Soft, cascading, and reversible. Nothing is rewritten and no bytes go."""
    raise NotImplementedError


@app.post('/api/restore')
def do_restore(body: At) -> dict:
    """Undo a delete -- a list operation, which is what soft delete buys."""
    raise NotImplementedError


@app.put('/api/cursor')
def set_cursor(body: At) -> dict:
    """Move `selected`. Stored in the tree, so it survives a restart.

    A mutation rather than a read because it is written down. Whether the front
    end should keep its own selection instead is a client question; the field
    exists because the CLI needs somewhere to point.
    """
    raise NotImplementedError


# -- errors ----------------------------------------------------------------

def install_error_handlers(app: FastAPI) -> None:
    """The core raises `KeyError` and `ValueError`; HTTP wants 404 and 400.

    Mapped once here rather than caught per route, because every route reaches
    the same two through `ops.check`: an unknown span is 404, an offset outside
    a span is 400, and a generation request with no model server attached is
    503. Nothing else is translated -- an unexpected exception should be a 500
    with a traceback in the log, not a tidy message that hides a bug.
    """
    raise NotImplementedError


# -- lifecycle -------------------------------------------------------------

def main(argv=None) -> int:
    """Open one tree, refuse to start without it, and serve.

    A tree that fails validation is a refusal rather than a warning: the
    validator's nine checks are the load-time contract, and a server that
    serves a tree it knows is broken hands the problem to every client at once.
    `loom.py` is the repair tool -- it can open with `strict=False`.

    In-flight spans left by a dead process are closed as `aborted` by
    `Session.open` before the first request is served, which is decision 8's
    load-time rule and is why "maybe still running" is not a state the API can
    report.
    """
    raise NotImplementedError


if __name__ == '__main__':
    raise SystemExit(main())
