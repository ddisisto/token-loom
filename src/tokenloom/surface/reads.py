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

    What it folds is every downward measure `docs/SURFACE.md` names, in one reversed pass,
    because they all want the same walk and a node's children are done before it is. Height
    was the first because `longest` needed it; the rest cost the pass nothing more.
    """

    def __init__(
        self,
        conn: sqlite3.Connection,
        anchor: int | None = None,
        hidden: bool = False,
        rooted: bool = False,
    ) -> None:
        self.anchor = anchor
        self.children: dict[int | None, list[R.Node]] = {}
        order: list[R.Node] = []
        if rooted and anchor is not None:
            # The anchor is in the tree rather than above it, which is what a measure drawn
            # *at* a root needs and what continuing *from* a node does not. It goes in first
            # so the reversed fold reaches it last, after everything below it.
            top = R.get_node(conn, anchor)
            if hidden or not top.deleted:
                self.children.setdefault(top.parent, []).append(top)
                order.append(top)
        for _, node, live in R.descend(conn, anchor):
            if not live and not hidden:
                continue
            self.children.setdefault(node.parent, []).append(node)
            order.append(node)
        self._height: dict[int, int] = {}
        self._size: dict[int, int] = {}
        self._forks: dict[int, int] = {}
        self._run: dict[int, int] = {}
        for node in reversed(order):  # depth-first, so a node's children are already done
            kids = self.children.get(node.id, ())
            self._height[node.id] = 1 + max((self._height[k.id] for k in kids), default=0)
            self._size[node.id] = 1 + sum(self._size[k.id] for k in kids)
            self._forks[node.id] = int(len(kids) > 1) + sum(self._forks[k.id] for k in kids)
            self._run[node.id] = 1 + (self._run[kids[0].id] if len(kids) == 1 else 0)

    def below(self, node: int | None) -> list[R.Node]:
        """The live children of a node, in insertion order."""
        return self.children.get(node, [])

    def height(self, node: int) -> int:
        """How many nodes the longest descent from here spans, counting this one."""
        return self._height[node]

    def holds(self, node: int) -> bool:
        """Whether this descent reached a node. What it did not reach it says nothing
        about, which is not the same as saying nothing is there."""
        return node in self._height

    def size(self, node: int) -> int:
        """How many nodes lie at or below this one. What has been explored under it, which
        is a fact about the reader's session and not about the model."""
        return self._size[node]

    def forks(self, node: int) -> int:
        """How many nodes at or below this one have more than one child.

        Nodes and not branches: a node with four children is one place a reader chose, not
        three. What a slate of previews would hold is a different count and wants its own
        measure, which `docs/SURFACE.md` leaves open.
        """
        return self._forks[node]

    def run(self, node: int) -> int:
        """How many nodes can be taken from here before a choice, counting this one.

        One at a leaf and one at a fork -- both are places the walking stops -- so this is
        the length of the corridor and not of what is past it. It is the measure behind
        *how far can I move before a decision*, which subtree size cannot answer: size says
        how much is below, never whether the next stretch is corridor or junction.
        """
        return self._run[node]

    def nodes(self) -> list[R.Node]:
        return [n for kids in self.children.values() for n in kids]


type Rule = Callable[[Subtree, list[R.Node]], R.Node]

type Scalar = Callable[[Subtree, int], int]

#: Every measure of the tree below a node that `docs/SURFACE.md` settles, by the name a
#: client asks for it under. A measure of the *substance* below -- what vocabulary is down
#: there -- is not here: it is open, and it does not fold over this pass.
DOWNWARD: dict[str, Scalar] = {
    "height": Subtree.height,
    "size": Subtree.size,
    "forks": Subtree.forks,
    "run": Subtree.run,
}


def argmax(measure: Scalar) -> Rule:
    """The rule a downward measure makes: the child with the most of it, ties to insertion
    order.

    This is the whole of the relation between rules and overlays. `longest` was written as
    a function before it was understood as one of these, and every downward measure makes a
    rule the same way -- which is why `RULES` is generated rather than listed. It does not
    run the other way: a rule may read insertion order or what the reader last took, and
    neither is a quantity worth drawing along a path.
    """

    def rule(tree: Subtree, candidates: list[R.Node]) -> R.Node:
        return max(candidates, key=lambda n: (measure(tree, n.id), -n.id))

    return rule


#: The family `docs/SURFACE.md` names, as far as it is built, one member per measure. Ties
#: bite for all of them and are insertion order.
RULES: dict[str, Rule] = {name: argmax(measure) for name, measure in DOWNWARD.items()}

