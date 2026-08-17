# Beyond the MVP

Nothing here is MVP scope, and nothing here should be built before the roadmap lands.
`ROADMAP.md` stays MVP-only until it does, and gets replaced by whatever comes next rather
than extended. This file is where that next thing will start from.

Two kinds of thing live here, and they differ in how settled they are:

- **Deferred from the MVP** — scoped and agreed, just not first. Reads and annotation,
  generation control, and streaming. The first was Phase 3 until the front end took that
  name; the others were phases until the MVP was cut back to the core and an interface on it.
- **Wanted eventually** — recorded now **only** because they bear on decisions the MVP is
  about to make. Embeddings, a generation controller, sibling divergence, token replay.

The test applied to the second kind: *does it force a format change, or does it fit
additively?* Two answers came back as constraints on Phase 1 — the bulk store generic over
record type, the intern table generic over parameter set — and are recorded there.
Everything else fits without the format knowing about it in advance.

---

## Deferred from the MVP

These were phases in their own right until the MVP was cut back to the token core, an
interface on it, and the smallest reading surface that is the instrument rather than a
demonstration of it. They sit *on top* of that rather than lead to it, and none of them is
speculative in the way the rest of this file is — they are scoped, agreed, and simply not
first.

### Reads and annotation

This was Phase 3 until the front end took the name. What it holds is everything the reading
surface could show that is not needed in order to seed, read and choose. Each is a read over
data already stored, and none of them wants anything from the format.

- **The slice viewport.** Showing the slice that was sent makes an otherwise invisible
  property legible: when looking at a token, the viewport shows exactly what was in context
  for the span that produced it. Slice is a property of the span rather than of the token, so
  a selection anywhere in a span resolves to that span's slice. `GET /api/slice` already
  answers it, and reports the nudged start — the slice that would be used rather than the one
  asked for.

  The second half is that the range is **re-selectable**: drag the start, and generate again
  under that context. That replaces `prompt_length` as a number with direct manipulation, and
  since slice start is a recorded parameter the result is a comparable experiment rather than
  a transient view. Both handles are selectable and they mean different things:

  - **moving the start** keeps the generation point and changes how much prefix the model
    sees — a new experiment at the same tip
  - **moving the end** moves the generation point itself — a new branch from that earlier
    position, which is the primitive the tree already has
  - **both** is the general case: branch at an earlier position under a restricted context

  The end never floats free of the continuation point because it *is* the continuation point.
  The invariant that a prompt is a contiguous ancestry slice ending at the branch point holds
  by construction rather than by prohibition.
- **Bookmarks and tags**, anchored to `(span, offset)` — one address, not an offset plus an
  id. A range bookmark is two of them, valid when both lie on one path. These want somewhere
  to keep something the format does not already hold, and the bulk store being generic over
  record type is what makes that a new record type rather than a new mechanism.
- **Sibling divergence as something visible.** The computation is built — `divergence` in
  `core/ops.py`, `loom.py diverge`, and `GET /api/batches/{batch}/divergence` — so what
  defers is only the showing of it. It is the cheapest direct read of the attractor question
  the instrument exists for, and it is currently reachable only by someone who knows to ask.
- **Visual distinction between explored and unexplored forks**, which the tree response
  already carries everything needed to derive.

### The reading surface's next layer

`FRONTEND.md` scopes the front end to seeding, reading and choosing. Four things sit
immediately on top of it, roughly in the order they would arrive:

- **Generating ahead of the request.** A reader who exhausts the alternatives at a tip asks
  for another and waits. Producing one speculatively, before it is asked for, is the first
  thing that would make the surface feel ahead of its reader — and it is the first generation
  the reader did not initiate, which is where an `initiator` key earns its place. Until then
  research trees and reading trees are separated by living in different directories, which is
  the granularity that matters.
- **Parameter control**, which is the generation-control section below seen from the reading
  surface. Its near-absence from the MVP is the point rather than a gap: the surface exposes
  chunk size, whose effect is pacing, and nothing else — so temperature and the rest stop
  being dials and become invisible conditions of the session.
