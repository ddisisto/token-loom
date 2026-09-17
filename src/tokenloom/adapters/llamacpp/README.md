# llama.cpp, measured

**What this backend actually does**, measured against the model and build named in the project's
`CLAUDE.md`. These are this adapter's notes: what is required of *any* backend is
`docs/ADAPTER.md`, and nothing here is a rule.

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
  there is no per-position logprob without it either. `record_rows >= 1` is a hard requirement.
- **Rank 0 is not always the sampled token**, and nothing in the response marks which one was
  taken. With `top_k` off it is absent from its own top-3 about a ninth of the time, and at
  the default `top_k: 40` about a thirtieth. Confining sampling to the top `k` and recording
  at least `k` alternatives makes it always present — 64/64 measured at `top_k == n_probs`,
  at temperature 0.9 and 1.5 alike — but still unmarked, so it is found by id and never by
  rank.

  **`top_k` is the only knob here that settles this in advance, and `n_probs` cannot be
  traded for it.** `top_k` is the one sampler in the chain whose support has a size fixed
  before the position is evaluated; `top_p`, `min_p` and `top_n_sigma` admit a prefix of
  unknown length, and `typical_p`, `xtc` and the penalties admit sets that are not prefixes
  at all — `xtc` removes top tokens outright, and a penalty reweights by what was generated
  rather than by probability, so no row count bounds either. Recording more rows
  does not close the gap either. Fraction of draws landing outside the top `n` raw ranks,
  `top_k` off, ~860 positions per row over five unalike prompts and three seeds:

  | temperature | outside top 10 | 20 | 40 | 80 | 200 |
  | --- | --- | --- | --- | --- | --- |
  | 0.8 | 3.3% | 1.9% | 0.9% | 0.7% | 0.2% |
  | 1.0 | 10.1% | 7.1% | 4.5% | 3.1% | 1.8% |
  | 1.2 | 41.2% | 36.7% | 33.6% | 29.8% | 25.2% |

  At 1.2 a twentyfold wider record moves it 41% → 25%: the tail is fat enough that coverage
  has to be bought from the sampler or given up. **`docs/ADAPTER.md` gives it up** — a draw
  past `record_rows` is one of the ways *Rankings* already allows a node to have no covering
  ranked edge — so `record_rows >= top_k` is a check this adapter makes on a request that
  names `top_k`, and not an obligation on anything else. Note what buying it costs: at
  temperature 1.2, `top_k` 80 makes the 30% of draws living past rank 80 unreachable by
  construction, and those are the draws a reading instrument exists to find.
- **`samplers` decides which sampler runs; the value decides nothing on its own.** A request
  naming `samplers: ["temperature"]` and omitting `top_k` draws identically to one sending
  `top_k: 0`, while the response still *reports* `top_k: 40` — inert. Sending `min_p: 0.9`
  inside a chain that does not list `min_p` changes nothing; outside one, it rewrites the
  continuation. Measured inert this way when out of the chain: `top_n_sigma`, `min_keep`,
  `repeat_last_n`, `xtc_threshold`, `dynatemp_exponent`, `adaptive_target`. Naming the chain
  closes over samplers a later build adds.

  **Two escape the list, and one of them escapes an identity-value list too.** `mirostat`
  replaces the chain wholesale when it is non-zero, and `dynatemp_range` lives *inside* the
  chain's `temperature` entry — at `2.0` both change the continuation with the chain pinned
  to `["top_k","temperature"]`. `dynatemp_range` is also absent from any plausible list of
  neutralised samplers, and `--dynatemp-range` is a launch flag, so a server started with it
  joins every request silently. Both are set explicitly on every request.

  **The residual risk is a future sampler that is neither in the chain nor set here.** The
  echo below catches a parameter resolved differently from how it was sent; it cannot catch
  one that was never sent. That is the reason to re-read this file against a new build.
- **The response echoes the settings it accepted — which is not everything it then did.**
  `generation_settings` is a flat dict carrying `samplers` and every sampling and recording
  parameter, so a request can be checked against it rather than trusted, which is what the
  adapter's `_check` is. Floats come back at single precision (`0.8` as
  `0.800000011920929`), so they are compared to that.

  **The echo is a net under the refusals and not a replacement for them.** `n_probs`
  200000 echoes back as `200000` while 152064 rows actually arrive — the clamp happens
  after the settings are recorded and nothing in the echo shows it. So the row count is
  cross-checked against `completion_probabilities` and not against the echo, the same way
  `truncated` is cross-checked rather than inferred.

  **`cache_prompt` is not echoed at all.** Its effect is visible in `timings.prompt_n`,
  which equals the whole prompt exactly when the cache is off — measured at 2, 3, 251 and
  2001 tokens. `tokens_evaluated` is *not* the signal: it reports the prompt length either
  way.
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
  else about them is lost, because bytes never come from here — and that last clause holds of
  the blocking form alone, as the next item is about.
