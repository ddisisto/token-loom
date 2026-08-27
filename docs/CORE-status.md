# The core — status

**Where `docs/CORE.md` stands.** It is cited and must not move, so what is true *for now* about
it lives here instead of in it.

---

## Locked

`docs/CORE.md` is locked at `marker` `token-loom/nodes-1`, on branch `core-design-lock`.

It was written as a plan, transcribed whole, reviewed against itself and its adapter contract,
and amended once. The terminator set was closed at lock rather than deferred, because adding one
later changes the meaning of an existing column and is the one event the conformance rule says
bumps `marker`.

## Not built

**Nothing is implemented.** No store has been written, no invariant has been checked by code, and
no tree has been built against a running server. The first thing that exists should be the thing
that proves the format can hold what the instrument produces.

The appendix is the closest thing to a test that exists: seven stages with real ids and logprobs
off `Qwen2.5-7B.i1-Q4_K_M`, walked by hand against every invariant. It is a fixture waiting for a
reader.

## Specified and unwitnessed

Three constructs are in the locked document that nothing has produced.

- **`eos`** — end-of-text did not appear in the top 40 at any of three document-ending prompts on
  this base model.
- **`cancelled`** — unreachable until `generate` can be interrupted. This is the one open item a
  locked core is already waiting on, and it belongs to the adapter; see `docs/ADAPTER.md`.
- **`failed`** and **`aborted`** — neither a backend death nor an abandoned writer has been
  exercised.

`refused` is the only one of the four non-ordinary terminators with a worked row, and it got one
because it is the only shape with a null `tip`.

## What the lock does not cover

The adapter contract is `docs/ADAPTER.md` and is deliberately unlocked; its own open items are
stated there and are not repeated here. The reading surface has no document yet.
