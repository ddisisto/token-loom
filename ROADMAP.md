# token loom — roadmap to MVP

A fork of [socketteer/loom](https://github.com/socketteer/loom), diverged far enough to
need its own name. Loom wove text blocks; this weaves tokens.

## The model

The tree is a **trie over bytes**, with tokens as an overlay.

What used to be a node is a *slice* — a run between branch points. Branching is an
operation on a **position**, not on a node: generate from anywhere, and if that position
falls mid-run, the run splits. Splitting is cheap and automatic.

Several things that were separate features collapse into that:

- "truncate mid-output to create a fork point" is not an edit — it is what branching
  mid-run already does
- single-token generation is just a length of 1; stepping token by token is a normal way
  to use the instrument, not a special mode
- the prompt sent to the model is a slice, recordable as bounds rather than as text

The user chooses when to sample broadly (many continuations at a position) and when to
sample deeply (one continuation, far). Nothing in the structure privileges either.

### Bytes anchor, tokens overlay

**All positions are byte offsets from the root, along a path.** Tokens are a per-span
overlay carrying their own byte extents.

Token indices cannot be the anchor. They are only well-defined relative to a tokenizer, so
branching from a position with a different model — which comparing models on a shared
prefix requires — puts the same point at a different index in each tokenization, and any
bookmark or slice bound anchored there drifts. Byte-level BPE gives the same problem
within a single model: a token can split a UTF-8 character in half, so character offsets
cannot address token boundaries either.

Byte offsets are tokenizer-independent, and every token boundary is a byte boundary even
under byte-level BPE. Nothing is lost: splitting a run at a token boundary is splitting at
a byte offset, per-token logprobs live inside their span keyed by span-local index, and
token position becomes a derived quantity computed under a stated tokenizer — which is
what it always actually was.

Bytes also exist before any tokenizer does, which is what lets a prompt be composed with
no model server running.

### Two segmentations, kept apart

Over the same bytes there are two independent groupings, and conflating them is the main
way this design can go wrong:

- **runs** — storage and display. A maximal span with no branch point in it. Boundaries
  move when the tree is split; carry no meaning of their own.
- **spans** — provenance. One authored or generated stretch, with the conditions that
  produced it. Never move once written.

Generation parameters attach to **spans**. Continuing from a tip without branching extends
a run but starts a new span, so one run may contain several spans at different
temperatures. That is correct and needs to stay expressible.

### Span provenance

Three categories, extensible later:

- **sampled** — produced by a generation call. Carries tokens, per-token logprobs, top-N
  counterfactuals, and full parameters.
- **counterfactual-selected** — a token the model ranked in its top-N but did not sample,
  chosen by the user. Carries the token and its logprob, and **references the sampled span
  whose top-N it came from** rather than inventing generation parameters it never had.
- **human-authored** — typed by the user. **No tokens.** Bytes only; whatever model reads
  it tokenizes it at generation time.

### Parameters are interned

Single-token stepping makes spans as numerous as tokens, so parameters are hashed and kept
once in a table, with spans referencing them — **not repeated, and not stored as deltas**.
Deltas would make a span's conditions path-dependent: you would replay every change from
the root to know what produced a token, every analysis query would walk ancestry, and
exporting a subtree would lose its baseline. Interning keeps each span self-describing
behind one lookup for the same saving.

Parameters are not the size problem in any case — a parameter set is ~150 bytes against
~150 bytes of top-N counterfactuals *per token*.

### Storage: tree and bulk, split

Token data does not live in the tree file. The tree structure stays small JSON, readable
by a human; **the bulk token data goes in an append-only sidecar store.** Backing store is
an implementation call at Phase 1 (jsonl or sqlite).

The arithmetic that forces this: single-token stepping plus top-N counterfactuals runs
150–400 bytes per token, so a 100k-token tree is 30–40MB — re-serialised on every save if
it were one file. That is reachable in ordinary use, not an extreme case.

**Deletion is soft**, which the append-only store makes nearly free: nothing is rewritten,
the tree marks a subtree dead. A vacuum pass to compact the store is a later option, not
part of MVP. Generated tokens cost real GPU time and token-level editing multiplies the
number of mutations, so destroying them on a keystroke is the wrong default.

### What travels with the data

Tokenizer identity, model, and generation parameters per span. Reproducibility is
**conditions-level, not bit-level** — no GPU float determinism. Any node is representative
under its conditions.

**Seed is per span, never per tree.** Same seed plus same prompt gives byte-identical
output, so a tree-fixed seed would make the N continuations of one position N copies of
each other. The tree holds a *base* seed and per-call seeds derive from it (base plus call
index): siblings stay distinct, and the whole tree still replays. Where a server exposes
no seed, the tree falls back to its creation timestamp as identity.

**Requested top-N is a parameter, not just an observation.** How many counterfactuals came
back is self-apparent from the store, but the server can return fewer than asked at a stop
or a truncation — so the requested value is recorded alongside temperature. Storage is
linear in N; 3 to start, controllable later.

## MVP

The intended flow, working well:

1. Enter one or more starting prompts, optionally separated by `<|endoftext|>` or another
   separator.
2. Generate forward, varying parameters, navigating the space that seed creates.

That is the whole of it. The only mutation is branching mid-run.

**The initial prompt is not editable once it has generated anything** — you fork from the
root instead. This makes the tree semantically append-only, not just its storage: every
byte offset ever recorded stays valid forever, and nothing ever needs marking stale.
Initial prompts are human-authored spans under an empty root, which is already the shape
of `EMPTY_TREE`.

The carve-out that keeps this from being painful: **a human-authored span stays editable
until something is generated from it.** Nothing references it yet, so the invariant holds.
Noticing a typo before you hit generate must not mean starting a new tree.

**Local inference only.** `llama-server` is the target for MVP; the hosted providers in the
capability table stay as they are, and anything they'd need is deferred rather than built.

---

## Phase 0 — clear the ground

Independent of everything else; both tracks reduce the surface later phases touch.

- **Remove tkinter.** Goes: `main.py`, the view/controller layer, `TreeModel`,
  `call_on_main_thread` and the cross-thread event workaround, the `@event` decorator
  system. Stays: `util/util_tree.py`, `gpt.py`, `util/gpt_util.py`, `util/util.py`.
  `model.py` gets **rewritten from required functionality** rather than carved down — what
  is actually used from it is `DEFAULT_MODEL_CONFIG` and `DEFAULT_GENERATION_SETTINGS`,
  imported by `web/` and `smoke_test.py`.
- **Adopt the name**: repo rename (GitHub redirects the old URL), package identity, before
  the `model.py` rewrite rather than after.
- **Drop the scratchpad** (`Tree.scratchpad` / `set_scratchpad`).
- **Cheap UI wins**, useful immediately and unaffected by the format change:
  - fork chip shows position: `⑂3/4`
  - viewport extends beyond content height, so the end of output can scroll near the top
  - scroll position stays stable when switching forks

## Phase 1 — the token core

One format change, done once, on a clean break.

- Bytes as the anchor; tokens as a per-span overlay with byte extents.
- Runs, with split-at-position as the primitive operation.
- Spans carrying provenance category, model, tokenizer, and interned parameters.
- Tree/bulk storage split, append-only bulk, soft delete.
- Prompt recorded as slice bounds — `(endpoint, start_byte, end_byte)` — not as text.
- **A representation for incomplete spans**, even though streaming is Phase 4. A span that
  is partial, growing, or abandoned mid-flight has to be expressible now, or Phase 4 forces
  a second format change.
- A `token-loom` format marker in the file.
- **No migration.** Existing trees stay historical; `data/local.json` becomes archive JSON,
  readable by hand but not by the app. Equivalent data is cheap to regenerate.

Orphan collection disappears with the side table keyed by response id — token data lives
with the tokens, so nothing can be orphaned.

## Phase 2 — generation control

- **Stop tokens explicit**: a configurable list, recorded per span, exposed in the UI.
  `<|endoftext|>` is included in the stream like any other token — no special case except
  at render time. Generation stops at whichever comes first, length or a stop token.
  Because stopping is a *setting* rather than a property of the token, an empty stop list
  generates straight through EOT, which is directly one of the things this instrument is
  for.
- UI toggle: render stop tokens as section breaks.
- **Settings store.** Last-used settings tracked and applied per tab/file. There is no
  settings endpoint today — `/api/generate` is the only thing that persists settings — so
  this is new surface.
- **Sweeps**: vary parameters across a batch. Interned per-span parameters cover most of
  it. Every batch carries an **id** automatically, so its siblings are always linkable; a
  **name** is optional and user-supplied. A named batch is an experiment, an unnamed one is
  just a batch — which keeps the distinction answerable, where defaulting the name to a
  timestamp would make everything look deliberate.

## Phase 3 — reads and annotation

Unlocked by Phase 1 and cheap once it lands.

- **Slice-restricted viewport**: when viewing a node, show exactly the slice that was sent
  to generate it. Makes an otherwise invisible property of the run legible.
- **Bookmarks and tags**, anchored to byte offsets and node ids.
- **Branch to a counterfactual**: at any token, the stored top-N are alternatives the model
  ranked but did not take. Selecting one splits the run and continues from there — no
  generation needed for the branch itself. This is the payoff that makes storing
  counterfactuals worth their size.
- Visual distinction between explored and unexplored forks.

## Phase 4 — streaming

Wanted for MVP, last of the structural work, and the only item that needs generation to
stop blocking. The format support lands in Phase 1; this is the machinery.

- On generation start, add placeholder forks for the `n` requested.
- Loading status after the fork chip: one chip per fork, each showing progress minimally.
- Navigating into an in-progress generation shows it grow in real time.

---

## Open questions

Only one left, and it is a measurement rather than a decision.

**Throughput under broad sampling.** `n` is ignored by providers, so N continuations are N
sequential calls. This is configuration, not code — but it wants measuring early, before
Phase 4, because the answer decides whether the progress chips show genuine concurrency or
sequential progress.

The likely finding is that nothing needs doing. N continuations from one position is the
best case for a prompt cache — identical prefix, repeated immediately — so sequential calls
should pay prompt processing once and generation N times. And `--parallel` is probably the
wrong lever: llama.cpp divides `--ctx-size` across slots, so four slots at 16k leaves 4k
each, trading exactly the context depth this design wants for concurrency it may not need.

Measure before changing anything. Optimise, if at all, at the end of Phase 4.

## Out of scope for MVP

Recorded so they are not re-litigated, not because they are rejected.

- **Migration from the old format.** Historical trees stay historical.
- **A test suite.** `smoke_test.py` plus live use is the posture; the clean-break format
  with no migration is what makes that affordable. The smoke test should cover the token
  path once Phase 1 lands.
- **Hosted providers.** Local inference only; the capability table keeps its entries but
  gets no new work.
- A second model judging, summarising or retransmitting. Generation stays human-gated.
- Prompt library, composition, templating.
- Automation, playbooks, hooks, instrumentation.
- Appending text after a generation (needs more thought first).
- Vacuum/compaction of the append-only store.
- **The tkinter app's expensive half is not inherited**: frame inheritance via deepmerge,
  tag scoping over node ancestry, hoisting, canonical paths, memory scoping,
  template/preset resolution. The intended flow needs none of them. Anything wanted later
  gets designed against the token model rather than ported.
- Upstream contribution. PR socketteer/loom#28 is a Tk 9 fix for a front end being removed,
  and upstream has not responded. Moot.
