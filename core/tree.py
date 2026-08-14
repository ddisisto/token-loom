"""Runs, spans and interned parameters -- the structural half of the format.

Spans own the bytes. Runs own no bytes at all: a run is an ordered list of
*pieces*, each naming a half-open range of a span. Splitting a run is therefore
arithmetic on integers and can never open a record. `PHASE-1.md` has the why,
the alternatives it was chosen over, and the invariants `validate.py` checks.

Four things here are easy to get wrong and worth stating at the top:

- **Text is `bytes`, everywhere in the core.** Every offset in the format is a
  byte offset, and `len` on a `str` counts characters -- so holding text as a
  `str` would silently make every extent, piece range and run start wrong the
  moment a non-ASCII character appeared. Decoding happens at the edges: on
  serialisation, and in whatever displays a run.
- **Piece offsets are span-relative**, always. A piece names a range *of a
  span*; its position within the run is implied by accumulation.
- **A piece is a half-open `[start, end)`**, an end rather than a length.
- **Ids are derived, not stored.** The next id is one past the highest in use,
  which is safe only because nothing is ever removed from `runs` or `spans` --
  delete is soft. A vacuum that purged them would have to carry a high-water
  mark, which is one more reason for it to stay a bulk-store operation.
"""
from __future__ import annotations

import json
import os
import uuid
from dataclasses import dataclass, field
from typing import Iterator, NamedTuple

from util.util import timestamp

FORMAT = 'token-loom/1'

# provenance categories. Agency -- what initiated a span -- is deliberately a
# separate axis, not a fourth value here.
HUMAN = 'human'
SAMPLED = 'sampled'
COUNTERFACTUAL = 'counterfactual'
KINDS = (HUMAN, SAMPLED, COUNTERFACTUAL)


class Piece(NamedTuple):
    """A half-open range of a span. Offsets are span-relative, and bytes.

    A zero-length piece is legal and means exactly one thing: a span with no
    bytes -- one in flight, or one aborted before its first token arrived --
    joined to the run it landed in. Completion widens it in place.
    """
    span: str
    start: int
    end: int

    @property
    def length(self) -> int:
        return self.end - self.start


class Position(NamedTuple):
    """A point in the tree: a run, and a byte offset within it.

    An offset alone is not a position. Sibling branches start at the same
    absolute offset, so the path is the other half of the address -- which is
    also why durable references store the offset and look the run up, rather
    than the reverse.
    """
    run: str
    offset: int


@dataclass
class Span:
    """An authored or generated stretch, and the conditions that produced it.

    Provenance is written once. The byte record -- `text` and `end` -- is empty
    at creation and filled in when generation completes; filled in, never
    overwritten. A span with no `end` is in flight.

    Termination reason is deliberately absent: it lives in the bulk store, so
    that finishing a generation never has to reopen this record.
    """
    id: str
    kind: str
    start: int                      # absolute byte offset from the root
    end: int | None = None          # absolute; None while in flight
    text: bytes | None = None
    created: str = ''
    # sampled
    params: str | None = None       # key into the intern table
    seed: int | None = None
    batch: str | None = None
    index: int | None = None        # position within the batch
    slice_start: int | None = None  # absolute, resolved -- see decision 4
    # counterfactual
    origin: dict | None = None      # {span, index, token_id}

    @property
    def complete(self) -> bool:
        return self.end is not None

    @property
    def length(self) -> int:
        return len(self.text) if self.text is not None else 0

    def to_json(self) -> dict:
        if self.text is None:
            text = None
        else:
            # A span is a whole number of tokens, and byte-level BPE can end
            # one mid-character -- so this is not guaranteed, only near-always
            # true. See the open question in PHASE-1.md; guessing at a repair
            # before seeing a real case would bury it.
            try:
                text = self.text.decode('utf-8')
            except UnicodeDecodeError as e:
                raise ValueError(
                    f'{self.id}: bytes do not decode as UTF-8 and the format '
                    f'has no escape for that yet -- {e}') from e
        out = {'kind': self.kind, 'text': text,
               'extent': [self.start, self.end], 'created': self.created}
        for name in ('params', 'seed', 'batch', 'index', 'slice_start', 'origin'):
            value = getattr(self, name)
            if value is not None:
                out[name] = value
        return out

    @classmethod
    def from_json(cls, id: str, d: dict) -> Span:
        start, end = d['extent']
        text = d.get('text')
        return cls(id=id, kind=d['kind'], start=start, end=end,
                   text=None if text is None else text.encode('utf-8'),
                   created=d.get('created', ''),
                   params=d.get('params'), seed=d.get('seed'),
                   batch=d.get('batch'), index=d.get('index'),
                   slice_start=d.get('slice_start'), origin=d.get('origin'))


