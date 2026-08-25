# The server

**What llama.cpp actually does**, measured against the model and build named in `CLAUDE.md`.

**Read this before writing or changing anything that talks to the server.** Nearly every item
below overturned a confident assumption, none of them is guessable from the API surface, and
several would produce a record that is quietly wrong rather than an error.

## The endpoint

The stack talks to llama.cpp's **native `/completion` endpoint**, not the OpenAI-compatible
one. Both return an identical token payload — `{id, token, bytes, logprob, top_logprobs}` —
so the native one is chosen for what it adds: `stop_type` separating `eos` from `word` from
`limit`, where the compatible layer flattens the first two into `finish_reason: stop`.

## Measured, and not obvious

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
