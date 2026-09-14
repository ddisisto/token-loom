"""The server: one tree, claimed for as long as the process runs.

`docs/SURFACE.md` has the surface claiming its tree and verifying once for the life of the
process rather than before every write, and this is that process. It serves the three reads
`surface.py` answers, the path predicate an adapter provides, and the five acts -- each under
its own verb, since a surface write with no verb would be a new kind of write.

**Reads run on connections of their own and writes on a thread of their own, and neither is
a concurrency scheme.** A sqlite3 connection cannot leave the thread that made it, and a read
served on the writer's connection would wait out a model call for no reason the store
imposes. What refuses a second write is the lock in `Writer`, because the document asks for
no queue.

**The server names no parameter a `generate` did not arrive with.** Defaults for those live
where a human types them, and an adapter that requires one says so itself -- as a refusal,
which is in the record. A server filling them in would be deciding what the store keeps,
one layer up from the place `docs/ADAPTER.md` forbids it.
"""

from __future__ import annotations

import sqlite3
import threading
from collections.abc import Callable, Iterator
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from starlette.applications import Starlette
from starlette.concurrency import run_in_threadpool
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from .. import surface as S
from ..core import Rejected, Source, Store, StoreError
from ..core import reads as R
from ..core.ports import Adapter
from . import wire

#: The family `docs/SURFACE.md` names, as far as it is built. A second member is a function
#: and an entry here; what settles which is right is reading one tree under two of them.
RULES: dict[str, S.Rule] = {"longest": S.longest}


class Busy(Exception):
    """A write was asked for while one was in flight. There is no queue."""


class Unreachable(Exception):
    """The backend could not be built. Nothing was written and the same request may succeed."""


class Failed(Exception):
    """A `generate` whose call happened and from which nothing could be recorded.

    The act carries `failed` and this does not name it: the store raises what the adapter
    raised, which knows no act id, and `docs/SURFACE.md` asks only the refusal to name one.
    """


# ---- the writer ----------------------------------------------------------------------


class Writer:
    """The store, and the one thread its connection lives on.

    Opening claims the tree and verifies it, so a tree another process holds fails here and
    not at the first write. Everything that writes is submitted to the same worker, which is
    what keeps the connection on the thread that made it.

    The lock is not what serialises the writes -- one worker does that. It is what refuses a
    second request rather than queueing it behind the first.
    """

    def __init__(self, path: str | Path, *, verify: bool = True) -> None:
        self.path = Path(path)
        self._pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="tokenloom-write")
        self._busy = threading.Lock()
        try:
            self.store: Store = self._pool.submit(
                Store.open, self.path, write=True, verify=verify
            ).result()
        except BaseException:
            self._pool.shutdown()
            raise

    def act[T](self, work: Callable[[Store], T]) -> T:
        """Run `work` against the store on the writer's thread, or raise `Busy`."""
        if not self._busy.acquire(blocking=False):
            raise Busy("a write is in flight; there is no queue")
        try:
            return self._pool.submit(work, self.store).result()
        finally:
            self._busy.release()

    def reader(self) -> sqlite3.Connection:
        return self.store.reader()

    def close(self) -> None:
        self._pool.submit(self.store.close).result()
        self._pool.shutdown()


@contextmanager
def reading(writer: Writer) -> Iterator[sqlite3.Connection]:
    conn = writer.reader()
    try:
        yield conn
    finally:
        conn.close()


class Backend:
    """The adapter, built on first need and kept.

    Reads need no model, and neither do `realise`, `delete` and `undelete`, so a tree is
    served with nothing running and a backend that cannot be reached is reported at the
    request that wanted it. The lock is so that two readers asking the predicate at once
    build it once.
    """

    def __init__(self, build: Callable[[], Adapter]) -> None:
        self._build = build
        self._made: Adapter | None = None
        self._lock = threading.Lock()

    def get(self) -> Adapter:
        with self._lock:
            if self._made is None:
                try:
                    self._made = self._build()
                except Exception as why:
                    raise Unreachable(f"no backend: {why}") from why
            return self._made


