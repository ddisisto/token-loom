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

- **`n_probs` below 1 returns no per-token record at all**, not merely no alternatives — so
  there is no per-position logprob without it either. `top_n >= 1` is a hard requirement.
- **Rank 0 is not always the sampled token**, and nothing in the response marks which one was
  taken. With `top_k` off it is absent from its own top-3 about a ninth of the time, and at
  the default `top_k: 40` about a thirtieth. Confining sampling to the top `k` and recording
  at least `k` alternatives makes it always present — 64/64 measured at `top_k == n_probs`,
  at temperature 0.9 and 1.5 alike — but still unmarked, so it is found by id and never by
  rank.
- **`completion_probabilities` is a window onto the raw distribution, and the whole sampler
  chain is invisible to it.** The values are pre-temperature *and* pre-truncation: the full
  softmax over the vocabulary. Measured at `top_k = n_probs = 10`, prompt `The capital of
  France is`, seed 1234 — all forty rows bit-identical across `temperature ∈ {0.5, 1.0, 1.5,
  2.0}`, same ids, same order, same logprobs to the last digit. Post-temperature scaling would
  put `gap(0.5)/gap(2.0)` at 4.0; measured 1.0000. Temperature *is* being applied — the
  sampled token flips between 1.0 and 1.5 — it just never reaches what is reported.
  `top_k ∈ {3, 10, 40, 0}` and `top_p ∈ {0.9, 0.5, 0.1}` likewise change nothing: `top_k = 3`
  returns the same ten rows, not three, and not ten with seven at `-inf`.

  **The ten sum to 0.784, and the missing mass is the rest of the vocabulary, not truncation.**
  The same sum appears at `top_k = 0`. Anything that reads a low sum as evidence of how the
  sampler was configured is reading it wrong.

  So a ranking recorded at temperature 1.5 is directly comparable to one recorded at 0.5, and
  the recorded parameters describe only which token was drawn.
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
  server accounting in text where the record is in tokens, and it is the reason the adapter
  must walk the two together: unchecked, the nodes it reports disagree with what the model
  emitted. The interior ids of a group have no ranking, which the core allows for; nothing
  else about them is lost, because bytes never come from here.
- **A stop string that does not land on a token boundary loses bytes the model emitted.** The
  server matches the stop string on *text*, then erases trailing entries by its *token* count,
  so tokens generated before the match go with it. Undecidable from the response, and fixable
  only by matching on ids server-side, which is not ours to change. **So the adapter does not
  expose `stop`**, and there is no `stop` terminator to record: it is the one knob that can
  silently make the record disagree with what was generated, and an adapter cannot repair what
  it cannot detect.
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
  tokenised into ids carrying real bytes even where a token is a fragment of a character.
  Tokenise/detokenise round-trips byte-exact on all thirteen cases measured, including
  astral-plane characters, zero-width joiners, combining marks and repeated whitespace. This
  is `tokenize` in the adapter contract, and it is what lets authored text be stored as ids
  with nothing else kept beside them.
- **`/detokenize` cannot return a token that does not decode alone.** A single fragment id
  answers HTTP 200 with `{"content": "�"}` — the replacement character, not the bytes.
  Measured on nine fragment ids from four scripts; the same ids come back exact from
  `/tokenize` with `with_pieces`, and a whole group detokenises exactly. So **bytes cannot be
  recovered by id through the server**, and the response is lossy rather than an error.
- **The vocabulary is in the model file, and it is exact.** `tokenizer.ggml.tokens` in the
  GGUF holds all 152064 entries in byte-level BPE encoding; applying the GPT-2 byte decoder
  gives real bytes for every id, fragments included. Checked against `/tokenize` with
  `with_pieces` on 48 ids across six scripts — 15 of them fragments — with zero mismatches,
  and a generation containing multi-token characters reassembles **byte-exact** from the id
  sequence alone. This is the route to per-token bytes; the server has none.
- **A control token spells nothing when generated and spells its literal form everywhere
  else.** `completion_probabilities` reports `{"id": 151643, "token": "", "bytes": []}` for
  `<|endoftext|>`, whether it was sampled or merely ranked. The vocabulary disagrees three
  independent ways: the GGUF entry is the 13 bytes `<|endoftext|>`, `/tokenize` returns that
  literal as the piece, and `/detokenize` returns it **with and without `special: true`** —
  the setting does not change the answer on this build. Taking the vocabulary's answer costs
  nothing and round-trips: `a<|endoftext|>b` tokenises to three ids and back.
- **`cache_prompt` is on, and a generation is therefore not guaranteed to replay token for
  token.** A full cache hit evaluates no prompt tokens, which changes the reduction order
  enough to perturb the logits and occasionally flip a near-tie: the same path, seed and
  parameters can give a *different* continuation warm than cold.

  **This is not contamination between calls, and the distinction is why it is acceptable.**
  The cache is a pure function of the prompt tokens — no seed reaches it — so warm and cold
  are two draws from the same distribution rather than one right and one wrong.
  Distributional statistics are unaffected; only exact replay of a *particular* generation is
  lost, and that was already conditional on the same build, GPU and quantisation.