#: `longest` is the height rule under the name that is older than the measure it turned out
#: to be, and the one `docs/SURFACE.md`'s open question argues about.
RULES["longest"] = RULES.pop("height")

longest: Rule = RULES["longest"]


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


def beneath(
    conn: sqlite3.Connection, cells: list[Segment[R.PathNode]], hidden: bool = False
) -> dict[int, dict[str, int]]:
    """What the tree below each node of a path holds, by measure.

    **The descent is anchored at the path's own root and not at the node the read was asked
    about.** A measure drawn along a whole path has to reach the ancestry, and what lies
    below an ancestor is where the tree widened -- which is the question a reader asks of the
    part they have already read. Where the reader is reading a root that is the descent the
    rule made anyway; where they are not it is a larger one, which is why this is asked for.

    `hidden` counts what has been set aside, and it follows the page's toggle rather than
    the rule's liveness. `docs/SURFACE.md` has why: a rule handed a live child and a hidden
    one would be choosing between them, while a measure only reports, so the two disagree
    wherever what is hidden is shown and the disagreement is what shows a reader what they
    pruned.

    One descent whatever the path's length, and none at all unless a measure is wanted. It
    is anchored at the path's own root and holds it, which is what `rooted` is for: a
    `Subtree` otherwise holds what is *below* its anchor, and a path's first node is a root,
    which would then be the one node on the path with no value.

    **It is the one read here that costs more than the path it decorates.** Over a 266-node
    path of `data/continuations`, `/path` answers in 5.4 ms, the ranking overlay adds 4.3,
    and this adds 16.5 -- one descent of 2,953 nodes and the fold over them. Anchoring above
    the roots instead would answer as well and descend all 13,595 to do it, which measured
    at 88 ms for the same call. What it cannot be is cached: what lies below a node changes
    with every act, which is why `docs/NEXT.md` puts it with liveness and not with the
    spellings.
    """
    if not cells:
        return {}
    tree = Subtree(conn, cells[0].nodes[0].node.id, hidden, rooted=True)
    return {
        mark.node.id: {name: read(tree, mark.node.id) for name, read in DOWNWARD.items()}
        for cell in cells
        for mark in cell.nodes
        if tree.holds(mark.node.id)
    }


def overlays(
    conn: sqlite3.Connection, cells: list[Segment[R.PathNode]]
) -> dict[int, list[R.Spread]]:
    """What the ranking each node of a path stood in says about that position.

    **It is the node's *parent's* ranking.** A node's own ranked edges are the alternatives
    for what follows it, which is the same reason `docs/SURFACE.md` has selecting a token
    ask about the ranking above. A root stood in none and is absent.

    Keyed by the node and not by the parent, because what a column draws is the position the
    node occupies and the parent is only where the answer was kept. It decorates a path the
    descent has already produced rather than joining its recursion, so it is one query
    whatever the path's length -- and it is asked for, so a column drawing no overlay pays
    for none of this.
    """
    above = {
        mark.node.id: mark.node.parent
        for cell in cells
        for mark in cell.nodes
        if mark.node.parent is not None
    }
    held = R.spreads(conn, above.values())
    return {node: held[parent] for node, parent in above.items() if parent in held}


# ---- 2. a ranking --------------------------------------------------------------------


def under(
    conn: sqlite3.Connection, node: int, hidden: bool = False
) -> dict[int, dict[str, int]]:
    """What the tree below each child of a node holds, by measure.

    `beneath` is the downward family read along a path; this is the same family read across
    the alternatives at one position. They are one quantity on two axes, which is what
    `docs/SURFACE.md` means by an overlay and a ranking being the same thing transposed: a
    band draws a measure down the page and this draws it across the rows, and a reader
    comparing the two is comparing a subtree against its siblings rather than against its
    ancestors.

    Only the children, because that is what a ranking's rows realise -- a row carries the
    node that took it and that node hangs directly here. The descent that answers them is
    the one below the node, which is bounded by exactly the subtree the rows partition.

    `hidden` follows the page's toggle and not the rule's liveness, for the reason
    `beneath` does: an arm the reader set aside weighs nothing while it is hidden and its
    own size while it is shown, and that disagreement is what shows a reader what they
    pruned.
    """
    tree = Subtree(conn, node, hidden)
    return {
        kid.id: {name: read(tree, kid.id) for name, read in DOWNWARD.items()}
        for kid in tree.below(node)
    }


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
