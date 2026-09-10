# The adapter contract

**What a backend must do to produce the record `docs/CORE.md` describes.** The operations, the
obligations behind them, and what to do when one cannot be met.

**This document moves as backends are met, and that is the point of the split.** `docs/CORE.md`
names no backend and moves only as its own work; meeting a backend is not that work. Nothing
here may contradict the core, and the core cites this document rather than anything a particular
backend happens to do.

---

## What an adapter is

An adapter provides the four operations below for one vocabulary. It may satisfy them however
it likes and from as many sources as it likes — reading a model file, calling one endpoint,
calling several. **Where it gets an answer is not the core's concern.**

An adapter absorbs its backend's faults rather than passing them through. Several backends are
lossy in ways that produce a record which is quietly wrong rather than an error, so what the core
sees is a repaired stream and not a raw one. Repairing is the adapter's whole job; the core has
no facility for it and no way to tell that it was needed.

## The operations

| operation | returns |
| --- | --- |
| `tokenize(bytes, special)` | the ids that spell those bytes, in order, each with its own bytes |
| `bytes_for(id)` | what that id spells, exactly, for every id the adapter can emit |
| `generate(ids, params)` | per position: the id drawn, and the ranked ids with their logprobs, as many as the recording bounds call for — and a terminator, which may be a refusal |
| `will_evaluate(ids)` | whether the backend would accept that path at all — a question, answered without calling the model and without writing anything |

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

What follows is stated separately because it is what a backend is most likely to fail quietly —
each of these is met or missed without anything erroring.

**Sampling and recording are named apart.** A parameter that shapes the draw keeps the name the
field gave it — `temperature`, `top_k`, `top_p`, `min_p`, `seed`. A parameter that governs what is
*recorded* is prefixed `record_`. Both kinds arrive in one `params` dict and a reader meets them
together in the row it interns to, so the distinction has to be legible in the key rather than
recoverable from knowing which is which: `top_p` and `record_mass` are both thresholds on
cumulative probability, and they do entirely different things.

**`record_rows >= top_k > 0`, and `record_rows >= 2`.** `top_k` confines the draw to raw ranks
`0…k−1`; `record_rows` is the most ranked ids that will be reported for a position. A drawn token
is therefore always among the alternatives reported for its position, which is what makes a node's
logprob derivable in the ordinary case. The core does not require it — *Rankings* provides for a
node with no covering ranked edge and states that nothing records why one is missing — so this is
an obligation here and not an invariant there. An adapter that cannot report at least `top_k`
refuses.

**`record_mass` bounds the same set by probability, and the two bounds compose.** What is reported
for a position is the shortest prefix of the ranking whose probabilities reach `record_mass`,
extended to two rows and to include the token actually drawn, and cut at `record_rows`. Three
lower bounds and one upper: two rows so that every position offers at least one alternative to
branch into, and the drawn token so that a stochastic draw landing past the mass bound cannot
leave a node with no derivable logprob — which `record_rows >= top_k` is what makes reachable.
**Failing to reach `record_mass` is not a failure.** Where the ceiling binds first, the recorded
set is what the ceiling allowed; that is an outcome and never a refusal, and no request is unmet
by it.

**An adapter requires every parameter that something other than the caller would otherwise
decide.** The core reads `length` and passes the rest through, so what a complete request looks
like is the adapter's to declare and to refuse without. Three things do the deciding when a
request is silent, and all three count: the backend's sampler chain, which joins any request that
does not name it; the backend's handling of its own cache, which moves the values recorded; and
the adapter's recording bounds, which fix what the store keeps for good. An adapter that supplies
its own default for one of these has adjusted the request as surely as the backend would have —
one level further up, where the record cannot see it either.

**A seed is the exception, and it is an exception rather than a case of the rule.** There is no
value for a backend to impose and none to substitute: one that picks a seed is not applying a
policy, it is declining to have one, and a caller who did not ask for reproducibility has had
nothing taken from them. What that costs is worth naming rather than leaving to inference — a
backend that picks a seed does not report it, so a stochastic act whose `params` name none cannot
be replayed, and nothing in the record marks it as one that cannot. The record stays honest: no
seed was asked for, and that is what it says. But replay is a property such an act does not have.
A caller that wants it names a seed, and a backend that cannot honour the one it names refuses.

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

**A second path exists for a caller who means the control token** — `special` — and it is never
the default. Nothing about the store changes between the two — only which ids come back.

## Refusal

**An adapter refuses rather than adjusting.** A refusal is a `generate` that returns without
calling the model, and it is recorded: the act stands with terminator `refused`, no tip, and the
parameters it was asked for.

