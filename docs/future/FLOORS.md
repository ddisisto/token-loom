# Floors

**A floor is an alternative whose probability hardly depends on what the text is saying, because
it prices a structural event rather than a word — the document ends, the excerpt is cut, the
paragraph breaks, the turn changes hands.** Content alternatives compete with one another for the
next word; a floor competes with the whole content hypothesis at once. Where every content
alternative has been ruled out, the floor is what is left standing behind the top token.

This document holds what the record already shows about floors, what is suspected about their
use as a reference level, and a probe that would settle the suspicions.

**Everything measured here is one model's**: Qwen2.5-7B base, i1-Q4_K_M, served by llama.cpp.
Which tokens act as floors, where they sit and what lies behind them are facts about that model
and its training mix. The mechanism proposed for them — a structural event any prefix is
compatible with — is not specific to it, so models sharing a family or a pretraining recipe are
likely to show the same shape at different levels. The technique of reading a floor off the
recorded rankings applies to any backend that returns them.

---

## What the record shows

**The trees these come from were grown by use, not built for the question.** `data/logozoa`
holds a DreamLaboratory code seed walked greedily for about 6,800 tokens with an operator picking
among ranked alternatives, and a `USER:`/`ASSISTANT:` root walked the same way.
`data/continuations` holds the continuations probe — four seeds, eight draws at each of three
temperatures — and later walks from its Austen seed.

**The recorded rankings are thinner than `record_rows` suggests.** The adapter keeps rows until
their cumulative probability reaches `record_mass`, never fewer than two, and always the drawn
token's. At `record_mass` 0.9, a position whose top token carries more than 0.9 stores exactly
two rows — in the `USER:` root, 2,760 of 3,730 positions. So at confident positions the record
says what came second and nothing about how far below it anything else sat. Every claim below is
limited by that, and the ones it limits most say so.

### At a confident position, the runner-up is a way to stop

**On the DreamLaboratory path, the second-ranked token is `<|endoftext|>` at most positions where
the model is near-certain, and almost nowhere else.**

| p(top) | positions | runner-up is EOS |
|---|---|---|
| ≥ 0.999 | 2,345 | 74% |
| 0.99 – 0.999 | 1,892 | 31% |
| 0.9 – 0.99 | 965 | 3% |
| < 0.9 | 1,424 | ~0 |

Where EOS is second, the top token is template scaffolding — ` a`, ` dream`, `_d`, ` where`,
`("`. Where it is not, the runner-up is mostly another line of the template the model has already
written. The open slots of the template are the positions where it is absent.

**It is not priming by EOS in the context, though that raises it.** Positions whose context holds
no EOS give the same switch-on at the top of the scale at a lower level:

| p(top) | DreamLaboratory, EOS in context | Austen seed, no EOS in context | other probe seeds, no EOS in context |
|---|---|---|---|
| ≥ 0.999 | 74% | 24% | 22% |
| 0.99 – 0.999 | 31% | 7% | 5% |
| 0.9 – 0.99 | 3% | 3% | 1% |

**Along the DreamLaboratory path it rises with distance from the last EOS, not with nearness to
it** — among positions above 0.99, 34% within 100 tokens of one, 51% at 100–400, 63% at 400–1,000,
74% beyond. Distance there tracks how long the current repetition has run.

**In prose the stopping alternative is split across several tokens.** At the Austen root's
positions above 0.999, the leading runner-ups are EOS (150), `...` (135), `\n\n` (134) and `\n`
(114), of 2,301. Each is a way to end the unit — `...` is how a scraped excerpt is cut — and the
genre decides which form the ending takes. In a code context thick with `<|endoftext|>`, it is
almost always EOS.

**Roles have their own runner-ups.** In the `USER:`/`ASSISTANT:` root, assistant turns run more
confident than user turns even where the operator steered the user side (median p(top) 0.96
against 0.85; above 0.99 at 40% of positions against 26%). At confident assistant positions the
leading runner-up is EOS (72 of 954). At confident user positions it is a spelling of the
handover — `ASS`/`Ass`, `IST`/`IS`, `Assistant`/`AI`, and `Sure`, which skips the label and
starts the reply. Whether a handover floor runs through the body of a user turn as EOS runs
through assistant text is below what two rows can show.

### What waits past EOS is a chat format

**Twice, independently, the model crossed an EOS into `Human:` … `Assistant:`.** On the deepest
Austen path, the first greedy tokens after an EOS are `Human:` followed by a verbatim copy of the
whole preceding document, then `Assistant:`; further on comes an Orca-style system prompt (*You
are an AI assistant. User will you give you a task…*), which puts instruction-tuning data in this
base model's pretraining mix. In the `USER:` root, the model kept the operator's format for five
exchanges, emitted EOS greedily at the end of the fifth assistant turn, and returned as `Human:`
… `\n\nAssistant:`, closing every exchange after that with EOS — one conversation per document,
which is how a dump of such data is laid out.

