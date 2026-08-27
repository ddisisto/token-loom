# CLAUDE.md

**This file is for things that are true about the code and easy to get wrong.** Direction is
not here. A finding about what a model does is not here either.

## What this is, and what it's for

**token loom** — a machine output research tool. Givens go in, generations come out, and the
surface exists to read across them: a generation is not an answer to be accepted or rerolled,
it is one path among those the model made available, and several are held at once. That much
is the interface this is named after — inspired by
[socketteer/loom](https://github.com/socketteer/loom), and the debt is conceptual and real.

**What is different is that the record goes down to the token.** Every generation carries
what else was ranked at every position it passed through, so a path can be read against the
alternatives that were live along it — not just against its siblings. A branch can be taken
at a token the model ranked and did not sample. That is the whole reason the tree is a trie
over tokens rather than over text, and it is what the name is for.

The tree is in `core/`, with two clients on it: a command line and an HTTP API, the latter
also serving the reading surface.

Two things pull on the design:

- **Base-model behaviour matters more than chat quality.** A chat-templated reply is a
  different object than a continuation of the prior. Where the two conflict, favour the raw
  continuation path.
- **No capability may be surface-only.** The command line is the reference client and the
  floor: if a thing can be done at all, it can be done without the reading surface. This is
  not a use case, it is a check on where capability is allowed to live — anything reachable
  only by clicking has put itself somewhere the record cannot follow.

Controlled research — attractors in the prior, how temperature gates access to them, framing
as a change of basis, what survives repeated retransmission — is where this points, and the
core should not preclude it. It is deliberately not being designed for now. The questions get
better with more use of the instrument, and designing around an experiment nobody has
specified yet is how a format acquires a base unit it does not need.

## Token replay is a fidelity property, not an optimisation

Concatenating stored token ids is not the same object as tokenising the concatenated text:
BPE merges across the join, so re-tokenising can hand the model a sequence it never emitted.
For an instrument built on iterating a model against itself, replay is the correct path and
re-tokenisation the artefact. This is why the format stores tokens and derives bytes, rather
than the reverse.

It follows that **consistency comes from storage, not from re-derivation.** Tokenising two
runs of text separately and concatenating will not generally equal tokenising their joined text —
measured at 80% of cut points on ordinary English — and that is a property of the record
rather than a fault to correct.

## The documents

- **`docs/CORE.md`** is what the format *is* — node, edge, source, ranking, act, the on-disk
  shape, the invariants, the operations. It carries no arguments and is written against one test:
  can someone implement a reader from it alone. **It is locked and does not move**; what is true
  of it only for now is `docs/CORE-status.md`.
- **`docs/ADAPTER.md`** is what a backend must do to produce that record — the operations, the
  obligations behind them, and what to do when one cannot be met. **It is deliberately not
  locked**, and it moves as backends are met. It carries its own status inline.
- **`docs/SERVER.md`** is what llama.cpp actually does, measured. Read it before writing or
  changing anything that talks to the server. **It is the llama.cpp adapter's notes, and neither
  the core nor the contract cites it.** What is required of any backend is `docs/ADAPTER.md`;
  what one backend happens to do is here.

**The core names no backend, and no backend's limitation may become a rule in it.** One did once —
llama.cpp will not evaluate a prompt whose bytes end mid-character, which had become an invariant
forbidding acts at fragment nodes, including ones that call no model. The core forms positions;
an adapter decides which its backend will accept.

Direction, the reading surface and its constraints get their own documents in `docs/` when
there is something to say.

**Every fact has one home, and a change moves it rather than copying it.** This is what bit
last time: a decision changed, the old statement of it was left standing somewhere else, and
during the transition — and worse, long after — there was no way to tell which source was
current. Duplication is not the cost; the dangling copy is. So when something changes,
delete or move what it supersedes in the same edit, and if a document earns no reader it is
deleted rather than kept for reference. What is recoverable from history does not need a
second home in the tree.

**Status goes in one place, never woven through.** A checkbox beside a requirement, a
`(done)` after a claim, a sentence saying what is true *for now* — these rot, because the
edit that records progress is also the edit that can soften the claim, and nothing marks
which one happened. Consolidated at the end of a document, or in a file of its own, it cannot
do that. Which of those depends only on whether the document has to be lockable: `docs/CORE.md`
is cited and must not move, so its status lives elsewhere; a document nothing cites is more
useful carrying its own inline.

**A citation from a document you may not edit says the cited thing is in the wrong place.**

## Inference

**Local only.** Qwen2.5-7B **base** (i1-Q4_K_M) on port 8081 as `qwen2.5-7b-base`. ~5.2GB
VRAM at 16k context on a GTX 1070, 122 tok/s prompt and 32 tok/s generation.
`mradermacher/Qwen2.5-7B-i1-GGUF` is a genuine base GGUF in a catalogue that is otherwise
almost all Instruct, and its imatrix quants beat the static ones at identical size.

**Nothing here can reach a hosted model, and that is upstream of the endpoint choice.** The
core needs per-token ids, bytes and logprobs on a *raw continuation*, and no OpenRouter
provider returns logprobs there — including ones whose `/models/{id}/endpoints` claim
otherwise. There are no true base models left in the hosted catalogue anyway.

The stack talks to llama.cpp's native `/completion` endpoint, not the OpenAI-compatible one.
**`docs/SERVER.md` holds what that server actually does** — the endpoint choice, and a list
of measured behaviours that is not guessable from the API surface. Several of them produce a
record that is quietly wrong rather than an error, so it is read before the adapter is
touched, not after something disagrees.

## Working conventions

- Run bash commands **serially and un-bundled**. No `&&` chains, no shell redirects.
- Multi-line `python -c` gets blocked by the command classifier — write a script into the
  scratchpad and run it. The shell is zsh, so quote globs (`--include='*.py'`).
- Recurring commands go in `scripts/`, which is **committed**.
- `data/` is disposable scratch and is gitignored.
- Stage explicitly. Never `git add -A`.

## Writing code and tests

- **Fix root causes.** A workaround that leaves the original fault in place is not a fix.
- **A derived value is the easiest thing to get silently wrong**, because nothing disagrees
  with it. Anything derived deserves a test that reaches it on purpose, since ordinary use
  will not.
- **Test the invariant, not the value.** The test that earned its keep most asserted that an
  operation left a recorded *address* unchanged, not that some field equalled a particular
  pair. Value-equality tests pass on wrong implementations.
- **Arithmetic in a test is code, and nothing checks it.** Compute expected values; do not
  eyeball them.
- When a check fails, ask **"is the test wrong or is the code wrong?"** before fixing either.
  Twice the honest answer was "the test asks for something the design makes unreachable" —
  which is a finding, and belongs in the docstring.

## Method

How decisions get made here — what has paid off, and what it cost to skip.

- **Three stages, and each finds bugs the others cannot.** Lock the decisions in a document,
  stress-test the document, then write code. Ten real faults have fallen out of one planning
  phase in prose that would have been expensive in code. Others fell out only of
  *using* the finished thing, and one only of *running a path nothing had run*. Planning,
  using and exercising are three different instruments and none substitutes.
- **Reading deeply is a fourth.** A design that survives review can still be the wrong object.
- **A one-line rejection of a structural option is a warning sign.** One such line has decided
  a base unit for a year before now. Options that would change the shape of the format deserve
  a worked counterexample before they are struck out — and a rejection that names a use case
  should be re-read when that use case leaves the documents.
- **Probe rather than reason, when the question is decidable.** Nearly every item in
  `docs/SERVER.md` overturned a confident assumption in minutes. The general form: **absence
  of observation cannot settle a question about what is possible.** Ask the vocabulary, not
  the samples.

## State

**Nothing is built.** The format is locked and has not been implemented or tested against a
running server. The first thing that exists should be the thing that proves the format can hold
what the instrument produces. `docs/CORE-status.md` is where that stands, and it is the file that
moves — not this section, and not `docs/CORE.md`.
