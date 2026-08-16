"""What the API says, and how it says it. No HTTP in this file.

Everything with a rule attached lives here rather than in a route handler, for
the reason `core_test.py` exists at all: the parts that are easy to get wrong
are worth exercising without a server in the way.

Four rules, and each is a decision rather than a formatting preference.

**A position is `(span, offset)`, in two spellings.** In a JSON body or
response it is an object -- `{"span": "s3", "offset": 9}`, `null` for the root
-- because a two-element array is unreadable in a request log and invites a
client to index it. In a path or query parameter it is the string `s3+9`, with
`.` for the root, which is exactly the grammar `loom.py` already parses. One
grammar, two clients, and a URL that can be typed by hand.

**Text carries the file's escape onto the wire.** A span's bytes usually decode
and go out as a string; when they do not -- a given span holding a paste, a
counterfactual branch onto a byte-fallback token -- they go out as
`{"b64": "..."}`, the same shape `FORMAT.md` uses on disk. Inventing a second
convention for the same problem one layer up is how the two drift.

**Runs travel as composition, never as identity.** A run is derived, so it has
no id and cannot be given one: renumbering on the next render would make any id
a lie the moment a branch appeared. What travels is the decomposition -- which
spans, which byte ranges, which forks below -- and the client lays out from
that.

**Nothing derived is sent that the client could not recompute**, and nothing
stored is withheld. Absolute offsets are the test case: they are convenient for
a viewport, they are derived, and they are *not* sent. A client that wants one
sums the ancestry, which is what the core does.
"""
from __future__ import annotations

from core import BulkStore, Position, Tree, divergence, runs, token_offsets
from core.tree import encode_text, id_order


class Unknown(KeyError):
    """A name the tree does not have: a span, a batch, a token index."""


class Malformed(ValueError):
    """A syntactically wrong address or an offset outside its span."""


# -- positions -------------------------------------------------------------

def parse_position(tree: Tree, text: str) -> Position | None:
    """`s3+9`, `s3` (its tip), or `.` (the root). Raises on anything else.

    Same grammar as `loom.py:parse_position`, minus the empty case: the CLI
    reads an empty argument as "the cursor", and a request that means the
    cursor has to say so, because a client that omits an address by accident
    should be told rather than served.
    """
    if not text:
        raise Malformed('an address is required; `.` is the root')
    if text == '.':
        return None
    span_id, plus, offset = text.partition('+')
    if span_id not in tree.spans:
        raise Unknown(f'no span {span_id}')
    if not plus:
        return tree.tip(span_id)
    try:
        at = int(offset)
    except ValueError:
        raise Malformed(f'{text}: an offset must be a number') from None
    return checked(tree, Position(span_id, at))


def checked(tree: Tree, pos: Position) -> Position:
    """A position whose offset is inside the bytes its span has.

    `ops.check` asks the same question and answers with `None`; this one hands
    back the position so it can be used inline, which is the only difference.
    """
    span = tree.spans[pos.span]
    if not 0 <= pos.offset <= span.length:
        raise Malformed(f'{pos.offset} is outside {pos.span} '
                        f'(0..{span.length})')
    return pos


def position_json(pos: Position | None) -> dict | None:
    """`{"span", "offset"}`, or `null` for the root."""
    return None if pos is None else {'span': pos.span, 'offset': pos.offset}


def position_from_json(tree: Tree, value) -> Position | None:
    """The inverse, validated against the tree.

    Validation happens here rather than in the route because an address that
    names a missing span and an address past the end of a real one are the same
    class of client error and should answer the same way.
    """
    if value is None:
        return None
    if isinstance(value, str):
        # accepted so one client can use one spelling throughout, rather than
        # switching grammars depending on whether it is asking or telling
        return parse_position(tree, value)
    if not isinstance(value, dict) or 'span' not in value:
        raise Malformed(f'not a position: {value!r}')
    if value['span'] not in tree.spans:
        raise Unknown(f"no span {value['span']}")
    return checked(tree, Position(value['span'], int(value.get('offset', 0))))


# -- text ------------------------------------------------------------------

def text_json(raw: bytes | None):
    """A string, `{"b64": ...}`, or `null` for bytes that have not arrived.

    `core.tree.encode_text` already does this and is reused rather than
    reimplemented -- the wire and the file agree by construction, not by two
    functions being kept in step.
    """
    return encode_text(raw)


# -- the tree --------------------------------------------------------------

def span_json(tree: Tree, store: BulkStore, span_id: str) -> dict:
    """One span, as stored, plus the two facts that live in the bulk store.

        {"id", "kind", "parent", "text", "length", "created",
         "params", "seed", "batch", "index", "slice_start", "origin",
         "complete", "terminator"}

    `length` is sent even though it is `len(text)`, because a span in flight
    has no text and a client still has to lay it out. `terminator` comes from
    the store, and its absence on a complete span is impossible rather than
    unknown -- the validator refuses that combination at load.

    `complete` is `text is not None` and is sent as its own field on purpose:
    "in flight" is a state the client renders differently, and asking a client
    to infer a state from a null is how the null acquires a second meaning.
    """
    span = tree.spans[span_id]
    return {
        'id': span.id,
        'kind': span.kind,
        'parent': position_json(span.parent),
        'text': text_json(span.text),
        'length': span.length,
        'created': span.created,
        'params': span.params,
        'seed': span.seed,
        'batch': span.batch,
        'index': span.index,
        'slice_start': position_json(span.slice_start),
        'origin': span.origin,
        'complete': span.complete,
        'terminator': store.terminator(span.id),
    }