Refuse when the prompt and requested length exceed the room available; when `record_rows` exceeds
what the backend will report; when a parameter the backend requires is missing or cannot be
honoured;
when the backend will not evaluate the path it was given; when a parameter is named that the
backend does not understand; and whenever any parameter would otherwise have to be clamped,
substituted or ignored.

**Refuse also when the backend would meet the request and misreport how.** The first two entries
above are not hypothetical on llama.cpp: it clamps `n_probs` above the vocabulary size without
saying so, and it truncates a generation that will not fit while still reporting the stop type
the core reads as `limit`. Both come back HTTP 200. An adapter that only refuses what errors is
not refusing the cases that matter.

**The path is one of the things that can be refused.** The core forms nodes freely and holds no
notion of a character boundary, so an adapter is handed paths its backend may decline — llama.cpp
will not answer for a prompt whose bytes end mid-character, however the prompt is expressed. The
predicate is the backend's and belongs here; `create` and `realise` reach those nodes regardless,
since neither calls a model.

Never truncate a prompt to fit. Never meet a smaller `record_rows` than the one asked for and
report the difference as though the distribution ran out — a set cut short by `record_mass` is the
parameters doing what they say, and one cut short by the backend is a request adjusted. Never
clamp a temperature into a supported range, and never substitute a default for a parameter the
backend does not understand.

**Refuse in one place.** Every condition above is decidable from the request and the adapter's own
configuration, which is to say it is equally decidable before the model call and after the act is
written. A second way to decline a request gives a caller two paths leaving two different traces,
and the caller cannot tell which it will get. `generate` is where a request is declined.

**Asking is not declining.** A client that wants to know whether a node can be generated from —
so a reading surface can say so before offering the act — asks `will_evaluate`, and the answer
writes nothing and stands in for no refusal. The real request still goes through `generate` and
still records `refused`.

**The two answers must agree.** `will_evaluate` rejects a path exactly where `generate` refuses
one, on the same predicate. An adapter whose answers disagree is worse than one that cannot be
asked at all: a client told a path is generatable and then refused has been given two answers and
no way to know which it will get.

**Refusal, failure and abandonment are three outcomes.** `refused` never called the model;
`failed` called it and the backend broke under it; `aborted` is what a later writer records for a
generation whose own writer is gone. None names a tip, and the store tells them apart.

**The core takes the terminator and nothing else.** Whatever a refusal carries beyond it — a
message, a code, both — is the adapter's answer to its caller, and this contract does not shape
it.

## Cancellation

The core's `cancelled` terminator records a generation a caller stopped. Reaching it needs a
`generate` that can be interrupted and that returns what it drew, which the blocking form above is
not.

**An adapter that cannot be interrupted never produces `cancelled`.** Stopping one of its
generations means killing the writer, which the next writer records as `aborted`, and which loses
every token the model produced — nodes land only in the core's second write.

**The interruptible form is not the same operation with a way in**, which is what measuring it
settled. A streamed generation on the one backend that exists reports a multi-token character's
final id and drops the ids before it — in no chunk, and on both of its endpoints; that adapter's
notes have the sequences. The loss shows in the token counters and the ids are gone, and reading
them back from the group's bytes is the artefact this format exists to avoid. So a streamed act
would have to be declined, and a generation that could be stopped would be one that dies on an
emoji.

**`cancelled` therefore stays unreached on this backend, and that is a decision rather than a gap.**
It is specified, nothing produces it, and a `generate` short enough to be worth stopping is short
enough to wait for. An adapter whose backend streams *without* losing ids may produce it, and the
core is unchanged either way.

**A client that wants a long generation it can stop may issue it as consecutive acts** over a
shorter `length`, each blocking and each complete, so that stopping is declining to issue the next
one. This is a technique available to a client, not an obligation on one: the command line does
not use it, and what a client that does use it presents as a block of output is its own construct
rather than a unit of the record. Two things follow for such a client, and are easier written down
than discovered:

- **A block can be refused part-way.** Room is checked per act, so a caller may be met five times
  and refused on the sixth. There is no way to check a block up front, because a block is not a
  thing the adapter is ever asked for.
- **Each act carries its own parameters**, so a path is replayed act by act rather than from one
  request.

**It trades a perturbed measurement for a faithful record**, and the trade is not close: acts of a
shorter `length` move the logprobs recorded at a boundary, which *Determinism* is about and which
the format absorbs by construction, while streaming loses ids, which nothing absorbs.

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

