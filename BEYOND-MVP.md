# Beyond the MVP

Nothing here is MVP scope, and nothing here should be built before the roadmap lands.
`ROADMAP.md` stays MVP-only until it does, and gets replaced by whatever comes next rather
than extended. This file is where that next thing will start from.

Two kinds of thing live here, and they differ in how settled they are:

- **Deferred from the MVP** — scoped and agreed, just not first. Generation control and
  streaming, which were phases until the MVP was cut back to the core, an interface on it,
  and the reads that make it legible.
- **Wanted eventually** — recorded now **only** because they bear on decisions the MVP is
  about to make. Embeddings, a generation controller, sibling divergence, token replay.

The test applied to the second kind: *does it force a format change, or does it fit
additively?* Two answers came back as constraints on Phase 1 — the bulk store generic over
record type, the intern table generic over parameter set — and are recorded there.
Everything else fits without the format knowing about it in advance.

---

## Deferred from the MVP

These were phases in their own right until the MVP was cut back to "the token core, an
interface built on it, and the reads that make it legible". Both sit *on top* of that
rather than lead to it. Neither is speculative in the way the rest of this file is — they
are scoped, agreed, and simply not first.

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

### The prompt cache, and getting the speed back

`cache_prompt` is **off**, and the cost is real: a batch of twenty continuations from one
position reprocesses the same prompt twenty times instead of once. It was on until a
recorded span turned out not to reproduce from what it carries — a full cache hit evaluates
no prompt tokens, and that changes the arithmetic enough to change what a fixed seed samples.
Warm reproduced the stored sequence exactly; cold and cache-off both diverged from it at
index 16. Off is the setting that matches the stated intent, so off is where it stays for now.

Two ways to have both, neither worth building yet:

- **Record it.** Add the cache state to the interned parameters, so a span says which regime
  produced it. Honest, and it is a format change for a performance feature — the wrong order
  to do things in, and the reason it is here rather than in `FORMAT.md`.
- **Make the batch the reproducible unit rather than the span.** A batch is *n* sequential
  calls on one prompt, so replaying it from its start restores its own cache trajectory. This
  costs nothing and is arguably what the batch id was always for. It needs verifying before
  it can be claimed, and the claim is weaker: individual spans stop being independently
  reproducible, which is a real loss for counterfactual branching.

Worth reaching for when a sweep is slow enough to care. Nothing currently is.

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
transformers, since a 100–300M embedding model fits either way. `models.py` absorbs a new
endpoint as one entry in `MODEL_TYPES`, which is what the capability table was rebuilt for.

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

Assembly stays mixed-mode regardless. Human-authored spans carry no tokens by design, so
any prompt crossing one tokenises that region and replays the rest. The join question
arises at every human/generated boundary, and is the same question in both directions.