- **Rendering stop tokens as section breaks**, with the grouping toggles beside it —
  sentence, paragraph, bullet, or consecutive stretches of the same — for reading a batch as
  a group rather than following one path through it. Pure client work that costs the server
  nothing.
- **Reading a research tree**, read-only or read-write on a copy. Nothing in the surface
  prevents it and nothing in it is designed for it. The read-only case needs no change
  tracking at all, since a client that issues no mutation has nothing to keep in step.

### Generation control

- **Stop tokens configurable and exposed.** `<|endoftext|>` is in the stream like any other
  token, with no special case except at render time. Generation stops at whichever comes
  first: length, a stop token, or the context limit. Because stopping is a *setting* rather
  than a property of the token, an empty stop list generates straight through EOT — which
  is directly one of the things the instrument is for, and makes the context limit a
  routine terminator rather than an edge case.
- UI toggle: render stop tokens as section breaks.
- **Settings store.** Last-used settings per tab or file, server side. Phase 2 deliberately
  takes full parameters per call instead, so this is a convenience rather than a gap.
- **Sweeps.** Vary parameters across a batch. Interned per-span parameters cover most of it
  and Phase 1 mints the batch id, so what remains is the UI and an optional user-supplied
  **name**. A named batch is an experiment, an unnamed one is just a batch — a distinction
  worth keeping answerable, where defaulting the name to a timestamp would make everything
  look deliberate.

The format-level halves of these are already in Phase 1: the stop list interns with the
other parameters, termination reason distinguishes a stop token from a length limit, and
every span carries its batch id. What defers is interface.

### The prompt cache, and getting byte-exact replay back

`cache_prompt` is **on**, and what it costs is bitwise replay of an individual span. A full
cache hit evaluates no prompt tokens, which changes the reduction order enough to perturb the
logits, which occasionally flips a near-tie. Measured: warm reproduced a stored sequence
exactly, cold diverged from it at index 16 — and at sixteen tokens on another prompt, warm and
cold agreed completely. Late and sometimes, which is the signature of a small unbiased
perturbation rather than a wrong answer.

It was off for a stretch, on the reasoning that recorded conditions ought to reproduce their
span. **That reasoning was wrong in an interesting way.** The cache is a pure function of the
prompt tokens — no seed reaches it, and nothing of one request's sampling survives into the
next — so there is no contamination to argue is harmless. There is only floating-point noise
from a different batch shape, unbiased and uncorrelated with token identity. Warm and cold are
two draws from the same distribution, not one right and one wrong, and every distributional
statistic the research thread computes is unaffected to within that noise.

What was traded away is therefore narrower than it first looked: not correctness, but the
ability to regenerate a *particular* span byte for byte. That guarantee was already
conditional on the same llama.cpp build, the same GPU and the same quantisation. The cache was
one more condition in a list — distinguished only by varying call to call and being invisible,
which is a real objection to *silently* depending on it and not an objection to depending on
it at all.

Three ways back to the stronger form, roughly in order of cost:

- **Make it a parameter and record it.** `cache_prompt` becomes a setting like any other,
  interned with the rest, so every span says which regime produced it. Cheaper than this
  section used to claim: `Tree.intern` hashes whatever dict it is handed and the validator
  does not inspect parameters, so there is no schema to extend and no version to bump. This is
  the one to do when it is wanted. The front end does not want it: the cache being on for
  everything is what it would have asked for.
- **Control the cache explicitly rather than inheriting it.** Cold is a reproducible state;
  warm is only reproducible if you know the history. So byte-exact replay under a warm cache
  needs the cache reset at a known boundary, not merely the flag set — otherwise a span that
  replays today does so by luck. Whether llama-server exposes a clean reset wants checking
  before this is counted on.
- **A second adapter over `transformers`.** Where `past_key_values` is an object the caller
  owns rather than server state it inherits. This does not make warm and cold agree — same
  arithmetic, same perturbation — but it makes the choice explicit and auditable. It is wanted
  anyway for model internals, and that is the reason to build it; cache control is a bonus.

