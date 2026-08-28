"""The command line: the reference client, and the floor.

**No capability may be surface-only.** If a thing can be done at all it can be done here,
without the reading surface. That is not a use case -- it is a check on where capability
is allowed to live, since anything reachable only by clicking has put itself somewhere the
record cannot follow.

Reads take no lock and need no server. `realise` and `delete` need neither a server nor a
tokeniser; `create` needs a tokeniser; only `generate` calls a model.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from .core import Rejected, Source, Store, StoreError, violations
from .core import reads as R
from .core.check import Corrupt

DEFAULT_SERVER = os.environ.get("TOKENLOOM_SERVER", "http://localhost:8081")


# ---- showing bytes -------------------------------------------------------------------


def show_bytes(data: bytes) -> str:
    """Bytes that do not decode have no string form, and what a reader shows in their
    place is the reader's to choose. This one shows U+FFFD and says so in `--help`."""
    return data.decode("utf-8", errors="replace")


def token_repr(store: Store, node: R.Node) -> str:
    return repr(show_bytes(R.node_bytes(store.conn, node.id)))


def source_name(store: Store, source_id: int) -> str:
    kind, name = store.conn.execute(
        "SELECT kind, name FROM sources WHERE id = ?", (source_id,)
    ).fetchone()
    return f"{kind}:{name}" if name else kind


# ---- the adapter ---------------------------------------------------------------------


def adapter_for(args) -> object:
    """Built from the server's own answer about what it is serving.

    Inference is local only, so `/props` names the model file on disk -- which is the route
    to per-token bytes, since the server has none. The source name defaults to that file's
    stem because the name has to separate everything whose draws must not factor together,
    and the file is the thing that is actually being served: model, imatrix and quant.
    """
    from .adapters.llamacpp.adapter import LlamaCppAdapter
    from .adapters.llamacpp.client import LlamaCppClient
    from .adapters.llamacpp.vocab import GgufVocabulary

    client = LlamaCppClient(args.server)
    props = client.props()
    gguf = Path(args.gguf or props.model_path)
    if not gguf.exists():
        raise SystemExit(
            f"no model file at {gguf}. The server reports {props.model_path!r}; "
            "pass --gguf if it is not reachable from here."
        )
    return LlamaCppAdapter(
        Source("model", args.model or gguf.stem),
        GgufVocabulary.cached(gguf, props.model_alias or gguf.stem),
        client,
        cache_prompt=getattr(args, "cache_prompt", False),
    )


def actor(args) -> Source:
    return Source("user", getattr(args, "user", "") or "")


# ---- commands ------------------------------------------------------------------------


def cmd_init(args) -> int:
    store = Store.initialise(args.tree, vocabulary=args.vocab)
    print(f"{store.path}  vocabulary {store.vocabulary}  marker {store.tree['marker']}")
    return 0


def cmd_create(args) -> int:
    with Store.open(args.tree, write=True) as store:
        adapter = adapter_for(args)
        act = store.create(
            args.at, args.text, vocabulary=adapter, source=actor(args), special=args.special
        )
        tip = store.conn.execute("SELECT tip FROM acts WHERE id = ?", (act,)).fetchone()[0]
        nodes = R.act_tokens(store.conn, act)
        print(f"act {act}  create  {len(nodes)} tokens  tip {tip}")
        for node in nodes:
            print(f"  {node.id:>6}  {node.token_id:>7}  {token_repr(store, node)}")
    return 0


def cmd_generate(args) -> int:
    params = {
        "length": args.length,
        "top_k": args.top_k,
        "top_n": args.top_n,
        "temperature": args.temperature,
    }
    with Store.open(args.tree, write=True) as store:
        adapter = adapter_for(args)
        act, answer = store.generate(args.at, params, adapter=adapter, seed=args.seed)
        seed = store.conn.execute("SELECT seed FROM acts WHERE id = ?", (act,)).fetchone()[0]
        print(f"act {act}  generate  {answer.terminator}  seed {seed}")
        if answer.reason:
            print(f"  reason: {answer.reason}")
        for node in R.act_tokens(store.conn, act):
            logprob = R.node_logprob(store.conn, node.id)
            shown = "         -" if logprob is None else f"{logprob:10.4f}"
            print(f"  {node.id:>6}  {node.token_id:>7}  {shown}  {token_repr(store, node)}")
    return 0


