"""Spans and interned parameters -- the whole of the structural half.

A span is an authored or generated stretch. It holds its bytes, its provenance,
and one address naming where it continues from. That address is the only
structure there is: there are no runs, no pieces, and nothing to divide when a
branch lands in the middle of a span. `FORMAT.md` has the why, the alternatives
it was chosen over, and the invariants `validate.py` checks.

Four things here are easy to get wrong and worth stating at the top:

- **Text is `bytes`, everywhere in the core.** Every offset in the format is a
  byte offset, and `len` on a `str` counts characters -- so holding text as a
  `str` would silently make every offset and every parent address wrong the
  moment a non-ASCII character appeared. Decoding happens at the edges: on
  serialisation, and in whatever displays text.
- **A position is `(span, offset)`, and `None` is the root.** Not an absolute
  offset: sibling branches share those, so an offset alone cannot say which
  path it is on. A span is written once and never cut, so the pair survives
  every operation there is.
- **Absolute offsets are derived and stored nowhere.** An absolute offset is
  the sum of the offsets along a position's ancestry, which is what `absolute`
  computes. Anything that wrote one down would have to maintain it, and it
  would not survive export of a subtree.
- **Ids are derived, not stored.** The next id is one past the highest in use,
  which is safe only because nothing is ever removed from `spans` -- delete is
  soft. A vacuum that purged them would have to carry a high-water mark, which
  is one more reason for it to stay a bulk-store operation.
"""
from __future__ import annotations

import base64
import json
import os
import uuid
from dataclasses import dataclass, field
from typing import NamedTuple

from util.util import timestamp

FORMAT = 'token-loom/1.1'

# Provenance categories, and the axis is *where the bytes came from* -- not who
# typed them. `given` was `human` until the name proved too narrow: the human
# stays the authority behind such a span, but the bytes may be a paste, a file,
# or another model's output, none of which anyone authored here.
#
# Agency -- what initiated a span -- is deliberately a separate axis, not a
# fourth value here.
GIVEN = 'given'
SAMPLED = 'sampled'
COUNTERFACTUAL = 'counterfactual'
KINDS = (GIVEN, SAMPLED, COUNTERFACTUAL)


def encode_text(raw: bytes | None):
    """A span's bytes, as JSON can hold them.

    Almost always a plain string, which is what keeps the file readable. But a
    token can be a fragment of a character -- measured, not assumed: Qwen2.5
    tokenises a single alchemical symbol into three tokens, none of them valid
    UTF-8 alone -- so a span cut at a length limit can end mid-character and
    have no string form at all.

    That case falls back to `{"b64": ...}`. The alternative was dropping the
    trailing partial token, which would have made the tree quietly disagree
    with what the model emitted -- the one thing every other decision here is
    arranged to prevent. Being unreadable by eye costs nothing in exchange,
    since the bytes in question are half a character.
    """
    if raw is None:
        return None
    try:
        return raw.decode('utf-8')
    except UnicodeDecodeError:
        return {'b64': base64.b64encode(raw).decode('ascii')}


def decode_text(value) -> bytes | None:
    if value is None:
        return None
    if isinstance(value, dict):
        return base64.b64decode(value['b64'])
    return value.encode('utf-8')


def char_boundary(data: bytes, index: int) -> int:
    """The first character boundary at or after `index`.

    Byte offsets address token boundaries, and token boundaries are not always
    character boundaries -- so a slice start computed by subtracting a byte
    length can land inside a character. Sending that to a model means decoding
    it, which is where the slice would otherwise fail.
    """
    while index < len(data) and 0x80 <= data[index] < 0xC0:
        index += 1
    return index


class Position(NamedTuple):
    """A point in the tree: a span, and a byte offset within it.

    `None` in place of a Position is the root -- the point before any span,
    where an initial prompt goes. Several spans may sit there, which is how
    several initial prompts coexist without an empty node to hang them off.
    """
    span: str
    offset: int


def pos_json(pos: Position | None):
    return None if pos is None else [pos.span, pos.offset]