# ---- requests ------------------------------------------------------------------------


def _field(body: dict, name: str) -> Any:
    if name not in body:
        raise ValueError(f"this request needs {name!r}")
    return body[name]


def _actor(body: dict) -> Source:
    return Source("user", body.get("user") or "")


def _rule(request: Request, *, bare: bool = False) -> S.Rule | None:
    """`bare` admits `none`, which is the ancestry and nothing below -- what a client that
    already knows its leaf asks for. A preview has no such reading: it follows a rule or it
    is not a preview."""
    named = request.query_params.get("rule", "longest")
    if bare and named == "none":
        return None
    if named not in RULES:
        raise ValueError(f"no continuation rule {named!r}; this server has {sorted(RULES)}")
    return RULES[named]


def _int(request: Request, name: str) -> int:
    raw = request.query_params.get(name)
    if raw is None:
        raise ValueError(f"this read needs a {name!r}")
    try:
        return int(raw)
    except ValueError as why:
        raise ValueError(f"{name} must be an integer, not {raw!r}") from why


def _fault(kind: str, status: int, message: str, **extra: Any) -> JSONResponse:
    """The status says a request failed; the body says which kind of failure it was."""
    return JSONResponse({"error": kind, "message": message, **extra}, status_code=status)


HANDLERS = {
    Rejected: lambda r, e: _fault("rejected", 400, str(e)),
    Busy: lambda r, e: _fault("busy", 409, str(e)),
    Unreachable: lambda r, e: _fault("backend", 503, str(e)),
    Failed: lambda r, e: _fault("failed", 502, str(e)),
    StoreError: lambda r, e: _fault("store", 500, str(e)),
    KeyError: lambda r, e: _fault("not_found", 404, e.args[0] if e.args else "not found"),
    ValueError: lambda r, e: _fault("bad_request", 400, str(e)),
}


# ---- the application -----------------------------------------------------------------


