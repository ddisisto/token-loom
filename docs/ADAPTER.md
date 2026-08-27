# The adapter contract

**What a backend must do to produce the record `docs/CORE.md` describes.** The operations, the
obligations behind them, and what to do when one cannot be met.

**This document is not locked, and that is the point of the split.** `docs/CORE.md` is fixed and
names no backend; this one moves as backends are met. Nothing here may contradict the core, and
the core cites this document rather than anything a particular backend happens to do.

---

## What an adapter is

An adapter provides the three operations below for one vocabulary. It may satisfy them however
it likes and from as many sources as it likes — reading a model file, calling one endpoint,
calling several. **Where it gets an answer is not the core's concern.**

An adapter absorbs its backend's faults rather than passing them through. Several backends are
lossy in ways that produce a record which is quietly wrong rather than an error, so what the core
sees is a repaired stream and not a raw one. Repairing is the adapter's whole job; the core has
no facility for it and no way to tell that it was needed.

## The operations

| operation | returns |
| --- | --- |
| `tokenize(bytes)` | the ids that spell those bytes, in order, each with its own bytes |
| `bytes_for(id)` | what that id spells, exactly, for every id the adapter can emit |
| `generate(ids, params, seed)` | per position: the id drawn, and the `top_n` ranked ids with their logprobs — and a terminator |

## The obligations

Numbered against the conditions in the core's *What the record requires of a backend*, since
they exist to satisfy them.

1. **Ids, never text.** `generate` reports ids. The core stores no bytes from a generation and
   derives none from one, so a backend that can only report what it produced as text cannot be
   adapted by decoding it — the decoding is the artefact.
2. **`bytes_for` answers for every id**, including ids that are a fragment of a character and ids
   that are control tokens. It reports what the vocabulary says, never what a generation said
   about an occurrence. An id it cannot answer for cannot be stored at all.
3. **`tokenize` round-trips.** Reassembling its ids' bytes returns the input unchanged. `create`
   checks this on the text at hand, so a failure surfaces there rather than silently.
4. **The token sequence is evaluated verbatim.** No re-tokenising a prompt, no truncating it to
   fit, no template applied on the way in. An adapter that alters the sequence cannot replay a
   path, which is the property the whole format exists to hold.
5. **Rankings are the model's own distribution.** Their ids, order and values depend on the model
   and the path and on nothing in `params`. A backend that can only report a ranking already
   shaped by temperature or truncation cannot satisfy this — and the core would then have to key
   rankings on the act rather than the node, which is to say it could not merge at all.
6. **A request is met or refused, never adjusted.** See *Refusal*.

Three obligations follow from these but are stated separately, because they are the ones a
backend is most likely to fail quietly.

**`top_n >= top_k > 0`.** `top_k` confines the draw to raw ranks `0…k−1`; `top_n` is how many
ranked ids are reported. A drawn token is therefore always among the alternatives reported for
its position, which is what makes the core's `INV-RANK-COVERS` hold in the ordinary case. An
adapter that cannot report at least `top_k` refuses.

**The seed is honoured.** The core supplies one with every request, so there is no case where an
adapter chooses. An adapter whose backend cannot seed its sampler refuses rather than recording a
seed that did nothing.

**Room is checked before starting.** The prompt and the requested length together must fit. This
is why running out of context is not a way for a generation to end, and why the core's `limit`
terminator means exactly one thing.

## Refusal

**An adapter refuses rather than adjusting.** A refusal happens before the core writes anything,
so a refused request leaves no trace in the store.

Refuse when the prompt and requested length exceed the room available; when `top_n` exceeds what
the backend will report; when the seed cannot be honoured; and whenever any parameter would
otherwise have to be clamped, substituted or ignored.

Never truncate a prompt to fit. Never reduce `top_n` and report fewer. Never clamp a temperature
into a supported range, and never substitute a default for a parameter the backend does not
understand.

**A refusal is not an abort.** A refusal is a request that never started and that the store never
hears about; `aborted` is a generation that started, was recorded in flight, and died. The core
distinguishes them and only ever learns about the second.

## Declination

A `generate` may return an id it can give no ranking for — a backend that emits a token on a stop
condition without it passing through a sampler is the usual cause. **Report it as such.** The core
records the position as a node with no covering ranked edge, and stores the id like any other.

**Do not synthesise a ranking to fill the gap.** The core cannot tell an invented distribution
from a measured one, and it does not need the gap filled: a later generation that does report a
ranking there extends the node's record and supplies the missing edge on its own.

## Determinism, and what to do about disagreement

Obligation 5 makes a ranking a function of the model and the path. In practice a backend may not
be bit-reproducible — batch composition, cache state and kernel selection all move the last
decimal places — so two generations reaching one node can report slightly different values.

**The format does not care, by construction.** Ranks are recorded in the order presented, the
first value written for a token is the one kept, and a later generation appends only tokens not
already recorded. Nothing is ever rewritten, so a small disagreement cannot corrupt anything and
no tolerance appears in the core.

**Measure it anyway, and report it as a diagnostic.** The size of a backend's self-disagreement is
a fact about that backend worth knowing, and a large one is evidence of something obligation 5
forbids — a ranking that is not actually a function of the path. What counts as large is a
property of the backend, belongs in its notes, and is expected to move as it is measured.

## Backends

- **llama.cpp** — measured behaviour lives in `docs/SERVER.md`, which is that adapter's notes and
  nothing the core cites. Several of the behaviours recorded there produce a record that is
  quietly wrong rather than an error, so it is read before the adapter is touched, not after
  something disagrees.

---

## Status

- **Written against no implementation.** Nothing here has been exercised against a running
  backend, and the llama.cpp adapter does not exist.
- **`docs/SERVER.md` is unstructured**, still largely a dump from proof-of-concept work and some
  targeted probes. It is expected to be renamed and reorganised as the notes for this contract's
  first backend; the pointer above moves with it.
- **The refusal list is provisional.** It enumerates what is known to need refusing now. Meeting a
  second backend is the thing most likely to lengthen it, and lengthening it costs nothing here.
