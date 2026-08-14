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

## Sibling divergence

Parallel continuations from one position share some prefix with each other. The thought was
to dedup that storage and move the run's branch point to where they actually diverge.

Measured first, against the local base model — eight continuations of 32 tokens from one
position, seeded distinctly:

| temperature | common prefix, all 8 | distinct paths by depth | fully diverged | storage saved |
| ----------- | -------------------- | ----------------------- | -------------- | ------------- |
| 0.3         | 0 tokens             | 2, 2, 2, 5, 5, 5, 6, 7  | depth 13       | 13.4%         |
| 0.9         | 0 tokens             | 3, 7, 8, 8, 8, 8, 8, 8  | depth 3        | 2.3%          |
| 1.2         | 0 tokens             | 4, 7, 8, 8, 8, 8, 8, 8  | depth 3        | 2.0%          |

Two things follow, and they point opposite ways.

**The storage case is dead.** 2% at the working temperature is not worth a structural
change, and the saving only becomes interesting at temperatures the instrument is not
mainly used at.

**The structure is not what the framing assumed.** There is no single branch point to move
to: the common prefix of all eight was zero at every temperature. What exists is a *trie
among the siblings* — at 0.3, eight continuations are two distinct paths for three tokens,
then five, then seven. Divergence is nested and plural, so the display question is "render
the sibling sub-trie", not "shift the fork chip down". That is most of why it needs a spike.

The profile itself is the interesting artifact. "Eight samples, two paths, three tokens
deep" is the attractor question answered as a number, and it needs no format support —
comparing sibling token sequences is a read-layer computation over data Phase 1 already
stores.

**Single-token stepping is where this gets sharp.** At length 1, prefix-merging degenerates
into counting: N spans over a handful of distinct tokens. The multiplicity *is* the
measurement — an empirical frequency to set against the logprobs recorded alongside it,
which is a real instrument feature and still needs nothing new stored.

Which is the argument against merging in storage rather than merely a reason to defer it.
**Bytes are content and spans are events.** Merging bytes is safe; merging events destroys
multiplicity, and at short lengths multiplicity is the data. Merge-on-insert would also need
a join-on-delete to stay canonical — a structural mutation, in a format that has none at
all, for 2%.

That last point got sharper with `token-loom/2`. Spans are now the structure as well as the
record, so a merge would have to open one — which is the single thing the format forbids.
Prefix merging is not a deferred feature here; it is off the table for as long as
immutability is.

Phase 1 therefore does nothing here beyond what it already does. If a merged *view* of N
siblings over a shared prefix ever looks worthwhile, reaching it is a computation over data
already held, not a recovery of data thrown away — and it stays a read, because the spans
underneath it are the events and cannot be collapsed without losing them.

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
