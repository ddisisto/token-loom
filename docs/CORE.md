# The core

**What the format is.** Position, span, kind, the token overlay, the on-disk shape, the
worked example, the checks, and the operations. No arguments: nothing here has to be defended
to be read, and this document is meant to be locked early and left alone.

**The test this document is written against: can someone implement a reader from it alone?**

---

## 1. The unit is the token

A **token** is an id in a vocabulary together with the bytes it spells. The tree is a trie
over tokens.

Bytes are derived. A span's bytes are its tokens' bytes in order; a path's bytes are its
spans' bytes in order. Nothing addresses a byte, and no offset in this format is a byte
offset.

A token's bytes may be a fragment of a character. Qwen2.5 spells `🜁` — four UTF-8 bytes —
as three tokens, none of them valid UTF-8 alone. So a token has bytes but not always a
string, and decoding happens at the edges: display, and authoring.

A token's bytes may be empty. An end-of-text token spells nothing and is an ordinary token
in every other respect: it has an id, a logprob and its own ranked alternatives.

**Every span's bytes decode.** A token may be a fragment of a character, but a span whose
bytes are not valid UTF-8 is not a legal span — check 12 — so nothing in this format carries
bytes with no string form, and no escape exists for the case. Fragments are real and live
*inside* spans, where they are surrounded by the rest of their character.

This is a constraint on what may be written, not a claim about what a model can produce. An
adapter that cannot honour it for some generation declines that generation.

## 2. A position is `(span, index)`

`index` is how many of that span's tokens lie on the path — where the path *leaves* the
span. It runs from `0` to the span's token count inclusive.

A span is written once and never cut, so a position is durable under every operation.

Absolute, root-relative indices are derived and stored nowhere. They are meaningless in an
exported subtree, where a span id still travels.

**One point has two names, and the canonical one is the earlier span's.** Where a span ends
and a child begins, `(child, 0)` and `(parent, k)` name the same point; every position that
reaches storage or the wire is the second. A branch taken at index `0` of a span therefore
attaches beside that span rather than inside it. Index `0` of a *root* span has no earlier
name and is canonical as it stands — check 4.

**A position can only be formed into a span that has tokens.** One state has none: a
generated span still in flight (section 7). It cannot be a parent.

## 3. A span

A span is a run of tokens with one parent position. `kind` records **what decided the span
exists**:

| kind | decided by |
| --- | --- |
| `given` | someone outside the model |
| `sampled` | the model's own draw |
| `counterfactual` | a reader taking a road the model ranked and did not take |

Fields:

| field | on | meaning |
| --- | --- | --- |
| `kind` | all | the departure decision, above |
| `parent` | all | a position, or `null` for a root |
| `created` | all | timestamp, ISO 8601 |
| `deleted` | all | present and `true` if soft-deleted; absent otherwise |
| `params` | generated | index into the interned parameter table |
| `seed` | generated | the seed this call was made with |
| `slice_start` | generated | position the prompt began at, or `null` for the whole path |
| `origin` | `counterfactual` | `{span, index, rank, token_id}` — which alternative, and where |

"Generated" means `sampled` or `counterfactual`: both are model calls.

A `given` span has no fields of its own. Its bytes are its tokens' bytes, exactly as for
every other kind.

## 4. A given span is tokenised when it is created

Authoring is bytes in, tokens out. The text someone writes is tokenised against the tree's
vocabulary and stored as token rows, and the span keeps no separate record of what was
authored.

**Authored bytes are valid UTF-8, and the input path refuses anything else.**

**The round trip is verified where it happens, not where it is read.** Authoring tokenises,
then reassembles the rows exactly as section 13 will — bytes in order, with a control token
contributing its recorded spelling — and compares that against the authored bytes. A mismatch
refuses the span rather than recording it. So the authored text is exactly recoverable, and
nothing needs to store it twice.

The comparison is against the reassembly rather than against a detokenise call because a
detokeniser's treatment of control tokens is a setting, and a setting nobody recorded can let
the check pass while the stored rows say something else.

