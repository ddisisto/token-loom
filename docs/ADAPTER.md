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
| `generate(ids, params, seed)` | per position: the id drawn, and the `top_n` ranked ids with their logprobs — and a terminator, which may be a refusal |

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

## Authored text and special tokens

A control token's literal spelling is also ordinary text. `<|endoftext|>` is thirteen characters
that tokenise to one id, and thirteen characters that tokenise to a dozen ordinary ones. Both
readings spell the same bytes, so obligation 3's round trip accepts either and no field in the
store records which was meant.

**`tokenize` reads authored text as plain bytes.** Control sequences in it become the ordinary
tokens that spell them, and a user who quotes one does not inject it.

**A second path exists for a caller who means the control token**, and it is never the default.
Nothing about the store changes between the two — only which ids come back.

## Refusal

**An adapter refuses rather than adjusting.** A refusal is a `generate` that returns without
calling the model, and it is recorded: the act stands with terminator `refused`, no tip, and the
parameters and seed it was asked for.

Refuse when the prompt and requested length exceed the room available; when `top_n` exceeds what
the backend will report; when the seed cannot be honoured; when the backend will not evaluate the
path it was given; and whenever any parameter would otherwise have to be clamped, substituted or
ignored.

**The path is one of the things that can be refused.** The core forms nodes freely and holds no
notion of a character boundary, so an adapter is handed paths its backend may decline — llama.cpp
will not answer for a prompt whose bytes end mid-character, however the prompt is expressed. The
predicate is the backend's and belongs here; `create` and `realise` reach those nodes regardless,
since neither calls a model.

Never truncate a prompt to fit. Never reduce `top_n` and report fewer. Never clamp a temperature
into a supported range, and never substitute a default for a parameter the backend does not
understand.

**Refuse in one place.** Every condition above is decidable from the request and the adapter's own
configuration, which is to say it is equally decidable before the model call and after the act is
written. A second way to decline a request gives a caller two paths leaving two different traces,
and the caller cannot tell which it will get. `generate` is where a request is declined.

**Asking is not declining.** A client that wants to know whether a node can be generated from —
so a reading surface can say so, and so the command line can answer the same question — may ask
the adapter, and the answer writes nothing and stands in for no refusal. The real request still
goes through `generate` and still records `refused`. The shape of that query is not settled here.

**Refusal, failure and abandonment are three outcomes.** `refused` never called the model;
`failed` called it and the backend broke under it; `aborted` is what a later writer records for a
generation whose own writer is gone. None names a tip, and the store tells them apart.

**The shape of a refusal is not settled here** — a reason code, a message, both. What the core
takes from it is the terminator; the rest is the adapter's answer to its caller.

## Cancellation

The core's `cancelled` terminator records a generation a caller stopped. Reaching it needs a
`generate` that can be interrupted and that returns what it drew, which the blocking form above is
not.

**An adapter that cannot be interrupted never produces `cancelled`.** Stopping one of its
generations means killing the writer, which the next writer records as `aborted`, and which loses
every token the model produced — nodes land only in the core's second write.

The interruptible form is the same operation with a way in and the same return: the ids drawn so
far, their rankings, and `cancelled`. It arrives with streaming.

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

**Measured on llama.cpp over Vulkan, single slot: no disagreement at all.** Two requests differing
in seed and in `top_n` returned bit-identical logprobs for every rank they shared, and repeating a
request reproduced both the path and its values exactly. That is one backend on one machine with
`--parallel 1`, so it is not a general result — but note that the core holds its lock across a
whole act, so an adapter never sees its own requests batched together, which is where most of this
class of nondeterminism comes from in the first place.

## Backends

- **llama.cpp** — measured behaviour lives in `docs/SERVER.md`, which is that adapter's notes and
  nothing the core cites. Several of the behaviours recorded there produce a record that is
  quietly wrong rather than an error, so it is read before the adapter is touched, not after
  something disagrees.

---

## Status

- **Written against no implementation.** The llama.cpp adapter does not exist. The obligations
  have been probed against a running server — tokenisation, round-trip, ranking stability — but
  nothing has exercised refusal, declination, or a generation that ends on `eos`.
- **No `eos` draw has been observed.** End-of-text did not appear in the top 40 at any of three
  document-ending prompts on this base model, so the `eos` terminator is specified but unwitnessed.
- **`docs/SERVER.md` is unstructured**, still largely a dump from proof-of-concept work and some
  targeted probes. It is expected to be renamed and reorganised as the notes for this contract's
  first backend; the pointer above moves with it.
- **The refusal list is provisional.** It enumerates what is known to need refusing now. Meeting a
  second backend is the thing most likely to lengthen it, and lengthening it costs nothing here.
- **The shape of a refusal is unwritten** — reason code, message, or both. The core needs only the
  terminator, so this can wait for a client that has to display one.
- **`cancelled` is unreachable** until `generate` can be interrupted. The core specifies the
  terminator; nothing in the three-operation surface can produce it. This is the one open item that
  a locked core is already waiting on.
- **The special-token path is unnamed.** The plain-bytes default is settled; how a caller asks for
  the other reading is not.
- **The path predicate is measured at one end only.** `docs/SERVER.md` records that llama.cpp
  refuses a prompt whose bytes *end* mid-character. Whether it also refuses one carrying a
  completed invalid sequence with valid bytes after it — a stray continuation byte at depth 20 —
  is unmeasured, and it is the difference between a predicate that asks whether a path holds an
  incomplete character and one that asks whether it decodes end to end. Minutes of probing, and
  nothing is locked behind it.
- **The generatability query is unspecified.** Its shape waits for a client that has to draw one.