@dataclass
class Run:
    """A maximal stretch with no branch point in it. Structure, not record.

    Boundaries move freely: a split divides the piece list and relinks, and the
    prefix keeps this id. Nothing durable may be keyed by one -- after a split
    a stored id still resolves, but to less text than it did.
    """
    id: str
    parent: str | None
    start: int                                     # absolute byte offset
    pieces: list[Piece] = field(default_factory=list)
    children: list[str] = field(default_factory=list)

    @property
    def length(self) -> int:
        return sum(p.length for p in self.pieces)

    @property
    def end(self) -> int:
        return self.start + self.length

    def to_json(self) -> dict:
        return {'parent': self.parent, 'start': self.start,
                'pieces': [list(p) for p in self.pieces],
                'children': list(self.children)}

    @classmethod
    def from_json(cls, id: str, d: dict) -> Run:
        return cls(id=id, parent=d['parent'], start=d['start'],
                   pieces=[Piece(*p) for p in d['pieces']],
                   children=list(d['children']))


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


def pretty(obj, indent: int = 0, width: int = 84) -> str:
    """JSON that stays openable by hand: nested where it must be, inline where
    it fits.

    `json.dump(indent=2)` puts every extent bound and every piece bound on its
    own line, which turns a seven-run tree into three hundred. The tree file
    being readable is a stated goal of the format, and it already gave up
    reading as prose when runs stopped holding text -- it should not also give
    up reading as structure.
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
    """The tree file: structure, spans, and the interned parameter table."""
    tree_id: str
    base_seed: int
    root: str
    runs: dict[str, Run] = field(default_factory=dict)
    spans: dict[str, Span] = field(default_factory=dict)
    params: dict[str, dict] = field(default_factory=dict)
    selected: dict | None = None
    deleted: list[str] = field(default_factory=list)
    format: str = FORMAT

    # -- construction ----------------------------------------------------

    @classmethod
    def empty(cls, base_seed: int | None = None) -> Tree:
        """A tree with nothing but its root, which holds no bytes by design.

        Initial prompts are human spans hanging under it, which is the shape
        that lets several coexist as siblings.
        """
        if base_seed is None:
            base_seed = uuid.uuid4().int % 1_000_000
        root = Run(id='r0', parent=None, start=0)
        return cls(tree_id=uuid.uuid4().hex, base_seed=base_seed, root='r0',
                   runs={'r0': root})

    def new_run_id(self) -> str:
        return next_id(self.runs, 'r')

    def new_span_id(self) -> str:
        return next_id(self.spans, 's')

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

    # -- reading ---------------------------------------------------------
    #
    # These return bytes, not str. A piece boundary is a token boundary, and
    # byte-level BPE can put one in the middle of a character -- so a run's
    # bytes are not guaranteed to decode on their own even when the whole path
    # does. Decode at the point of display, not here.

    def piece_bytes(self, piece: Piece) -> bytes:
        span = self.spans[piece.span]
        if span.text is None:
            return b''
        return span.text[piece.start:piece.end]

    def run_bytes(self, run_id: str) -> bytes:
        return b''.join(self.piece_bytes(p) for p in self.runs[run_id].pieces)

    def ancestry(self, run_id: str) -> list[str]:
        """Root first, `run_id` last."""
        path = []
        current = run_id
        while current is not None:
            path.append(current)
            current = self.runs[current].parent
        path.reverse()
        return path

    def path_bytes(self, run_id: str) -> bytes:
        return b''.join(self.run_bytes(r) for r in self.ancestry(run_id))

    def live_runs(self) -> set[str]:
        """Reachable from the root without crossing a deleted subtree root."""
        dead = set(self.deleted)
        live: set[str] = set()
        stack = [self.root]
        while stack:
            current = stack.pop()
            if current in dead or current in live:
                continue
            live.add(current)
            stack.extend(self.runs[current].children)
        return live

    def pieces_of(self, span_id: str, runs: set[str] | None = None
                  ) -> Iterator[tuple[str, int, Piece]]:
        """Every piece referencing a span, as (run id, absolute offset, piece).

        Optionally restricted to a set of runs -- which is how the validator
        tells its two coverage checks apart.
        """
        for run in self.runs.values():
            if runs is not None and run.id not in runs:
                continue
            offset = run.start
            for piece in run.pieces:
                if piece.span == span_id:
                    yield run.id, offset, piece
                offset += piece.length

    # -- serialisation ---------------------------------------------------

    def to_json(self) -> dict:
        return {
            'format': self.format,
            'tree_id': self.tree_id,
            'base_seed': self.base_seed,
            'root': self.root,
            'spans': {k: v.to_json() for k, v in self.spans.items()},
            'runs': {k: v.to_json() for k, v in self.runs.items()},
            'params': self.params,
            'selected': self.selected,
            'deleted': self.deleted,
        }

    @classmethod
    def from_json(cls, d: dict) -> Tree:
        if d.get('format') != FORMAT:
            raise ValueError(f"not {FORMAT}: {d.get('format')!r}")
        return cls(
            tree_id=d['tree_id'], base_seed=d['base_seed'], root=d['root'],
            runs={k: Run.from_json(k, v) for k, v in d['runs'].items()},
            spans={k: Span.from_json(k, v) for k, v in d['spans'].items()},
            params=d.get('params', {}), selected=d.get('selected'),
            deleted=list(d.get('deleted', [])), format=d['format'],
        )

    def save(self, path: str) -> None:
        """Write via a temporary file and rename, so a crash cannot truncate.

        The tree file is rewritten whole on every save and is the only record
        of structure; a half-written one would lose the tree, not a save.

        Serialised before anything is opened, so that a span the format cannot
        represent -- see the open question in PHASE-1.md -- fails without
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