This is the same discipline as the UTF-8 refusal above: an invariant the record cannot
express is enforced at the edge that can see it. It also settles a question the bytes cannot.
A special-token literal in authored text may be read as one token or as its characters; the
two detokenise identically, so bytes cannot tell them apart, but the stored ids can, and no
field is needed to record which reading was taken.

Authoring therefore needs a vocabulary. A tree cannot be composed with nothing running.

**A tree has one vocabulary**, named in `tree.json` (section 9). Every span's ids are in it,
which is what makes a path replayable by concatenating them. It is recorded separately from
any model because two quants of one model share a vocabulary, and whether stored ids can be
replayed turns on the vocabulary rather than the weights. A tree in a second vocabulary is a
new tree, converted span by span through bytes.

## 5. The token overlay

One row per token, keyed by `(span, index)`:

| column | meaning |
| --- | --- |
| `index` | position within the span, `0`-based, no gaps |
| `token_id` | the vocabulary id |
| `bytes` | what it spells; may be empty, may be a fragment of a character |
| `logprob` | the log probability the model gave it, or `null` |

`logprob` is `null` on a `given` span's rows: nothing sampled them.

**`bytes` is nullable, and `null` is not the same as empty.**

- an **empty** blob means the token is known to spell nothing. Control tokens are the
  ordinary case, an end-of-text token among them. What such a token is *called* is a property
  of the vocabulary rather than of the row, and is recorded once per tree — section 9.
- **`null`** means the record does not know what this token spelled on its own. It arises
  where the server delivered a character's bytes as a group: the ids are all recovered, but
  only the collective bytes arrive, and re-tokenising the group in isolation does not
  reliably reproduce the same ids. The group's bytes are carried by the row that completed
  it, and the rows before it are `null`.

A span's bytes are its rows' bytes in order, with `null` contributing nothing — so the
derivation is correct in both cases, and the two are still distinguishable. `logprob` is
`null` on the same rows, and they carry no counterfactuals.

## 6. Counterfactuals

The alternatives the model ranked at a position it generated. One row per `(span, index,
rank)`:

| column | meaning |
| --- | --- |
| `index` | the position in the span these are alternatives at |
| `rank` | `0` is the highest-ranked; ranks are distinct within an index |
| `token_id`, `bytes`, `logprob` | as in the overlay |

**The sampled token is always among them, and is not marked.** It is found by its id, not by
its rank — rank `0` is the most probable token, which is frequently not the one sampled. The
overlay and the counterfactual rows stay independent records of the same position; what is
guaranteed is that the position's own outcome appears in its own ranking.

The guarantee is a constraint on the parameters, in section 8: sampling is confined to the
top `k`, and at least `k` alternatives are recorded, so the sampled token cannot fall outside
what was written down.

**The recorded probabilities are the model's own, not renormalised over the recorded set.**
They sum to less than one, by the mass the truncation removed.

A `counterfactual` span carries, at its index `0`, the alternatives recorded at the position
it departed from — the same distribution, the same prefix — so it is answerable on its own
terms.

## 7. Termination

One row per span, written when the span stops:

| reason | means |
| --- | --- |
| `eos` | the model emitted an end-of-text token |
| `length` | the requested number of tokens was produced |
| `context` | the context window ran out first |
| `aborted` | the process generating it is gone |

**`length` and `context` are not distinguished by the server.** Both arrive as
`stop_type: "limit"`, so the difference is derived: nothing stopped it, *and* it produced
fewer tokens than were asked for. The comparison is against the **budget sent**, which for a
branch is one less than the length recorded (section 12) — comparing against the recorded
length would mark every completed branch `context`.

**A generated span with no terminator row is in flight.** Whether it is still being generated
is not a question the store can answer; the lock in section 9 answers it. A writer holding
that lock knows no other writer is live, so every such span is abandoned and is recorded
`aborted`.

`eos` is not a state of the span. The end-of-text token is an ordinary row in the overlay,
with its own counterfactuals, and the terminator names the reason beside it.

## 8. Interned parameters

Every distinct parameter set is written once in a table and referenced by index.

