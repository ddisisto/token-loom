"""What the reads and the acts look like on the wire.

Bytes are the thing that does not travel. A token may spell a fragment of a character, so a
spelling crosses as the text it decodes to with U+FFFD in place of what does not -- the same
choice the command line makes -- next to whether it decoded at all. A client that wants the
bytes has the token id and the vocabulary.

Sources cross as ids with the map beside them, because a path of a thousand nodes carries the
same handful of them over and over. The table is small enough that sending all of it is
cheaper than working out which are present.

`PathNode` and `RankedEdge` are flattened here rather than mirrored. Their nesting is what
keeps the record's own shape visible in `core/reads.py`; a client reading a node's `logprob`
should not have to know it came from an edge.
"""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Callable
from typing import Any

from ..core import reads as R
from . import reads as S


def spelled(data: bytes) -> dict[str, Any]:
    try:
        return {"text": data.decode("utf-8"), "decodes": True}
    except UnicodeDecodeError:
        return {"text": data.decode("utf-8", "replace"), "decodes": False}


def node(item: R.Node) -> dict[str, Any]:
    return {
        "id": item.id,
        "parent": item.parent,
        "token": item.token_id,
        "source": item.source,
        "deleted": item.deleted,
    }


def root(item: R.Node, name: S.Label) -> dict[str, Any]:
    """A root with what a list of them is drawn from: its opening text, and whether the
    tree parts where that text stops.

    `forked` is a fact about the tree and the text is not enough to carry it -- a label cut
    for room and one cut at a divergence read the same. What marks it, and how far the text
    is cut again to fit, are the client's: it has the column and the server does not.
    """
    return {
        **node(item),
        "label": "".join(cell.text for cell in name.segments),
        "forked": name.forked,
    }


def path_node(mark: R.PathNode) -> dict[str, Any]:
    """A node of a path with what is derived at it: whether it is live, what the ranking
    above gave it, and whether its parent parts here."""
    return {**node(mark.node), "live": mark.live, "logprob": mark.logprob, "fork": mark.fork}


def segment[T](cell: S.Segment[T], project: Callable[[T], Any]) -> dict[str, Any]:
    return {
        "text": cell.text,
        "decodes": cell.decodes,
        "nodes": [project(item) for item in cell.nodes],
    }


def ranked(row: R.RankedEdge) -> dict[str, Any]:
    """One row of a ranking. `child` is the node that realised it, and its absence is what
    makes the row branchable."""
    return {
        "source": row.edge.source,
        "rank": row.edge.rank,
        "token": row.edge.token_id,
        "logprob": row.edge.logprob,
        **spelled(row.spelling),
        "child": row.child.id if row.child is not None else None,
    }


def branch(line: S.Branch) -> dict[str, Any]:
    """One preview line, whose nodes are ids rather than records.

    A preview line is text and somewhere to select from, and a record per node would repeat
    what the line already gives or what is true of all of it: the run says each node's parent,
    and the subtree is live by construction. A client wanting a node's source or its ranking
    asks about that node.

    It is nearly the whole response otherwise. A band opened at a root of a twenty-thousand
    node tree carries eight kilobytes of text, and carried it in a megabyte of node records
    before this sent ids.
    """
    return {
        "parts_at": line.parts_at,
        "segments": [segment(cell, lambda n: n.id) for cell in line.segments],
        "branches": [branch(inner) for inner in line.branches],
        "dropped": line.dropped,
    }


def source_names(conn: sqlite3.Connection) -> dict[str, str]:
    return {
        str(row[0]): (f"{row[1]}:{row[2]}" if row[2] else row[1])
        for row in conn.execute("SELECT id, kind, name FROM sources")
    }


def act(conn: sqlite3.Connection, which: int) -> dict[str, Any]:
    """An act and the nodes it produced.

    A `create` or a `realise` produces every node under it; a `generate` produces those and
    a terminator, and one still in flight has none of either. `delete` and `undelete`
    produce no nodes at all -- what they changed is read off the node they name.

    The source map is not here: an act list would carry the same one on every row.
    """
    row = conn.execute(
        "SELECT a.id, a.op, a.origin, a.tip, a.created, a.terminator, a.rank, a.model, "
        "a.actor, p.json FROM acts a LEFT JOIN params p ON p.id = a.params WHERE a.id = ?",
        (which,),
    ).fetchone()
    if row is None:
        raise KeyError(f"no act {which}")
    return {
        "id": row[0],
        "op": row[1],
        "origin": row[2],
        "tip": row[3],
        "created": row[4],
        "terminator": row[5],
        "rank": row[6],
        "model": row[7],
        "actor": row[8],
        "params": json.loads(row[9]) if row[9] else None,
        "nodes": [node(n) for n in R.act_tokens(conn, which)],
    }
