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

- **spans** — provenance *and* bytes. One authored or generated stretch, the conditions
  that produced it, and the text it produced. Written once and never touched again.
- **runs** — structure and display. A maximal stretch with no branch point in it, holding
  no bytes of its own: an ordered list of *pieces*, each naming a span and a range within
  it. Boundaries move freely when the tree is split; they carry no meaning of their own.

Generation parameters attach to **spans**. Continuing from a tip without branching extends
a run but starts a new span, so one run may reference several spans at different
temperatures. That is correct and needs to stay expressible.

Putting the bytes on spans rather than runs is what makes "never move once written" true by
construction instead of by discipline. Splitting a run divides a list of integers; it cannot
open a span, so it cannot damage a record. It also leaves exactly one copy of every byte,
so there is no second copy to disagree with. See `PHASE-1.md` for the shape and for the
alternatives this was chosen over.

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

Token data does not live in the tree file. The tree structure and its text stay small JSON;
**the bulk token data goes in an append-only sidecar store**, which Phase 1 settles as
sqlite — random access without loading, an index for the intern table, and somewhere for
later record types to land.

The tree file is still meant to be openable by hand, but it is no longer *readable* as
prose: runs hold pieces rather than text, so following a path by eye means resolving pieces
into spans. That is the accepted cost of one copy of every byte, and the headless driver's
dump is the answer for reading a tree.

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

**Slice start is a parameter too**, not a viewport setting. Two generations from the same
position with different slice starts are different experiments — same prefix, different
amount of it visible — which is "framing acts as a change of basis" made directly
manipulable. It interns like any other parameter, so it costs nothing. Slice start is
fixed for the whole of a run: every token in a span shares one slice, and the steps of a
multi-token run all see the same start rather than a sliding window.

Context size is recorded with it. "Hit the context limit" is uninterpretable without
knowing which limit — `--ctx-size` is a serving choice and `--parallel` divides it.

### Why a span ended

Sampled spans record a **termination reason**: length reached, stop token hit, context
limit reached, or aborted. Whether the model chose to stop or was cut off is exactly the
kind of distinction the attractor question turns on, so this is worth recording
independently of any feature that needs it.

The context-limit case cannot be read off `finish_reason` — the OpenAI-compatible layer
reports `length` both for "reached the requested length" and for "ran out of context",
flattening a distinction llama.cpp's native endpoint makes. Derive it: prompt tokens plus
requested length against `n_ctx` says which wall is coming before it arrives.

## MVP

The intended flow, working well:

1. Enter one or more starting prompts, optionally separated by `<|endoftext|>` or another
   separator.
2. Generate forward, varying parameters, navigating the space that seed creates.

That is the whole of it. The only mutation is branching mid-run.

**Nothing is editable in place, ever.** Recorded bytes are immutable; the only destructive
operation is delete, which cascades. This makes the tree semantically append-only, not just
its storage: every byte offset ever recorded stays valid forever, nothing needs marking
stale, and a recorded slice keeps meaning what it meant when it was written. Initial
prompts are human-authored spans under an empty root, which is already the shape of
`EMPTY_TREE`.

The rule is absolute rather than carved out, because the carve-out — "editable until
something is generated from it" — is the kind of conditional invariant that reads as a
guarantee and is not one. **`PATCH /api/node/{id}` leaves the API entirely.** Its one safe
case is served exactly by delete-and-re-author: a span with no dependents cascades to
nothing, so the two are the same operation with different names. Carrying the old text
into the authoring box is a client-side convenience and no concern of the format.

The consequence is worth stating plainly rather than softening: fixing a typo in a prompt
that has already generated means losing what it generated. That is the honest price of
records that stay true, and it is why forking is cheap.

**Local inference only.** `llama-server` is the target for MVP; the hosted providers in the
capability table stay as they are, and anything they'd need is deferred rather than built.

**The MVP is Phases 0 through 3**: clear the ground, the token core, the API and front end
rebuilt against it, then the reads that make the core legible. Generation control beyond
what the format already records, and streaming, are work *on top* rather than steps toward
it — both are deferred entire to `BEYOND-MVP.md`. Deferring streaming costs nothing later
because the representation it needs lands in Phase 1 regardless, which was the reason for
pulling it forward.

---

## Phase 0 — clear the ground ✅

Done. The ground it cleared is what makes Phase 1 affordable: with tkinter gone the
on-disk format has no second consumer, so it is free to change.

- ✅ **Removed tkinter** — 169 files, 15,747 lines. `main.py`, the view/controller layer,
  `TreeModel`, `call_on_main_thread` and the cross-thread event workaround, the `@event`
  decorator system, and `config/`, whose fewshots, presets, interfaces and transformers all
  fed the expensive half that is not inherited. The surviving surface was **four import
  lines**.
