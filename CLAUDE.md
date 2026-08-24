# CLAUDE.md

## What this is

**token loom** — a machine output research tool. Givens go in, generations come out, and the
surface exists to read across them. The tree is a trie over **tokens**, in `core/`, with two
clients on it: a command line and an HTTP API, the latter also serving the reading surface.

Inspired by [socketteer/loom](https://github.com/socketteer/loom). No code is shared and none
ever was in this repository; the debt is conceptual and it is real.

**This file is for things that are true about the code and easy to get wrong.** Direction is
not here. A finding about what a model does is not here either.

## Where this came from, and what it is not

This is a second implementation. The first is tagged in this repository and reachable, and
`main` begins from an orphan root — there is no shared history and nothing is merged forward.

**The first one made the tree a trie over bytes**, with tokens as a per-span overlay, and
reached a working instrument that was in daily use. The base unit was the mistake, and it was
load-bearing: positions were byte offsets, so a token boundary that no byte offset could name
was unreachable, a prompt that ended inside a character could not be sent, and the escape
hatches for both had spread into the format, the validator, the wire and the surface. The
argument that put bytes there was cross-model comparison on a shared prefix — addressing one
point in two vocabularies — which was never a requirement of this project and had appeared in
no live document for some time.

**What is kept from it is measurement and method, not code.** Every fact below was paid for
once and does not need paying for again. Everything else starts here.

**This section is temporary.** It exists so the legacy can be referred to while the shape is
being set, and it should be deleted once this repository stands on its own. If it is still
here when the surface is being built, that is a smell.

## The documents

- **`docs/CORE.md`** is what the format *is* — position, span, kind, the token overlay, the
  on-disk shape, the checks, the operations. It carries no arguments and is written against
  one test: can someone implement a reader from it alone? It is meant to be locked early and
  then not move.

Direction, the reading surface and its constraints get their own documents in `docs/` when
there is something to say. **Anything that answers *is it done* goes in exactly one file,
which holds no reasoning of its own and is deleted when it is done.**

**Every fact has one home, and a change moves it rather than copying it.** This is what bit
last time: a decision changed, the old statement of it was left standing somewhere else, and
during the transition — and worse, long after — there was no way to tell which source was
current. Duplication is not the cost; the dangling copy is. So when something changes,
delete or move what it supersedes in the same edit, and if a document earns no reader it is
deleted rather than kept for reference. What is recoverable from history does not need a
second home in the tree.

## What it's for

**Reading what a model does, by branching through its continuations rather than taking one.**
A generation is not an answer to be accepted or rerolled; it is one path among those the
model made available, and the surface exists to hold several of them at once. That much is
the interface this is named after, and the debt is acknowledged.

**What is different is that the record goes down to the token.** Every generation carries
what else was ranked at every position it passed through, so a path can be read against the
alternatives that were live along it — not just against its siblings. A branch can be taken
at a token the model ranked and did not sample. That is the whole reason the tree is a trie
over tokens rather than over text, and it is what the name is for.

Two things pull on the design:

- **Base-model behaviour matters more than chat quality.** A chat-templated reply is a
  different object than a continuation of the prior. Where the two conflict, favour the raw
  continuation path.
- **No capability may be surface-only.** The command line is the reference client and the
  floor: if a thing can be done at all, it can be done without the reading surface. This is
  not a use case, it is a check on where capability is allowed to live — anything reachable
  only by clicking has put itself somewhere the record cannot follow.

**There is no export and none is wanted.** The store is the format; anything that reads it
shares the format.

Controlled research — attractors in the prior, how temperature gates access to them, framing
as a change of basis, what survives repeated retransmission — is where this points, and the
core should not preclude it. It is deliberately not being designed for now. The questions get
better with more use of the instrument, and designing around an experiment nobody has
specified yet is how the last one acquired a base unit it did not need.

## Inference

**Local only.** Qwen2.5-7B **base** (i1-Q4_K_M) on port 8081 as `qwen2.5-7b-base`. ~5.2GB
VRAM at 16k context on a GTX 1070, 122 tok/s prompt and 32 tok/s generation.
`mradermacher/Qwen2.5-7B-i1-GGUF` is a genuine base GGUF in a catalogue that is otherwise
almost all Instruct, and its imatrix quants beat the static ones at identical size.

The stack talks to llama.cpp's **native `/completion` endpoint**, not the OpenAI-compatible
one. Both return an identical token payload — `{id, token, bytes, logprob, top_logprobs}` —
so the native one is chosen for what it adds: `stop_type` separating `eos` from `word` from
`limit`, where the compatible layer flattens the first two into `finish_reason: stop`.

**Nothing here can reach a hosted model, and that is upstream of the endpoint choice.** The
core needs per-token ids, bytes and logprobs on a *raw continuation*, and no OpenRouter
provider returns logprobs there — including ones whose `/models/{id}/endpoints` claim
otherwise. There are no true base models left in the hosted catalogue anyway.

### Measured, and not obvious

- **`n_probs` below 1 returns no per-token `bytes`**, not merely no counterfactuals — so
  there is no token overlay at all without it. `top_n >= 1` is a hard requirement.
- **Rank 0 is not always the sampled token**, and nothing in the response marks which one was
  taken. With `top_k` off it is absent from its own top-3 about a ninth of the time, and at
  the default `top_k: 40` about a thirtieth. Confining sampling to the top `k` and recording
  at least `k` alternatives makes it always present — 64/64 measured at `top_k == n_probs`,
  at temperature 0.9 and 1.5 alike — but still unmarked, so it is found by id and never by
  rank.
- **The returned probabilities are not renormalised over the returned set.** They sum to
  about 0.90 at `k = 3` and 0.96 at `k = 10`, so what is stored is the model's own
  distribution and `top_k` shows up in the record as missing mass rather than as rescaled
  numbers. Truncation is visible instead of being folded in.
- **`completion_probabilities` is not the sampled sequence.** It is that sequence regrouped
  onto character boundaries: the server accumulates generated text and emits a record only
  once the accumulation is valid UTF-8, so a character split across several tokens yields
  *one* entry carrying the whole group's bytes but the **last fragment's** id, logprob and
  alternatives. `tokens` — from `return_tokens` — is the real sequence, and the two must be
  walked together, because an entry's id is its group's final token. Zero merging measured on
  English prompts, all of it on astral-plane characters and rare CJK.

  **The per-fragment bytes cannot be recovered by re-tokenising the group.** Tokenising `🜁`
  in context yields a different leading id than tokenising it alone — `11162` against `9284` —
  so pieces read back that way are not necessarily the tokens that were generated.

  **This is a token-level fault and does not go away with a token-level format.** It is the
  server accounting in text where the record is in tokens, and it is the reason a span's
  rows can disagree with what the model emitted if the alignment is not checked.
- **A stop string that does not land on a token boundary loses bytes the model emitted.** The
  server matches the stop string on *text*, then erases trailing entries by its *token* count,
  so tokens generated before the match go with it. Undecidable from the response, and fixable
  only by matching on ids server-side, which is not ours to change. This is why `CORE.md`
  offers no `stop` parameter and no `stop` terminator — it is the one knob that can silently
  make a span's rows disagree with what was generated.
- **`/completion` accepts a prompt as an array of token ids, and evaluates it verbatim.** The
  same text as two different id sequences gives two different continuations — `tok(" hello")`
  is `[23811]`, `tok(" hel") + tok("lo")` is `[11338, 385]`, and they diverge immediately. The
  server does not re-tokenise. Mixed arrays of strings and ids work and concatenate.
- **An array of only strings is a batch, not a concatenation.** `["a", "b"]` returns a JSON
  *list* of two separate completions, one per element. Any array containing an id is one
  prompt; a single-element string array is one prompt.
- **A prompt that ends inside a character is refused however it is expressed.** As text it
  cannot be decoded to send. As token ids it answers HTTP 500,
  `"The model produced output that does not match the expected Content-only format"` — with
  `n_probs: 0`, with `return_tokens: false`, and under streaming alike. Sending ids does not
  make a mid-character position reachable; only never forming one does.
- **An empty prompt is accepted and generates nothing.** HTTP 200, empty content, no tokens,
  no `completion_probabilities`, `tokens_evaluated: 0`, `stop_type: "none"` — beside counters
  that never entered a generation loop. An empty *string* is not the model's empty context:
  seeding with the end-of-text token generates normally.
- **Special-token literals in authored text are parsed as tokens by default.**
  `<|endoftext|>` is one token, `<|im_start|>` is one, `a<|endoftext|>b` is three.
  `parse_special: false` gives the literal characters instead. **Detokenising either reading
  returns the same string**, so the two are indistinguishable from the bytes. The stored ids
  are what tell them apart — one token against several.
- **`/tokenize` with `with_pieces` returns per-token bytes exactly.** A piece is a JSON string
  when it decodes and a JSON *array of ints* when it does not, so authored text can be
  tokenised into rows carrying real bytes even where a token is a fragment of a character.
  Tokenise/detokenise round-trips byte-exact on all thirteen cases measured, including
  astral-plane characters, zero-width joiners, combining marks and repeated whitespace. This
  is what lets an authored span be stored as tokens with nothing else kept beside them.
- **`cache_prompt` is on, and a span is therefore not guaranteed to replay byte for byte.** A
  full cache hit evaluates no prompt tokens, which changes the reduction order enough to
  perturb the logits and occasionally flip a near-tie: the same slice, seed and parameters can
  give a *different* continuation warm than cold.

  **This is not contamination between calls, and the distinction is why it is acceptable.**
  The cache is a pure function of the prompt tokens — no seed reaches it — so warm and cold
  are two draws from the same distribution rather than one right and one wrong.
  Distributional statistics are unaffected; only bitwise replay of a *particular* span is
  lost, and that was already conditional on the same build, GPU and quantisation.

### Token replay is a fidelity property, not an optimisation

Concatenating stored token ids is not the same object as tokenising the concatenated text:
BPE merges across the join, so re-tokenising can hand the model a sequence it never emitted.
For an instrument built on iterating a model against itself, replay is the correct path and
re-tokenisation the artefact. This is why the format stores tokens and derives bytes, rather
than the reverse.

It follows that **consistency comes from storage, not from re-derivation.** Tokenising two
spans separately and concatenating will not generally equal tokenising their joined text —
measured at 80% of cut points on ordinary English — and that is a property of the record
rather than a fault to correct.

## Method

What has paid off, and what it cost to skip.

- **Three stages, and each finds bugs the others cannot.** Lock the decisions in a document,
  stress-test the document, then write code. Ten real faults fell out of the first project's
  planning phase in prose that would have been expensive in code. Others fell out only of
  *using* the finished thing, and one only of *running a path nothing had run*. Planning,
  using and exercising are three different instruments and none substitutes.
- **Reading deeply is a fourth.** A design that survives review can still be the wrong object.
- **A one-line rejection of a structural option is a warning sign.** This has now happened
  twice, and the second time it decided the base unit for a year. Options that would change
  the shape of the format deserve a worked counterexample before they are struck out — and a
  rejection that names a use case should be re-read when that use case leaves the documents.
- **Probe rather than reason, when the question is decidable.** Nearly every item under
  *Measured* above overturned a confident assumption in minutes. The general form: **absence
  of observation cannot settle a question about what is possible.** Ask the vocabulary, not
  the samples.
- **A derived value is the easiest thing to get silently wrong**, because nothing disagrees
  with it. Anything derived deserves a test that reaches it on purpose, since ordinary use
  will not.
- **Test the invariant, not the value.** The test that earned its keep most asserted that an
  operation left a recorded *address* unchanged, not that some field equalled a particular
  pair. Value-equality tests pass on wrong implementations.
- **Arithmetic in a test is code, and nothing checks it.** Compute expected values; do not
  eyeball them.
- **Keep what is wanted apart from what is done.** A document that tracks progress becomes a
  record of progress and stops being the thing you can lock and point at.
- **A citation from a document you may not edit says the cited thing is in the wrong place.**
- When a check fails, ask "is the test wrong or is the code wrong?" before fixing either.
  Twice the honest answer was "the test asks for something the design makes unreachable" —
  which is a finding, and belongs in the docstring.

## Working conventions

- Run bash commands **serially and un-bundled**. No `&&` chains, no shell redirects.
- Multi-line `python -c` gets blocked by the command classifier — write a script into the
  scratchpad and run it. The shell is zsh, so quote globs (`--include='*.py'`).
- Recurring commands go in `scripts/`, which is **committed**.
- `data/` is disposable scratch and is gitignored.
- Fix root causes. A workaround that leaves the original fault in place is not a fix.
- Stage explicitly. Never `git add -A`.

## State

**Nothing is built.** `CORE.md` is the format and it has not been implemented or tested
against a running server. The first thing that exists should be the thing that proves the
format can hold what the instrument produces.