def cmd_realise(args) -> int:
    with Store.open(args.tree, write=True) as store:
        source = _edge_source(store, args.at, args.source)
        act = store.realise(args.at, source, args.rank, actor=actor(args))
        tip = store.conn.execute("SELECT tip FROM acts WHERE id = ?", (act,)).fetchone()[0]
        node = R.get_node(store.conn, tip)
        print(f"act {act}  realise  rank {args.rank} of {source}  -> node {tip}")
        print(f"  {tip:>6}  {node.token_id:>7}  {token_repr(store, node)}")
    return 0


def _edge_source(store: Store, node: int, named: str | None) -> Source:
    """Two sources may rank at one node, so a rank alone names nothing. Where only one
    has ranked there, naming it is a formality this spares the caller."""
    if named:
        return Source("model", named)
    found = {row[0] for row in store.conn.execute(
        "SELECT DISTINCT source FROM edges WHERE node = ?", (node,))}
    if not found:
        raise SystemExit(f"node {node} has no ranked edges")
    if len(found) > 1:
        names = ", ".join(sorted(source_name(store, s) for s in found))
        raise SystemExit(f"node {node} is ranked by more than one source ({names}); pass --source")
    kind, name = store.conn.execute(
        "SELECT kind, name FROM sources WHERE id = ?", (found.pop(),)
    ).fetchone()
    return Source(kind, name)


def cmd_delete(args) -> int:
    with Store.open(args.tree, write=True) as store:
        store.undelete(args.node) if args.undo else store.delete(args.node)
        print(f"node {args.node}  {'live' if R.is_live(store.conn, args.node) else 'not live'}")
    return 0


def cmd_show(args) -> int:
    with Store.open(args.tree) as store:
        if args.node is None:
            print(f"{store.path}  vocabulary {store.vocabulary}")
            for table in ("nodes", "edges", "acts", "params", "sources", "vocab"):
                count = store.conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                print(f"  {table:>8}  {count}")
            for root in R.roots(store.conn):
                print(f"  root {root.id}  {token_repr(store, root)}")
            return 0

        node = R.get_node(store.conn, args.node)
        logprob = R.node_logprob(store.conn, node.id)
        print(f"node {node.id}  token {node.token_id}  {token_repr(store, node)}")
        print(f"  source     {source_name(store, node.source)}")
        print(f"  parent     {node.parent}")
        print(f"  depth      {R.depth(store.conn, node.id)}")
        print(f"  logprob    {'-' if logprob is None else f'{logprob:.4f}'}")
        print(f"  live       {R.is_live(store.conn, node.id)}"
              f"{'  (row carries deleted)' if node.deleted else ''}")
        print(f"  frequency  {R.frequency(store.conn, node.id)}"
              f"  acts {R.acts_through(store.conn, node.id)}")
        print(f"  path       {show_bytes(R.path_bytes(store.conn, node.id))!r}")

        kids = R.children(store.conn, node.id)
        if kids:
            print(f"  children ({len(kids)})")
            for kid in kids:
                lp = R.node_logprob(store.conn, kid.id)
                print(f"    {kid.id:>6}  {'      -' if lp is None else f'{lp:7.4f}'}  "
                      f"{token_repr(store, kid):<16}  {source_name(store, kid.source)}"
                      f"{'' if R.is_live(store.conn, kid.id) else '  (not live)'}")

        edges = R.unrealised_edges(store.conn, node.id)
        if edges:
            print(f"  branchable ({len(edges)} unrealised of "
                  f"{len(R.ranking(store.conn, node.id))} ranked)")
            for edge in edges[: args.limit]:
                spelled = store.conn.execute(
                    "SELECT bytes FROM vocab WHERE token_id = ?", (edge.token_id,)
                ).fetchone()[0]
                print(f"    rank {edge.rank:>3}  {edge.logprob:8.4f}  "
                      f"{show_bytes(bytes(spelled))!r:<16}  {source_name(store, edge.source)}")
            if len(edges) > args.limit:
                print(f"    ... {len(edges) - args.limit} more (--limit)")
    return 0