- ✅ **Renamed in the same pass**, because renames are free during a rewrite and expensive
  after. `model.py` meant *MVC* model, not language model, and would have flipped meaning
  silently. "gpt" as a generic word for language model was already literally wrong. `config.py`
  was avoided deliberately: naming a file after the format of its contents rather than its
  subject is how junk drawers start.

  ```
  models.py      registry + capability table     (model.py + util/gpt_util.py)
  params.py      generation parameters           (DEFAULT_GENERATION_SETTINGS)
  inference.py   the generation call             (gpt.py)
  util/          util.py, util_tree.py
  web/           server, tree, generation, static
  ```

  The registry and the capability table merged because they are instances and types of one
  concept, split across two files for historical reasons only. `params.py` is named for what
  Phase 1 makes it — a parameter set as a first-class object with hashing and interning —
  rather than for the bag of defaults it starts as.
- ✅ **Adopted the name.** Repo renamed (GitHub redirects the old URL), package identity
  updated ahead of the rewrite rather than after.
- ✅ **Dropped what tkinter was holding up.** `logit_bias`, a GPT-2 token mask meaningless
  for the models in use; the Janus Celery client, pointed at the original author's own redis
  and called by nothing; and the settings keys nothing reads — preset, template,
  global_context, start, restart. Dependencies went from sixteen to six.
- ✅ **Cheap UI wins**: fork chip shows position (`⑂3/4`); the read pane extends beyond its
  content so the end of the text can reach the top of the window; and **scroll is the
  reader's** — nothing moves the view automatically, with position remembered per tab for
  the browser session. Fork-switch stability fell out of that rather than needing its own
  work, since siblings share their whole prefix.
- ~~Drop the scratchpad~~ — deferred. It is a button that gets ignored, and the container it
  lives in is due a rewrite anyway; removing it now is work done twice.

Local inference is now the default: `params.py` ships `qwen2.5-7b-base`.

## Phase 1 — the token core

One format change, done once, on a clean break. **`PHASE-1.md` is the detailed plan** —
decisions locked, the on-disk shape with a validated worked example, and the build order.
This section is the scope; that file is the design.

- Bytes as the anchor; tokens as a per-span overlay with byte extents.
- Spans hold the bytes and are written once; runs are structure over them, with
  split-at-position as the primitive operation.
- Spans carrying provenance category, model, tokenizer, termination reason, and interned
  parameters.
- **Keep the token `id` and the `bytes` array the server already returns**, for sampled
  tokens and for every counterfactual, and key counterfactuals by id rather than by their
  surface string. `inference.py` currently discards both. `bytes` is the byte extent this
  whole model is anchored on, handed over directly — re-deriving it by encoding the token
  string is lossy for exactly the byte-fallback tokens that split a character, which is the
  case byte anchoring exists to handle. Ids cost ~4 bytes against 150–400 per token, and
  recovering one from its string collides on special tokens with a literal surface form and
  on duplicate vocab entries. Neither can be retrofitted onto trees already generated.
- Tree/bulk storage split, append-only bulk, soft delete.
- Prompt recorded as slice bounds — `(endpoint, start_byte, end_byte)` — not as text.
- **A batch id on every span, minted per generation call.** Pulled forward from the
  deferred generation-control work because it is a field, not a feature: without it the
  siblings of one call are not linkable and a batch cannot be read back as the experiment
  it was. An optional user-supplied name still layers on later.
- **A representation for incomplete spans**, even though streaming is deferred. A span that
  is partial, growing, or abandoned mid-flight has to be expressible now, or streaming
  forces a second format change. A span with no terminator record is in flight; one left in
  flight by a dead process loads as aborted.
- A `token-loom` format marker in the file.
- **No migration.** Existing trees stay historical; `data/local.json` becomes archive JSON,
  readable by hand but not by the app. Equivalent data is cheap to regenerate.
- **A headless driver, landing with the core rather than after it.** Create a tree,
  author, generate, branch, split, dump — with no browser. This is what makes a big-bang
  front-end replacement survivable: the system is exercisable and verifiable before any UI
  exists. It is also the posture the project already claims, that anything which only works
  by clicking is half-built.

Orphan collection disappears with the side table keyed by response id — token data lives
with the tokens, so nothing can be orphaned.

**Two things stay generic, deliberately.** Both are free to decide now and expensive to
change later, and both come from `BEYOND-MVP.md` — nothing there is built in the MVP, but
these two shapes are what keep it additive rather than a second format change.

