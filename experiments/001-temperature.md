# 001 — Temperature, across three prompts

Run 2026-08-15 against Qwen2.5-7B base (i1-Q4_K_M) on llama-server b10221. Tree at
`data/sweep-1/`, which is not committed. Measure pinned at `06d573c`, results at `129670e`.

**Verdict: P1 fails, P0 holds, P2 survives with its framing moot.** The headline is in the
results below, and the finding it turned up instead — that the prompt effect is larger than
the temperature effect — is on `RESEARCH.md`'s front page under question 3.

> Moved verbatim from `RESEARCH.md` when the notebook was split into a landing page and this
> directory. The pre-registration text is unchanged, including its reference to "the
> horizontal rule at the end of this section", which still sits where it did.

---

## Pre-registration

**Written before the sweep ran, and not edited after.** Everything below the horizontal rule
at the end of this section was fixed before a single continuation existed. Corrections go in
a *results* section underneath, never here — a pre-registration that gets tidied up once the
numbers are in is not one.

The reason to bother, given that exploration is what produced the best thing on this page:
**only the claim already made needs protecting.** Playbook 2 says 0.2 and 1.3 both locked
onto *the silence of X* while 0.8 escaped. That is written down, it is specific, and it is
the result that would be most satisfying to keep. Novel observation needs no defending
against a three-sample impression becoming a twenty-sample one. This does.

### Conditions

Three prompts, all roots of `data/demo/`, all short and all open continuations rather than
instructions — the two long roots (`s19`, `s28`) are excluded because their length would
confound with `prompt_length`:

| | prompt | bytes |
| --- | --- | --- |
| A | `The lighthouse keeper wrote in his log:` | 39 |
| B | `There are three kinds of silence. The first is` | 46 |
| C | `She opened the door and found` | 29 |

B is playbook 2's prompt and carries the claim. A and C are there to say whether it
generalises. They are as neutral and open as prompts get, which is not very — any of them can
be read as leading, and how much of that reading is the prompt's and how much is the reader's
is part of what the sweep is looking at.

Six bands: **0.1, 0.3, 0.6, 0.9, 1.2, 1.5**. `n=20`, `length=28`, `top_n=3`,
`prompt_length=6000`, everything else default. 18 batches, 360 continuations. `length=28`
matches playbook 2 so the demo's nine samples stay comparable.

### The measure, fixed now

Frame-lock is read by eye everywhere above, which is exactly the thing that must stop before
more samples are added. Operationally, over the `n` siblings of one batch:

> **`lock(k)`** = the size of the largest subset of siblings sharing their first `k` tokens,
> divided by `n`.

`lock(3)` is the primary measure. Three tokens is *the / silence / of*, which is the frame
the claim is about. `lock(1)` and `lock(10)` are reported beside it. Nothing here needs a
format change or a new call: it is a comparison of token sequences already stored, which is
the sibling-divergence read under a different name — and that read must be built and pinned
against `data/demo/` **before** it is pointed at the sweep.

Note what this measure is not. It is lexical, and "The one that surprised me" established
that the interesting convergence is not lexical. That is fine and deliberate: playbook 2's
*the silence of X* is a shared opening token sequence, so it is a lexical claim, and it is a
different phenomenon from playbook 1's genre convergence. Keeping them apart is half the
point.

### The predictions

**P0, the null, and the one to beat.** `lock(3)` falls monotonically as temperature rises.
This is what naive sampling theory says and it is a live possibility. Writing it down first
is what stops "not monotonic!" from meaning "not perfectly monotonic across six noisy bands".

**P1, the claim under test.** `lock(3)` is U-shaped: higher at 0.1–0.3 and 1.2–1.5 than at
0.6–0.9, on prompt B. If it holds on A and C too it is a fact about temperature; if it holds
only on B it is a fact about that prompt, which is also worth knowing and is the more likely
outcome.

**P2, the sharp one.** The two ends are not the same phenomenon.

- Low-temperature lock is *the same completion*: siblings agree on the frame and keep
  agreeing. `lock(10)` stays close to `lock(3)`.
