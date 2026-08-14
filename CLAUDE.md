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

**`ROADMAP.md` is the living document.** Direction, phases, open questions and what is
deliberately out of scope live there. It stays MVP-only until the MVP lands, then gets
replaced rather than extended. Two companions: `FORMAT.md` is the on-disk format and the
reasoning behind it, and is meant to outlive the phases; `BEYOND-MVP.md` holds the wants
that reach past the MVP and the constraints they impose on decisions made now. This file is
for things that are true about the code and easy to get wrong.

**Phase 1 has landed, and been amended once.** The token core is built, tested and usable
from the command line. Using the `token-loom/1` build surfaced that runs and pieces were a
larger mechanism than the problem: `token-loom/2` replaced them with a parent address on each
span, which deleted `split` outright along with two of nine validator checks and a third that
went tautological. It also settled what a position looks like on the wire, which was the one
Phase 2 decision flagged as needing to be made early. `FORMAT.md` has the shape and the
alternatives. Phase 2 — the API and front end rebuilt against it — is the current work.

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
  `token-loom/1` retires this: token data lives with the tokens, keyed by span.
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
    derived, and do not survive export of a subtree. Run ids are display-only under
    `token-loom/2` and must never reach storage or the wire.
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

- **Plan in prose, then build.** Phase 1 went: lock the decisions in a document, stress-test
  it, *then* write code. Ten real faults fell out in prose that would have been expensive in
  code — including a validator invariant that contradicted soft delete and would have fired
  on every tree after the first delete. Prose is not sufficient, though: the eleventh fault,
  the one that cost a format version, only fell out of *using* the finished thing. Both
  stages are load-bearing and neither finds the other's bugs.
- **A one-line rejection of a structural option is a warning sign.** `token-loom/1` dismissed
  the shape that turned out to be right in a single sentence, aimed at a variant nobody had
  written down. Options that would change the shape of the format deserve a worked
  counterexample before they are struck out. See "Alternatives considered" in `FORMAT.md`.
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
- Recurring commands go in `scripts/` (gitignored via a `[Ss]cripts` rule, so it holds
  local-only tooling) so they can be pre-authorised once. `scripts/web.sh` runs the web
  backend on 8080; `scripts/llama-server.sh` serves the local base model on 8081 (env
  overrides `REPO`/`FILE`/`ALIAS`/`PORT`/`CTX`); `scripts/loom.sh` is the command-line
  instrument (`LOOM_TREE` picks the tree directory, default `data/tree`);
  `scripts/screenshot.sh` grabs and crops the browser window, overwriting its output in place
  so an open editor tab refreshes instead of closing — run it bare, with no arguments.
  `scripts/run.sh` launched the tkinter app and is now dead.
- Models come from the Hugging Face CLI, installed standalone via
  `uv tool install huggingface_hub` so it stays out of the project venv. Use `hf download -q`
  when capturing the path — without `-q` it prints `path=/...` and the prefix ends up in the
  filename.
- `data/local.json` is not disposable, and belongs to the **old** format — Phase 1 makes no
  attempt to migrate it, by decision. `data/tree/` is the new stack's default and is
  disposable scratch.
- Use `Read` on files rather than `cat`.
- Fix root causes. A workaround that leaves the original fault in place is not a fix.

## Open threads

**The `token-loom/2` amendment** is the live one — `FORMAT.md` under "Landing the
amendment". It is decided, not open; what is outstanding is the code.

Then **throughput under broad sampling** — `ROADMAP.md` under "Open questions" — which is a
measurement rather than a decision, and is cheap to take: `core/session.py:generate` issues
N sequential calls with `cache_prompt` on, which is the best case for the prompt cache.

One limitation left deliberately unhandled: a generation point placed *inside* a character
has no string form, and `core/llama.py` raises rather than guessing. Fixing it properly means
sending token ids, which is the token-replay path in `BEYOND-MVP.md` and needs mixed-mode
assembly, since human spans have no tokens.

The naming thread is closed: **token loom**. The repo rename and package identity land in
Phase 0, before `model.py` is rewritten. Note the name collides with crypto in search
results (`TokenLoom.io` is a Solana service, `LOOM` is an ERC-20 ticker) — a known,
accepted discoverability cost, not an oversight.