def pos_from_json(value) -> Position | None:
    return None if value is None else Position(value[0], value[1])


@dataclass
class Span:
    """An authored or generated stretch, and the conditions that produced it.

    Provenance -- including `parent`, which is where the structure lives -- is
    written once. The byte record is empty at creation and filled in when
    generation completes; filled in, never overwritten. A span with no `text`
    is in flight.

    Termination reason is deliberately absent: it lives in the bulk store, so
    that finishing a generation never has to reopen this record.
    """
    id: str
    kind: str
    parent: Position | None = None   # None is the root
    text: bytes | None = None
    created: str = ''
    # sampled
    params: str | None = None        # key into the intern table
    seed: int | None = None
    batch: str | None = None
    index: int | None = None         # position within the batch
    slice_start: Position | None = None
    # counterfactual
    origin: dict | None = None       # {span, index, token_id}

    @property
    def complete(self) -> bool:
        return self.text is not None

    @property
    def length(self) -> int:
        return len(self.text) if self.text is not None else 0

    def to_json(self) -> dict:
        out = {'kind': self.kind, 'parent': pos_json(self.parent),
               'text': encode_text(self.text), 'created': self.created}
        for name in ('params', 'seed', 'batch', 'index', 'origin'):
            value = getattr(self, name)
            if value is not None:
                out[name] = value
        if self.slice_start is not None:
            out['slice_start'] = pos_json(self.slice_start)
        return out

    @classmethod
    def from_json(cls, id: str, d: dict) -> Span:
        """`parent` is read as a required key, and that is load-bearing.

        Every span written by this format carries it -- a root carries it as
        `null` -- so nothing valid is refused. What it refuses is a file from
        the shape this replaced, where structure lived in runs and pieces and a
        span had no parent at all. Read with `.get()`, every one of those spans
        would come back as a root: no error, no missing field, a tree that
        loads and validates and is not the tree that was written.

        The marker alone could not catch it. That shape also called itself
        `token-loom/1` -- it never went live, so the number was reclaimed
        rather than spent on it -- and this format called itself the same until
        the `given` rename moved it to `1.1`. The marker now happens to differ,
        which is luck rather than a defence: this check is structural, holds
        whatever a file claims about itself, and reads the one key that shape
        lacks.
        """
        if 'parent' not in d:
            raise ValueError(
                f'span {id} has no `parent`, so this is not a {FORMAT} tree. '
                f'A span from the run-and-piece shape kept its structure '
                f'elsewhere and would load silently as a root.')
        return cls(id=id, kind=d['kind'], parent=pos_from_json(d['parent']),
                   text=decode_text(d.get('text')), created=d.get('created', ''),
                   params=d.get('params'), seed=d.get('seed'),
                   batch=d.get('batch'), index=d.get('index'),
                   slice_start=pos_from_json(d.get('slice_start')),
                   origin=d.get('origin'))


def next_id(existing, prefix: str) -> str:
    """One past the highest numeric suffix in use. See the module docstring."""
    highest = -1
    for key in existing:
        if key.startswith(prefix):
            try:
                highest = max(highest, int(key[len(prefix):]))
            except ValueError:
                continue
    return f'{prefix}{highest + 1}'


def id_order(span_id: str) -> tuple:
    """Sort key putting s2 before s10, and anything odd last but stable.

    Creation order, since ids are minted one past the highest in use -- which
    is what a fork chip counts through, and the only order siblings have.
    """
    try:
        return (0, int(span_id[1:]))
    except ValueError:
        return (1, span_id)