def runs_json(tree: Tree, reach: dict[str, int], start: tuple) -> dict:
    """The derived run tree: `{"pieces", "width", "children"}`.

        {"pieces": [{"span": "s0", "begin": 0, "end": 39}],
         "width": 39,
         "children": [ ... the same shape ... ]}

    No ids anywhere, and byte ranges are span-local -- `begin`/`end` are
    offsets into the named span, which is the only frame that survives an
    export.

    A thin re-shaping of `core.ops.runs`, which is where the derivation lives
    now: the CLI had it first, the API needs it identically, and the zero-width
    fork rule is not something to implement twice. All this adds is naming the
    tuple fields, because a wire format that requires counting positions in an
    array is one a client gets wrong silently.
    """
    return _name_pieces(runs(tree, reach, start))


def _name_pieces(node: dict) -> dict:
    return {'pieces': [{'span': span, 'begin': begin, 'end': end}
                       for span, begin, end in node['pieces']],
            'width': node['width'],
            'children': [_name_pieces(c) for c in node['children']]}


def tree_json(tree: Tree, store: BulkStore) -> dict:
    """The whole readable state in one response.

        {"format", "tree_id", "base_seed", "selected", "spans", "params",
         "deleted", "live", "runs"}

    One response rather than several because the tree file is small by design
    -- the bulk data is deliberately elsewhere -- and a client assembling a view
    from four requests would have four chances to see a half-applied mutation.

    `live` is `Tree.live()`: reachable spans mapped to how many of their bytes
    the tree still reaches. It is derived, and it is sent anyway, because the
    alternative is every client reimplementing the deletion cascade.
    """
    reach = tree.live()
    return {
        'format': tree.format,
        'tree_id': tree.tree_id,
        'base_seed': tree.base_seed,
        'selected': position_json(tree.selected),
        'spans': {span_id: span_json(tree, store, span_id)
                  for span_id in sorted(tree.spans, key=id_order)},
        'params': tree.params,
        'deleted': [position_json(p) for p in tree.deleted],
        'live': reach,
        'runs': runs_json(tree, reach, (None, 0, False)),
    }


# -- the token overlay -----------------------------------------------------

def tokens_json(store: BulkStore, span_id: str) -> list[dict]:
    """A span's tokens, each with its byte extent and its alternatives.

        [{"idx": 0, "begin": 0, "end": 5, "token_id": 1001,
          "logprob": -0.42, "text": " calm",
          "counterfactuals": [{"rank": 0, "token_id": 1005,
                               "logprob": -0.92, "text": " clear"}]}]

    `begin`/`end` are span-local byte offsets, accumulated from the rows -- the
    conversion from the token overlay back to the anchor, which is what makes a
    click on a token into a position.

    `token_id` and `logprob` are `null` on a merged row, and its
    counterfactuals are absent rather than empty. That is not a gap in the
    record: llama-server regroups its output onto character boundaries, so a
    merged row's id would describe only the last fragment of the character its
    bytes spell. See `core/llama.py:_align`.

    Rank 0 is not the sampled token about a third of the time at temperature
    0.9, so a client must not mark the sampled one by rank. Compare `token_id`.
    """
    offsets = token_offsets(store, span_id)
    alternatives: dict[int, list] = {}
    for c in store.counterfactuals(span_id):
        alternatives.setdefault(c.idx, []).append(
            {'rank': c.rank, 'token_id': c.token_id, 'logprob': c.logprob,
             'text': text_json(c.bytes)})
    return [{'idx': t.idx, 'begin': offsets[t.idx], 'end': offsets[t.idx + 1],
             'token_id': t.token_id, 'logprob': t.logprob,
             'text': text_json(t.bytes),
             'counterfactuals': alternatives.get(t.idx, [])}
            for t in store.tokens(span_id)]


def batches_json(tree: Tree, store: BulkStore) -> list[dict]:
    """Generation calls, as the experiments they were.

        [{"batch": "b0", "from": {"span": "s0", "offset": 39},
          "params": "p0", "spans": ["s1", "s2"]}]

    `params` is the intern key, not the settings: the table comes with the tree
    in one response, and sending the values here would duplicate a record whose
    whole point is being stored once.
    """
    order: list[str] = []
    members: dict[str, list[str]] = {}
    for span_id in sorted(tree.spans, key=id_order):
        span = tree.spans[span_id]
        if not span.batch:
            continue
        if span.batch not in members:
            order.append(span.batch)
        members.setdefault(span.batch, []).append(span_id)
    return [{'batch': batch,
             'from': position_json(tree.spans[members[batch][0]].parent),
             'params': tree.spans[members[batch][0]].params,
             'spans': sorted(members[batch], key=id_order)}
            for batch in order]


def batch_spans(tree: Tree, batch: str) -> list[str]:
    """The spans of one call, in the order they were made.

    Raises rather than returning an empty list for a batch that is not there:
    "no such call" and "a call that produced nothing" are different answers,
    and the second one cannot happen.
    """
    spans = sorted((s.id for s in tree.spans.values() if s.batch == batch),
                   key=id_order)
    if not spans:
        raise Unknown(f'no batch {batch}')
    return spans


def divergence_json(store: BulkStore, span_ids: list[str],
                    depths=(1, 3, 10)) -> dict | None:
    """`core.ops.divergence`, unchanged -- it already returns plain data.

    Sent as-is deliberately. It is the only quantitative read the instrument
    has on where a prompt tends to go, and a client that cannot reach it is
    short of the floor rather than short of a convenience.
    """
    profile = divergence(store, span_ids, depths)
    if profile is None:
        return None
    # JSON object keys are strings, so the integer depths of `lock` and `short`
    # would come back as strings anyway. Doing it here means the shape is the
    # same in the tests as on the wire, rather than differing by a round trip.
    return dict(profile,
                lock={str(k): v for k, v in profile['lock'].items()},
                short={str(k): v for k, v in profile['short'].items()})