- High-temperature lock is *the same frame, different fillers*: siblings agree for three
  tokens and then scatter. `lock(10)` collapses relative to `lock(3)`.

So the discriminator is the ratio **`lock(10) / lock(3)`**, predicted high at 0.1 and low at
1.5 — falling monotonically even if `lock(3)` itself does not. P2 can fail while P1 holds,
which is what makes it worth stating: if `lock(3)` is U-shaped and the ratio does not
separate the ends, the U is one effect rather than two and this whole framing needs redoing.

P2 is also where the two levels stop competing. Token overlap and frame agreement become two
axes of one plot rather than a cheap measure and a good one.

### What this design cannot do

- **`n=20` sees 40% versus 80%. It does not see 60% versus 75%.** A null result means "too
  small to see at this sample size", not "did not happen".
- **Three prompts is not a sample of prompts.** Any effect that holds on all three is a
  hypothesis about prompts in general, not a measurement of them.
- **One model, one quantisation, one server.** Nothing here separates a fact about
  temperature from a fact about Qwen2.5-7B at Q4_K_M.
- The bands are not evenly spaced in anything meaningful. Temperature is not a physical
  quantity and 0.1→0.3 is not the same step as 1.2→1.5.

### Blinding

Continuations are written to the tree and to a log that neither of us reads while the sweep
runs. Status is checked with `params`, which prints conditions and span counts and no
generated text. The classifier is built against `data/demo/` and pinned before the sweep
output is opened. Then unblind, and look at everything.

The point is narrow: judging "is this locked onto the frame" while knowing the temperature is
precisely how the three-sample impression got made in the first place.

---

## Results

360 continuations, 60 per band, all validating. The measure was built, tested and pinned
against `data/demo/` at `06d573c` before anything here was opened.

### lock(3), the pre-registered measure

|  | 0.1 | 0.3 | 0.6 | 0.9 | 1.2 | 1.5 |
| --- | --- | --- | --- | --- | --- | --- |
| A *lighthouse* | 1.00 | 1.00 | 1.00 | 0.75 | 0.75 | 0.75 |
| B *silence* | 1.00 | 0.95 | 0.80 | 0.35 | 0.30 | 0.40 |
| C *door* | 0.50 | 0.35 | 0.10 | 0.10 | 0.10 | 0.05 |

### The verdicts

**P1 fails. There is no U.** `lock(3)` is monotone non-increasing on all three prompts. B's
0.30 → 0.40 between 1.2 and 1.5 is six spans against eight, comfortably inside the noise the
design admitted to up front. Nothing at 1.5 approaches its own low-temperature value on any
prompt.

**So the playbook 2 observation was three-sample noise**, which is exactly what the sweep was
for. The frame-lock at 1.3 was real in that batch and did not survive twenty samples. Worth
noting that the *demo data still shows it* — `diverge` on `data/demo/` gives `lock(3)` 1.00 at
0.2, 0.33 at 0.8 and 1.00 at 1.3 — so the original reading was not a misreading. It was three
samples doing what three samples do.

**P0 holds.** Monotone decline is what happens, and the naive model of temperature was right.

**P2 holds where it can be measured, and its framing is moot.** The ratio `lock(10)/lock(3)`
on prompt A runs 1.00, 0.95, 0.55, 0.27, 0.13, 0.07 — the predicted decay, cleanly. But P2
was posed as telling apart *two ends of a U*, and there is no U, so what survives is the
weaker claim it rests on: agreement gets shallower as temperature rises, rather than merely
rarer. On C the ratio is a floor artifact and means nothing — `lock(10)` sits at 0.05, which
is one span in twenty, so 0.05/0.10 reads as 0.50 while describing a single continuation.

### What the sweep found instead

**Depth carries the signal; presence does not.** `lock(3)` on prompt A is pinned at 1.00
across half the range and never falls below 0.75. `lock(10)` over the same range runs 1.00,
0.95, 0.55, 0.20, 0.10, 0.05. The pre-registered primary measure turned out to be the blunter
of the two — three tokens is short enough that agreement there survives almost anything, and
the interesting variation is in how far the agreement extends.

