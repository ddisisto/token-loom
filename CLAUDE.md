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

The tree is `src/tokenloom/core/`, and the command line is the client on it. A reading
surface over an HTTP API is where this is going, which is why the second point below is a
constraint and not an observation.

**The claim is not concurrency control, and reading it as such costs an argument every
time.** One `flock`, one writer — and what it buys is that two things can be read off the
store instead of guessed at: what a writer verified cannot change beneath it, so verifying
is once per claim; and an act left in flight is one whose writer is gone, which is what
makes `aborted` decidable. Simultaneous writers to one tree are not wanted and never have
been, so what it costs to exclude them is not a question. `docs/CORE.md`'s *On disk* is
where this is stated.

**A read sits above the core when it needs a character, a measure of room, or what the
reader did.** `src/tokenloom/surface/reads.py` is that layer — segmentation, the continuation rule,
and the three reads `docs/SURFACE.md` states — and `core/reads.py` holds the record half each
of them stands on. The core answers about the record and stops, which is what keeps a
decision about display from becoming a fact about the format.

Two things pull on the design:

- **Base-model behaviour matters more than chat quality.** A chat-templated reply is a
  different object than a continuation of the prior. Where the two conflict, favour the raw
  continuation path.
- **No write may be surface-only.** Every write the surface can make, the command line can
  make. Reads, views and navigation are the surface's own. What this protects is the record
  and not a second client: a mutation reachable only by clicking has put itself somewhere
  the record cannot follow, while a way of looking records nothing and costs nothing. It is
  close to self-enforcing, since `docs/CORE.md` closes the set of writes — five acts — and
  each already has a verb. A surface write with no verb would be a new kind of write, which
  is a core change and gets read as one.

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
  can someone implement a reader from it alone. **It moves only as its own deliberate piece of
  work** — never in passing, and never to accommodate what a backend or a client turned out to
  want. `marker` is what tells a reader it moved.
  **How a derivation is shaped is not an argument.** *A descent from the root carries the answer
  down* and *it is a `LEFT JOIN`* say what the relation between the tables is, which a reader
  implementing one needs and cannot infer; the document already speaks SQL, since *On disk* is
  DDL. A claim about what something *costs* is the other thing, and belongs with the code that
  pays it.
  **Its *Derived reads* names only what a reader would otherwise get wrong**, and is not a
  catalogue of queries. One grew there before anything used it, and four of its entries were
  reads nothing called, two of them restating facts that already had homes in *Acts* and
  *Sources*.
- **`docs/ADAPTER.md`** is what a backend must do to produce that record — the operations, the
  obligations behind them, and what to do when one cannot be met. **It moves as backends are
  met**, which is the point of the split, and it carries its own status inline.
- **`docs/SURFACE.md`** is the reading surface's design and constraints, **drafted and not
  accepted**. It is written against a different test than the core's — can a reader tell what is
  settled from what is open, and does each open question say what would settle it — because a
  design in progress fails by writing an open question down as a rule. It moves until the surface
  is built.
- **`docs/NEXT.md`** is what gets built next and why in that order. **It is living**: items are
  added as they come up and deleted once they close or fall out of scope, so it never
  accumulates a history of itself. Nothing cites it, and nothing should — it is the one document
  that is allowed to be wrong tomorrow.

**The core names no backend, and no backend's limitation may become a rule in it.** One did once —
llama.cpp will not evaluate a prompt whose bytes end mid-character, which had become an invariant
forbidding acts at fragment nodes, including ones that call no model. The core forms positions;
an adapter decides which its backend will accept.

**A backend's notes live with that backend's code, and the contract may cite them as evidence
and never as a requirement.** `docs/ADAPTER.md` leans on measurements to explain why an
obligation reads as it does — why `cancelled` is unreachable, what *Determinism* is guarding —
and that is the right use. The moment such a citation is what *makes* a rule true, the rule has
a backend inside it.

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
which one happened. A section at the end of the document it is about cannot do that. A file of
its own can: parted from its subject it drifts into holding what the subject should have said,
and then there are two answers.