For an instrument that favours the raw continuation, this makes EOS the door to the object it is
trying not to produce.

### Salad begins in the tail

**Coherence at high temperature follows truncation, and it ends at a tail token.** Once one lands,
the context is off-distribution, the next ranking is flatter, and more tail is drawn.
`docs/SPINE.md`'s *Evidence in hand* has the measurements, from `data/continuations`' Austen
seed and from a probe of bounds at temperature 2.0.

---

## What is suspected

**A floor is a reference level with a meaning.** Every absolute log-probability carries the
normaliser over the whole vocabulary, which the tail dominates; a difference between two tokens
does not. Any reference token cancels the normaliser — a floor makes the difference read as
*how much more plausible this is than stopping*, which should be comparable across positions,
genres and temperatures where p(top) is not.

**The number of content alternatives above the floor is an openness count.** None is a locked
position, one a committed choice, several an open slot. Entropy smears the same distinction by
counting tail mass the model does not mean. Of the two conditions *the model is sure of this
word* and *nothing but stopping is consistent here*, p(top) sees only the first; "runner-up is a
floor" is the second, and would be a cheap flag for `docs/SPINE.md`'s kind of reading.

**Sampling only above the floor is a truncation rule with a reason.** It would be greedy at
locked positions and broad in open slots with no fixed `k`, anchored to a structural event where
min-p anchors to the top token. It also names a class of deviation: a draw below the floor is
one the model itself ranked below ending the document — and an operator's pick above the floor is
a different act from one below it.

**Floors co-exist, one per unit the model believes it is inside, and their movement is a
readout of that belief.** A turn inside a transcript inside a file would carry nested floors. EOS
rising against `\n\n` says the unit is ending rather than continuing; EOS rising with the length
of a repetition looks like the model's own sense that the text has gone degenerate; a `Human:`
floor surfacing says the chat prior is near. Choosing which floor to measure against is choosing
which unit to read at, which plausibly belongs to the reader.

**A floor may be a sequence.** `\n\nHuman:` begins with a token content shares. Its price is a
product of steps, read by realising the first token and drawing on greedily — which the tree
already makes cheap.

**What would weaken all of this is a floor that does not hold still.** Floor-relative measures
cancel only what moves with the floor. The loop-length rise is signal for the readout and noise
for the reference, so which floor is chosen decides what is seen.

---

## What the record cannot yet say

**How far below a confident top token the floor sits.** At `record_mass` below 1 that position
keeps two rows, so a floor is seen only when it is second. `record_mass: 1.0` keeps rows up to
`record_rows`.

**Where the floor sits at an open position.** Floors measured so far lie around −8 to −11 nats,
under dozens of content tokens where the slot is open; a hundred rows may still miss them. The
format stores ranked rows only, so recording a designated token's log-probability at every
position regardless of rank is a change to what `docs/CORE.md` stores, and would be read as one.
What llama.cpp's native endpoint returns is the top `n_probs`, and its ceiling and cost are not
yet measured.

---

## The probe

**A scripted tree, built through the command line's acts alone, under `scripts/` and into a fresh
tree under `data/`.** Held still throughout: `record_mass` 1.0, `record_rows` as large as the
server tolerates, a distinct seed per draw, one writer.

**0. The row ceiling.** Probe how many rows the server will return and at what cost per token.
This decides how much of the floor anything below can see, so it comes first.

**1. Seeds crossed with an EOS in the prefix.** Four formats — raw prose, code, `USER:`/
`ASSISTANT:`, and the native `Human:`/`\n\nAssistant:` — each with and without an
`<|endoftext|>` in the prefix. Settles how much of the EOS floor is the floor and how much is
priming.

**2. Long greedy runs.** About 1,500 tokens from each seed, long enough to cross open slots and
locked stretches and to reach a loop. Settles how the floor moves with repetition, and whether
the count above the floor separates open from locked where p(top) does not.

**3. Floor probes.** At fixed intervals along each run, realise the first token of each candidate
floor — EOS, `\n\n`, `\n` — and draw a few tokens greedily. Settles what each floor leads into
(`\n\n` into `Human`, `USER` or more prose) and prices the multi-token ones.

**4. Truncation.** From the same seeds, several draws each at T≈1.2 untruncated, at `top_k` 20,
and cut at the floor; record where each draw fell against the floor at its position. Settles
whether draws below the floor are what start salad.

---

## Status

Nothing here has been built, and the probe has not been run. The findings above come from trees
grown for other purposes, under recording settings that hide the floor wherever the model is sure.
