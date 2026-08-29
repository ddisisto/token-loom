#!/usr/bin/env python
"""Project a tree into one file, for a client that cannot reach the store.

**No server and no model.** Reads only, so it takes no lock and does not modify the tree.
The projection is deliberately dumb: it carries the rows and the two derived values that
cost a join, and computes nothing a reader could not compute for itself.

**Bytes go out base64 and never decoded.** A token's bytes may be a fragment of a
character, so decoding here would decide -- on behalf of whatever reads this -- a question
`docs/CORE.md` leaves to the reader. Ids index `vocab`; nothing repeats a spelling.

    uv run scripts/dump.py data/example -o probe/tree.js --js
    uv run scripts/dump.py data/appendix -o probe/tree-appendix.js --js --var TREE_APPENDIX
    uv run scripts/dump.py data/example | jq .
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import sys
from pathlib import Path

from tokenloom.core import Store
from tokenloom.core import reads as R


def b64(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def project(store: Store) -> dict:
    conn = store.conn
    return {
        "tree": {
            "path": str(store.path),
            "vocabulary": store.vocabulary,
            "created": store.tree.get("created"),
        },
        "vocab": {
            str(t): b64(bytes(b))
            for t, b in conn.execute("SELECT token_id, bytes FROM vocab")
        },
        "sources": {
            str(i): {"kind": k, "name": n}
            for i, k, n in conn.execute("SELECT id, kind, name FROM sources")
        },
        "nodes": nodes(store),
        "rankings": rankings(store),
        "acts": acts(store),
    }


def nodes(store: Store) -> list[dict]:
    """Every node, with the one derived value that is not a walk: its own logprob.

    `logprob` is the ranked edge at its parent, for its source, carrying its token -- read
    through `reads` rather than recomputed here, because a derived value computed twice is
    a derived value that can disagree with itself.
    """
    out = []
    for row in store.conn.execute(
        "SELECT id, parent, token_id, source, deleted FROM nodes ORDER BY id"
    ):
        node = R.Node(row[0], row[1], row[2], row[3], bool(row[4]))
        out.append({
            "id": node.id,
            "parent": node.parent,
            "token": node.token_id,
            "source": node.source,
            "deleted": node.deleted,
            "logprob": R.node_logprob(store.conn, node.id),
        })
    return out


def rankings(store: Store) -> dict[str, list[dict]]:
    """The whole ranking at each node, each row marked with the child that realised it.

    Not `unrealised_edges`, which is the branchable set alone. A reader looking at a
    position wants to see the token that was taken sitting in its own ranking -- at what
    rank, against what else -- and the branchable set is then the rows with no child.
    """
    out: dict[str, list[dict]] = {}
    for node, source, rank, token, logprob, child in store.conn.execute(
        """
        SELECT e.node, e.source, e.rank, e.token_id, e.logprob, c.id
          FROM edges e
          LEFT JOIN nodes c
            ON c.parent = e.node AND c.token_id = e.token_id AND c.source = e.source
         ORDER BY e.node, e.source, e.rank
        """
    ):
        out.setdefault(str(node), []).append({
            "source": source,
            "rank": rank,
            "token": token,
            "logprob": logprob,
            "realised": child,
        })
    return out


def acts(store: Store) -> list[dict]:
    out = []
    for act, op, source, origin, tip, created, params, seed, terminator, rank in store.conn.execute(
        "SELECT a.id, a.op, a.source, a.origin, a.tip, a.created, p.json, a.seed, "
        "a.terminator, a.rank FROM acts a LEFT JOIN params p ON p.id = a.params ORDER BY a.id"
    ):
        out.append({
            "id": act, "op": op, "source": source, "origin": origin, "tip": tip,
            "created": created, "params": json.loads(params) if params else None,
            "seed": seed, "terminator": terminator, "rank": rank,
            "nodes": [n.id for n in R.act_tokens(store.conn, act)],
        })
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="dump.py", description=__doc__)
    parser.add_argument("tree", type=Path)
    parser.add_argument("-o", "--out", type=Path, help="write here; default is stdout")
    parser.add_argument("--js", action="store_true",
                        help="wrap as `window.<var> = ...` so a file:// page can load it "
                             "without a server, which `fetch` will not do")
    parser.add_argument("--var", default="TREE",
                        help="the global `--js` assigns to; default TREE")
    parser.add_argument("--indent", type=int, default=None)
    args = parser.parse_args(argv)

    with Store.open(args.tree) as store:
        body = json.dumps(project(store), indent=args.indent, ensure_ascii=False)
    text = f"window.{args.var} = {body};\n" if args.js else body + "\n"

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text)
        print(f"{args.out}  {len(text)} bytes", file=sys.stderr)
    else:
        try:
            sys.stdout.write(text)
            sys.stdout.flush()
        except BrokenPipeError:
            # Piped into `head` or `jq | less`, and a reader that stops early must not
            # look like a crash. The command line does the same, for the same reason.
            os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
