# CLAUDE.md

## What this is

**token loom** — a fork of [socketteer/loom](https://github.com/socketteer/loom),
originally a tkinter interface for exploring language model completions as a branching
tree of text. Upstream went quiet around 2023.

It has stopped being a revival, and has diverged far enough to take its own name. Loom
wove text blocks; this weaves tokens. The tree is a trie over **bytes** with tokens as a
per-span overlay, in `core/`, driven from the command line by `loom.py`. The tkinter app is
gone, and so is the browser front end that ran the old node format — Phase 2 retired it
along with the whole OpenAI-compatible path. `api/` is its replacement's server half and
`web/` its reading surface — built, and not yet lived in.

**`ROADMAP.md` is the living document** for the build. Direction, phases and what is
deliberately out of scope live there. It stays MVP-only until the MVP lands, then gets
replaced rather than extended. Its companions: `FORMAT.md` is the on-disk format and the
reasoning behind it, meant to outlive the phases; `FRONTEND.md` and `INTERACTION.md` are
Phase 3, the concept and the interaction respectively; `BEYOND-MVP.md` holds the wants that
reach past the MVP and the constraints they impose now; `RESEARCH.md`, `experiments/` and
`PLAYBOOKS.md` belong to the other thread, below. This file is for things that are true about
the code and easy to get wrong, and it is shared by both.

**`FRONTEND.md` and `INTERACTION.md` are two documents on purpose.** The first holds the
concept and fourteen numbered constraints; the second holds the elements, the gestures and
what each action does, and is the thing checked against them. Folding them together leaves
nothing outside the specifics to hold them to, and the first specific that conflicts with a
constraint gets fixed by softening the constraint in the same edit. They also rot at very
different rates.

## Two threads, one substrate

The work has split in two, and the split is worth understanding before picking either up.

- **The build.** An API and a front end, rebuilt against the core. The API landed as Phase 2;
  Phase 3 is the front end, and `FRONTEND.md` with `INTERACTION.md` is where it lives.
  `BEYOND-MVP.md` sits behind all of it. This is the MVP path and it has an end state.
- **The research.** Using the instrument that Phase 1 finished — attractors, temperature,
  framing, retransmission. `RESEARCH.md` is the landing page — the questions, what is believed
  about each with its evidence attached, and what to run next; `experiments/` is the record,
  one file per experiment; `PLAYBOOKS.md` is how the moves are made. It has no end state, and
  its instrument already works.

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
  with — if an experiment ever produces enough to make that a bad trade, the honest move is to
  say so in its file rather than to quietly not commit it. Run logs are not committed; the
  tree holds every byte they recorded.

  **Committed trees have to be migrated when the format moves.** 001's was gitignored when the
  `given` rename bumped the marker, and stopped loading without anything noticing. `data/demo/`
  survived only because `demo.py --force` rebuilt it — which an experiment tree can never do,
  since rebuilding it would destroy the record.

**Both are consumers of one substrate.** `core/` is the instrument; `loom.py` is one client
and the API is the next. That is why this file is not split: every fact in it — bytes as the
anchor, the save ordering, `n_probs >= 1`, the conventions, the method — is equally true on
both sides. Only *direction* forks, and direction lives in the two documents above.

Three things follow:

- **If the build thread finds itself changing `core/`, stop and ask why.** The API should sit
  on the substrate, not reach into it. The CLI is the reference client and the floor for what
  the API must do; if something is missing, it is usually missing from both.
- **A branch each.** The threads share `core/` and `loom.py` and will otherwise collide —
  the research thread wants small CLI additions, the build thread retired the old stack
  around it. The research thread lives on `research`; `main` stays
  the trunk and the build thread's home. Merge `main` into `research` freely, and `research`
  back into `main` when something lands that both threads want — a CLI addition, a doc change.
- **Findings go in `RESEARCH.md` (or `experiments/`), facts about the code go here.** A
  measurement of what a model does is not a note about the codebase, and the two rot at
  completely different rates.

**Phases 1 and 2 have landed.** The token core is built, tested and usable from the command
line, the on-disk format is `token-loom/1.1`, and `api/` speaks it over HTTP. Phase 1 settled
what a position looks like on the wire, which was the one Phase 2 decision flagged as needing
to be made early. `FORMAT.md` has the shape, the alternatives it was chosen over, and — worth
reading before proposing a change to it — the one-line rejection that nearly kept the wrong
one.

**Phase 3, the front end, is built and not yet lived in.** `web/` works end to end against a
live model and renders in a real browser; what has not happened is a person reading through
it for an hour, which is the stage that found the faults planning and testing did not in
every phase before this one. It asked the core for two things in the end rather than none —
both small, both recorded below and in `FORMAT.md`.

Three things about it are easy to get wrong from the outside:

- **The model's context is the whole active path** rather than a window onto it, so
  `prompt_length` is `null` — the whole path — and never the path's measured length, which
  would mint a fresh interned parameter set on every generation.
- **Every point in the rendered text resolves to a `(span, offset)`**, which counterfactual
  branching needs and a finished surface cannot be opened up to accept later. On the wire
  that offset is a byte; in the browser a string index counts UTF-16 units, and the two part
  company on the first curly quote a model emits. `web/path.mjs:indexed` is the conversion
  and it is not optional.
- **Branching onto a byte-fallback token is declined by the surface, not by the core.** Such
  a span has no string form, and rendering the path around one would mean decoding across a
  span boundary. `loom.py` keeps the capability; the flyout shows those alternatives
  unselectable with the reason, and a tree already holding one is refused rather than drawn.

`origin` is `ddisisto/token-loom` (GitHub redirects the old `ddisisto/loom`), `upstream` is
`socketteer/loom`. Work happens on `main`. The tag `pre-token-core` preserves the last commit
where the browser UI was the whole instrument.
PR socketteer/loom#28 sent the Tk 9 and threading fixes upstream, partly to probe whether
upstream is still monitored — it isn't, and the fix targets a front end being removed, so
it is moot.

## What it's for

Loom's original framing is a writing instrument — you hold the pen, the model offers
branches. That still holds, but the direction here is closer to an instrument for studying
what a model does when iterated against itself: attractors in the prior, how temperature
gates access to them, how framing acts as a change of basis, whether anything survives
repeated retransmission. Read the interactive tree as one way of looking at that, not the
only one.

Practically this means two things pull on the design:

- **Base-model behaviour matters more than chat quality.** A chat-templated reply is a
  different object than a continuation of the prior. Where the two conflict, favour the raw
  continuation path.
- **Headless and batch use are first-class, not an afterthought.** Generation with recorded
  temperature/seed/length metadata, per-token logprobs, and structured export of the tree
  are the things downstream analysis actually needs. Anything that only works by clicking is
  half-built.

Neither is an argument for gutting the interactive UI. It is an argument for not letting the
UI be the only entry point.

## Inference

**Local only, for MVP.** `scripts/llama-server.sh` serves Qwen2.5-7B **base** (i1-Q4_K_M)
on port 8081 as `qwen2.5-7b-base`. ~5.2GB VRAM at 16k context on the GTX 1070, 122 tok/s
prompt and 32 tok/s generation — fast enough to work in.

The new stack talks to it on the **native `/completion` endpoint**, not the
OpenAI-compatible one — `core/llama.py`, the only thing in the project that leaves the
process. Both
return an identical token payload (`{id, token, bytes, logprob, top_logprobs}`), so the
native one is chosen for what it adds: `stop_type` separating `eos` from `word` from
`limit`, where the compatible layer flattens the first two into `finish_reason: stop`. Two
things measured there that are not obvious:

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
  prompts, all of it on astral-plane characters and rare CJK. Consequences worth keeping in
  mind: a **sampled** span can therefore never end mid-character, so `FORMAT.md`'s `{"b64": …}`
  serialisation is unreachable from generation; and `Token.idx` is an entry index, not a model
  token index, wherever a merge happened.
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
  conditional on the same build, GPU and quantisation. It was off for a stretch on the
  contrary reasoning, which is recorded in `BEYOND-MVP.md` along with the three ways back to
  the stronger form — the first of which is to make it an interned parameter, so a span at
  least says which regime produced it.

It is the only setup that gives **raw continuation and per-token logprobs at once**, and
that pairing is the whole point: a continuation of the prior is a different object than a
chat reply, and the counterfactuals are what makes the tree readable at the token level.
Nothing hosted offers both. OpenRouter's chat endpoint returns logprobs but applies a chat
template; its completions endpoint returns raw continuation but **no provider returns
logprobs there**, including ones whose `/models/{id}/endpoints` claim otherwise. There are
no true base models left in the hosted catalogue anyway.

Finding a genuine base GGUF has the same scarcity problem: a search for Qwen2.5-7B returns
almost nothing but Instruct. `mradermacher/Qwen2.5-7B-i1-GGUF` is real
(`base_model: Qwen/Qwen2.5-7B`), and its imatrix quants beat the static ones at identical
size.

The hosted entries went with `models.py` in Phase 2, and nothing here can reach a hosted
model at all — a deliberate, accepted cost. The reason is upstream of the endpoint choice:
the token core needs per-token ids, bytes and logprobs on a *raw continuation*, and no
OpenRouter provider returns logprobs there. Adding a hosted provider later means a second
adapter beside `core/llama.py`, not an entry in a capability table. Two things measured
then, worth keeping if that ever happens:

- **Provider choice changes semantics for an identical request.** DeepInfra serves
  `mistralai/mistral-nemo` as raw continuation; Io Net chat-templates it. Hence the pinned
  `extra_body: {provider: {order: [...], allow_fallbacks: false}}` on that entry.
- `n` is ignored by most providers, so N continuations are N sequential calls; `echo` is
  unsupported.

## Code notes

- **One stack, since Phase 2 retired the other.** `core/` is the substrate (`tree.py`
  spans/interned parameters, `store.py` the bulk sqlite, `validate.py` the load-time checks,
  `ops.py` the operations and the derived reads, `llama.py` generation, `session.py` the
  three held together with the save ordering). Two clients sit on it and neither sits on the
  other: `loom.py` for the command line, `api/` over HTTP. Four suites — `core_test.py`,
  `api_test.py` and `node web/web_test.mjs` run with no model, `llama_test.py` needs the
  server on 8081.

  **The front end is a third shape rather than a third client of the core.** `web/` is a
  client of the API, served by the same process off the same origin, and it reaches `core/`
  through nothing. If it ever seems to need the core directly, that is the "stop and ask why"
  case above.

  **`web/` is ES modules with no build step, and `.mjs` rather than `.js` on purpose** —
  Python's `mimetypes` already answers `text/javascript` for it, so modules load with nothing
  configured and the extension says what the file is at every reference. `path.mjs` holds
  every derivation and touches no document, which is what lets `node web/web_test.mjs` check
  them; `fixtures.py` generates that test's input through `wire.tree_json`, so the fixtures
  are what the server sends rather than what the test's author believed it sends. The static
  mount is last in `api/server.py` and a catch-all keeps `/api` from falling into it, because
  a file server answers an unknown POST with 405 rather than 404.

  **The path is laid out once and drawn twice, and the target section is drawn by neither
  copy.** Reading `surface.mjs` as if it renders once will not survive contact. `#above` and
  `#below` hold the same flow at the same width, clipped at two different points — the fork
  the reader is standing on, and the end of the run leaving it — with the lower one translated
  so it resumes under the card band. The stretch between the two points is the band's, and
  leaving it in the prose as well is what put a verbatim copy of the selected card directly
  beneath its own card. `INTERACTION.md` has the reasoning; three things about it bite:
  `clip-path` clips **hit-testing** as well as painting, which is why clicks need no
  arbitration between the copies; the split is the **line box**, which `getClientRects()`
  does not give you (it answers with font boxes, 10px shorter here) and a zero-width
  `height: 1lh` mark does; and the band's width is measured against the viewport, so
  `html { overflow-y: scroll }` is load-bearing rather than cosmetic — without it the
  scrollbar's arrival changes the width that decided the layout that summoned the scrollbar.

  What went: `inference.py`, `models.py`, `params.py`, `util/`, `web/`, `smoke_test.py` and
  `scripts/web.sh` — the OpenAI-compatible path, the capability table, the old node format
  and the browser UI that read it. The tag `pre-token-core` has all of it, and git history
  has every file that was ever tracked. Dependencies are down to `requests`; fastapi,
  uvicorn and httpx are the `web` group, because a tree is usable without them.

  **Do not reconstruct any of it from history to solve a new problem.** The capability
  table described how hosted providers differ, and the reason it went is upstream of its
  design: no hosted provider returns logprobs on a raw continuation, so none of them can
  feed the token core whatever shape it speaks. A hosted provider later is a second adapter
  beside `core/llama.py`.
- **The API is one tree per process**, started on a directory. No session registry, no
  save endpoint — `core/session.py` writes after every mutation, so saving is not something
  a client does — and no `PATCH`, which `api_test.py` asserts by its absence. Positions are
  `{"span", "offset"}` in bodies and `s3+9` in query parameters, the grammar `loom.py`
  parses. Every mutation answers with the whole tree.
- **Nothing guards two processes writing one tree directory.** `loom.py` and a running API
  will clobber each other's `tree.json`, and re-minted span ids inherit the dead span's bulk
  rows. Partly caught by validator check 6; stale counterfactual ranks survive it. The fixes
  — a lock on the directory, and a check that no bulk row names a span the tree lacks — are
  in `CLAUDE-HANDOVER.md` and not built.
- **Three things about the format that are easy to get wrong**, all load-bearing:
  - **Text is `bytes` everywhere in the core.** Every offset is a byte offset, and `len` on
    a `str` counts characters — holding text as a string is wrong on the first non-ASCII
    character and right on every ASCII test. Decoding happens at two edges only: writing the
    file, and display.
  - **A token boundary is not always a character boundary.** Measured, not assumed: Qwen2.5
    tokenises `🜁` into three tokens, none valid UTF-8 alone. So a span can end mid-character
    (serialised as `{"b64": …}`), and a slice start can land inside one (`slice_at` nudges it
    forward before the span records it).
  - **A position is `(span, offset)`, and nothing else is durable.** A span is written once
    and never cut, so the pair survives every operation. Absolute root-relative offsets are
    derived, and do not survive export of a subtree. Runs are derived too — they have no ids
    and nothing that identifies one may reach storage or the wire.
- **One thing about the derived runs**, which is layout-only and still bites: a branch
  anchored at byte 0 of a span that also continues makes a run of zero width. That is a fork
  point rather than a run, and `core/ops.py:outline` needs its `resuming` flag to say so —
  without it the case either loses the branch or forks into itself forever. `runs` lives in
  `ops.py` rather than in either client precisely because implementing that rule twice is
  getting it wrong twice.

  **Zero width is not the condition for splicing that node away — zero width *and* having
  children is.** Splicing lifts a node's branches past a point with no text at it, so a
  childless zero-width node has nothing to lift and splicing it merely deletes it. What it
  deleted was a span in flight and a span completed with no bytes, which are the two states
  decision 8 exists to make renderable. Phase 3 found this by asking what the card slider
  would draw; the CLI cannot reach either state, because it only ever renders finished
  generations.
- Generation is an ordinary blocking call. The worker thread, the hand-back queue and the
  virtual events silently dropped across threads were artifacts of Tk owning the main loop,
  and went with it. Streaming would reintroduce asynchrony deliberately — it is deferred to
  `BEYOND-MVP.md`, but the format support it needs (in-flight spans) is already in.
- **Generation is two calls, not one**: `begin_generation` writes provenance, the tree is
  saved, then the model is called and `complete` fills in the byte record. That ordering is
  not bookkeeping — it makes a crash mid-generation legible, and guarantees no bulk row can
  name a span the tree has not heard of.

## Method

What has paid off here, and what it cost to skip.

- **Three stages, and each finds bugs the others cannot.** Phase 1 went: lock the decisions
  in a document, stress-test the document, then write code. Ten real faults fell out in prose
  that would have been expensive in code — including a validator invariant that contradicted
  soft delete and would have fired on every tree after the first delete. The eleventh, which
  cost a format version, fell out only of *using* the finished thing. The twelfth fell out
  only of *running a path nothing had run*: `CONTEXT` was unreachable dead code, because the
  flag that signals it was being raised on as an error. Planning, using and exercising are
  three different instruments and none of them substitutes.
- **A one-line rejection of a structural option is a warning sign.** The shape that turned
  out to be right was dismissed in a single sentence, aimed at a variant nobody had written
  down, and got as far as being built the other way. Options that would change the shape of
  the format deserve a worked counterexample before they are struck out. See "Alternatives
  considered" in `FORMAT.md`.
- **A derived value is the easiest thing to get silently wrong**, because nothing disagrees
  with it. Of the five termination reasons, four are reported by the server and one is
  computed — and the computed one was the one that had never once been recorded. Anything
  derived deserves a test that reaches it on purpose, since ordinary use will not.
- **Probe rather than reason, when the question is decidable.** Confident assumptions that a
  throwaway script overturned in minutes: the native and OpenAI endpoints return an
  *identical* token payload; the sampled token is absent from its own top-3 about a third of
  the time at temperature 0.9; `n_probs: 0` drops per-token **bytes**, not merely
  counterfactuals; `🜁` is three tokens, none valid UTF-8 alone. The general form —
  **absence of observation cannot settle a question about what is possible.** Ask the
  vocabulary, not the samples.
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
- Recurring commands go in `scripts/`, so they can be pre-authorised once. It is **committed**
  — it used to be swallowed by a `[Ss]cripts` rule inherited from a virtualenv gitignore
  template, which was an accident rather than a decision. `scripts/api.sh` serves one tree
  over HTTP on 8080; `scripts/llama-server.sh` serves the local base model on 8081 (env
  overrides `REPO`/`FILE`/`ALIAS`/`PORT`/`CTX`); `scripts/loom.sh` is the command-line
  instrument. Both clients take the tree directory from `LOOM_TREE`, default `data/tree`.
  `run.sh` (the tkinter app), `screenshot.sh` (the browser window) and `web.sh` (the old
  backend) are gone with the front ends they drove; the first two are in the archive below.
- Models come from the Hugging Face CLI, installed standalone via
  `uv tool install huggingface_hub` so it stays out of the project venv. Use `hf download -q`
  when capturing the path — without `-q` it prints `path=/...` and the prefix ends up in the
  filename.
- **`data/` holds exactly one committed thing: `data/demo/`** — `PLAYBOOKS.md` quotes it line
  by line, and `demo.py --force` is the only thing that should rewrite it. `data/*` is
  gitignored with an explicit exception for it. Everything else there is disposable scratch;
  `data/tree/` is `loom.py`'s default.
- **`demo.py --force` does not reproduce the committed tree — it replaces it.** Measured
  during the `given` rename: a rebuild at the same base seed, against the same server, with
  every interned parameter set byte-identical, differed in **14 of 37 spans**. Most diverge
  after a shared prefix rather than at the first token, which is drift rather than a
  different seed; the cause is not established and the candidates — unrecorded serving flags
  (`--parallel`, batch size, build) and ordinary GPU float nondeterminism — are not
  distinguishable from here. Nothing is contradicted: reproducibility is stated as
  conditions-level, and this is what that buys. The practical consequences are what matter.
  Rebuilding invalidates every quoted line in `PLAYBOOKS.md`, so **the demo tree is rebuilt
  only when its content is meant to change**. The rename was therefore applied to
  `data/demo/tree.json` as a two-field text substitution — five `kind` values and the marker,
  six lines, no byte of any span touched — which is the one sanctioned exception to the line
  above, and it is sanctioned precisely because it keeps the record faithful where a rebuild
  would not.
- **The archive is `../archive/`, a sibling of the repo and outside it.** It holds the
  old-format trees (`local.json`, `loom_demo.json` and the rest), `data/backups/`, the dead
  `run.sh`/`screenshot.sh`, and upstream's README screenshots. Nothing there is needed to run
  anything; it is kept because `local.json` in particular is not reproducible. It is
  deliberately not a path inside the repo, so no ignore rule has to defend it. Git history
  still has every file that was once tracked — untracking is not deletion.
- **Read files with whichever tool the harness is steering towards.** This used to say
  "use `Read` rather than `cat`", and it was dropped rather than defended: some sessions
  inject a standing instruction to prefer shell equivalents (`cat`, `sed -n`, heredocs) over
  the file tools, and a project rule that contradicts it produces a silent coin-flip every
  turn plus an argument about which authority wins. The rules below it are the ones with a
  reason behind them and they still hold either way: one operation per call, no `&&` chains,
  no redirecting output to a file to read it back.
- Fix root causes. A workaround that leaves the original fault in place is not a fix.

## Open threads

Nothing is open at the format level, which is what allows the two threads to run beside each
other: Phase 3 is the build thread's work, `RESEARCH.md`'s "what to run next" is the other's,
and neither needs the format to change.

One cheap probe is outstanding and nothing depends on it: **whether llama-server accepts an
empty prompt.** Generating at the root with no seed authored is reachable — `slice_at`
clamps to `b''` and `slice_start` records as `null` — and would be unconditional sampling
from the prior. The MVP requires a character in the seed, so nothing needs the answer; it is
noted because "reachable but never run" is exactly the shape of the `CONTEXT` bug.

Two limitations left deliberately unhandled, both recorded in `FORMAT.md` under "Settled by
measurement" and both with the same root:

- **A generation point placed *inside* a character** has no string form, and `core/llama.py`
  raises rather than guessing.
- **A stop string that does not land on a token boundary** silently loses the bytes the
  model emitted before the match, because llama-server drops trailing entries by the stop
  string's token count and a span's text is what its token rows spell. The alignment in
  `_read` deliberately does *not* second-guess this: a tail is expected under
  `stop_type: word` and undecidable from the response, so only a tail under `limit` or `eos`
  raises `Incomplete`.

Both are fixed properly by sending and matching on **token ids** rather than text — the
token-replay path in `BEYOND-MVP.md`, which needs mixed-mode assembly since given spans have
no tokens. The UTF-8 regrouping above is a third case with the same root — the server
accounts in text, not tokens — and the first that silently corrupted records rather than
merely refusing. Still not worth pulling token replay forward for, but that ledger now has
three entries.

One path is now known to be unreachable rather than merely untested: **a sampled span cannot
end mid-character**, because llama-server emits bytes only once they decode. So
`FORMAT.md`'s `{"b64": …}` span serialisation is reachable from authoring and branching but
never from generation — which is exactly the shape of the `CONTEXT` bug. Closed: both live
paths are now reached on purpose in `core_test.py`, and `FORMAT.md` records which operations
can produce the escape and which cannot.

The naming thread is closed: **token loom**. The repo rename and package identity land in
Phase 0, before `model.py` is rewritten. Note the name collides with crypto in search
results (`TokenLoom.io` is a Solana service, `LOOM` is an ERC-20 ticker) — a known,
accepted discoverability cost, not an oversight.