- **Streaming reports a group's final id and drops the rest, on both endpoints.** The same
  regrouping, and here it costs the ids themselves. Each SSE chunk carries its own `tokens`
  and its own `completion_probabilities`, so the two can still be walked together per chunk —
  but a chunk covering a multi-token character reports **one** id where the model emitted
  several. Prompt `🜁 🜂 🜃 🜁 🜂 🜃 🜁 🜂`, `n_predict` 10, seed 5, `top_k` = `n_probs` = 5:
  blocking returns `[11162, 250, 225, 271, 2, 11162, 241, 248, 576, 67176]`, streamed returns
  `[225, 271, 2, 248, 576, 67176]`. Four ids the model emitted appear in no chunk at all.
  `/v1/completions` streams the same six, so the compatible layer is not a way out.

  **The loss is detectable and the ids are not recoverable.** Each chunk's `tokens_predicted`
  advances by what was really drawn — by 3 where the chunk reported one id — so a reader can
  see how many ids it is missing and never which. Reading them back by re-tokenising the
  group's bytes is the artefact this whole format exists to avoid: more than one id sequence
  can spell those bytes and end on the reported id, and nothing in the response says which was
  sampled.

  The terminal event carries `stop_type`, `truncated`, `timings` and an **empty** `tokens`, so
  a stream closed early learns neither how it would have ended nor what it lost.
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

  **The refusal is about the tail alone, and not about whether the path decodes.** Measured
  on seven id sequences: `The` + `F0 9F` and `The` + `F0 9F 9C` answer 500, while `The` +
  `9C` + ` sky`, `The` + `F0 9F` + ` sky` and — the one that settles it — `The` + `9C` all
  answer 200. A completed invalid sequence with valid bytes after it is accepted, and so is
  a stray continuation byte in last position. So the predicate asks whether the bytes end
  with an *under-filled* multi-byte sequence, which is narrower than asking whether they
  decode end to end, and a path that does not decode is not thereby unreachable.
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
- **`n_probs` has no ceiling short of the vocabulary, and above it clamps in silence.**
  Requests for 200, 1000, 5000 and 152064 all report exactly that many rows; 152065 and
  200000 both report 152064, HTTP 200, with nothing in the response saying so. A cap on how
  many alternatives can be recorded is therefore not a thing this build has — but a request
  above the vocabulary is a parameter met approximately, which is the one thing an adapter
  may not pass on.
- **A generation that will not fit is truncated, and still reports `stop_type: limit`.**
  With `n_ctx` 16384: a 16000-token prompt asking for 500 answers HTTP 200 with
  `truncated: true`, 384 tokens drawn, and `stop_type: limit`. A 16380-token prompt asking
  for 100 gives 4 tokens the same way. **This is the fault that most needs absorbing**: the
  core's `limit` means *it drew the requested length*, so a pass-through adapter would
  record a terminator that is a lie, and only `truncated` — a field nothing obliges a reader
  to look at — distinguishes it. The prompt *alone* exceeding `n_ctx` is clean by contrast:
  HTTP 400, `exceed_context_size_error`, naming both numbers.
- **End-of-text is drawable and rankable on this base model, and whether it appears at all is a
  question of the prompt.** At three document-ending prompts it did not reach the top 40; after
  ` The end.` (`[576, 835, 13]`) it is ranked at −1.364 and is drawn on 5 of 8 seeds at
  temperature 1.0, arriving with `stop_type: eos`, `tokens_predicted: 1` and
  `tokens: [151643]`. It reaches `completion_probabilities` like any other token, with its
  bytes empty and its ranking present.
- **`cache_prompt` defaults on in the server, and a generation is therefore not guaranteed to
  replay token for token.** A full cache hit evaluates no prompt tokens, which changes the
  reduction order enough to perturb the logits and occasionally flip a near-tie: the same
  path, seed and parameters can give a *different* continuation warm than cold. The cache is
  a pure function of the prompt tokens — no seed reaches it.

  **Measured, and it is not the last decimal places.** Prompt `The sky`, `top_k` = `n_probs`
  = 5, temperature 0.9: cold against cold is bit-identical, warm against warm is
  bit-identical, and **cold against warm differs by up to 0.056** across the five rows — the
  gap between ranks 1 and 3 narrows by 0.107, which is enough to reorder a near-tie. Each
  cache state is internally reproducible, so this is a second variable rather than noise: a
  ranking recorded with the cache on is a function of the model, the path, *and* what was
  generated before it.

  **How large it looks depends on how deep it was measured, and a partial hit is worse than
  a full one.** Greedy, `top_k` 1, 80 rows, 20 positions, five prompts:

  | comparison | path agreed through | max abs Δlogprob, p50 / max | positions reordered |
  | --- | --- | --- | --- |
  | cold vs cold | 20/20 | 0.000000 / 0.000000 | 0/20 |
  | full-warm vs full-warm | 20/20 | 0.000000 / 0.000000 | 0/20 |
  | cold vs full-warm | 20/20 | 0.059 / 0.259 | 20/20 |
  | cold vs **partial**-warm | **11/20** | 0.153 / 0.580 | 11/11 |

  The 0.056 above was five rows deep; eighty rows deep the same comparison reaches 0.26. A
  *partial* hit — the cache holding some prefix of an unrelated path, which is what
  branching produces — reaches 0.58 and moved a **greedy** path off its cold course at
  position 11 of 20. **Cold is the only state that reproduces**, and it reproduces exactly,
  which is what makes a first-written value in the core a value and not a coin toss.