**Making the batch the reproducible unit is not on this list**, having been considered and
rejected. A batch is *n* sequential calls on one prompt, so replaying it from its start ought
to restore its own cache trajectory — but only if the state entering the batch is known, which
is server history nothing records and nothing can verify afterwards. A span that replays
because the cache happened to be warm the same way is a lucky record, not a reproducible one.
It also degenerates for a batch of one, which is what counterfactual branching and every
retransmission chain produce.

### Streaming

The only item that needs generation to stop blocking, and the reason Phase 1 carries a
representation for incomplete spans despite streaming not being built.

- On generation start, add placeholder forks for the `n` requested.
- Loading status after the fork chip: one per fork, progress shown minimally.
- Navigating into an in-progress generation shows it grow in real time.

Deferring this costs nothing later precisely because the format support was pulled forward.
That was the trade made when it was noticed; this is it paying out.

---

## Embeddings and distances

Wanted at some scale, for the obvious reason: "does anything survive repeated
retransmission" is a question about distance, and reading it off text by eye does not
scale past a handful of branches.

### Two different things share the name

- **Text embeddings.** A vector per slice from a small dedicated model. ~4KB at 1024
  dimensions. Cheap, and the case that matters first.
- **Model-internal states.** The residual stream at a token position, from the model doing
  the generating. Qwen2.5-7B is 28 layers of 3584 dimensions, so keeping every layer is
  ~200KB *per token* — around 700× the per-token budget the storage split was sized
  against. One chosen layer is ~7KB and affordable; all layers is not, and the constraint
  is VRAM and disk rather than anything about the design.

The second is the more interesting one for the attractor question and should not be
assumed to follow from the first.

### This does not mean dropping llama.cpp

On the GTX 1070 that would be a downgrade rather than a swap. Qwen2.5-7B at fp16 under
transformers is ~15GB against 8GB of VRAM — it does not fit at all, and the 4-bit
`bitsandbytes` path that would fit is slower than the Q4_K_M currently doing 32 tok/s in
5.2GB at 16k context.

The shape is a **second process, not a replacement**: llama.cpp keeps generation, and
embeddings come from something small running alongside — either another `llama-server` or
transformers, since a 100–300M embedding model fits either way. A second endpoint is a
second adapter beside `core/llama.py` — the capability table that would once have absorbed it
as a dict entry retired with the old stack, and its extension point went with it.

Model-internal states are the exception: those need direct model access, and therefore
transformers, and therefore a real decision about VRAM. Defer it.

### Storage shape

An embedding is a pure function of *(text, model)*. That makes it different from token
data in a way worth respecting rather than flattening:

|                | token data                | embeddings                     |
| -------------- | ------------------------- | ------------------------------ |
| keyed by       | span, positionally        | content hash + embedding model |
| scope          | the tree that produced it | global                         |
| duplicates     | meaningful (provenance)   | wasteful (dedupe for free)     |

Cross-tree comparison is most of the point — comparing runs *is* the experiment — so a
global content-addressed store beats a per-tree sidecar plus a merge step later. Same
mechanism as the bulk store, same append-only discipline, same vacuum; different instance,
different key.

### No vector index for a long time

100k vectors at 1024 dimensions is ~400MB, and brute-force cosine over that is a single
matmul in tens of milliseconds. An approximate index is worth revisiting somewhere near
1M vectors, not before. numpy returns at that point, having just been removed.

---

## Generation controller

Automatic continuation and branch exploration driven by what has already been generated —
logprob statistics, embedding distance, content. The user still decides when to hand over.

This fits what Phase 1 and Phase 2 already define, with one shape caveat and one
discipline.

**The caveat** is recorded in `ROADMAP.md` under Phase 1: agency is orthogonal to
provenance category. A controller-driven span still has *sampled* tokens; what differs is
what initiated it. Keeping those on separate axes is free now and a schema change later.

**The discipline** is to record configuration, not measurements. The controller's inputs
are recomputable — logprob statistics from stored logprobs, distances from stored vectors —
but the threshold that fired is not. So controller settings intern like any other parameter
set and nothing derived gets written down. This is what keeps the storage cost of a
controller close to zero.

