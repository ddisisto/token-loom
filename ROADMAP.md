# token loom — roadmap to MVP

A fork of [socketteer/loom](https://github.com/socketteer/loom), diverged far enough to
need its own name. Loom wove text blocks; this weaves tokens.

## The model

The tree is a **trie over bytes**, with tokens as an overlay.

Read "trie" in its general sense — the key is an arbitrary object, and here the key is
`(bytes, the conditions that produced them)`. That is why two generations that emit the same
text are two nodes and not one: they are the same bytes under different conditions, so they
are different keys. It is also why they *would* merge if the conditions were identical too,
which same-seed-same-prompt makes a reachable case rather than a theoretical one.

Branching is an operation on a **position**, not on a node: generate from anywhere, and the
new stretch simply records where it continues from. There is no node to manufacture and
nothing to divide, so branching mid-span costs exactly what branching at a tip costs.

Several things that were separate features collapse into that:

- "truncate mid-output to create a fork point" is not an edit — it is what branching
  mid-span already does
- single-token generation is just a length of 1; stepping token by token is a normal way
  to use the instrument, not a special mode
- the prompt sent to the model is a slice, recordable as bounds rather than as text

A *run* — a stretch between branch points — is still the unit of reading and layout, but it
is **derived** rather than stored. See `FORMAT.md`.

The user chooses when to sample broadly (many continuations at a position) and when to
sample deeply (one continuation, far). Nothing in the structure privileges either.

### Bytes anchor, tokens overlay

**A position is a byte offset into a span** — `(span, offset)`. Tokens are a per-span
overlay carrying their own byte extents.

Offsets are the anchor; the span is what says *which path*, since sibling branches share
their absolute offsets and an offset alone cannot tell them apart. A span is written once
and never cut, so the pair is invariant under every operation there is. Absolute
root-relative offsets are derived from it and stored nowhere — they are also meaningless in
an exported subtree, where a span address still travels.

Token indices cannot be the anchor. They are only well-defined relative to a tokenizer, so
branching from a position with a different model — which comparing models on a shared
prefix requires — puts the same point at a different index in each tokenization, and any
bookmark or slice bound anchored there drifts. Byte-level BPE gives the same problem
within a single model: a token can split a UTF-8 character in half, so character offsets
cannot address token boundaries either.

Byte offsets are tokenizer-independent, and every token boundary is a byte boundary even
under byte-level BPE. Nothing is lost: branching at a token boundary is branching at a byte
offset, per-token logprobs live inside their span keyed by span-local index, and token
position becomes a derived quantity computed under a stated tokenizer — which is what it
always actually was.

Bytes also exist before any tokenizer does, which is what lets a prompt be composed with
no model server running.

### One stored thing, one derived thing

Over the same bytes there are two groupings, and only one of them is written down:

- **spans** — provenance, bytes, *and* structure. One authored or generated stretch, the
  conditions that produced it, the text it produced, and one address naming where it
  continues from. Written once and never touched again.
- **runs** — reading and layout. A maximal chain of spans with no branch point in it.
  **Derived**, computed from the span tree, stored nowhere. Boundaries carry no meaning of
  their own, which is exactly why they should not be persisted.

Generation parameters attach to spans. Continuing from a tip without branching starts a new
span, so one run may cover several spans at different temperatures. That is correct and
needs to stay expressible — and it stays expressible for free once a run is a computed
grouping rather than a record.

An edge in the tree is `(span, byte offset)`, not a node id. That is the whole of why
nothing has to be divided when a branch lands mid-span: a child simply records the offset it
continues from, and the parent is untouched. "Never move once written" becomes true by
construction rather than by discipline, there is exactly one copy of every byte, and exactly
one representation of where each byte sits.

`FORMAT.md` has the shape, the alternatives it was chosen over, and — worth reading before
proposing a change to it — the one-line rejection that nearly kept the wrong answer.

### Span provenance

Three categories, extensible later:

- **sampled** — produced by a generation call. Carries tokens, per-token logprobs, top-N
  counterfactuals, and full parameters.
- **counterfactual-selected** — a token the model ranked in its top-N but did not sample,
  chosen by the user. Carries the token and its logprob, and **references the sampled span
  whose top-N it came from** rather than inventing generation parameters it never had.
- **given** — text that came from outside this tree's generation. **No tokens.** Bytes
  only; whatever model reads
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

The tree file stays openable by hand *and* readable: a span holds its own text and one
address naming its parent, so following a path by eye is following links between strings.
An earlier draft of this document booked "no longer readable as prose" as the accepted cost
of keeping one copy of every byte. That was wrong — the two are unrelated, and the
unreadability came from putting a second structure between the spans and the text. The
headless driver's dump is still the better way to read a large tree.

The arithmetic that forces the tree/bulk split: single-token stepping plus top-N
counterfactuals runs 150–400 bytes per token, so a 100k-token tree is 30–40MB —
re-serialised on every save if it were one file. That is reachable in ordinary use, not an
extreme case.

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
fixed for the whole of a span: every token in one shares a slice, and the steps of a
multi-token generation all see the same start rather than a sliding window.

Context size is recorded with it. "Hit the context limit" is uninterpretable without
knowing which limit — `--ctx-size` is a serving choice and `--parallel` divides it.

### Why a span ended

Sampled spans record a **termination reason**: length reached, a stop string matched, the
model emitting end-of-text, the context limit, or aborted. Whether the model chose to stop
or was cut off is exactly the kind of distinction the attractor question turns on, so this
is worth recording independently of any feature that needs it — and end-of-text is the
model's own choice where a stop string is the operator's, so they are kept apart.

Both halves of this argue for llama.cpp's native endpoint over the OpenAI-compatible one,
which flattens `eos` and `stop` into a single `finish_reason: stop`. Phase 1 measured the
rest: the two return an identical token payload, so nothing is given up by preferring the
one that answers the question.

The context-limit case still has to be derived, because `stop_type: limit` covers both
walls. The cheap derivation is not arithmetic against `n_ctx`: if nothing stopped the
generation and it produced fewer tokens than were asked for, running out of context is the
only thing left that could have.

## MVP

The intended flow, working well:

1. Enter one or more starting prompts, optionally separated by `<|endoftext|>` or another
   separator.
2. Generate forward, varying parameters, navigating the space that seed creates.

That is the whole of it. The only mutation is branching mid-span.

**Nothing is editable in place, ever.** Recorded bytes are immutable; the only destructive
operation is delete, which cascades. This makes the tree semantically append-only, not just
its storage: every address ever recorded stays valid forever, nothing needs marking stale,
and a recorded slice keeps meaning what it meant when it was written. Initial prompts are
given spans with no parent — several may coexist, which is what makes `EMPTY_TREE`
literally empty.

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

## Phase 1 — the token core ✅

Built and landed as `token-loom/1.1`. **`FORMAT.md` is the format document** — decisions
locked, the on-disk shape with a worked example, and the alternatives each choice was made
over. It also settled the one Phase 2 decision flagged as needing to be made early: what a
position looks like on the wire.

The shape as built: `core/tree.py` (structure, spans, interned parameters), `core/store.py`
(the bulk store), `core/validate.py` (the load-time checks), `core/ops.py` (the operations),
`core/llama.py` (generation, native), `core/session.py` (the three held together, with the
save ordering), and `loom.py` for the command line.

What the section below described as scope, and what it looks like having been built:

- Bytes as the anchor; tokens as a per-span overlay with byte extents.
- Spans hold the bytes, the structure and their own provenance, and are written once. One
  parent address each, so branching mid-span divides nothing and there is no split
  operation at all.
- Spans carrying provenance category, model, tokenizer, termination reason, and interned
  parameters.
- **Keep the token `id` and the `bytes` array the server already returns**, for sampled
  tokens and for every counterfactual, and key counterfactuals by id rather than by their
  surface string. `bytes` is the byte extent this whole model is anchored on, handed over
  directly — re-deriving it by encoding the token string is lossy for exactly the
  byte-fallback tokens that split a character, which is the case byte anchoring exists to
  handle, and which Qwen2.5 has been measured to produce for rare scripts and emoji. Ids
  cost ~4 bytes against 150–400 per token, and recovering one from its string collides on
  special tokens with a literal surface form and on duplicate vocab entries. Neither can be
  retrofitted onto trees already generated.
- **A native `llama-server` adapter rather than a patched `inference.py`.** The existing
  path is built around the OpenAI-compatible surface and a capability table describing how
  providers differ, and neither survives contact with one local server — two thirds of it
  is unreachable, and `seed`, which the whole design rests on, was never in the request at
  all. The decisive point is upstream of the endpoint: no hosted provider returns logprobs
  on a raw continuation, so none of them can feed the token core whatever shape it speaks.
  `inference.py`, `models.py` and `params.py` were left untouched and retired together in
  Phase 2. Accepted cost: adding a hosted provider later is a second adapter rather than
  one entry in the capability table.
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
  author, generate, branch, delete, dump — with no browser. This is what makes a big-bang
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

## Phase 2 — API ✅, front end next

A clean replacement rather than a port. The old API spoke node ids throughout, and a
node-shaped compatibility view over the new model would have meant carrying the old
vocabulary into the thing built to replace it — cheaper in the short run and a permanent tax
after. It was retired whole rather than ported: `inference.py`, `models.py`, `params.py`,
`util/`, `web/` and `smoke_test.py` are gone, and the tag `pre-token-core` holds them.

**The server half is built** — `api/server.py` for the routes, `api/wire.py` for the
encoding, `api_test.py` for 62 checks that need no model. What it settled beyond the
scope below:

- ✅ **Positions, not nodes**, in the API surface. A position is `(span, byte offset)`;
  generation, branching and selection all take one. Nothing else appears on the wire — in
  particular, derived run ids never do, because a derived grouping renumbers.
- ✅ **No edit endpoint.** `PATCH /api/node/{id}` does not come across, per the immutability
  rule above. Delete cascades; authoring creates. Asserted by its absence, because a rule
  nothing tests is one a later convenience quietly reverses.
- ✅ **Full parameters per call**, rather than server-side settings state. This keeps
  generation reproducible from the request alone, which is what makes the headless path and
  the UI the same client. `GET /api/settings` says what the server would fill in, so a
  client can send it rather than rely on the server to.
- ✅ **One tree per process**, the directory a launch argument. No session registry and no
  active session for a mutation to be ambiguous about; several trees are several processes.
- ✅ **No save endpoint.** Sessions and save/save-as were listed here as carrying over "in
  function", and they do: the function of save is the save ordering in `core/session.py`,
  which writes after every mutation, and the function of save-as is copying a directory.
- ✅ **Every mutation answers with the whole tree**, so no client keeps a second model of the
  structure. Affordable because the tree file is small by construction and the bulk data is
  deliberately elsewhere.
- **Token-level rendering** as the default read surface, with runs as the unit of layout —
  the front end's work, and what remains of this phase. Runs are derived in `core/ops.py`
  and travel as composition with no ids, so the layout unit is available without the client
  computing it.

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
- **Bookmarks and tags**, anchored to `(span, offset)` — one address, not an offset plus a
  node id. A range bookmark is two of them, valid when both lie on one path.
- **Branch to a counterfactual**: at any token, the stored top-N are alternatives the model
  ranked but did not take. Selecting one anchors a new span at that token's offset — no
  generation needed for the branch itself, and nothing divided to make room for it. This is the payoff that makes storing
  counterfactuals worth their size.
- Visual distinction between explored and unexplored forks.
- **Sibling divergence**, as a read over stored token ids: siblings of one batch agree for
  a while and then split, nested rather than at a single point. Measured at 2% of storage
  and so explicitly not a storage feature — see `BEYOND-MVP.md`. The profile it yields is
  the cheapest direct read of the attractor question the instrument exists for.

---

## Out of scope for MVP

Recorded so they are not re-litigated, not because they are rejected.

Wants that reach past the MVP but bear on decisions it makes — embeddings and distance, a
generation controller, sibling divergence, token replay under a future inference path — live in
`BEYOND-MVP.md`. Nothing there is built here; the two constraints they impose on Phase 1
are already folded in above.

- **Throughput and any other optimisation.** `n` continuations are `n` sequential calls,
  which is the best case for a prompt cache — identical prefix, repeated immediately — and
  `--parallel` is the wrong lever anyway, since llama.cpp divides `--ctx-size` across slots
  and trades the context depth this design wants for concurrency it may not need. None of
  that needs settling before there is something to be slow.
- **Migration from the old format.** Historical trees stay historical.
- **A test suite**, in the pytest-and-fixtures sense. What exists instead is three
  executable checks — `core_test.py`, `api_test.py`, `llama_test.py` — each a script that
  prints what it asserted and why. The clean-break format with no migration is what makes
  that affordable. `smoke_test.py` retired with the stack it smoke-tested.
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
