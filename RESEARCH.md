# Research

The other thread. `ROADMAP.md` is the build path — an API and a front end, on top of a core
that is finished. This is the thread that *uses* the core, and its instrument already works:
`loom.py`, `data/demo/` and `PLAYBOOKS.md` are a working research setup, not a preview of
one.

So this document is not a roadmap and should not become one. It has no end state. It holds
**the questions, what has been run, what came back, and what to run next** — an agenda at the
top and a notebook underneath, growing by accretion.

`PLAYBOOKS.md` is the *how*: five moves, with commands. This is the *what and why*.

## The standing caveat

**Nothing recorded here is a result yet.** Every number below comes from three to eight
samples on one prompt against one model, which is enough to demonstrate a move and enough to
form a hypothesis, and is not enough to support a claim about anything. Where something reads
like a finding, read it as *a thing worth running properly*.

The apparatus is honest about conditions — every span carries the parameters that produced
it, and `params` lists them — so upgrading any of these from anecdote to measurement is a
matter of running more, not of building more.

---

## The questions

From `ROADMAP.md`'s framing, which has not changed and is what the instrument was shaped
around:

1. **Attractors in the prior.** Where does a prompt tend to go, and how strongly? What
   escapes?
2. **Temperature as a gate.** What does temperature give access to, and is the relationship
   monotonic?
3. **Framing as a change of basis.** How much of the prior has to be visible before a
   continuation changes character?
4. **Survival under retransmission.** Iterate the model against itself — what persists, and
   what washes out?

A fifth has emerged from the runs rather than from the framing:

5. **At what level does convergence live?** See "The one that surprised me" below.

### The null prompt is not a baseline

Worth writing down because it was believed for a while and is wrong. Generating from an empty
prompt feels like the privileged view of the prior — the model unprompted, saying what it
would say. It isn't. It is one more conditioning, and a strange one: the region of the
distribution reachable from no context at all is narrow and unrepresentative, not neutral.

The prior is whatever it is, and it is not directly observable. Every prompt is a window onto
some part of it, the sliding window is the instrument for moving that window around, and no
position of the window is the true one. That reframes question 3 — framing is not distortion
away from a baseline, because there is no baseline to be distorted away from. It is the only
access there is.

Which makes the instrument more interesting rather than less, and puts the burden somewhere
specific: on choosing windows whose bias is legible, and on saying what it is.

---

## What has been run

### Sibling divergence, measured

Eight continuations of 32 tokens from one position, seeded distinctly, compared token by
token. Originally run to settle whether prefix-merging was worth doing in storage — it is
not, and that conclusion lives in `BEYOND-MVP.md` where the storage question belongs. The
*measurement* is research and belongs here.

| temperature | common prefix, all 8 | distinct paths by depth | fully diverged | shared storage |
| --- | --- | --- | --- | --- |
| 0.3 | 0 tokens | 2, 2, 2, 5, 5, 5, 6, 7 | depth 13 | 13.4% |
| 0.9 | 0 tokens | 3, 7, 8, 8, 8, 8, 8, 8 | depth 3 | 2.3% |
| 1.2 | 0 tokens | 4, 7, 8, 8, 8, 8, 8, 8 | depth 3 | 2.0% |

**The common prefix of all eight was zero at every temperature.** Not small — zero. Siblings
differ on their first token essentially always.

> **Corrected by sweep 1.** True at 0.3 and above, on this prompt. At 0.1 a constrained prompt
> holds an eighteen-token common prefix across twenty siblings. See "A recorded finding,
> corrected" below.

And divergence is **nested and plural** rather than a single branch point: at 0.3, eight
continuations occupy two distinct paths for three tokens, then five, then seven. There is a
trie among the siblings. "Eight samples, two paths, three tokens deep" is the attractor
question answered as a number, and it needs nothing new stored — comparing sibling token
sequences is a read over data already held.

**This is the most valuable unbuilt read in the project.** It is the only quantitative
handle on question 1, and everything else so far is eyeballed prose.

### The five playbooks

Run against `data/demo/`, which is committed. `PLAYBOOKS.md` has the transcripts.