**A status section holds only what has no home yet.** It is where a finding lands while it is
still being learned, which makes it structurally the place duplicates are born: the body gets
written later, and retiring the note reads as tidying rather than as finishing the job. An
item should die the moment a home is written for it, and an entry announcing that something
is settled is the signal that one did not.

**A citation from a document you may not edit says the cited thing is in the wrong place.**

## Inference

**Local only.** Qwen2.5-7B **base** (i1-Q4_K_M) on port 8081 as `qwen2.5-7b-base`. ~5.2GB
VRAM at 16k context on a GTX 1070, 122 tok/s prompt and 32 tok/s generation.
`mradermacher/Qwen2.5-7B-i1-GGUF` is a genuine base GGUF in a catalogue that is otherwise
almost all Instruct, and its imatrix quants beat the static ones at identical size.

**The alias is the vocabulary's name and not the source's.** `qwen2.5-7b-base` is what
`/props` reports and what a tree is created against; the source name defaults to the model
file's stem, `Qwen2.5-7B.i1-Q4_K_M`, because it has to separate anything whose draws must not
factor together and a different quantisation is a different model. **The core cannot check
this** — naming is the enforcement, and two models served under one alias merge into one
source silently, which is the exact failure the merge key exists to prevent.

**Nothing here can reach a hosted model, and that is upstream of the endpoint choice.** The
core needs per-token ids, bytes and logprobs on a *raw continuation*, and no OpenRouter
provider returns logprobs there — including ones whose `/models/{id}/endpoints` claim
otherwise. There are no true base models left in the hosted catalogue anyway.

The stack talks to llama.cpp's native `/completion` endpoint, not the OpenAI-compatible one.
**`src/tokenloom/adapters/llamacpp/README.md` holds what that server actually does** — the
endpoint choice, and a list of measured behaviours that is not guessable from the API surface.
Several of them produce a record that is quietly wrong rather than an error, so it is read
before the adapter is touched, not after something disagrees. It sits beside the code it is
about so that reading it first is where you already are.

## Working conventions

- Run bash commands **serially and un-bundled**. No `&&` chains.
- Multi-line `python -c` gets blocked by the command classifier. A `python3 - <<'PY'` heredoc
  is not, and neither are ordinary redirects — both were used throughout the build without
  trouble, so the constraint is narrower than it once read. The shell is zsh, so quote globs
  (`--include='*.py'`).
- Recurring commands go in `scripts/`, which is **committed**.
- `data/` is disposable scratch and is gitignored.
- Stage explicitly. Never `git add -A`.
- The project is a `uv` one: `uv sync`, `uv run pytest`, `uv run tokenloom`, and
  `uv run ruff check src tests scripts` before every commit.
- **`uv run pytest` needs no server.** The live tests skip without one; `-m live` runs only
  those, and they are the ones that can tell you the docs have gone stale.

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
- **A question that keeps coming back is usually planted by the prose.** The claim was
  stated by what it refuses, so what refusing costs came up session after session — about a
  simultaneity nobody had asked for. Re-answering it each time was cheaper than noticing,
  which is what let it run. When something recurs, read what introduces it rather than what
  raised it.
- **Probe rather than reason, when the question is decidable.** Nearly every item in
  the llama.cpp adapter's notes overturned a confident assumption in minutes. The general
  form: **absence of observation cannot settle a question about what is possible.** Ask the
  vocabulary, not the samples.

## State

**The format is built per `docs/CORE.md`, with a command line that makes every write it
admits.** `src/tokenloom/core/` is the store — the five acts, the derived reads and a checker for
every named invariant — and trees have been built against a running server. What the backend
leaves open is the Status section of `docs/ADAPTER.md`; **what gets built next is
`docs/NEXT.md`.** Those two are the files that carry what is unfinished; this section is not one,
and neither is `docs/CORE.md`.
