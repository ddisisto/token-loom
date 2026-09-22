"""The three reads `docs/SURFACE.md` names, and the segmentation they are stated in.

These sit above `core/reads.py` because each needs something the record has no notion of:
a character, a line's worth of room, or which continuation the reader is following. The
core answers questions about the record and stops there.

Nothing here is an interface. The document states the three as what must be answerable from
one descent, and this is that; what an API or a command line hands a client is its own.

`label` is not a fourth. A list of roots is a point read the core already answers, and what
it cannot answer is what to call them; that is bounded by a budget and costs nothing like a
read.
"""

from __future__ import annotations

import codecs
import sqlite3
from collections.abc import Callable, Sequence
from dataclasses import dataclass

from ..core import reads as R

# ---- segments ------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Segment[T]:
    """The shortest run of nodes whose bytes decode: the display unit and the addressable
    unit both. In ordinary English it is one node; across a multi-token character, several.

    It cannot be split, so nothing addresses a node inside one.
    """

    nodes: list[T]
    text: str
    decodes: bool


def _completable(data: bytes) -> bool:
    """Whether appending bytes could still make `data` decode.

    A truncated character can; a stray continuation byte never will, and waiting for one
    would swallow the whole rest of the run into a segment that is not short.
    """
    try:
        codecs.getincrementaldecoder("utf-8")().decode(data, False)
    except UnicodeDecodeError:
        return False
    return True


def segments[T](items: Sequence[T], spell: Callable[[T], bytes]) -> list[Segment[T]]:
    """Group a run of nodes into segments, in order.

    A segment closes at the first node whose arrival makes the whole accumulated buffer
    decode -- the whole buffer, not the part of it the decoder could emit, so a token that
    finishes one character and opens another leaves the segment open. Bytes that will never
    decode close a segment where they stand, marked, spelling U+FFFD in their place; a run
    ends that way when a path ends mid-character, and so does one node when its bytes are a
    stray continuation byte.
    """
    out: list[Segment[T]] = []
    run: list[T] = []
    buf = b""
    for item in items:
        data = spell(item)
        if run and not _completable(buf + data):
            # What is held was a truncated character and this node is not its tail. It
            # closes where it stands rather than reaching forward over text that decodes.
            out.append(Segment(run, buf.decode("utf-8", "replace"), False))
            run, buf = [], b""
        run.append(item)
        buf += data
        try:
            text = buf.decode("utf-8")
        except UnicodeDecodeError:
            if _completable(buf):
                continue
            out.append(Segment(run, buf.decode("utf-8", "replace"), False))
        else:
            out.append(Segment(run, text, True))
        run, buf = [], b""
    if run:
        out.append(Segment(run, buf.decode("utf-8", "replace"), False))
    return out


# ---- the continuation rule -----------------------------------------------------------


class Subtree:
    """The live tree below an anchor, held in memory from one descent.

    A rule is asked for a choice at every node a continuation passes, and `longest` has to
    know how far each child reaches, so the descent is made once and kept. Dead nodes are
    dropped as they arrive: liveness carries down, so a dead node takes its children with
    it and what is left is still a tree.

    `hidden` keeps them instead, which is for descending ground that is dead throughout --
    below a live leaf, where there is nothing live left to pass over. A rule handed both
    kinds at one parent would be choosing between them, which is what `docs/SURFACE.md`'s
    *Hidden* forbids, so nothing hands it both.
    """

    def __init__(
        self, conn: sqlite3.Connection, anchor: int | None = None, hidden: bool = False
    ) -> None:
        self.anchor = anchor
        self.children: dict[int | None, list[R.Node]] = {}
        order: list[R.Node] = []
        for _, node, live in R.descend(conn, anchor):
            if not live and not hidden:
                continue
            self.children.setdefault(node.parent, []).append(node)
            order.append(node)
        self._height: dict[int, int] = {}
        for node in reversed(order):  # depth-first, so a node's children are already done
            self._height[node.id] = 1 + max(
                (self._height[k.id] for k in self.children.get(node.id, ())), default=0
            )

    def below(self, node: int | None) -> list[R.Node]:
        """The live children of a node, in insertion order."""
        return self.children.get(node, [])

    def height(self, node: int) -> int:
        """How many nodes the longest descent from here spans, counting this one."""
        return self._height[node]

    def nodes(self) -> list[R.Node]:
        return [n for kids in self.children.values() for n in kids]


