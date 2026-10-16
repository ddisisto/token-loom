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


# ---- the reference arm ----------------------------------------------------------------

#: Two logprobs within this of each other are one row, as everywhere a ranking is read: a
#: backend does not present near-ties in a reproducible order, so an exact comparison would
#: call about half of them a preference.
TIE = 1e-9


#: Why an arm goes no further, and what each of them is worth buying.
#:
#: **Only one of these is a price.** An arm that stopped is not an arm the model has no more
#: of: three of the four are the record declining to answer rather than running out, and a
#: greedy roll at the position merges onto what is already there and writes nothing. A caller
#: that read `full` as *done* and everything else as *for sale* would charge for two of them.
FULL = "full"  #: it filled the room it was given, and a larger limit would give more
ENDS = "ends"  #: the record has no more, and a roll extends it -- the one that costs
CLOSED = "closed"  #: the top row continues and was set aside; what reaches it is `undelete`
DECLINES = "declines"  #: two sources ranked here, so there is no one top row to follow


@dataclass(frozen=True, slots=True)
class Reference:
    """How far the model's own continuation from a node is already written down.

    `docs/SPINE.md` has the reference arm as the model left alone from a position, and a
    greedy rollout is how one is made. What is read here is the part of that rollout the
    tree already holds -- the descent that never leaves the top row -- which costs no
    inference and is the same nodes a rollout would merge onto.

    `why` is which of the four above ended it, and it is what a caller checks before
    spending rather than the length, since three of the four are not for sale.
    """

    nodes: list[R.Node]
    cells: list[Segment[R.Node]]
    why: str


def _onward(conn: sqlite3.Connection, node: int, hidden: bool) -> tuple[R.Node | None, str]:
    """The child on the top row at `node`, or None and why the record does not have one.

    Follows the refusals a ranking is read under elsewhere rather than re-deciding them: a
    position two sources ranked has no single top row, and a position nothing ranked has
    none at all. A tie at the top is several rows, and the child taken is the first of them
    in insertion order -- the same tie-break the continuation rules use, and for the same
    reason, that the record stores no order to prefer.

    **The two refusals are not the same answer.** Two sources is a position this read will
    never follow, however much is spent on it; nothing ranked is a position a roll would
    both rank and continue. Only the second is somewhere to spend, which is why they are
    told apart here rather than folded into one absence.

    A set-aside child is told apart from no child for the same reason and the opposite one:
    the record has the continuation and the reader put it away, so what reaches it is an
    `undelete` and never a rollout -- one would merge onto the node still carrying the flag
    and write nothing at all. A tie where one of the best children is live and another is
    not is not closed: the live one is taken and the arm carries on.
    """
    edges = R.ranking(conn, node)
    sources = {e.source for e in edges}
    if len(sources) > 1:
        return None, DECLINES
    values = [e.logprob for e in edges if e.logprob is not None]
    if not sources or not values:
        return None, ENDS
    source, top = sources.pop(), max(values)
    best = {e.token_id for e in edges if e.logprob is not None and e.logprob >= top - TIE}
    shut = False
    for kid in R.children(conn, node):
        if kid.source == source and kid.token_id in best:
            if hidden or not kid.deleted:
                return kid, ""
            shut = True
    return None, CLOSED if shut else ENDS


def reference(
    conn: sqlite3.Connection, node: int, limit: int, hidden: bool = False
) -> Reference:
    """The recorded reference arm below `node`, up to `limit` nodes.

    **This is the continuation family's shape and is deliberately not one of its rules.** A
    `Rule` is handed the candidates and must pick one of them; this one has to be able to
    say that none of them is the model's, which is the whole of what it reports. Widening
    the contract so a rule may decline would make every other rule answer a question it
    does not have.

    It is also the check that keeps a hover from spending twice. `docs/SPINE.md` has a row
    that already carries a stub left unrolled, and a greedy rollout merges onto whatever a
    previous one wrote -- so what is already here is what a second rollout would produce,
    and reading it is how that is known without asking.
    """
    out: list[R.Node] = []
    at = node
    # An arm that never stops is one that filled the room it was given, which is the only
    # one of the four nothing reports: `_onward` says why it declined and says nothing when
    # it did not.
    why = FULL
    while len(out) < limit:
        kid, stopped = _onward(conn, at, hidden)
        if kid is None:
            why = stopped
            break
        out.append(kid)
        at = kid.id
    spell = R.token_bytes(conn, (n.token_id for n in out))
    return Reference(
        nodes=out,
        cells=segments(out, lambda n: spell[n.token_id]),
        why=why,
    )


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