Identity needs nothing new. Phase 2 already gives every batch an id automatically with an
optional user-supplied name; a controller *run* — in the sense of one execution, not the
structural sense the format uses — is the same object.

---

## Sibling divergence, and why it is not a storage feature

Parallel continuations from one position share some prefix with each other. The thought was
to dedup that storage and move the run's branch point to where they actually diverge.

**Measured, and the storage case is dead.** The numbers are in `RESEARCH.md`, where the
measurement belongs — it is a read about what the model does, not a fact about files. What
matters here is the two things they settled.

**Sharing is 2% at the working temperature**, rising to 13% only at temperatures the
instrument is not mainly used at. That is not worth a structural change.

> **These numbers reach further than their evidence.** They come from eight siblings on one
> prompt at 0.3, 0.9 and 1.2 — and 0.3 is the lowest band measured. Experiment 001 later found
> fifteen byte-identical duplicates in twenty siblings at 0.1, where the sharing arithmetic is
> completely different. The conclusion is probably still right, because 0.1 is not a regime
> this project works in, but *probably* is the honest word and it was not the word used. Left
> in place rather than cut: they are accurate at the conditions they were taken at, and the
> record of what was actually measured is worth more than a tidier paragraph. The argument
> below does not depend on them.

**And there is no single branch point to move to.** The common prefix of all eight siblings
was zero at every temperature *measured* — see the caveat above; at 0.1 it is not. What exists
is a *trie among the siblings*, nested and plural, so even the display question is "render the
sibling sub-trie" rather than "shift the fork chip down". The framing that motivated merging
was wrong about the shape, and that is the part of this section that carries the argument.

**Single-token stepping is where this gets sharp.** At length 1, prefix-merging degenerates
into counting: N spans over a handful of distinct tokens. The multiplicity *is* the
measurement — an empirical frequency to set against the logprobs recorded alongside it,
which is a real instrument feature and still needs nothing new stored.

Which is the argument against merging in storage rather than merely a reason to defer it.
**Bytes are content and spans are events.** Merging bytes is safe; merging events destroys
multiplicity, and at short lengths multiplicity is the data. Merge-on-insert would also need
a join-on-delete to stay canonical — a structural mutation, in a format that has none at
all, for 2%.

And it is sharper than a cost argument. A span is the structure as well as the record, so
merging two would mean opening one — which is the single thing the format forbids, and the
thing every address recorded anywhere depends on not happening. Prefix merging is not a
deferred feature here; it is off the table for as long as immutability is.

Phase 1 therefore does nothing here beyond what it already does. If a merged *view* of N
siblings over a shared prefix ever looks worthwhile, reaching it is a computation over data
already held, not a recovery of data thrown away — and it stays a read, because the spans
underneath it are the events and cannot be collapsed without losing them.

That read is **built** — `divergence` in `core/ops.py`, `loom.py diverge` at the command line
— and it needed nothing from this file, which is what it was listed here to record. It was
the most valuable unbuilt thing in the project until experiment 001 gave it something to
measure; what it measures is surface convergence, and the genre-level read that would answer
question 1 is still unbuilt and still wants embeddings.

## Token replay instead of re-tokenisation

If inference later moves to transformers, input assembled for a model should reuse the
token ids that model already emitted, where the tokenizer matches, rather than
re-tokenising the text.

Phase 1 carries the two fields this needs — token `id` and the `bytes` array — for reasons
that stand on their own. Beyond that it is input assembly, not storage.

Worth being clear that this is **a fidelity property, not an optimisation**. Concatenating
stored token ids is not the same object as tokenising the concatenated text: BPE merges
across the join, so re-tokenising can hand the model a sequence it never emitted. For an
instrument built around iterating a model against itself, replay is arguably the correct
path and re-tokenisation is the artifact. The two therefore differ in result, which makes
the choice a condition of the run — and conditions intern for free.

Assembly stays mixed-mode regardless. Given spans carry no tokens by design, so any prompt
crossing one tokenises that region and replays the rest. The join question arises at every
given/generated boundary, and is the same question in both directions.