def pretty(obj, indent: int = 0, width: int = 84) -> str:
    """JSON that stays openable by hand: nested where it must be, inline where
    it fits.

    `json.dump(indent=2)` puts every parent address on its own pair of lines,
    which turns a five-span tree into a hundred. The tree file being readable
    is a stated goal of the format, and with spans holding their own text and
    their own attachment it reads as prose again -- that is worth not throwing
    away at the serialiser.
    """
    compact = json.dumps(obj, ensure_ascii=False)
    if indent + len(compact) <= width:
        return compact
    pad = ' ' * indent
    if isinstance(obj, dict) and obj:
        items = [f'{json.dumps(k, ensure_ascii=False)}: {pretty(v, indent + 2, width)}'
                 for k, v in obj.items()]
    elif isinstance(obj, list) and obj:
        items = [pretty(v, indent + 2, width) for v in obj]
    else:
        return compact
    body = (',\n' + pad + '  ').join(items)
    open_, close = ('{', '}') if isinstance(obj, dict) else ('[', ']')
    return f'{open_}\n{pad}  {body}\n{pad}{close}'


@dataclass
class Tree:
    """The tree file: spans, and the interned parameter table.

    That is the whole of it. There is no separate structure to keep in step
    with the spans, which is why most of what a validator over this data would
    otherwise check is not a question that can be asked here at all.
    """
    tree_id: str
    base_seed: int
    spans: dict[str, Span] = field(default_factory=dict)
    params: dict[str, dict] = field(default_factory=dict)
    selected: Position | None = None
    deleted: list[Position] = field(default_factory=list)
    format: str = FORMAT
    # derived, rebuilt on demand; never serialised
    _children: dict | None = field(default=None, init=False, repr=False,
                                   compare=False)

    # -- construction ----------------------------------------------------

    @classmethod
    def empty(cls, base_seed: int | None = None) -> Tree:
        """A tree with nothing in it at all.

        `selected` is None, which is the root -- a tree always has a position,
        even before it has a span, and that position is where the first prompt
        goes. It is the only special case in the addressing.
        """
        if base_seed is None:
            base_seed = uuid.uuid4().int % 1_000_000
        return cls(tree_id=uuid.uuid4().hex, base_seed=base_seed)

    def new_span_id(self) -> str:
        return next_id(self.spans, 's')

    def add(self, span: Span) -> Span:
        """The one way a span enters the tree, so the child index cannot be
        left stale by a caller that forgot."""
        self.spans[span.id] = span
        self._children = None
        return span

    def intern(self, settings: dict) -> str:
        """Return the key for a parameter set, minting one if it is new.

        Generic over parameter set rather than specific to generation
        settings, per the roadmap: anything that gives rise to a span interns
        the same way.
        """
        fingerprint = json.dumps(settings, sort_keys=True)
        for key, existing in self.params.items():
            if json.dumps(existing, sort_keys=True) == fingerprint:
                return key
        key = next_id(self.params, 'p')
        self.params[key] = dict(settings)
        return key

    # -- structure -------------------------------------------------------

    def children_of(self, span_id: str | None) -> list[tuple[int, str]]:
        """What branches from a span, as `(offset, child)` pairs.

        `None` asks for the roots. This is the read the whole structure turns
        on, so it goes through an index built once and dropped whenever a span
        is added -- exact match on a point, where an overlapping-range design
        would have needed a scan. Order is by offset, then by creation, which
        is what a fork chip counts through.
        """
        if self._children is None:
            index: dict[str | None, list[tuple[int, str]]] = {}
            for span in self.spans.values():
                key = span.parent.span if span.parent else None
                offset = span.parent.offset if span.parent else 0
                index.setdefault(key, []).append((offset, span.id))
            for entries in index.values():
                entries.sort(key=lambda entry: (entry[0], id_order(entry[1])))
            self._children = index
        return self._children.get(span_id, [])

    def tip(self, span_id: str) -> Position:
        return Position(span_id, self.spans[span_id].length)

    def ancestry(self, pos: Position | None) -> list[Position]:
        """The chain of positions from the root down to `pos`, root first.

        Each entry names a span and how much of it lies on the path -- so the
        chain is both the route and the recipe for the text along it.
        """
        chain: list[Position] = []
        while pos is not None:
            chain.append(pos)
            pos = self.spans[pos.span].parent
        chain.reverse()
        return chain

    def path_bytes(self, pos: Position | None) -> bytes:
        """Every byte from the root to this position, along its path.

        Returns bytes, not str. A parent offset is a token boundary, and
        byte-level BPE can put one inside a character -- so a fragment of a
        path is not guaranteed to decode even when the whole of it does.
        Decode at the point of display, not here.
        """
        return b''.join((self.spans[p.span].text or b'')[:p.offset]
                        for p in self.ancestry(pos))

    def absolute(self, pos: Position | None) -> int:
        """The root-relative byte offset of a position.

        Derived, never stored: it is the sum of the offsets along the ancestry,
        which is the whole of the arithmetic. Useful for display and for slice
        bounds; meaningless in an exported subtree, which is why the format
        addresses by span instead.
        """
        return sum(p.offset for p in self.ancestry(pos))

    # -- deletion --------------------------------------------------------

    def live(self) -> dict[str, int]:
        """Reachable spans, each mapped to how many of its bytes are reached.

        A span missing from the result is unreachable entirely. One present
        with a value below its length was cut by a deletion address: its bytes
        are all still recorded, the tree simply stops reaching them, and
        nothing continues past the cut.

        That the live extent of a span is a prefix from byte 0 is not an
        invariant anything has to check. It is the shape of the answer, and
        there is no other shape available.
        """
        cut: dict[str, int] = {}
        for pos in self.deleted:
            if pos.span in self.spans:
                cut[pos.span] = min(cut.get(pos.span, pos.offset), pos.offset)

        reach: dict[str, int] = {}
        stack: list[str | None] = [None]
        while stack:
            parent = stack.pop()
            limit = None if parent is None else reach[parent]
            for offset, child in self.children_of(parent):
                if limit is not None:
                    # a child anchored at or past a cut hangs off dead bytes
                    if offset > limit or (offset == limit and parent in cut):
                        continue
                if cut.get(child) == 0:
                    continue          # the span itself was deleted whole
                reach[child] = cut.get(child, self.spans[child].length)
                stack.append(child)
        return reach

    def resolves(self, pos: Position | None) -> bool:
        """Is this position still on a reachable path?

        An address always resolves in the sense that it names bytes that were
        written; this asks the narrower question the UI needs, which is whether
        the tree still reaches them.
        """
        if pos is None:
            return True
        reach = self.live()
        return pos.span in reach and pos.offset <= reach[pos.span]

    # -- serialisation ---------------------------------------------------

    def to_json(self) -> dict:
        return {
            'format': self.format,
            'tree_id': self.tree_id,
            'base_seed': self.base_seed,
            'spans': {k: v.to_json() for k, v in self.spans.items()},
            'params': self.params,
            'selected': pos_json(self.selected),
            'deleted': [pos_json(p) for p in self.deleted],
        }

    @classmethod
    def from_json(cls, d: dict) -> Tree:
        if d.get('format') != FORMAT:
            raise ValueError(f"not {FORMAT}: {d.get('format')!r}")
        return cls(
            tree_id=d['tree_id'], base_seed=d['base_seed'],
            spans={k: Span.from_json(k, v) for k, v in d['spans'].items()},
            params=d.get('params', {}),
            selected=pos_from_json(d.get('selected')),
            deleted=[pos_from_json(p) for p in d.get('deleted', [])],
            format=d['format'],
        )

    def save(self, path: str) -> None:
        """Write via a temporary file and rename, so a crash cannot truncate.

        The tree file is rewritten whole on every save and is the only record
        of structure; a half-written one would lose the tree, not a save.

        Serialised before anything is opened, so that a span the format cannot
        represent -- see the open question in FORMAT.md -- fails without
        leaving a stray temporary file behind.
        """
        body = pretty(self.to_json()) + '\n'
        os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
        tmp = f'{path}.tmp'
        with open(tmp, 'w') as f:
            f.write(body)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)

    @classmethod
    def load(cls, path: str) -> Tree:
        with open(path) as f:
            return cls.from_json(json.load(f))


def now() -> str:
    return timestamp()
