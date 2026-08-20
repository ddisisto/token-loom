# CLAUDE.md

## What this is

**token loom** — a machine output research tool. Givens go in, generations come out, and the
surface exists to read across them. The tree is a trie over **bytes** with tokens as a
per-span overlay, in `core/`, with two clients on it: `loom.py` for the command line and
`api/` over HTTP, the latter also serving `web/`, the reading surface.

It began as a fork of [socketteer/loom](https://github.com/socketteer/loom) and no longer
shares a line with it — new core, inference, storage, API, surface and documents. The
relationship is conceptual and the credit is real; `DIRECTION.md` states both.

**This file is for things that are true about the code and easy to get wrong.** Direction is
not here. A finding about what a model does is not here either.

## The documents

- **`DIRECTION.md`** is the living document: what this is, where it stands, what v1.0 means,
  and what is deliberately out of scope. Read it first for anything about *where this is
  going*.
- **`FORMAT.md`** is the on-disk format and the reasoning behind it, meant to outlive the
  phases. Worth reading before proposing a change to it — including the one-line rejection
  that nearly kept the wrong answer.
- **`FRONTEND.md` and `INTERACTION.md` are two documents on purpose.** The first holds the
  concept and fourteen numbered constraints; the second holds the elements, the gestures and
  what each action does, and is the thing checked against them. Folding them together leaves
  nothing outside the specifics to hold them to, and the first specific that conflicts with a
  constraint gets fixed by softening the constraint in the same edit. They also rot at very
  different rates.
- **`RESEARCH.md`** is the other thread's landing page; `experiments/` is its record.
- `ROADMAP.md` and `BEYOND-MVP.md` are the MVP's own documents and are being retired into
  `DIRECTION.md`. Treat anything in them as historical unless `DIRECTION.md` repeats it.

## Two threads, one substrate

- **The build.** The API and the reading surface. The MVP has landed and is in daily use;
  v1.0 is the surface becoming a place to read across several actualised paths rather than
  one path with alternatives at hand. `DIRECTION.md` leads it.
- **The research.** Using the instrument — attractors, temperature, framing, retransmission.
  **Parked deliberately**, one cycle in, because the questions get better with more use of
  the tool. Its conventions still bind:

  **An experiment file is written in two commits and not tidied between them** — the
  pre-registration before the run, the results after — so `git log --follow` over one file
  shows whether the predictions moved once the numbers were in. That is the whole of what
  pre-registration buys, and editing an experiment file after its results land spends it.
  Corrections are appended, never merged in.

  **The tree an experiment produced is committed beside its write-up**, as
  `experiments/NNN-name/` next to `experiments/NNN-name.md`. Not in `data/`, which is ignored
  scratch, and not left out because it is binary: a span is not guaranteed to regenerate from
  the conditions it carries, so the artefact *is* the evidence and a write-up citing a tree
  nobody else has is citing nothing. 001 is 1.4MB for 360 spans, which is the scale to reckon
  with. Run logs are not committed; the tree holds every byte they recorded.

  **Committed trees have to be migrated when the format moves.** 001's was gitignored when
  the `given` rename bumped the marker, and stopped loading without anything noticing.
  `data/demo/` survived only because `demo.py --force` could rebuild it — which an experiment
  tree can never do, since rebuilding it would destroy the record.

  **The research thread keeps its own trees.** Since the two-writer guard landed, the two
  threads are also kept apart by the kernel rather than by protocol.

Both are consumers of one substrate, which is why this file is not split: every fact in it is
equally true on both sides. Two things follow:

- **If the build thread finds itself changing `core/`, stop and ask why.** The API sits on
  the substrate; it does not reach into it. The CLI is the reference client and the floor for
  what the surface must be able to reach — if something is missing, it is usually missing
  from both, and it belongs in `core/ops.py` rather than in either client. Three times now
  that was the honest answer.
- **A branch each.** The threads share `core/` and `loom.py` and will otherwise collide. The
  research thread lives on `research`; `main` is the trunk and the build thread's home. Merge
  `main` into `research` freely, and back when something lands that both want.

## What it's for

An instrument for studying what a model does when iterated against itself: attractors in the
prior, how temperature gates access to them, how framing acts as a change of basis, whether
anything survives repeated retransmission. Two things pull on the design:

- **Base-model behaviour matters more than chat quality.** A chat-templated reply is a
  different object than a continuation of the prior. Where the two conflict, favour the raw
  continuation path.
- **Headless and batch use are first-class.** Generation with recorded temperature/seed/length
  metadata and per-token logprobs is what downstream analysis needs. Anything that only works
  by clicking is half-built.

  **There is no export, and none is wanted.** The bulk store *is* the export — the only
  consumer is the research thread, which shares the format and reads the sqlite directly,
  building whatever tooling an experiment waits on. Naming export as an outstanding
  requirement here read as a gap for a while, and it is not one.

## Inference

**Local only.** `scripts/llama-server.sh` serves Qwen2.5-7B **base** (i1-Q4_K_M) on port 8081
as `qwen2.5-7b-base`. ~5.2GB VRAM at 16k context on the GTX 1070, 122 tok/s prompt and
32 tok/s generation.

The stack talks to it on the **native `/completion` endpoint**, not the OpenAI-compatible one
— `core/llama.py`, the only thing in the project that leaves the process. Both return an
identical token payload (`{id, token, bytes, logprob, top_logprobs}`), so the native one is
chosen for what it adds: `stop_type` separating `eos` from `word` from `limit`, where the
compatible layer flattens the first two into `finish_reason: stop`.

Four things measured there that are not obvious:

- **`n_probs` below 1 returns no per-token `bytes`**, not merely no counterfactuals — so
  there is no token overlay at all without it. `top_n >= 1` is a hard requirement.
- **Rank 0 is not always the sampled token.** At temperature 0.9 the sampled token is absent
  from its own top-3 roughly a third of the time, so `tokens` and `counterfactuals` are
  independent records rather than one list with a marked entry.
- **`completion_probabilities` is not the sampled sequence.** It is that sequence regrouped
  onto character boundaries: the server accumulates generated text and emits a record only
  once the accumulation is valid UTF-8, so a character split across several tokens yields
  *one* entry carrying the whole group's bytes but the **last fragment's** id, logprob and
  alternatives. `tokens` — from `return_tokens` — is the real sequence, and `_align` in
  `core/llama.py` walks the two together because an entry's id is its group's final token.
  A merged row records `token_id` and `logprob` as `None` and drops its counterfactuals;
  anything else asserts a correspondence that does not hold. Zero merging measured on English
  prompts, all of it on astral-plane characters and rare CJK. Two consequences: a **sampled**
  span can never end mid-character, so `FORMAT.md`'s `{"b64": …}` serialisation is
  unreachable from generation; and `Token.idx` is an entry index, not a model token index,
  wherever a merge happened.
- **`cache_prompt` is on, and a span is therefore not guaranteed to replay byte for byte.** A
  full cache hit evaluates no prompt tokens, which changes the reduction order enough to
  perturb the logits and occasionally flip a near-tie: the same slice, seed and parameters can
  give a *different* continuation warm than cold. Measured — warm reproduced a stored span's
  20 entries exactly, cold gave 22 and diverged at index 16; on another prompt at 16 tokens
  they agreed completely.

  **This is not contamination between calls, and the distinction is the whole reason it is
  acceptable.** The cache is a pure function of the prompt tokens — no seed reaches it, and
  nothing of one request's sampling survives into the next. What differs is unbiased
  floating-point noise from a different batch shape, so warm and cold are two draws from the
  same distribution rather than one right and one wrong. Distributional statistics are
  unaffected; only bitwise replay of a *particular* span is lost, and that was already
  conditional on the same build, GPU and quantisation.

**Nothing here can reach a hosted model, and that is upstream of the endpoint choice.** The
token core needs per-token ids, bytes and logprobs on a *raw continuation*, and no OpenRouter
provider returns logprobs there — including ones whose `/models/{id}/endpoints` claim
otherwise. There are no true base models left in the hosted catalogue anyway. Adding one
later means a second adapter beside `core/llama.py`, never an entry in a capability table.
Two things measured before that path was retired, worth keeping if it ever returns: provider
choice changes semantics for an identical request (DeepInfra serves `mistralai/mistral-nemo`
as raw continuation, Io Net chat-templates it), and `n` is ignored by most providers so N
continuations are N sequential calls.

Models come from the Hugging Face CLI. `mradermacher/Qwen2.5-7B-i1-GGUF` is a genuine base
GGUF (`base_model: Qwen/Qwen2.5-7B`) in a catalogue that is otherwise almost all Instruct,
and its imatrix quants beat the static ones at identical size.

## Code notes

**One stack.** `core/` is the substrate — `tree.py` spans and interned parameters, `store.py`
the bulk sqlite, `validate.py` the load-time checks, `ops.py` the operations and the derived
reads, `llama.py` generation, `session.py` the three held together with the save ordering.
Two clients sit on it and neither sits on the other: `loom.py` and `api/`.

**The front end is a third shape rather than a third client of the core.** `web/` is a client
of the API, served by the same process off the same origin, and it reaches `core/` through
nothing. If it ever seems to need the core directly, that is the "stop and ask why" case.

**Four suites.** `core_test.py`, `api_test.py` and `node web/web_test.mjs` run with no model;
`llama_test.py` needs the server on 8081. `api_test.py` needs the `web` dependency group —
`uv run --group web python api_test.py`. `llama_test.py:context_limit` needs a *second*
server and skips rather than fails without one:

    CTX=512 PORT=8082 scripts/llama-server.sh --n-gpu-layers 0

CPU-only, because a second GPU instance does not fit in 8GB beside the first.

There is no pytest-and-fixtures suite and that is deliberate: each check is a script that
prints what it asserted and why, which the clean-break format with no migration is what makes
affordable.

### The format, and the three things easy to get wrong

- **Text is `bytes` everywhere in the core.** Every offset is a byte offset, and `len` on a
  `str` counts characters — holding text as a string is wrong on the first non-ASCII
  character and right on every ASCII test. Decoding happens at two edges only: writing the
  file, and display.
- **A token boundary is not always a character boundary.** Measured, not assumed: Qwen2.5
  tokenises `🜁` into three tokens, none valid UTF-8 alone. So a span can end mid-character
  (serialised as `{"b64": …}`), and a slice start can land inside one (`slice_at` nudges it
  forward before the span records it).
- **A position is `(span, offset)`, and nothing else is durable.** A span is written once and
  never cut, so the pair survives every operation. Absolute root-relative offsets are derived
  and do not survive export of a subtree. Runs are derived too — they have no ids, and
  nothing that identifies one may reach storage or the wire.

**Generation is two calls, not one**: `begin_generation` writes provenance, the tree is saved,
then the model is called and `complete` fills in the byte record. That ordering is not
bookkeeping — it makes a crash mid-generation legible, and guarantees no bulk row can name a
span the tree has not heard of.

Generation is an ordinary blocking call. The worker thread, the hand-back queue and the
virtual events silently dropped across threads were artifacts of Tk owning the main loop, and
went with it. Streaming would reintroduce asynchrony deliberately; the format support it needs
— in-flight spans — is already in.

### The derived runs

**`runs` lives in `ops.py` rather than in either client**, precisely because implementing its
rules twice is getting them wrong twice. Two of those rules bite:

- **A branch anchored at byte 0 of a span that also continues makes a run of zero width.**
  That is a fork point rather than a run, and `outline` needs its `resuming` flag to say so —
  without it the case either loses the branch or forks into itself forever.

  **Zero width is not the condition for splicing that node away — zero width *and* having
  children is.** Splicing lifts a node's branches past a point with no text at it, so a
  childless zero-width node has nothing to lift and splicing it merely deletes it. What it
  deleted was a span in flight and a span completed with no bytes, which are the two states
  decision 8 exists to make renderable. The CLI cannot reach either, because it only ever
  renders finished generations.
- **`outline` emits the resuming branch first**, so a fork's children read oldest first: the
  span was there before anything branched off it, and a continuation generated at that point
  is therefore always last. It used to be appended last, which put every new branch second
  from the end and made the surface's "one more, on the right" land on the left instead. The
  wire promises no ordering regardless — `path.mjs:continues` decides which child is on the
  path **by bytes**, and `main.mjs:landed` finds a new card **by the span it holds**. Both
  would be wrong if they trusted the order.

### The API

**One tree per process**, started on a directory. No session registry, no save endpoint —
`core/session.py` writes after every mutation, so saving is not something a client does — and
no `PATCH`, which `api_test.py` asserts by its absence. Positions are `{"span", "offset"}` in
bodies and `s3+9` in query parameters, the grammar `loom.py` parses. Every mutation answers
with the whole tree. Text may arrive as `{"b64": …}` instead of a string.

**One writer per tree directory, and the kernel enforces it.** `Tree.save` rewrites the file
whole, so two writers do not interleave — the later save destroys the earlier one's spans, and
a re-minted span id inherits the dead span's bulk rows. `core/lock.py` is `flock` on the
directory's **own file descriptor**, taken by `Session` when it opens for writing and held for
the life of the process. Four things about it are easy to get wrong:

- **Reads take no lock at all**, not even a shared one, and a reading `Session` is refused by
  nothing. `loom.py show` against a tree a server holds is the case it exists for; `loom.py`'s
  `READS` set is what decides, and anything absent from it is treated as a writer.
- **A reader also does not run in-flight recovery**, because closing a span out as `aborted`
  writes to both halves of the directory. So a reader can see a span in flight that a writer
  would have closed — which is what it is, and the validator has no objection to one.
- **`Session.save` is where a reader is refused**, not each operation, so an operation added
  later cannot forget. The consequence is that a refused mutation has already touched that
  session's *in-memory* tree; nothing reaches the file, and the session's only exit is being
  discarded.
- **The sqlite store cannot stand in for the lock**, and this is settled: the file destroyed
  is `tree.json`, which sqlite cannot see; `store.py` commits after every write and sqlite's
  locks are per-transaction; and WAL exists precisely so readers and writers do not block.
  `locking_mode = EXCLUSIVE` would block readers, which is the one thing that must not happen.

The lock is per process, never per operation — `GET /api/tree` under a running generation is
load-bearing and untouched. The half that catches damage *already* done is validator check 8:
no bulk row may name a span the tree lacks. A soft-deleted span is still in `tree.spans`, so
it is not one of them.

`GET /api/settings` is the only route that needs the model server and 503s without one.
Everything else, including authoring, works with nothing on 8081 — composing a prompt with no
model running is a property of the format, and `api_test.py` asserts it.

### The reading surface

`web/` is ES modules with no build step, and `.mjs` rather than `.js` on purpose — Python's
`mimetypes` already answers `text/javascript` for it, so modules load with nothing configured.
`path.mjs` holds every derivation and touches no document, which is what lets
`node web/web_test.mjs` check them; `fixtures.py` generates that test's input through
`wire.tree_json`, so the fixtures are what the server sends rather than what the test's
author believed it sends. The static mount is last in `api/server.py` and a catch-all keeps
`/api` from falling into it, because a file server answers an unknown POST with 405 rather
than 404.

Three things about it are easy to get wrong from the outside:

- **The model's context is the whole active path** rather than a window onto it, so
  `prompt_length` is `null` — the whole path — and never the path's measured length, which
  would mint a fresh interned parameter set on every generation.
- **Every point in the rendered text resolves to a `(span, offset)`**, which counterfactual
  branching needs and a finished surface cannot be opened up to accept later. On the wire that
  offset is a byte; in the browser a string index counts UTF-16 units, and the two part company
  on the first curly quote a model emits. `web/path.mjs:indexed` is the conversion and it is
  not optional.
- **Branching onto a byte-fallback token is declined by the surface, not by the core.** Such a
  span has no string form, and rendering the path around one would mean decoding across a span
  boundary. `loom.py` keeps the capability; the flyout shows those alternatives unselectable
  with the reason, and a tree already holding one is refused rather than drawn.

**The selection is the path.** Selecting a card routes the cursor onto it, and `route()` is
called from `apply()` rather than from the acts, because the *default* selection has to hold
the invariant too — a batch arriving, a permalink naming a card, and a tree `loom.py` left
elsewhere are all the same case and none is a keystroke. A consequence worth knowing: opening
a tree can move its cursor. Three guards keep it from running away, and `INTERACTION.md` has
them.

**The path is laid out once and drawn twice, and the target section is drawn by neither
copy.** Reading `surface.mjs` as if it renders once will not survive contact. `#above` and
`#below` hold the same flow at the same width, clipped at two different points, with the lower
one translated so it resumes under the card band; the stretch between the two points is the
band's. Three things about it bite: `clip-path` clips **hit-testing** as well as painting,
which is why clicks need no arbitration between the copies; the split is the **line box**,
which `getClientRects()` does not give you (it answers with font boxes, 10px shorter here) and
a zero-width `height: 1lh` mark does; and the band's width is measured against the viewport, so
`html { overflow-y: scroll }` is load-bearing rather than cosmetic — without it the
scrollbar's arrival changes the width that decided the layout that summoned the scrollbar.

**All of this is what v1.0 replaces.** The band becomes columns and the two-copy apparatus
retires with it; see `DIRECTION.md`. Until then it is what is on the screen.

### What was removed, and why not to bring it back

`inference.py`, `models.py`, `params.py`, `util/`, the old `web/`, `smoke_test.py` and
`scripts/web.sh` went with Phase 2 — the OpenAI-compatible path, the capability table, the old
node format and the browser UI that read it. The tag `pre-token-core` has all of it, and git
history has every file that was ever tracked. Dependencies are down to `requests`; fastapi,
uvicorn and httpx are the `web` group, because a tree is usable without them.

**Do not reconstruct any of it from history to solve a new problem.** The capability table
described how hosted providers differ, and the reason it went is upstream of its design: no
hosted provider returns logprobs on a raw continuation, so none of them can feed the token
core whatever shape it speaks.

## Method

What has paid off here, and what it cost to skip.

- **Three stages, and each finds bugs the others cannot.** Lock the decisions in a document,
  stress-test the document, then write code. Ten real faults fell out of Phase 1 in prose that
  would have been expensive in code — including a validator invariant that contradicted soft
  delete and would have fired on every tree after the first delete. The eleventh, which cost a
  format version, fell out only of *using* the finished thing. The twelfth fell out only of
  *running a path nothing had run*: `CONTEXT` was unreachable dead code, because the flag that
  signals it was being raised on as an error. Planning, using and exercising are three
  different instruments and none of them substitutes.
- **Reading deeply is a fourth.** The card band was correct against its own document and wrong
  against an hour of reading, which is what put the column model in `DIRECTION.md`. A design
  that survives review can still be the wrong object.
- **A one-line rejection of a structural option is a warning sign.** The shape that turned out
  to be right was dismissed in a single sentence, aimed at a variant nobody had written down,
  and got as far as being built the other way. Options that would change the shape of the
  format deserve a worked counterexample before they are struck out.
- **A derived value is the easiest thing to get silently wrong**, because nothing disagrees
  with it. Of the five termination reasons, four are reported by the server and one is
  computed — and the computed one was the one that had never once been recorded. Anything
  derived deserves a test that reaches it on purpose, since ordinary use will not.
- **Probe rather than reason, when the question is decidable.** Confident assumptions that a
  throwaway script overturned in minutes: the native and OpenAI endpoints return an *identical*
  token payload; the sampled token is absent from its own top-3 about a third of the time at
  temperature 0.9; `n_probs: 0` drops per-token **bytes**; `🜁` is three tokens, none valid
  UTF-8 alone. The general form — **absence of observation cannot settle a question about what
  is possible.** Ask the vocabulary, not the samples.
- **Test the invariant, not the value.** The test that earned its keep most asserted that an
  operation left a recorded *address* unchanged, not that some field equalled a particular
  pair. Value-equality tests pass on wrong implementations.
- **Arithmetic in a test is code, and nothing checks it.** Phase 1's mistakes were almost all
  in test assertions — miscounted byte lengths, one tautology that could never fail. Compute
  expected values; do not eyeball them.
- When a check fails, ask "is the test wrong or is the code wrong?" before fixing either.
  Twice the honest answer was "the test asks for something the design makes unreachable" —
  which is a finding, and belongs in the docstring.

## Working conventions

- Run bash commands **serially and un-bundled**. No `&&` chains, no shell redirects.
- Multi-line `python -c` gets blocked by the command classifier — write a script into the
  scratchpad and run it. The shell is zsh, so quote globs (`--include='*.py'`) or they are
  eaten before the command sees them.
- Recurring commands go in `scripts/`, which is **committed**. `scripts/api.sh` serves one
  tree over HTTP on 8080; `scripts/llama-server.sh` serves the local base model on 8081 (env
  overrides `REPO`/`FILE`/`ALIAS`/`PORT`/`CTX`); `scripts/loom.sh` is the command-line
  instrument. Both clients take the tree directory from `LOOM_TREE`, default `data/tree`.
- **`data/` holds exactly one committed thing: `data/demo/`**, built by `demo.py --force`.
  `data/*` is gitignored with an explicit exception for it; everything else there is
  disposable scratch, and `data/tree/` is `loom.py`'s default.

  **`demo.py --force` does not reproduce the committed tree — it replaces it.** Measured
  during the `given` rename: a rebuild at the same base seed, against the same server, with
  every interned parameter set byte-identical, differed in **14 of 37 spans**. Most diverge
  after a shared prefix rather than at the first token, which is drift rather than a different
  seed; the cause is not established and the candidates — unrecorded serving flags
  (`--parallel`, batch size, build) and ordinary GPU float nondeterminism — are not
  distinguishable from here. Nothing is contradicted: reproducibility is stated as
  conditions-level, and this is what that buys. The constraint that used to follow from it is
  **gone** — `PLAYBOOKS.md` quoted the tree line by line and has been retired, so rebuilding
  now invalidates nothing but the tree's own identity.
- **The archive is `../archive/`, a sibling of the repo and outside it.** It holds the
  old-format trees (`local.json`, `loom_demo.json` and the rest), `data/backups/`, the dead
  `run.sh`/`screenshot.sh`, and upstream's README screenshots. Nothing there is needed to run
  anything; it is kept because `local.json` in particular is not reproducible. It is
  deliberately not a path inside the repo, so no ignore rule has to defend it. Git history
  still has every file that was once tracked — untracking is not deletion.
- **Read files with whichever tool the harness is steering towards.** This used to say "use
  `Read` rather than `cat`", and it was dropped rather than defended: some sessions inject a
  standing instruction to prefer shell equivalents, and a project rule that contradicts it
  produces a silent coin-flip every turn plus an argument about which authority wins. The
  rules above it are the ones with a reason behind them and they hold either way.
- Fix root causes. A workaround that leaves the original fault in place is not a fix.

## Open threads

Nothing is open at the format level, which is what lets the surface be redesigned without the
format moving.

One cheap probe is outstanding and nothing depends on it: **whether llama-server accepts an
empty prompt.** Generating at the root with no seed authored is reachable — `slice_at` clamps
to `b''` and `slice_start` records as `null` — and would be unconditional sampling from the
prior. Nothing needs the answer; it is noted because "reachable but never run" is exactly the
shape of the `CONTEXT` bug.

Two limitations left deliberately unhandled, both recorded in `FORMAT.md` under "Settled by
measurement" and both with the same root:

- **A generation point placed *inside* a character** has no string form, and `core/llama.py`
  raises rather than guessing.
- **A stop string that does not land on a token boundary** silently loses the bytes the model
  emitted before the match, because llama-server drops trailing entries by the stop string's
  token count and a span's text is what its token rows spell. The alignment in `_read`
  deliberately does *not* second-guess this: a tail is expected under `stop_type: word` and
  undecidable from the response, so only a tail under `limit` or `eos` raises `Incomplete`.

Both are fixed properly by sending and matching on **token ids** rather than text — the
token-replay path, which needs mixed-mode assembly since given spans have no tokens. The UTF-8
regrouping above is a third case with the same root — the server accounts in text, not tokens
— and the first that silently corrupted records rather than merely refusing. Still not worth
pulling token replay forward for, but that ledger now has three entries.

One path is known to be unreachable rather than merely untested: **a sampled span cannot end
mid-character**, because llama-server emits bytes only once they decode. So `FORMAT.md`'s
`{"b64": …}` span serialisation is reachable from authoring and branching but never from
generation — which is exactly the shape of the `CONTEXT` bug. Both live paths are now reached
on purpose in `core_test.py`.

**A zero-width token cannot be clicked, so the surface cannot reach what the record holds.**
An `eos` terminator is an ordinary token row with no bytes — id, logprob and counterfactuals
all present, `begin == end` — so the model's own ranked alternatives to stopping are stored on
every span that ended that way. `web/flyout.mjs:tokenAt` resolves a click with
`t.begin <= offset && offset < t.end`, strictly exclusive at `end`, so no offset can ever match
one. Not an oversight in one branch: it is the only lookup the client has. `loom.py branch s32
4 1` takes that alternative today and no gesture in the browser can. Nothing is wrong in the
core or the format; `FORMAT.md` records the row itself under "Settled by measurement".

**This is not the same gap as a multi-token character, and the difference decides the fix.**
That case *is* reachable — the row has bytes, so it has a glyph — and the flyout says plainly
that a character spelled by several tokens has no alternatives to offer, because llama-server's
regrouping means the record genuinely has none. So one is a pointing problem with a client-side
fix, and the other is a data limitation closed only by token replay. They look alike from the
reader's seat and are opposites underneath.