| field | source |
| --- | --- |
| `temperature`, `top_p`, `top_k`, `top_n`, `length` | the caller |
| `model`, `n_ctx` | the server |

**`top_n >= top_k > 0`.** `top_k` bounds what may be sampled; `top_n` is how many ranked
alternatives are recorded. Requiring the second to be at least the first is what makes
section 6's guarantee hold. `top_k` is a condition of the run and not a display setting: it
truncates the distribution the model samples from, and at small `k` it removes real mass —
about a tenth of it at `k = 3`.

The vocabulary is not here. It belongs to the tree, not to a call — section 4.

## 9. On disk

Three files in a directory.

**`tree.json`** — structure and provenance. Small, and readable by eye.

```json
{
  "marker": "token-loom/2",
  "created": "2026-08-24T11:56:00Z",
  "tokenizer": "qwen2.5-7b-base",
  "specials": {"151643": "<|endoftext|>"},
  "params": [
    {"temperature": 0.9, "top_p": 0.95, "top_k": 3, "top_n": 3, "length": 8,
     "model": "qwen2.5-7b-base", "n_ctx": 16384}
  ],
  "spans": {
    "s1": {"kind": "given", "parent": null, "created": "…"},
    "s2": {"kind": "sampled", "parent": {"span": "s1", "index": 5},
           "created": "…", "params": 0, "seed": 90210, "slice_start": null},
    "s3": {"kind": "counterfactual", "parent": {"span": "s1", "index": 5},
           "created": "…", "params": 0, "seed": 90211, "slice_start": null,
           "origin": {"span": "s2", "index": 0, "rank": 2, "token_id": 6521}}
  }
}
```

`specials` maps the id of every control token the tree holds — in an overlay row or a
counterfactual row — to its literal spelling. Those tokens spell nothing, so this is the one
point in the format where the bytes are empty by design and a reader would otherwise have
nothing to show. It is an excerpt of the vocabulary named above, written when such an id is
first stored, and it is what keeps a tree displayable from the store alone. A reader with no
entry for an id shows the id.

Every field here is written by a tree operation. A client that wants to remember where
someone was reading keeps that outside the store; it is not part of the record.

**`bulk.sqlite`** — the rows. A new record type is a new table, not a new mechanism.

```sql
CREATE TABLE tokens (
  span TEXT, idx INTEGER, token_id INTEGER, bytes BLOB, logprob REAL,
  PRIMARY KEY (span, idx));
CREATE TABLE counterfactuals (
  span TEXT, idx INTEGER, rank INTEGER, token_id INTEGER, bytes BLOB, logprob REAL,
  PRIMARY KEY (span, idx, rank));
CREATE TABLE terminators (span TEXT PRIMARY KEY, reason TEXT, recorded TEXT);
```

`bytes` is a BLOB, so no escape is needed anywhere in the store. The overlay's `index` is
`idx` in SQL, because `INDEX` is a keyword.

**`lock`** — held with `flock` for the duration of any write, and **not across a model
call**. A generation in flight holds nothing, so several can be in flight at once and each
takes the lock only to write its rows.

This is what makes section 7's `aborted` decidable. The kernel releases the lock when its
holder dies, so a writer that acquires it knows no other writer is live and every generated
span without a terminator row is abandoned. Recording those is the first write after
acquisition, so **opening a tree for writing can modify it.** A reader taking no lock sees a
span in flight as exactly that, and can conclude nothing about whether it is still running.

## 10. Worked example

`s1` is authored, and tokenised against the tree's vocabulary as it is written:

| idx | token_id | bytes | logprob |
| --- | --- | --- | --- |
| 0 | 785 | `The` | — |
| 1 | 6722 | ` capital` | — |
| 2 | 315 | ` of` | — |
| 3 | 9625 | ` France` | — |
| 4 | 374 | ` is` | — |

Those five rows spell `The capital of France is`, which is what was authored. Detokenising
them returns it exactly, and the input path checked that before writing them.

`s2` is generated from `(s1, 5)` — the tip. Its first rows:

| idx | token_id | bytes | logprob |
| --- | --- | --- | --- |
| 0 | 12095 | ` Paris` | −0.31 |
| 1 | 13 | `.` | −1.10 |

with counterfactuals at index 0:

| rank | token_id | bytes | logprob |
| --- | --- | --- | --- |
| 0 | 12095 | ` Paris` | −0.31 |
| 1 | 264 | ` a` | −2.88 |
| 2 | 6521 | ` located` | −3.41 |

`s3` takes rank 2. Its parent is `(s1, 5)` — the same position `s2` departs from, not a
position inside `s2` — and its index `0` is token `6521`, copied from that row. Everything
from index `1` on is generated.

The path through `s3` reads `The capital of France is located…`.

## 11. The checks

A tree is valid when all of these hold.

1. Span ids are unique, and every `parent` names a span that exists.
2. Following `parent` from any span reaches a root; there are no cycles.
3. A `parent` position's `index` is within the named span's token count. A span that is
   named as a parent therefore has tokens.
4. A `parent` position with `index == 0` names a root span. Any other point at the start of
   a span has an earlier name, and section 2 requires that one be used.
5. A `given` span has no `params`, no `seed` and no `origin`.
6. A generated span has `params` and `seed`.
7. A `counterfactual` span has `origin`; `origin` names a counterfactual row that exists; and
   the span's own token row at index `0` carries that row's `token_id` and `logprob`.
8. Token rows for a span are indexed `0…n−1` with no gaps and no duplicates.
9. A row with `null` bytes carries a `null` logprob and no counterfactuals.
10. Every counterfactual row names an index that exists in that span's overlay, and ranks are
    distinct within an index.
11. No row in any bulk table names a span the tree does not hold. A soft-deleted span is
    still held, so its rows are not orphans.
12. A span's bytes are valid UTF-8. A span with no rows has no bytes and passes trivially.
13. Every descendant of a deleted span is deleted.

## 12. Operations

| operation | writes | leaves |
| --- | --- | --- |
| `author(at, bytes)` | a `given` span and its token rows | tokenised against the tree's vocabulary; refuses if the round trip does not hold |
| `generate(at, settings, n)` | `n` `sampled` spans | provenance first, then the rows |
| `branch(span, index, rank, settings)` | one `counterfactual` span | row `0` pre-filled, the rest generated |
| `delete(span)` | the `deleted` flag, on that span and every descendant | rows and ids untouched |

**Generation is two writes, not one.** The span, its parameters and its seed are written and
the tree is saved *before* the model is called; the token rows and the terminator are
written when it answers. A span with provenance and no rows is therefore a generation in
flight, and no bulk row can ever name a span the tree has not heard of.

`branch` is a generation whose first token is decided rather than sampled. It follows the
same ordering and differs in four places: row `0` comes from the recorded counterfactual
rather than from the response, the prompt carries that token, the budget sent to the model is
one less than the length recorded, and `kind` says `counterfactual`.

**Row `0` is written with the rest of the rows, not ahead of them.** `origin` already records
which token was taken, so nothing is lost by waiting, and an in-flight branch is then exactly
an in-flight generation: provenance and no rows.

Its parent is the position the origin token sits *at* — `(origin_span, index)` — canonicalised
as section 2 requires, so a branch at index `0` attaches to the origin span's own parent.

**A requested length of 1 makes no model call.** The budget is one less than the length, so
there is nothing to ask for: the row is written, the span is completed with `length`, and the
operation stays reachable with no server.

## 13. Derived reads

Nothing here is stored.

- **A span's bytes** — its token rows' bytes in order.
- **A path's bytes** — the bytes of each span on the ancestry, each taken up to the index at
  which the path leaves it.
- **Display text** — the same walk, decoded, with every control token contributing its
  `specials` spelling in place of its empty bytes. This is what a reader shows, and what the
  authoring check in section 4 compares against; for a `given` span it returns what was
  authored.
- **Ancestry** — the chain of positions from a position back to its root.
- **Runs** — maximal stretches of path with nothing branching off them. Runs have no ids.
- **Absolute index** — a position's distance from the root, in tokens.