def cmd_path(args) -> int:
    with Store.open(args.tree) as store:
        data = R.path_bytes(store.conn, args.node)
        if args.raw:
            sys.stdout.buffer.write(data)
        else:
            print(show_bytes(data))
    return 0


def cmd_tree(args) -> int:
    with Store.open(args.tree) as store:
        start = args.at
        for depth, node in R.walk(store.conn, start):
            if depth > args.depth:
                continue
            live = R.is_live(store.conn, node.id)
            ranked = len(R.unrealised_edges(store.conn, node.id))
            print(f"{'  ' * depth}{node.id:>6}  {token_repr(store, node):<18}"
                  f"{'' if live else ' [deleted]'}"
                  f"{f'  +{ranked}' if ranked else ''}")
    return 0


def cmd_acts(args) -> int:
    with Store.open(args.tree) as store:
        rows = store.conn.execute(
            "SELECT a.id, a.op, a.origin, a.tip, a.created, a.terminator, a.rank, "
            "a.seed, p.json, a.source FROM acts a LEFT JOIN params p ON p.id = a.params "
            "ORDER BY a.id"
        ).fetchall()
        for act, op, origin, tip, created, terminator, rank, seed, params, source in rows:
            bits = [f"{act:>4}", f"{op:<8}", created, f"{source_name(store, source):<24}",
                    f"origin {origin}", f"tip {tip}"]
            if terminator:
                bits.append(terminator)
            if rank is not None:
                bits.append(f"rank {rank}")
            if params:
                bits.append(f"{params} seed {seed}")
            print("  ".join(bits))
    return 0


def cmd_check(args) -> int:
    with Store.open(args.tree) as store:
        found = violations(store.conn)
        for violation in found:
            print(violation)
        counts = {
            table: store.conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in ("nodes", "edges", "acts")
        }
        print(f"{'FAILED' if found else 'clean'}: {len(found)} violations over "
              + ", ".join(f"{v} {k}" for k, v in counts.items()))
    return 1 if found else 0


def cmd_props(args) -> int:
    """What the adapter would talk to, and what it would call itself."""
    from .adapters.llamacpp.client import LlamaCppClient

    props = LlamaCppClient(args.server).props()
    print(json.dumps({
        "server": args.server,
        "n_ctx": props.n_ctx,
        "model_alias": props.model_alias,
        "model_path": props.model_path,
        "source_name_default": Path(props.model_path).stem,
    }, indent=2))
    return 0