def shut(conn: sqlite3.Connection, node: int) -> bool:
    """Whether the live tree stops at `node` because what is below it was set aside.

    The same question `reference` answers about the top row, asked about a whole position:
    a path that ran out and a path a reader closed look identical once the text stops, and
    only one of them is somewhere the model has not been asked yet. **It is the difference
    between *nothing has run here* and *this was shut deliberately***, which nothing on the
    page could say with the toggle off.

    A node carrying children of which none is live is closed whichever of them it was, so
    this reports the state and names no node: what reaches a set-aside arm is the toggle,
    and the boundary drawn inside it is what carries the `undelete`.
    """
    kids = R.children(conn, node)
    return bool(kids) and all(kid.deleted for kid in kids)


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
    with every act.
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

    **The order is the surface's and not the record's.** A ranking is a set, so sorting is
    what a reader does with one; the token breaks a tie so that two rows of equal value
    come back the same way twice.
    """
    return sorted(
        R.ranking_with_children(conn, node),
        key=lambda r: (r.edge.source, -r.edge.logprob, r.edge.token_id),
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


# ---- naming a waypoint ---------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Waypoint:
    """Where a waypoint stands, and the text a list of them is drawn from."""

    node: int
    root: int
    under: int | None  #: the nearest waypoint above it, of those asked about together
    live: bool  #: neither it nor anything above it is set aside
    lead: str  #: the text before its segment, cut from the front to the budget
    token: str  #: its segment's text
    trail: str  #: the text after it, to where the tree parts or to the budget
    parts: bool  #: the trail stopped where the tree parts, rather than at a leaf or for room


def waypoints(
    conn: sqlite3.Connection, nodes: Sequence[int], budget: int
) -> dict[int, Waypoint | None]:
    """Each of `nodes`, placed among the others, or `None` for one the tree does not hold.

    Like `label`, this names what a list holds rather than reading a path: one ancestry
    walk per node, so it costs what the waypoints' depths add up to. `under` is reckoned
    only among the nodes asked about together, which is what a list nesting them wants.

    A waypoint is named by the text either side of it, with its own segment apart so the
    token it marks can be picked out. The lead is cut from its front. The trail is a
    root's label begun below it, so it stops where the tree parts for the reason a label
    does: past that point it would follow whichever rule was live.
    """
    asked = set(nodes)
    out: dict[int, Waypoint | None] = {}
    for node in nodes:
        if not R.node_exists(conn, node):
            out[node] = None
            continue
        line = R.path_nodes(conn, node)
        # A character is at most four bytes and a token at least one, so this many nodes
        # spell at least the budget whatever they are.
        tail = line[-(budget * 4 + 1):]
        spell = R.token_bytes(conn, (n.token_id for n in tail))
        cells = segments(tail, lambda n, spell=spell: spell[n.token_id])
        if len(tail) < len(line):
            cells = cells[1:]  # it may begin inside a character the cut went through
        kept, width = [], 0
        for cell in reversed(cells[:-1]):
            if width + len(cell.text) > budget:
                break
            kept.append(cell.text)
            width += len(cell.text)
        kids = [k for k in R.children(conn, node) if not k.deleted]
        after = label(conn, kids[0].id, budget) if len(kids) == 1 else None
        out[node] = Waypoint(
            node=node,
            root=line[0].id,
            under=next((n.id for n in reversed(line[:-1]) if n.id in asked), None),
            live=R.path_liveness(line)[-1],
            lead="".join(reversed(kept)),
            token=cells[-1].text if cells else "",
            trail="".join(cell.text for cell in after.segments) if after else "",
            parts=after.forked if after else len(kids) > 1,
        )
    return out


# ---- the map -------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Strand:
    """A maximal run of nodes each with one child: opened at a root or at a child of a fork,
    and closed at a fork or a leaf. It is the unit the map draws, and what it carries is what
    placing one needs and nothing about how it is placed.

    Which strands are hair is not here. It is a cut the reader moves, so the read says what a
    cut is made from -- whether it is a leaf, how long, whether a hover's stub -- and the page
    makes it.
    """

    head: int
    tail: int
    up: int | None  #: the head of the strand whose tail this one hangs from
    depth: int  #: nodes above the head
    length: int  #: nodes in it
    weight: int  #: nodes at or below its head, of those the read holds
    logprob: float | None  #: the head's, in the ranking at the fork it leaves
    leaf: bool
    stub: bool  #: a leaf drawn at temperature 0 past its head, as a hover's stub is
    aside: int | None  #: how many of its nodes come before what was set aside, where any was


def _greedy(writings: list[R.Writing] | None) -> bool:
    return bool(writings) and all(
        w.op == "generate" and (w.params or {}).get("temperature") == 0 for w in writings
    )


def strands(conn: sqlite3.Connection, root: int, hidden: bool = False) -> list[Strand]:
    """The tree under `root` as strands, depth-first, a strand before those below it and
    siblings in id order.

    Like `label`, this names what the tree holds rather than reading a path, and unlike it,
    it is the whole of one root: one descent, which carries the set-aside nodes whatever
    `hidden` says because the acts that wrote the live ones may have their tips among them.
    `hidden` decides what is drawn, as it does for every read the page makes, and a root that
    is itself set aside holds nothing until it is on.

    **A stub is `docs/SPINE.md`'s**, read off the acts: every act that wrote a node past the
    head drew at temperature 0. The head is left out because a hover's stub opens on the row
    it was taken from, which a `realise` wrote, and a leaf of one node is not a stub at all.
    """
    top = R.get_node(conn, root)
    if top.parent is not None:
        raise ValueError(f"node {root} is not a root")
    if top.deleted and not hidden:
        return []
    parents: dict[int, int | None] = {top.id: None}
    live: dict[int, bool] = {top.id: not top.deleted}
    kids: dict[int, list[int]] = {}
    for _, node, alive in R.descend(conn, root):  # siblings arrive in id order
        parents[node.id] = node.parent
        live[node.id] = alive
        if hidden or alive:
            kids.setdefault(node.parent, []).append(node.id)
    wrote = R.writings(conn, parents)

    runs: list[tuple[list[int], int | None, int]] = []  # nodes, the strand above, depth
    stack: list[tuple[int, int | None, int]] = [(top.id, None, 0)]
    while stack:
        head, up, depth = stack.pop()
        run = [head]
        while len(below := kids.get(run[-1], ())) == 1:
            run.append(below[0])
        runs.append((run, up, depth))
        for kid in reversed(kids.get(run[-1], ())):
            stack.append((kid, head, depth + len(run)))

    weight: dict[int, int] = {}
    for run, up, _ in reversed(runs):  # a strand comes before every strand below it
        weight[run[0]] = weight.get(run[0], 0) + len(run)
        if up is not None:
            weight[up] = weight.get(up, 0) + weight[run[0]]
    ranked = R.logprobs(conn, (run[0] for run, up, _ in runs if up is not None))

    out = []
    for run, up, depth in runs:
        leaf = not kids.get(run[-1])
        cut = next((i for i, n in enumerate(run) if not live[n]), None)
        out.append(Strand(
            head=run[0],
            tail=run[-1],
            up=up,
            depth=depth,
            length=len(run),
            weight=weight[run[0]],
            logprob=ranked.get(run[0]),
            leaf=leaf,
            stub=leaf and len(run) > 1 and all(_greedy(wrote.get(n)) for n in run[1:]),
            aside=cut,
        ))
    return out


def placed(
    conn: sqlite3.Connection, strands: list[Strand], nodes: Sequence[int]
) -> dict[int, tuple[int, int] | None]:
    """Where each of `nodes` stands among `strands`: the head of the strand holding it and
    its depth, or None for one they do not hold -- another root's, one the tree does not
    hold, or one set aside while the map leaves that out. One ancestry walk per node."""
    by = {s.head: s for s in strands}
    out: dict[int, tuple[int, int] | None] = {}
    for node in nodes:
        if not R.node_exists(conn, node):
            out[node] = None
            continue
        line = R.path_nodes(conn, node)
        depth = len(line) - 1
        s = next((by[n.id] for n in reversed(line) if n.id in by), None)
        out[node] = (s.head, depth) if s and depth < s.depth + s.length else None
    return out
