# Roadmap to MVP

## The model

The tree is a **trie over tokens**, not a tree of text blocks.

What used to be a node is now a *slice* — a run of tokens between branch points. Branching
is an operation on a **position**, not on a node: generate from anywhere, and if that
position falls mid-run, the run splits. Splitting is cheap and automatic.

Several things that were separate features collapse into that one idea:

- "truncate mid-output to create a fork point" is not an edit — it is what branching
  mid-run already does
- single-token generation is just a length of 1; stepping token by token is a normal way
  to use the instrument, not a special mode
- absolute token positions are stable under splitting, so they work as durable anchors
- the prompt sent to the model is a slice, recordable as bounds rather than as text

The user chooses when to sample broadly (many continuations at a position) and when to
sample deeply (one continuation, far). Nothing in the structure privileges either.

### Two segmentations, kept apart

Over the same token sequence there are two independent groupings, and conflating them is
the main way this design can go wrong:

- **runs** — storage and display. A maximal span with no branch point in it. Boundaries
  move when the tree is split; carry no meaning of their own.
- **spans** — provenance. The tokens produced by one generation call, with the conditions
  that produced them. Never move once written.

Generation parameters attach to **spans**. Continuing from a tip without branching extends
a run but starts a new span, so one run may contain several spans at different
temperatures. That is correct and needs to stay expressible.

Single-token stepping makes spans as numerous as tokens, so parameters are **interned, not
repeated and not stored as deltas**: hash the parameter set, keep it once in a table, and
have spans reference it. Deltas would make a span's conditions path-dependent — you would
replay every change from the root to know what produced a token, every analysis query would
walk ancestry, and exporting a subtree would lose its baseline. Interning keeps each span
self-describing behind one lookup for the same saving. Parameters are not the size problem
in any case: a parameter set is ~150 bytes against ~150 bytes of top-N counterfactuals
*per token*.

### What travels with the data

Tokenizer identity, model, and generation parameters per span. Token positions are
per-path and per-tokenizer; concatenating per-node tokenizations is only sound because
generation genuinely resumed at each seam, so the tokenizer has to be recorded, not
assumed.

Reproducibility is **conditions-level, not bit-level**. No GPU float determinism. Record
an RNG seed where the server supports it. Any node is representative under its conditions.

## MVP

The intended flow, working well:

1. Enter one or more starting prompts, optionally separated by `<|endoftext|>` or another
   separator.
2. Generate forward, varying parameters, navigating the space that seed creates.

That is the whole of it. The only mutations are replacing the initial prompt and branching
mid-run.

---

## Phase 0 — clear the ground

Independent of everything else; both reduce the surface the later phases touch.

- **Remove tkinter.** Goes: `main.py`, the view/controller layer, `TreeModel`,
  `call_on_main_thread` and the cross-thread event workaround, the `@event` decorator
  system. Stays: `util/util_tree.py`, `gpt.py`, `util/gpt_util.py`, `util/util.py`.
  `model.py` gets **rewritten from required functionality** rather than carved down — what
  is actually used from it is `DEFAULT_MODEL_CONFIG` and `DEFAULT_GENERATION_SETTINGS`,
  imported by `web/` and `smoke_test.py`.
- **Drop the scratchpad** (`Tree.scratchpad` / `set_scratchpad`).
- **Cheap UI wins**, useful immediately and unaffected by the format change:
  - fork chip shows position: `⑂3/4`
  - viewport extends beyond content height, so the end of output can scroll near the top
  - scroll position stays stable when switching forks

Dropping tkinter is what makes the rest affordable: the on-disk format stops being a
compatibility constraint, leaving only `web/` and existing data files, which are
migratable.

## Phase 1 — the token-based core

One format change, done once. These all touch the same structure; doing them separately
means migrating the data repeatedly.

- Tokens become the record; text is derived. Per-token logprobs and top-N counterfactuals
  stored inline with the run rather than in a side table keyed by response id.
- Runs, with split-at-position as the primitive operation.
- Spans carrying model, tokenizer, and full generation parameters.
- Absolute token positions, stable across splits.
- Prompt recorded as slice bounds — `(endpoint, start, end)` — not as text.
- **Migration** for existing trees. `data/local.json` is not disposable; human-entered text
  needs tokenizing to acquire positions, and existing `model_responses` data has to land on
  the runs it generated.

Orphan collection as it exists today disappears with the side table — token data lives with
the tokens, so nothing can be orphaned.

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
- **Sweeps**: vary parameters across a batch. Per-span parameters cover most of it; what
  remains is whether a batch carries an *experiment identity* linking its siblings, or
  whether that is inferred. Decide before writing sweep code (see open questions).

## Phase 3 — reads and annotation

Everything here is unlocked by Phase 1 and cheap once it lands.

- **Slice-restricted viewport**: when viewing a node, show exactly the slice that was sent
  to generate it. Makes an otherwise invisible property of the run legible.
- **Bookmarks and tags**, anchored to absolute token positions and to node ids.
- **Branch to a counterfactual**: at any token, the stored top-N are alternatives the model
  ranked but did not take. Selecting one splits the run and continues from there — no
  generation needed for the branch itself. This is the payoff that makes storing
  counterfactuals worth their size.
- Visual distinction between explored and unexplored forks.

## Phase 4 — streaming

Wanted for MVP, last of the structural work, and the only item that needs generation to
stop blocking.

- On generation start, add placeholder forks for the `n` requested.
- Loading status after the fork chip: one chip per fork, each showing progress minimally.
- Navigating into an in-progress generation shows it grow in real time.

---

## Open questions

1. **Counterfactual storage volume.** Top-N per token for every token is the bulk of the
   file. Always stored, or a generation setting? Today's `local.json` was 405KB for 19
   responses under the old scheme.
2. **Experiment identity for sweeps** — recorded, or inferred from span timestamps?
3. **Replacing the initial prompt** changes ancestor text and invalidates every recorded
   slice beneath it. Clear the recorded prompts, disallow it once generations exist, or
   mark them stale?
4. **Seed handling** — record always where the server supports it, or only on request?

## Out of scope for MVP

Recorded so they are not re-litigated, not because they are rejected.

- A second model — judging, summarising, retransmitting. Generation stays human-gated.
- Prompt library, composition, templating.
- Automation, playbooks, hooks, instrumentation.
- Appending text after a generation (needs more thought first).
- **The tkinter app's expensive half is not inherited**: frame inheritance via deepmerge,
  tag scoping over node ancestry, hoisting, canonical paths, memory scoping,
  template/preset resolution. The intended flow needs none of them. This closes the open
  thread that has been in `CLAUDE.md` since the web front end began — the answer is "none,
  for MVP", and anything wanted later gets designed against the token model rather than
  ported.
- Upstream contribution. PR socketteer/loom#28 is a Tk 9 fix for a front end being removed,
  and upstream has not responded. Moot.
