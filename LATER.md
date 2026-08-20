# Later

Things considered and set aside, kept because the thinking is worth not doing twice. **Nothing
here is planned, scoped or scheduled**, and nothing here should be built because it is written
down.

It is not `DIRECTION.md`'s *out of scope for v1.0*, and the difference is horizon rather than
confidence. That list names decisions made **about v1.0**, so they are not re-litigated during
it; this file is about no cycle in particular. Where both mention a thing, the decision is
there and whatever detail is worth keeping is here.

It replaces `BEYOND-MVP.md`, which was written before there was anything to use and lost most
of its content to the experience of using it. Git holds that file, and a few documents written
earlier cite it by name — what they cite is either in `DIRECTION.md` now, settled in
`FORMAT.md` or `CLAUDE.md`, or below.

## Bookmarks, tags and annotation

Anchored to `(span, offset)` — one address, not an offset plus an id. A range is two of them,
valid when both lie on one path. Annotation is the same anchor carrying text instead of a
label.

These are the only things here that want to keep something the format does not already hold,
and even so they want no new mechanism: the bulk store is generic over record type, so they
are a new record type in a store that already takes them.

## Parameter control

Temperature, top-p, top-n and the rest, reachable from the reading surface rather than fixed
for the session.

It was dropped from the MVP to keep the focus on the core and an interface on it, and it stays
out of v1.0 for the same reason — but unlike the rest of this file it has a real chance of
coming back soon after, and it is here rather than in `DIRECTION.md` only because nothing
about v1.0 turns on it.

Its near-absence is currently a position rather than a gap. The surface exposes chunk size,
whose effect is pacing, and nothing else — so temperature and the rest stop being dials and
become invisible conditions of the session. Exposing them is a change to that claim and not
merely an addition to a panel, which is the part worth thinking about before it is built.

Nothing is needed underneath it. Parameters intern per span already, so a tree records where
its reader changed anything without the format hearing about it.

## Streaming

The one thing here that needs generation to stop being an ordinary blocking call.

The format support it needs is already in — a span in flight has provenance and no bytes, and
that is a state the surface already renders. So what streaming changes is that such a span
fills progressively instead of arriving whole, and the render path is the one that exists.
What it costs is asynchrony, deliberately reintroduced.

Deferring it costs nothing later precisely because the format support was pulled forward while
it was cheap. That was the trade made when it was noticed, and this is it paying out.

## Embeddings and distances

Wanted at some scale, for the reason `RESEARCH.md` gives: *does anything survive repeated
retransmission* is a question about distance, and reading it off text by eye does not scale
past a handful of branches. The genre-level measure that question 1 wants is the same gap seen
from the other side.

**Two different things share the name, and the second does not follow from the first.**

- **Text embeddings.** A vector per slice, from a small model that does only that. Cheap
  enough not to think about, and the case that would arrive first.
- **Model-internal states.** The residual stream at a token position, from the model doing the
  generating. Orders of magnitude larger per token, and it needs direct access to the model
  rather than a served endpoint — so it needs a real decision about what is loaded and where,
  which the first does not.

The second is the more interesting one for the attractor question, which is exactly why it
should not be assumed to come along with the first.

**Neither means dropping llama.cpp.** The shape is a second process alongside it — generation
stays where it is, and a small embedding model runs beside it as a second adapter next to
`core/llama.py`. Model-internal states are the exception, since they need the generating model
itself, and that is the part with a cost attached.
