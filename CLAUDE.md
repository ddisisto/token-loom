# CLAUDE.md

## What this is

**token loom** — a fork of [socketteer/loom](https://github.com/socketteer/loom),
originally a tkinter interface for exploring language model completions as a branching
tree of text. Upstream went quiet around 2023.

It has stopped being a revival, and has diverged far enough to take its own name. Loom
wove text blocks; this weaves tokens. The tree is a trie over **bytes** with tokens as a
per-span overlay, driven by the web front end in `web/`, with the tkinter app scheduled for
removal.

**`ROADMAP.md` is the living document.** Direction, phases, open questions and what is
deliberately out of scope live there. This file is for things that are true about the code
and easy to get wrong.

`origin` is `ddisisto/loom`, `upstream` is `socketteer/loom`. Work happens on `main`.
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

## API landscape (learned the hard way)

- OpenRouter chat endpoint (`type: openrouter`) returns logprobs but applies a chat template.
- OpenRouter completions endpoint (`type: openrouter-completion`) returns raw continuation but
  **no provider returns logprobs there**, even ones whose `/models/{id}/endpoints` claim to.
- You cannot get both from OpenRouter. This is the central constraint that pushed toward local
  inference (llama.cpp / `llama-server`), where both are available at once.
- Provider choice changes semantics for an identical request: DeepInfra serves
  `mistralai/mistral-nemo` as raw continuation, Io Net chat-templates it. Hence the pinned
  `extra_body: {provider: {order: [...], allow_fallbacks: false}}` on that entry.
- `n` is ignored by most providers (loom issues repeated calls instead); `logit_bias` is
  rejected outright; `echo` is unsupported.
- No true base models remain in the hosted catalogue.
- Local inference resolves the constraint and now works: `scripts/llama-server.sh` serves
  Qwen2.5-7B **base** (i1-Q4_K_M) on port 8081 as model `qwen2.5-7b-base`, giving raw
  continuation *and* top-N counterfactuals per token. ~5.2GB VRAM at 16k context on the
  GTX 1070, 122 tok/s prompt and 32 tok/s generation — fast enough to work in.
- The GGUF catalogue has the same base-model scarcity as the hosted one: a search for
  Qwen2.5-7B returns almost nothing but Instruct. `mradermacher/Qwen2.5-7B-i1-GGUF` is a
  genuine base (`base_model: Qwen/Qwen2.5-7B`), and its imatrix quants are better quality
  at identical size to the static ones.

## Code notes

- Model types are described by `MODEL_TYPES` in `util/gpt_util.py`, merged over
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
- Model configs live in `DEFAULT_MODEL_CONFIG` in `model.py`; API keys resolve through
  `util/gpt_util.py:get_correct_key`, which reads a per-model kwarg first and the environment
  second. `.env` is loaded in `main.py` and is gitignored — it must never reach a commit.
- **Current format, until Phase 1 of the roadmap lands.** A node's token data lives in
  `model_responses`, keyed by response id, with the node holding `generation: {id, index}`.
  Siblings from one call **share** a response id, so anything reasoning about reachability
  must do it over the whole tree — `util/util_tree.py:collect_orphaned_responses` does, and
  runs on delete and on save. The token-based format retires this entirely: token data will
  live with the tokens, so nothing can be orphaned.
- **Until the tkinter app is removed, Tk may only be touched from the main thread.** Virtual
  events (`event_generate`) are queued per-thread and are *silently dropped* across threads —
  they do not raise, they just never fire. `TreeModel.call_on_main_thread()` exists for this;
  use it from any generation worker. Calling `tree_updated()` directly from a worker crashes
  the process with SIGILL. Relatedly, `@event` in `model.py` decorates the method that
  immediately follows it, so inserting a method between the decorator and its target silently
  rebinds it.

## Working conventions

- Run bash commands **serially and un-bundled**. No `&&` chains, no shell redirects.
- Recurring commands go in `scripts/` (gitignored via a `[Ss]cripts` rule, so it holds
  local-only tooling) so they can be pre-authorised once. `scripts/run.sh` launches the
  tkinter app into the top-left quarter of monitor 2; `scripts/screenshot.sh` grabs and crops
  that region, overwriting its output in place so an open editor tab refreshes instead of
  closing. `scripts/web.sh` runs the web backend on 8080; `scripts/llama-server.sh` serves the
  local base model on 8081 (env overrides `REPO`/`FILE`/`ALIAS`/`PORT`/`CTX`).
- Models come from the Hugging Face CLI, installed standalone via
  `uv tool install huggingface_hub` so it stays out of the project venv. Use `hf download -q`
  when capturing the path — without `-q` it prints `path=/...` and the prefix ends up in the
  filename.
- `data/local.json` is not disposable. Any format migration has to carry it.
- Use `Read` on files rather than `cat`.
- Fix root causes. A workaround that leaves the original fault in place is not a fix.

## Open threads

Roadmap-level questions — counterfactual storage volume, experiment identity for sweeps,
what replacing the initial prompt does to recorded slices, seed handling, throughput under
broad sampling — live in `ROADMAP.md` under "Open questions".

The naming thread is closed: **token loom**. The repo rename and package identity land in
Phase 0, before `model.py` is rewritten. Note the name collides with crypto in search
results (`TokenLoom.io` is a Solana service, `LOOM` is an ERC-20 ticker) — a known,
accepted discoverability cost, not an oversight.