type Rule = Callable[[Subtree, list[R.Node]], R.Node]


def longest(tree: Subtree, candidates: list[R.Node]) -> R.Node:
    """Deepest wins, ties go to insertion order.

    The one member of the family that needs nothing but the tree, which is why it is the
    first implementation and not why it is right.
    """
    return max(candidates, key=lambda n: (tree.height(n.id), -n.id))


def continuation(
    conn: sqlite3.Connection,
    node: int | None = None,
    rule: Rule = longest,
    hidden: bool = False,
) -> list[R.Node]:
    """The rest of a path below `node`, chosen a step at a time by `rule`.

    Live nodes only, so a node that is itself out of the live tree continues nowhere --
    unless `hidden`, which follows what has been set aside and is how such a node is reached
    at all.
    """
    return _continue(Subtree(conn, node, hidden), node, rule)


def _continue(tree: Subtree, node: int | None, rule: Rule) -> list[R.Node]:
    out: list[R.Node] = []
    while kids := tree.below(node):
        pick = rule(tree, kids)
        out.append(pick)
        node = pick.id
    return out


# ---- 1. a path -----------------------------------------------------------------------


def path(
    conn: sqlite3.Connection,
    node: int,
    rule: Rule | None = longest,
    hidden: bool = False,
) -> list[Segment[R.PathNode]]:
    """Root to a leaf through `node`, in segments, each carrying its nodes' marks.

    `rule` picks what comes below `node`. Pass `None` for the ancestry alone, which is what
    a surface holding its own path wants once it already knows the leaf.

    `hidden` carries the path on past the live leaf into what has been set aside, which is
    how a reader reaches a tail they hid in order to bring it back. **It appends and never
    chooses**: the live path is picked first and is the same path either way, so what the
    second pass adds begins where the first ran out. Nothing live lies below that point --
    a live leaf has no live children -- so the rule is never offered a live node and a
    hidden one together.

    A node that is itself hidden continues nowhere without this, which is why asking for the
    path *through* one shows it alone until the toggle is on.
    """
    leaf = node
    if rule is not None:
        if rest := continuation(conn, node, rule):
            leaf = rest[-1].id
        if hidden and (more := continuation(conn, leaf, rule, hidden=True)):
            leaf = more[-1].id
    marks = R.annotated_path(conn, leaf)
    spell = R.token_bytes(conn, (m.node.token_id for m in marks))
    return segments(marks, lambda m: spell[m.node.token_id])


# ---- 2. a ranking --------------------------------------------------------------------


def ranking(conn: sqlite3.Connection, node: int) -> list[R.RankedEdge]:
    """Every ranked edge at a node, in the order the surface shows them.

    Descending logprob, and source by source: a node several models have ranked holds
    several rankings, and one order over the union would sit rows side by side that were
    never alternatives to each other.
    """
    return sorted(
        R.ranking_with_children(conn, node),
        key=lambda r: (r.edge.source, -r.edge.logprob, r.edge.rank),
    )


# ---- 3. a branch subtree -------------------------------------------------------------


@dataclass(slots=True)
class Branch:
    """One preview line: where it parts from the line it hangs under, what it reads, and
    the lines that part from it."""

    parts_at: int  #: characters into the line above, at a segment boundary
    segments: list[Segment[R.Node]]
    branches: list[Branch]
    dropped: int  #: lines this one cannot show, which took their own alternatives with them