def build_app(writer: Writer, backend: Backend) -> Starlette:
    """Routes over an already-open tree.

    The writer is opened before this rather than in a lifespan, so a tree another process
    holds is reported by whoever started the server rather than as a failure to come up.
    """

    # ---- reads: each takes a connection of its own and closes it ----------------------

    def tree(request: Request) -> JSONResponse:
        with reading(writer) as conn:
            return JSONResponse({
                "path": str(writer.store.path),
                "vocabulary": writer.store.vocabulary,
                "marker": writer.store.tree["marker"],
                "counts": {
                    table: conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                    for table in ("nodes", "edges", "acts")
                },
                "roots": [wire.node(n) for n in R.roots(conn)],
                "sources": wire.source_names(conn),
            })

    def path(request: Request) -> JSONResponse:
        node = request.path_params["node"]
        rule = _rule(request, bare=True)
        with reading(writer) as conn:
            cells = S.path(conn, node, rule)
            return JSONResponse({
                "node": node,
                "leaf": cells[-1].nodes[-1].node.id,
                "rule": request.query_params.get("rule", "longest"),
                "segments": [wire.segment(cell, wire.path_node) for cell in cells],
                "sources": wire.source_names(conn),
            })

    def ranking(request: Request) -> JSONResponse:
        node = request.path_params["node"]
        with reading(writer) as conn:
            R.get_node(conn, node)  # a node that is not there is not an empty ranking
            return JSONResponse({
                "node": node,
                "rows": [wire.ranked(row) for row in S.ranking(conn, node)],
                "sources": wire.source_names(conn),
            })

    def branches(request: Request) -> JSONResponse:
        node = request.path_params["node"]
        budget = _int(request, "budget")
        rule = _rule(request)
        with reading(writer) as conn:
            R.get_node(conn, node)  # a subtree descent from a leaf is empty either way
            lines = S.branches(conn, node, budget, rule)
            return JSONResponse({
                "node": node,
                "budget": budget,
                "rule": request.query_params.get("rule", "longest"),
                "branches": [wire.branch(line) for line in lines],
                "sources": wire.source_names(conn),
            })

    def acts(request: Request) -> JSONResponse:
        """What was done, newest first. `in_flight` is the `generate` with no terminator --
        what an inline placeholder stands for, which is why a page reloaded mid-generation
        does not lose it."""
        limit = _int(request, "limit") if "limit" in request.query_params else 50
        flight = request.query_params.get("in_flight") in ("1", "true")
        with reading(writer) as conn:
            rows = conn.execute(
                "SELECT id FROM acts"
                + (" WHERE op = 'generate' AND terminator IS NULL" if flight else "")
                + " ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
            return JSONResponse({
                "acts": [wire.act(conn, row[0]) for row in rows],
                "sources": wire.source_names(conn),
            })

    def evaluable(request: Request) -> JSONResponse:
        """Whether the backend would evaluate the path at a node. Advisory, and it writes
        nothing: a request that goes anyway is refused by the adapter and recorded."""
        raw = request.query_params.get("node")
        node = int(raw) if raw else None
        with reading(writer) as conn:
            ids = R.path_token_ids(conn, node) if node is not None else []
        return JSONResponse({"node": node, "evaluable": backend.get().will_evaluate(ids)})

    # ---- writes: five acts, each under its own verb -----------------------------------

    async def create(request: Request) -> JSONResponse:
        body = await request.json()
        adapter = await run_in_threadpool(backend.get)
        named = body.get("attribute")
        source = Source.parse(named) if named else None

        def work(store: Store) -> dict:
            act = store.create(
                body.get("at"), _field(body, "text"),
                vocabulary=adapter, actor=_actor(body), source=source,
                special=bool(body.get("special")),
            )
            return wire.act(store.conn, act)

        return JSONResponse(await run_in_threadpool(writer.act, work), status_code=201)

    async def generate(request: Request) -> JSONResponse:
        body = await request.json()
        adapter = await run_in_threadpool(backend.get)
        params = dict(_field(body, "params"))

        def work(store: Store) -> tuple[str | None, dict]:
            try:
                act, answer = store.generate(
                    body.get("at"), params, adapter=adapter, actor=_actor(body)
                )
            except Rejected:
                raise  # the core declined before writing; there is no act to name
            except Exception as why:
                raise Failed(str(why)) from why
            return answer.reason, wire.act(store.conn, act)

        reason, shape = await run_in_threadpool(writer.act, work)
        if shape["terminator"] == "refused":
            return _fault("refused", 422, reason or "the adapter declined", act=shape)
        return JSONResponse(shape, status_code=201)

    async def realise(request: Request) -> JSONResponse:
        """The source is named rather than inferred: a rank alone names nothing where two
        models have ranked, and the ranking read gives every row its own."""
        body = await request.json()
        source = Source.parse(_field(body, "source"))

        def work(store: Store) -> dict:
            act = store.realise(
                _field(body, "at"), source, _field(body, "rank"), actor=_actor(body)
            )
            return wire.act(store.conn, act)

        return JSONResponse(await run_in_threadpool(writer.act, work), status_code=201)

    def _liveness(undo: bool):
        async def endpoint(request: Request) -> JSONResponse:
            body = await request.json()
            node = _field(body, "node")

            def work(store: Store) -> dict:
                write = store.undelete if undo else store.delete
                act = write(node, actor=_actor(body))
                return {
                    **wire.act(store.conn, act),
                    "node": wire.node(R.get_node(store.conn, node)),
                    "live": R.is_live(store.conn, node),
                }

            return JSONResponse(await run_in_threadpool(writer.act, work), status_code=201)

        return endpoint

    return Starlette(
        routes=[
            Route("/tree", tree),
            Route("/path/{node:int}", path),
            Route("/ranking/{node:int}", ranking),
            Route("/branches/{node:int}", branches),
            Route("/acts", acts),
            Route("/evaluable", evaluable),
            Route("/create", create, methods=["POST"]),
            Route("/generate", generate, methods=["POST"]),
            Route("/realise", realise, methods=["POST"]),
            Route("/delete", _liveness(False), methods=["POST"]),
            Route("/undelete", _liveness(True), methods=["POST"]),
        ],
        exception_handlers=HANDLERS,
    )
