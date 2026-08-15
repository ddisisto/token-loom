# Handover

Working notes too ephemeral for `CLAUDE.md`, `ROADMAP.md` or `FORMAT.md`, carried across a
compaction.

**Delete each item as it closes, and the file when it empties.** It is a message between
sessions, not documentation. Anything here that turns out to be durable belongs in one of
the three files above instead.

---

## Where things stand

Every thread the previous handover carried is closed, and `main` is pushed and in sync.
`core_test.py` 145 green with no model, `llama_test.py` 47 green against the server.

`PLAYBOOKS.md` is new and is the best entry point to what the instrument is *for* — five
moves worked end to end against `data/demo/`, which is **committed** and reads with no model.
`demo.py --force` rebuilds it. `README.md` is no longer upstream's tkinter documentation.

Phase 1 is done and there is nothing open at the format level.

**The work has since split in two**, which most of this file predates — see `CLAUDE.md`,
"Two threads, one substrate". Phase 2 is the build thread and `ROADMAP.md` has its scope;
`RESEARCH.md` leads the other. The notes below are shared unless they say otherwise, and
each thread gets its own briefing rather than inheriting this one.

## What is worth knowing before Phase 2 starts

**The CLI is the specification.** That framing was adopted for the polish pass and it held:
`loom.py` now does everything the API needs to, so the Phase 2 surface can be read off it
rather than designed fresh. Positions parse as `span` / `span+offset` / `.`, and `batches`
and `params` are the two reads that turn recorded-but-unread fields into something.

**Nothing in the CLI emits machine-readable output.** Every command prints for a human. That
is fine for a reference client and is the one thing the API cannot copy — worth deciding
early whether the API is a separate surface over `core/` (probably) or whether `loom.py`
grows a `--json` mode (probably not).

**`llama_test.py:context_limit` needs a second server** and skips rather than fails without
one. It was running during this session and has been stopped:

    CTX=512 PORT=8082 scripts/llama-server.sh --n-gpu-layers 0

CPU-only because a second GPU instance does not fit in 8GB beside the first. Everything else
uses the ordinary 8081.

**`data/tree/` is a stale-format tree** and refuses to load, correctly — it was written
before the marker was renumbered. Delete it and `loom.py new` when it is next wanted. The old
`data/*.json` trees belong to the old format and are untouched; `data/local.json` in
particular is not disposable.

## Loose ends that are not threads

- `daniel-notes.md` and `daniel-notes-next.md` are untracked, neither committed nor ignored.
  The former's `<|endoftext|>` concern is **already satisfied at the format level**:
  end-of-text arrives in the overlay as a token with its id and zero bytes, not swallowed.
  What is left of that note is rendering, which is Phase 2/3 work.
- Three CLI things noticed and deliberately not done, since none is needed yet: `params`
  prints every field of every entry where a diff between two would read better; nothing
  filters `show` by batch; and **`gen` leaves the cursor on the span it made**, so sampling
  one position repeatedly means naming the position each time. That last one is right for
  walking forward and wrong for sampling in place — `PLAYBOOKS.md` documents both rather
  than picking, because which default is correct depends on the move.
- `data/tree/` still holds the stale-format tree and `loom.py new` now refuses it cleanly
  rather than tracebacking. It is disposable; delete it when convenient.