def branches(
    conn: sqlite3.Connection, node: int, budget: int, rule: Rule = longest
) -> list[Branch]:
    """The live subtree below `node` as preview lines, depth-first.

    Each line is one live child of a divergence followed by `rule` -- the same rule that
    selecting it would follow, so what it shows is a truthful prefix of what taking it
    gives. `budget` is a line's worth of characters, and a line always gets its first
    segment however wide that segment is.

    A line cut by the budget cannot say where the alternatives past the cut part from it,
    so they are counted rather than returned. So is a divergence inside a multi-token
    character: a segment cannot be split, and there is no column at which such a line
    begins. `dropped` is both, since what a reader is owed is how many are not there.
    """
    tree = Subtree(conn, node)
    spell = R.token_bytes(conn, (n.token_id for n in tree.nodes()))

    def draw(start: R.Node) -> tuple[Branch, list[tuple[R.Node, int]]]:
        run, forks = [start], []
        at: int | None = start.id
        while kids := tree.below(at):
            pick = rule(tree, kids)
            if others := [k for k in kids if k.id != pick.id]:
                forks.append((len(run), others))  # they part at this position in the run
            run.append(pick)
            at = pick.id

        cells = segments(run, lambda n: spell[n.token_id])
        boundary, taken, chars = {0: 0}, 0, 0
        for cell in cells:
            taken += len(cell.nodes)
            chars += len(cell.text)
            boundary[taken] = chars

        kept, width = [], 0
        for cell in cells:
            if kept and width + len(cell.text) > budget:
                break
            kept.append(cell)
            width += len(cell.text)

        shown: list[tuple[R.Node, int]] = []
        dropped = 0
        for position, others in forks:
            if position in boundary and boundary[position] <= width:
                shown.extend((o, boundary[position]) for o in others)
            else:
                dropped += len(others)
        return Branch(0, kept, [], dropped), shown

    top: list[Branch] = []
    stack = [(n, 0, top) for n in reversed(tree.below(node))]
    while stack:
        start, parts_at, into = stack.pop()
        branch, shown = draw(start)
        branch.parts_at = parts_at
        into.append(branch)
        for child, at in reversed(shown):
            stack.append((child, at, branch.branches))
    return top


# ---- naming a root -------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Label:
    """What a root opens with, and whether the tree parts where that stops."""

    segments: list[Segment[R.Node]]
    forked: bool  #: it stopped where the tree parts, rather than at a leaf or for room


def label(conn: sqlite3.Connection, node: int, budget: int) -> Label:
    """The run from `node` down to where it first parts, or to `budget` characters.

    This is not a fourth read. A list of roots is a point read that `docs/CORE.md` already
    answers, and what it cannot answer is what to call them; this is that, and it is bounded
    so that naming a root never costs what reading one does. Children and bytes are asked a
    node at a time, which is what keeps the walk proportional to the budget rather than to
    the tree: a root of a twelve-thousand-node trie is named from about twenty of them.

    It stops where the tree parts because that is the last text belonging to the root rather
    than to one continuation of it -- reading past a fork would follow whichever rule was
    live, and the rule is a parameter of every other read. `forked` says it was that stop
    and not one of the other two, since a caller marking a divergence must not mark a leaf.

    A segment is atomic and the first is always taken, as in `branches`, so a label can
    exceed the budget only by its own opening segment. The anchor is always taken and a root
    has no incoming edge, so a root cannot be the divergence and a label is never empty.
    """
    run, buf, forked = [R.get_node(conn, node)], R.node_bytes(conn, node), False
    while len(buf.decode("utf-8", "replace")) <= budget:
        live = [k for k in R.children(conn, run[-1].id) if not k.deleted]
        if len(live) != 1:
            forked = len(live) > 1
            break
        run.append(live[0])
        buf += R.node_bytes(conn, live[0].id)

    spell = R.token_bytes(conn, (n.token_id for n in run))
    kept, width = [], 0
    for cell in segments(run, lambda n: spell[n.token_id]):
        if kept and width + len(cell.text) > budget:
            return Label(kept, False)  # it stopped for room, whatever the tree does below
        kept.append(cell)
        width += len(cell.text)
    return Label(kept, forked)