- **Continuing inside one call and starting a fresh call at the same path are not the same
  measurement**, and the cache does not decide it. Prompt `The sky`, `top_k` 1 so the path is
  forced, `n_probs` 5, temperature 1.0: sixteen tokens drawn in one call, against the same
  sixteen drawn as two calls of eight. All three runs drew an identical path, and repeating
  any request reproduced its rows bit-for-bit — so what follows is signal.

  | second chunk against the single call | max \|Δlogprob\| | rank order kept |
  | --- | --- | --- |
  | repeat of the same request | 0.000000 | 8 of 8 positions |
  | `cache_prompt` off | 0.057154 | 7 of 8 |
  | `cache_prompt` on | 0.036281 | 6 of 8 |

  Warm lands marginally *closer* to the unchunked record than cold, so the cache is neither
  the cause nor the cure. **The disagreement does not decay after the boundary either** — it
  is 0.013 at the first position past it and 0.042 at the eighth, because a KV state that
  differs at all is inherited by everything downstream. This is the same order of magnitude
  as the cold/warm gap above, and it reorders ranks, which is what matters.

  Cost of a boundary, warm: `prompt_n` 1 and `prompt_ms` 26, against 190 ms to draw the
  chunk's eight tokens. Cold, the whole path is re-evaluated at each boundary.
- **`n_probs` moves the values it shares with a smaller request, reproducibly and by very
  little.** Prompt `The capital of France is`, greedy, cache off, requests back to back.
  Repeating one request is bit-identical — a floor of exactly zero — and against that floor,
  10 rows and 40 rows disagree by **1.383e-05** at rank 9, the same figure on every trial. 10
  against 200 gives the same 1.383e-05; **40 against 200 is bit-identical.** So it is neither
  noise nor a gradient: it is a step somewhere between 10 and 40 that then saturates.

  This is a fourth variable of the same kind as the cache and the chunk boundary and about
  four thousand times smaller — it cannot reorder anything that is not already an exact tie.
  The format absorbs it the way it absorbs the others: a ranking extends, the first value
  written is the one kept, so a node first ranked by a narrow act keeps that act's values for
  the rows a later wide one shares. **`scripts/mass.py` is the reason this was found** — it
  asks for a wide ranking and applies the bounds locally, which is only sound because the
  wide values agree with the narrow ones to this order.
- **`/slots/0?action=erase` answers HTTP 501 on this build**, so the cache cannot be cleared
  between requests from the client. Measurements that need a cache state control it by what
  they send, not by resetting the server.
- **`temperature: 0` is argmax, and nothing else about the response changes.** The path is
  identical across seeds (1 and 99) and across `top_k` (1 and 40), and every drawn token was
  the rank-0 row of its own position — greedy needs no seed to repeat. More to the point,
  **the rows reported at temperature 0 are bit-identical to those at 1.0**: same ids, same
  order, same logprobs, same sum. Greedy is a separate sampler in llama.cpp and the
  temperature sweep above only covered {0.5, 1.0, 1.5, 2.0}, so this had to be measured
  rather than assumed — a ranking bounded by probability mass has nothing to bound if
  temperature 0 reports a degenerate one.
- **How much of the distribution a position holds varies by two orders of magnitude, and it
  varies with what is being read.** `scripts/mass.py` measures it; 160 greedy positions over
  five unalike prompts, rows needed to reach 0.9 of the mass:

  | prompt | p50 | p90 |
  | --- | --- | --- |
  | `Q: What is 17 times 23?` | 1 | 3 |
  | `def fibonacci(n):` … | 1 | 4 |
  | `The capital of France is` | 5 | 36 |
  | `Once upon a time,` … | 4 | 65 |
  | `The sky above the port was…` | 78 | 200+ |

  Overall p50 is 3 and p90 is 101. **Most positions are sharp and a minority are very flat**,
  and the flat ones are where branching is worth anything — so a flat row budget both
  over-records the sharp positions and truncates the interesting ones. A mass bound is what
  makes a wide ceiling affordable: at `record_mass` 0.9, a `record_rows` of 80 stores 0.86×
  what a flat 20 stores, keeps 3 rows at the median position, and leaves only 12% of
  positions cut short by the ceiling. Measured on this model; the script exists to re-measure
  it for another.