**The prompt effect is larger than the temperature effect**, which nothing predicted:

| | | 0.1 | 0.3 | 0.6 | 0.9 | 1.2 | 1.5 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| common prefix, all 20 | A | **18** | 4 | 3 | 0 | 0 | 0 |
| | B | 4 | 0 | 0 | 0 | 0 | 0 |
| | C | 0 | 0 | 0 | 0 | 0 | 0 |
| distinct paths of 20 | A | **5** | 10 | 19 | 20 | 20 | 20 |
| | B | 8 | 19 | 20 | 20 | 20 | 20 |
| | C | 18 | 20 | 20 | 20 | 20 | 20 |

Prompt C at **0.1** is less converged than prompt A at **1.5** — `lock(3)` 0.50 against 0.75,
20 distinct paths against 20, no common prefix in either. A whole temperature range is worth
less than the difference between two short, unremarkable English prompts. Whatever
temperature is doing, it is doing it *within* an envelope the prompt sets, and the envelope
varies more than the thing inside it.

That is question 3 arriving as a number, from an experiment aimed at question 2.

**At 0.1, most of the samples are the same sample.** Exact byte-identical duplicates, of 20:
A has 15, B has 12, C has 2. Twenty generations at 0.1 on prompt A buy five distinct
continuations. Not a subtle effect and not one the lock numbers show directly — `lock(3)` and
`lock(10)` are both 1.00 there, which is the measure saying "they agree" where the honest
statement is "they are the same string".

### A recorded finding, corrected

> **The common prefix of all eight was zero at every temperature.** Not small — zero. Siblings
> differ on their first token essentially always.

That was under "Sibling divergence, measured", and as a general claim it is **false**. At
0.1 prompt A has an eighteen-token common prefix across twenty siblings; at 0.3 it has four.
The original measurement was taken at 0.3, 0.9 and 1.2 on a single prompt, and it is correct
at those conditions — its lowest band is where the effect starts and the prompt it used
behaves like B or C rather than A. Read it as *"zero at 0.3 and above, on that prompt"*, which
is what it measured.

This bears on the prefix-merging conclusion in `BEYOND-MVP.md`, which was drawn from shared
storage of 2–13% over the same three bands. At 0.1 with 15 duplicates in 20 the arithmetic is
completely different. The conclusion is probably still right, because 0.1 is not a regime this
project works in — but it was decided on evidence that does not cover the case that would
overturn it, and that is worth knowing.

### Caveats that survive

Everything the pre-registration said it could not do, it still cannot. One model, one
quantisation, three prompts, `n=20`. Additionally: nine spans of 360 hold fewer than the 28
tokens requested while reporting `length` — the llama-server UTF-8 regrouping recorded in
`CLAUDE.md` under *Inference*. All are 18 tokens or longer, so `lock(3)` and `lock(10)` are
untouched; the *distinct paths* row counts a short sequence as its own path, which can inflate
it by at most a few in the 0.6 and 1.5 bands.

---

## Appended after the fact

**2026-08-16 — the records this sweep produced predate the alignment fix.** `d31a3d2` changed
how `core/llama.py` reads a response: a character split across several tokens now records as
one row with `token_id` and `logprob` absent, rather than carrying the last fragment's id as
though it described the character. `data/sweep-1/` was written before that and about 40 of its
~10,070 token rows still carry the old shape. `lock(3)` and `lock(10)` read the first three
and ten entries and are unaffected; nothing here was re-run.

**Reproducibility is weaker than this document assumed.** `cache_prompt` was on during the
sweep, and a full cache hit changes what a fixed seed samples. Replaying a span warm
reproduces it exactly; replaying it cold does not. So these 360 continuations are a faithful
record of what the model produced, but they are *not* reproducible from the conditions each
span carries alone. It is off from `d31a3d2` onward, so 002 will not have this problem.