**1. Attractor strength.** Eight continuations of *"The lighthouse keeper wrote in his
log:"* at 0.9. All eight open with a timestamp; **seven turn into arithmetic word problems**;
one stays an actual log entry. The prior for this prompt is not "a lighthouse keeper's log",
it is "a maths textbook using one as set dressing".

**2. Temperature.** Same position at 0.2, 0.8, 1.3, three samples each. **0.2 and 1.3 both
locked onto the same syntactic frame** — *the silence of X* — differing only in what fills
`X`. 0.8 was the band that escaped the frame and started sentences a different way.

If that survives more samples it is the interesting result on this page, because it is
**non-monotonic** and the naive model of temperature does not predict it. Three samples per
band is far too few to believe it. It is cheap to run properly.

**3. Framing.** One position, 40 bytes of prefix visible versus 404. With the tail only, the
model invents a context for *"the first thing worth saying about the results is"* —
significance testing, cosmology. With the whole note it continues the note's own argument,
one continuation picking up its *first / second* structure. Same position, same temperature,
different basis.

**4. Counterfactual propagation.** At temperature 0.9 the sampled token is absent from its
own top-3 **about a third of the time**. In the demo, token 2 sampled `' lying'` at −3.90
while `' sitting'` sat at −2.13 — and rank 1 was `' ______'`, the model holding a
fill-in-the-blank exercise open as a live possibility three tokens in. Branching to a
counterfactual costs no generation; only finding out where it leads does.

**5. Retransmission.** Eight steps, each seeing only 120 bytes of what came before. The
seed instruction is out of view within two steps. **The content washed out; the genre did
not** — by step 7 the text was numbering its own advice in the same instructional register it
had drifted into by step 1.

### The one that surprised me

Put the sibling-divergence table beside playbook 1 and they appear to contradict each other.

- **Token level:** the common prefix of eight siblings is *zero*, and at 0.9 they are fully
  distinct by depth 3.
- **Genre level:** seven of eight arrive at the same place — an arithmetic word problem —
  having shared no tokens at all.

They do not contradict. They say the attractor **is not in the token sequence**. Eight
continuations that agree on nothing lexically still agree on what kind of text they are.
Whatever is being pulled toward is at the level of register, form, corpus region — not
surface.

That reframes question 1. "Where does the prior go" cannot be answered by comparing token
sequences, which is precisely what the one quantitative read available measures. **The
cheapest measurement and the thing worth measuring are not the same thing**, and noticing
that is worth more than either.

It also sharpens what an embedding would be *for* — see `BEYOND-MVP.md`. Distance between
sibling continuations is the natural handle on genre-level convergence, where token overlap
is the handle on surface convergence, and the gap between the two is the finding.

### About the apparatus

Facts established while building, all recorded in `FORMAT.md` under "Settled by measurement",
listed here because they constrain what is measurable:

- **No hosted provider returns logprobs on a raw continuation.** Chat endpoints have
  logprobs and apply a template; completions endpoints give raw continuation and no provider
  returns logprobs there, including ones whose `/models/{id}/endpoints` claim otherwise. Local
  serving is not a preference here, it is the only option.
- **The sampled token is often not rank 0** — about a third of the time at 0.9. Tokens and
  counterfactuals are independent records for this reason.
- **A token can be a fragment of a character.** Qwen2.5 tokenises `🜁` into three tokens,
  none valid UTF-8 alone.
- **`<|endoftext|>` is an ordinary token in the distribution.** The demo caught it sampled at
  rank 0 with two ordinary words ranked below it, producing a span of zero bytes terminating
  as `eos`. Nothing swallows it.
- **A stop string off a token boundary silently loses bytes**, so stop strings should be kept
  to plausible token sequences until the token-replay path exists.
