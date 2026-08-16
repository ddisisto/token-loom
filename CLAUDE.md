# CLAUDE.md

## What this is

**token loom** — a fork of [socketteer/loom](https://github.com/socketteer/loom),
originally a tkinter interface for exploring language model completions as a branching
tree of text. Upstream went quiet around 2023.

It has stopped being a revival, and has diverged far enough to take its own name. Loom
wove text blocks; this weaves tokens. The tree is a trie over **bytes** with tokens as a
per-span overlay, in `core/`, driven from the command line by `loom.py`. The tkinter app is
gone; the web front end in `web/` still runs the *old* node format and is what Phase 2
replaces.

**`ROADMAP.md` is the living document** for the build. Direction, phases and what is
deliberately out of scope live there. It stays MVP-only until the MVP lands, then gets
replaced rather than extended. Its companions: `FORMAT.md` is the on-disk format and the
reasoning behind it, meant to outlive the phases; `BEYOND-MVP.md` holds the wants that reach
past the MVP and the constraints they impose now; `RESEARCH.md`, `experiments/` and
`PLAYBOOKS.md` belong to the other thread, below. This file is for things that are true about
the code and easy to get wrong, and it is shared by both.

## Two threads, one substrate

The work has split in two, and the split is worth understanding before picking either up.

- **The build.** An API and a front end, rebuilt against the core. `ROADMAP.md`, Phases 2
  and 3, with `BEYOND-MVP.md` behind it. This is the MVP path and it has an end state.
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

**Both are consumers of one substrate.** `core/` is the instrument; `loom.py` is one client
and the API is the next. That is why this file is not split: every fact in it — bytes as the
anchor, the save ordering, `n_probs >= 1`, the conventions, the method — is equally true on
both sides. Only *direction* forks, and direction lives in the two documents above.

Three things follow:

- **If the build thread finds itself changing `core/`, stop and ask why.** The API should sit
  on the substrate, not reach into it. The CLI is the reference client and the floor for what
  the API must do; if something is missing, it is usually missing from both.
- **A branch each.** The threads share `core/` and `loom.py` and will otherwise collide —
  the research thread wants small CLI additions, the build thread retires `inference.py`,
  `models.py` and `params.py` around it. The research thread lives on `research`; `main` stays
  the trunk and the build thread's home. Merge `main` into `research` freely, and `research`
  back into `main` when something lands that both threads want — a CLI addition, a doc change.
- **Findings go in `RESEARCH.md` (or `experiments/`), facts about the code go here.** A
  measurement of what a model does is not a note about the codebase, and the two rot at
  completely different rates.

**Phase 1 has landed.** The token core is built, tested and usable from the command line,
and the on-disk format is `token-loom/1`. It settled what a position looks like on the wire,
which was the one Phase 2 decision flagged as needing to be made early. `FORMAT.md` has the
shape, the alternatives it was chosen over, and — worth reading before proposing a change to
it — the one-line rejection that nearly kept the wrong one. Phase 2, the API and front end
rebuilt against it, is the current work.

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
OpenAI-compatible one — `core/llama.py`, which does not go through `inference.py`. Both
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
- **`cache_prompt` is off, deliberately, and it costs prompt processing on every call.** A
  full cache hit evaluates no prompt tokens, and that changes the arithmetic enough to change
  what a fixed seed samples — the same slice, seed and parameters reproduce a *different*
  continuation warm than cold. Measured on a recorded span: warm reproduced its 20 stored
  entries exactly, cold and cache-off both gave 22 and diverged at index 16. Conditions that
  only reproduce from the right cache state are not conditions, and the recorded conditions
  are the whole product. `BEYOND-MVP.md` holds the thread for getting the speed back.

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

The hosted entries in `models.py` still work for the old stack and are left alone, but the
new one cannot reach them at all — a deliberate, accepted cost. The reason is upstream of the
endpoint choice: the token core needs per-token ids, bytes and logprobs on a *raw
continuation*, and no OpenRouter provider returns logprobs there. Adding a hosted provider
later means a second adapter beside `core/llama.py`, not an entry in the capability table.
Two things worth keeping in mind if that ever happens:

- **Provider choice changes semantics for an identical request.** DeepInfra serves
  `mistralai/mistral-nemo` as raw continuation; Io Net chat-templates it. Hence the pinned
  `extra_body: {provider: {order: [...], allow_fallbacks: false}}` on that entry.
- `n` is ignored by most providers, so N continuations are N sequential calls; `echo` is
  unsupported.

## Code notes

- **Two stacks coexist, deliberately, until Phase 2 retires the old one.**

  The **new** one is everything Phase 1 built: `core/` (`tree.py` runs/spans/interned
  parameters, `store.py` the bulk sqlite, `validate.py` nine load-time checks, `ops.py` the
  six operations, `llama.py` generation, `session.py` the three held together with the save
  ordering) plus `loom.py` for the command line. `core_test.py` runs with no model;
  `llama_test.py` needs the server.

  The **old** one is `inference.py`, `models.py`, `params.py`, `util/` and `web/`. It still
  runs the browser UI, it is the thing tagged `pre-token-core`, and **the new stack does not
  import any of it** except `util.util.timestamp`. It retires whole in Phase 2 — do not
  migrate it piecemeal, and do not extend it.
- Model types are described by `MODEL_TYPES` in `models.py`, merged over
  `MODEL_TYPE_DEFAULTS`. Adding a provider means adding one entry there, not editing
  `model_type in (...)` tuples across `generate()`, `openAI_generate()` and
  `get_correct_key()` as it used to. Note `sends_echo` (does the request ask for the prompt
  back) is not `echoes_prompt` (does the response contain it) — Together AI accepts the echo
  parameter and ignores it, which is why it needed a special case in one place but not the
  other. Likewise `logprobs_format` is not implied by `endpoint`: `llama-server` answers a
  *completions* request with the *chat*-shaped logprobs payload (`logprobs.content`, a list
  of per-token dicts) rather than the legacy parallel arrays.
- A locally served model has no API key, and the OpenAI client raises rather than sending
  when it cannot resolve an auth method — so `gen()` falls back to the literal string
  `'placeholder'`. Without that, no local entry can work at all.
- Model configs live in `DEFAULT_MODEL_CONFIG` in `models.py`; API keys resolve through
  `models.py:get_correct_key`, which reads a per-model kwarg first and the environment
  second. `.env` is loaded in `web/server.py` and is gitignored — it must never reach a
  commit.
- **The old node format**, still what `web/` reads. A node's token data lives in
  `model_responses`, keyed by response id, with the node holding `generation: {id, index}`.
  Siblings from one call **share** a response id, so anything reasoning about reachability
  must do it over the whole tree — `util/util_tree.py:collect_orphaned_responses` does.
  The token core retires this: token data lives with the tokens, keyed by span, so nothing
  can be orphaned and there is no collection pass.
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
- **One thing about the derived runs**, which is display-only and still bites: a branch
  anchored at byte 0 of a span that also continues makes a run of zero width. That is a fork
  point rather than a run, and `loom.py:outline` needs its `resuming` flag to say so — without
  it the case either loses the branch or forks into itself forever.
- Generation is an ordinary blocking call. The worker thread, the hand-back queue and the
  virtual events silently dropped across threads were artifacts of Tk owning the main loop,
  and went with it. Streaming would reintroduce asynchrony deliberately — it is deferred to
  `BEYOND-MVP.md`, but the format support it needs (in-flight spans) is already in.
- **Generation is two calls, not one**: `begin_generation` writes provenance, the tree is
  saved, then the model is called and `complete` fills in the byte record. That ordering is
  not bookkeeping — it makes a crash mid-generation legible, and guarantees no bulk row can
  name a span the tree has not heard of.
- `logit_bias` no longer exists. It was a GPT-2 token mask, meaningless for the models in
  use and already listed in `drop_params` for every OpenRouter type. `inference.gen()` still
  passes `logit_bias=None` so the request builders below it need no change.

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
  template, which was an accident rather than a decision. `scripts/web.sh` runs the web
  backend on 8080; `scripts/llama-server.sh` serves the local base model on 8081 (env
  overrides `REPO`/`FILE`/`ALIAS`/`PORT`/`CTX`); `scripts/loom.sh` is the command-line
  instrument (`LOOM_TREE` picks the tree directory, default `data/tree`). `run.sh` (the
  tkinter app) and `screenshot.sh` (the browser window) are gone with the front ends they
  drove — both are in the archive below.
- Models come from the Hugging Face CLI, installed standalone via
  `uv tool install huggingface_hub` so it stays out of the project venv. Use `hf download -q`
  when capturing the path — without `-q` it prints `path=/...` and the prefix ends up in the
  filename.
- **`data/` holds exactly one committed thing: `data/demo/`** — `PLAYBOOKS.md` quotes it line
  by line, and `demo.py --force` is the only thing that should rewrite it. `data/*` is
  gitignored with an explicit exception for it. Everything else there is disposable scratch;
  `data/tree/` is `loom.py`'s default.
- **The archive is `../archive/`, a sibling of the repo and outside it.** It holds the
  old-format trees (`local.json`, `loom_demo.json` and the rest), `data/backups/`, the dead
  `run.sh`/`screenshot.sh`, and upstream's README screenshots. Nothing there is needed to run
  anything; it is kept because `local.json` in particular is not reproducible. It is
  deliberately not a path inside the repo, so no ignore rule has to defend it. Git history
  still has every file that was once tracked — untracking is not deletion.
- Use `Read` on files rather than `cat`.
- Fix root causes. A workaround that leaves the original fault in place is not a fix.

## Open threads

Nothing is open at the format level, which is what allows the two threads to run beside each
other: Phase 2 is the build thread's work, `RESEARCH.md`'s "what to run next" is the other's,
and neither needs the format to change.

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
token-replay path in `BEYOND-MVP.md`, which needs mixed-mode assembly since human spans have
no tokens. The UTF-8 regrouping above is a third case with the same root — the server
accounts in text, not tokens — and the first that silently corrupted records rather than
merely refusing. Still not worth pulling token replay forward for, but that ledger now has
three entries.

One path is now known to be unreachable rather than merely untested: **a sampled span cannot
end mid-character**, because llama-server emits bytes only once they decode. So
`FORMAT.md`'s `{"b64": …}` span serialisation is reachable from authoring and branching but
never from generation — which is exactly the shape of the `CONTEXT` bug, and wants a test
that reaches it on purpose rather than an assumption that it works.

The naming thread is closed: **token loom**. The repo rename and package identity land in
Phase 0, before `model.py` is rewritten. Note the name collides with crypto in search
results (`TokenLoom.io` is a Solana service, `LOOM` is an ERC-20 ticker) — a known,
accepted discoverability cost, not an oversight.