- **The bulk store is generic over record type**, not named or shaped for tokens. Tokens
  are its first record type, not its definition. Anything else derived per span — an
  embedding being the concrete case — is then a new record type in an existing store,
  sharing its append-only discipline and its eventual vacuum, rather than a parallel
  mechanism.
- **The intern table is generic over parameter set**, not specifically over generation
  settings. Any configuration that gives rise to a span interns the same way.

One related shape in the model, for the same reason: **agency is orthogonal to provenance
category, not a fourth value of it.** A span produced by something driving generation
automatically still has *sampled* tokens; what differs is what initiated it. Provenance
stays a statement about token origin, with room beside it for an optional initiator
reference. Folding the two axes into one enum is what forces the schema change.

## Phase 2 — API and front end, rebuilt

A clean replacement rather than a port. The current API speaks node ids throughout, and a
node-shaped compatibility view over runs and spans would mean carrying the old model's
vocabulary into the thing built to replace it — cheaper in the short run and a permanent
tax after. The old front end keeps working from a tag for as long as it is wanted.

- **Positions, not nodes**, in the API surface. A position is `(path, byte offset)`;
  generation, branching and selection all take one.
- **No edit endpoint.** `PATCH /api/node/{id}` does not come across, per the immutability
  rule above. Delete cascades; authoring creates.
- **Full parameters per call**, rather than server-side settings state. This keeps
  generation reproducible from the request alone, which is what makes the headless path and
  the UI the same client. Last-used settings become a client convenience, not a server
  concern.
- **Token-level rendering** as the default read surface, with runs as the unit of layout.
- Sessions, save/save-as and the tree pane carry over in function, rebuilt against the new
  model.

Deferred out of this phase and recorded in `BEYOND-MVP.md`: the generation-control UI —
stop-token configuration and section-break rendering, a server-side settings store, and
sweeps beyond the batch id that Phase 1 mints. The parts of those that are format-level
are already in Phase 1; what defers is UI.

## Phase 3 — reads and annotation

The last of the MVP. Unlocked by Phase 1 and cheap once Phase 2 has somewhere to put it.

- **Slice-selectable viewport.** Showing the slice that was sent is the first half: when
  viewing a token, the viewport shows exactly what was in context for the span that
  produced it, which makes an otherwise invisible property of the run legible. Slice is a
  property of the span, not of the token, so a selection anywhere in a span resolves to
  that span's slice.

  The second half is that the range is **re-selectable**: drag the start, and generate
  again under that context. This replaces `prompt_length` as a number with direct
  manipulation, and since slice start is a recorded parameter, the result is a comparable
  experiment rather than a transient view.

  Both handles are selectable, and they mean different things:

  - **moving the start** keeps the generation point and changes how much prefix the model
    sees — a new experiment at the same tip
  - **moving the end** moves the generation point itself — a new branch from that earlier
    position, which is the primitive the tree already has
  - **both** is the general case: branch at an earlier position under a restricted context

  The end never floats free of the continuation point because it *is* the continuation
  point. The invariant that a prompt is a contiguous ancestry slice ending at the branch
  point holds by construction, not by prohibition.
- **Bookmarks and tags**, anchored to byte offsets and node ids.
- **Branch to a counterfactual**: at any token, the stored top-N are alternatives the model
  ranked but did not take. Selecting one splits the run and continues from there — no
  generation needed for the branch itself. This is the payoff that makes storing
  counterfactuals worth their size.
- Visual distinction between explored and unexplored forks.
- **Sibling divergence**, as a read over stored token ids: siblings of one batch agree for
  a while and then split, nested rather than at a single point. Measured at 2% of storage
  and so explicitly not a storage feature — see `BEYOND-MVP.md`. The profile it yields is
  the cheapest direct read of the attractor question the instrument exists for.

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

Wants that reach past the MVP but bear on decisions it makes — embeddings and distance, a
generation controller, sibling divergence, token replay under a future inference path — live in
`BEYOND-MVP.md`. Nothing there is built here; the two constraints they impose on Phase 1
are already folded in above.

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
- Vacuum/compaction of the append-only store. When it lands it has one hard constraint:
  bytes still referenced by a surviving span's recorded slice cannot be reclaimed, or
  compaction quietly breaks the records immutability exists to protect.
- **The tkinter app's expensive half is not inherited**: frame inheritance via deepmerge,
  tag scoping over node ancestry, hoisting, canonical paths, memory scoping,
  template/preset resolution. The intended flow needs none of them. Anything wanted later
  gets designed against the token model rather than ported.
- Upstream contribution. PR socketteer/loom#28 is a Tk 9 fix for a front end being removed,
  and upstream has not responded. Moot.