- **`tokens_predicted` can overstate what comes back.** In sweep 1, nine spans of 360 (2.5%)
  reported `stop_type: limit` with `tokens_predicted` at the requested 28 while
  `completion_probabilities` carried 20–27 entries, so the span is short by the difference.
  It replays deterministically — the same slice, seed and parameters reproduce the same short
  sequence — so the record is faithful to what the server returned, and the shortfall is
  upstream. Two things measured while establishing that: the server's own `content` agrees
  with the shorter array rather than with the count, and the `tokens` id array (requested via
  `return_tokens` and never read by the core) disagrees with `completion_probabilities` from
  around index 6. The core reads only `completion_probabilities`, which is the array `content`
  corroborates.

---

## Sweep 1: temperature, pre-registered

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

## Sweep 1: results

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
temperature is doing, it is doing it *within* a envelope the prompt sets, and the envelope
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

That is under "Sibling divergence, measured" above, and as a general claim it is **false**. At
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
tokens requested while reporting `length` — a llama-server discrepancy between
`tokens_predicted` and `completion_probabilities`, recorded under "About the apparatus". All
are 18 tokens or longer, so `lock(3)` and `lock(10)` are untouched; the *distinct paths* row
counts a short sequence as its own path, which can inflate it by at most a few in the 0.6 and
1.5 bands.

---

## What to run next

Roughly in order of what would sharpen the most per unit of GPU time.

1. ~~**The temperature non-monotonicity, properly.**~~ Run. It was three-sample noise, and the
   hour it took to find out is the whole argument for the exercise. What it turned up instead
   is the new item 0.

0. **The prompt effect, which is bigger than the one that was being measured.** Three prompts
   spread `lock(3)` at fixed temperature as widely as six temperature bands spread it at fixed
   prompt. That wants many prompts at two or three bands, not many bands — the axis worth
   sampling densely is the one that turned out to move things. Pick prompts along something
   articulable (how constrained the continuation is, how much of a genre the opening names) so
   the result is a statement rather than a scatter.
2. **Attractor strength as a number.** Playbook 1 across many prompts at fixed conditions.
   What fraction escape? Does the escape rate move with temperature, and does it move the
   same way the frame-lock does?
3. **Framing as a sweep, not two points.** `prompt_length` over a range rather than 40 versus
   404, looking for whether character changes gradually or has a threshold.
4. **Retransmission, long.** Forty steps rather than eight, with a fixed window. When does
   seed content die, and does the register stabilise or keep drifting? This is the cheapest
   long-running experiment available.
5. **Single-token stepping as frequency measurement.** At length 1, N spans over a handful of
   distinct tokens: the multiplicity *is* an empirical frequency, to be set against the
   logprobs recorded beside it. Does the sampler do what the logprobs say?

---

## What the instrument cannot do yet

Tool gaps that actually block the above, as opposed to conveniences.

- **Nothing quantitative exists.** Every finding on this page was read by eye off `show`.
  The sibling-divergence profile is the first real read and needs no format support.
- **No export.** Getting a tree into anything else for analysis means reading the sqlite
  directly. Fine for now; a blocker the moment there is a statistic worth plotting.

None of these needs a format change, which is the point of the format. They are reads and CLI
surface, and each should be built when an experiment is actually waiting on it — not before.

### Closed

Both of these were in the way of experiment 1 rather than of the analysis, which is why they
went first: 360 generations is not a thing you can drive by hand or read whole.

- **~~`gen` moves the cursor~~**, so repeated sampling at one position meant naming the
  position each time — right for walking forward, wrong for sampling in place. `gen --stay`
  leaves the cursor at the generation point. Not a change of default: both readings are
  correct and neither is the other's special case.
- **~~No batch filtering.~~** `show <position> --depth n` roots the render at a point and caps
  how far it forks; `batches --params <key>` selects every call made under one set of
  conditions. Interning is by value, so the key already *is* the condition — the level between
  "one call" and "the whole tree" turned out to be a selection the tree could already make,
  and only needed asking for.

Worth recording what building them cost, because it is the same fault twice: the depth cap is
a derived count over a display tree that splices zero-width nodes, and it was off by one in
**both** directions before a test that ran the multi-root and single-root shapes side by side
caught it. A zero-width node prints nothing, so it must neither occupy a level nor be a level
the cap can cut below. Ordinary use would not have surfaced either — every tree built by
following the playbooks has a single root.