**Measured on llama.cpp over Vulkan, single slot: repeating a request is bit-identical, and
changing how many rows it asks for is not quite.** Repeating one reproduced both the path and its
values exactly — a floor of zero — while a request for ten rows and one for forty disagreed by
1.3e-05 on the ranks they shared, reproducibly, and forty against two hundred agreed exactly. That
is a step rather than noise, four thousand times below the two variables below it, and too small
to reorder anything but an exact tie. It is recorded because a floor of zero is what makes it
visible at all, and because *the number of rows asked for* is the one thing here a client changes
casually. That is one backend on one machine with `--parallel 1`, so it is not a general result —
but note that a tree has one writer at a time, so an adapter never sees its own requests batched
together, which is where most of this class of nondeterminism comes from in the first place.

**The cache is the variable that was being held still, and it is worth more than the last decimal
places.** Cold against cold is bit-identical and warm against warm is bit-identical, but cold
against warm differs by up to 0.056 in logprob at the top of a five-row ranking — enough to
reorder a near-tie. That adapter's notes have the numbers. Because each state is internally
reproducible this is a *second variable* rather than noise, and a ranking recorded with the cache
on is a function of the model, the path and what was generated before it. That is the thing
obligation 5 asks a backend not to be. The format would survive either way — ranks are recorded in
the order presented and nothing is ever rewritten — but what survives corruption is not the same
as what is worth recording.

**It is not contamination between calls, which is why either setting is defensible.** The cache is
a pure function of the prompt tokens and no seed reaches it, so warm and cold are two draws from
one distribution rather than one right and one wrong. Distributional statistics are unaffected;
what is lost is exact replay of a *particular* generation, which was already conditional on the
same build, GPU and quantisation.

**A chunk boundary is a third variable of the same size, and it is not the cache's doing.**
Continuing inside one call and starting a fresh call at the same path disagree by up to 0.057 with
the cache off and 0.036 with it on — warm is marginally the *closer* of the two — and both reorder
ranks. It does not decay downstream, because a KV state that differs at all is inherited. Any
client that issues a long generation as consecutive acts — *Cancellation* has the one reason to —
carries this variable in practice rather than in principle.

**Which is bearable only because the disagreement is native to the instrument.** Branching is
already a fresh call at a path first reached by continuing: `realise` then `generate` at an
existing node extends a ranking whose earlier rows were measured mid-flight. A tree has always
held rows from both regimes, and *the format's answer is the one above* — first value written
wins, nothing rewritten. Chunking raises how often that happens; it introduces nothing new.

**So the record names the boundary.** Every act stores its `origin` and its `length`, so a reader
can see where a call started and how far it ran — which is more than the cache case offers, where
nothing in the store says which state a row was measured in. That asymmetry is what settles the
next paragraph.

**`cache_prompt` is a per-call parameter, and required.** It changes the draw, and a backend
handed a request that does not name it applies its own — which is precisely the policy the rule
above requires a parameter against, and the failure the neutralised-sampler list exists to
prevent. It is a parameter and not adapter
configuration because callers differ within one process: the command line asks for correctness and
sends `false`, a reading surface issuing chunked continuations asks for tractable latency and sends
`true`, and one adapter serves both. The core reads only `length` and interns the rest, so this
costs a second `params` row and no change to any table.

**What that buys a reader is per-act attribution and not per-row.** Where one act has ranked at a
node, its `params` says which cache state those rows were measured in. Where several have, the
first value written is the one kept and nothing records which act contributed it — so the answer
narrows to a set rather than resolving. A reader who needs certainty assumes the worst case, as
one always could; a reader who wants to *select* on it now can, in the common case.

## Backends

- **llama.cpp** — `src/tokenloom/adapters/llamacpp/`, exercised against a running server by
  `tests/test_live.py`. Measured behaviour lives in that directory's `README.md`, which is the
  adapter's own notes and binds nothing. Several of the behaviours recorded there produce a
  record that is quietly wrong rather than an error, so it is read before the adapter is touched,
  not after something disagrees.

---

## Status

**What is open, and nothing that has found a home above.**

- **Whether a refusal's reason outlives the call.** The adapter returns one and the calling
  client acts on it, which is all a client has needed so far; *Refusal* says the core takes none
  of it, so a later reader of the tree sees `refused` and no more. Most of that is recoverable —
  a refusal decidable from `params` or from the path is derivable from the act itself. What is
  not is the backend's capacity: a request refused for room, or for a `record_rows` above the
  vocabulary, met a server configuration the tree does not hold, and two servers running one
  model at different context lengths are one source to this format. If this is picked up, the
  cheap form is an adapter recording its capacity in `params`, which the core does not read; the
  fuller one is a nullable reason on the act.