# ---- wiring --------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="tokenloom",
        description="A trie over tokens, with what else was ranked at every position. "
                    "Bytes that do not decode are shown as U+FFFD; use `path --raw` for "
                    "the bytes themselves.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    def backend(p):
        p.add_argument("--server", default=DEFAULT_SERVER, help="llama.cpp base url")
        p.add_argument("--gguf", default=os.environ.get("TOKENLOOM_GGUF"),
                       help="model file; defaults to what the server reports serving")
        p.add_argument("--model", default=os.environ.get("TOKENLOOM_MODEL"),
                       help="source name; must separate anything whose draws must not "
                            "factor together. Defaults to the model file's stem.")
        p.add_argument("--user", default="", help="the acting user; empty is the unnamed user")
        p.add_argument("--cache-prompt", action="store_true", dest="cache_prompt",
                       help="let the server reuse its KV cache. Faster on long prompts, "
                            "and measurably perturbs the logits it reports: cold and warm "
                            "disagree by up to 0.056 on this build, enough to reorder "
                            "near-ties. Off by default so a ranking depends on the path "
                            "and nothing else.")

    p = sub.add_parser("init", help="make a tree")
    p.add_argument("tree", type=Path)
    p.add_argument("--vocab", required=True, help="the vocabulary this tree is in")
    p.set_defaults(fn=cmd_init)

    p = sub.add_parser("create", help="tokenise authored text into nodes")
    p.add_argument("tree", type=Path)
    p.add_argument("text")
    p.add_argument("--at", type=int, help="node to extend; omit to begin a root")
    p.add_argument("--special", action="store_true",
                   help="read control-token literals as control tokens. Never the default: "
                        "authored text is plain bytes, and quoting one does not inject it.")
    backend(p)
    p.set_defaults(fn=cmd_create)

    p = sub.add_parser("generate", help="draw from a model")
    p.add_argument("tree", type=Path)
    p.add_argument("--at", type=int, required=True)
    p.add_argument("--length", type=int, default=16)
    p.add_argument("--top-k", type=int, default=20, dest="top_k")
    p.add_argument("--top-n", type=int, default=20, dest="top_n",
                   help="how many alternatives to record. top_n >= top_k keeps the drawn "
                        "token inside its own ranking.")
    p.add_argument("--temperature", type=float, default=1.0)
    p.add_argument("--seed", type=int, help="omit and the core supplies one")
    backend(p)
    p.set_defaults(fn=cmd_generate)

    p = sub.add_parser("realise", help="take a ranked edge; no model is called")
    p.add_argument("tree", type=Path)
    p.add_argument("--at", type=int, required=True)
    p.add_argument("--rank", type=int, required=True)
    p.add_argument("--source", help="whose ranking; needed only where more than one ranked")
    p.add_argument("--user", default="")
    p.set_defaults(fn=cmd_realise)

    p = sub.add_parser("delete", help="mark a node deleted; liveness is derived")
    p.add_argument("tree", type=Path)
    p.add_argument("node", type=int)
    p.add_argument("--undo", action="store_true", help="clear it; live again only if its "
                                                       "ancestry is")
    p.set_defaults(fn=cmd_delete)

    p = sub.add_parser("show", help="a node, or the tree's shape")
    p.add_argument("tree", type=Path)
    p.add_argument("node", type=int, nargs="?")
    p.add_argument("--limit", type=int, default=20, help="unrealised edges to list")
    p.set_defaults(fn=cmd_show)

    p = sub.add_parser("path", help="a path's bytes")
    p.add_argument("tree", type=Path)
    p.add_argument("node", type=int)
    p.add_argument("--raw", action="store_true", help="the bytes, undecoded, to stdout")
    p.set_defaults(fn=cmd_path)

    p = sub.add_parser("tree", help="the shape, depth-first")
    p.add_argument("tree", type=Path)
    p.add_argument("--at", type=int)
    p.add_argument("--depth", type=int, default=1000)
    p.set_defaults(fn=cmd_tree)

    p = sub.add_parser("acts", help="what was done")
    p.add_argument("tree", type=Path)
    p.set_defaults(fn=cmd_acts)

    p = sub.add_parser("check", help="every invariant")
    p.add_argument("tree", type=Path)
    p.set_defaults(fn=cmd_check)

    p = sub.add_parser("props", help="what the server is serving")
    p.add_argument("--server", default=DEFAULT_SERVER)
    p.set_defaults(fn=cmd_props)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        try:
            return args.fn(args)
        finally:
            # `path --raw` exists to be piped, and a reader that stops early -- `head`,
            # `xxd | tail` -- must not look like a crash. Flushing here is what turns the
            # broken pipe into an exit code instead of a traceback at interpreter shutdown.
            sys.stdout.flush()
    except BrokenPipeError:
        os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())
        return 0
    except Corrupt as bad:
        print("this store fails an invariant and will not be written:\n  "
              + "\n  ".join(str(v) for v in bad.violations[:10]), file=sys.stderr)
        return 2
    except (Rejected, StoreError, KeyError, ValueError) as why:
        print(f"{type(why).__name__}: {why}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
