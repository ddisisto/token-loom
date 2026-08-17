# Research

The other thread. `ROADMAP.md` is the build path — an API and a front end, on top of a core
that is finished. This is the thread that *uses* the core, and its instrument already works:
`loom.py`, `data/demo/` and `PLAYBOOKS.md` are a working research setup, not a preview of one.

This is the **landing page**: the questions, what is currently believed about each, and what
to run next. It has no end state and it is not a roadmap, but it does have a length budget —
when it stops being readable in one sitting it has stopped doing its job.

- `experiments/` is the record. One file per experiment, pre-registration and results,
  written once and not tidied afterwards.
- `PLAYBOOKS.md` is the *how*: five moves, with commands, against the committed `data/demo/`.
- `BEYOND-MVP.md` holds what the instrument cannot do yet and what it would cost.

## How to read the findings

**Every finding carries its evidence.** There is no blanket disclaimer, because a blanket
disclaimer is wrong in both directions once some things are pre-registered at `n=20` and
others are three samples read by eye — it over-hedges the first and launders the second.

A finding tagged *(001)* points at an experiment file. A finding tagged *(playbook 2)* was a
demonstration, not an experiment: it happened before pre-registration existed here, its
transcript is in `PLAYBOOKS.md`, and it is an impression rather than a measurement. Where a
finding has nothing after it, that is the tag.

### What a finding may claim

**Distributional, with a confidence — never a byte-exact absolute.** This is a deliberate
trade and it decides what the instrument is for.

An individual span is not guaranteed to regenerate byte for byte from the conditions it
carries. `cache_prompt` is on, and a warm prompt cache perturbs the logits enough to flip a
near-tie now and then. What that perturbation is *not* is contamination between calls: the
cache is a pure function of the prompt tokens, no seed reaches it, and nothing of one
request's sampling survives into the next. It is unbiased numerical noise from a different
batch shape, so warm and cold are two draws from one distribution rather than one right and
one wrong.

Which means a claim about *what the model tends to do* is untouched, and a claim about *what
this specific span did* is a claim about a record rather than about a reproducible event. The
first is what the questions below ask. The second was never the product, and buying it back
cost a prompt reprocessed on every call for a guarantee already conditional on the same build,
the same GPU and the same quantisation.

So: prefer more samples over exact ones, and report an interval rather than a number wherever
the sample size will carry one. Experiment 001 is the pattern in negative — `n=20` was chosen
to resolve 40% against 80% and was honest that it could not resolve 60% against 75%, which is
what let its null result mean "too small to see here" instead of "did not happen".

---

## The questions

From `ROADMAP.md`'s framing, which has not changed and is what the instrument was shaped
around.

### 1. Attractors in the prior — where does a prompt tend to go?

**The attractor is not in the token sequence.** Eight continuations of *"The lighthouse keeper
wrote in his log:"* at 0.9 share no common prefix at all, and seven of the eight arrive at the
same place: an arithmetic word problem. The prior for that prompt is not "a lighthouse
keeper's log", it is "a maths textbook using one as set dressing". Continuations that agree on
nothing lexically still agree on what kind of text they are. Whatever is being pulled toward
lives at the level of register, form, corpus region — not surface.
*(playbook 1; n=8, one prompt, read by eye. The best thing on this page and the least
measured.)*

That is the thing this thread most needs a number for, and the cheapest available number does
not measure it. `lock(k)` compares token sequences, which is precisely the level the attractor
is *not* at. **The cheapest measurement and the thing worth measuring are not the same
thing** — noticing that was worth more than either. It also sharpens what an embedding would
be *for*: distance between sibling continuations is the natural handle on genre-level
convergence, where token overlap is the handle on surface convergence, and the gap between
them is the finding. See `BEYOND-MVP.md`.

**Divergence is nested and plural, not a single branch point.** At 0.3, eight continuations
occupy two distinct paths for three tokens, then five, then seven — a trie among the siblings
rather than one fork.

Eight continuations of 32 tokens from one position, seeded distinctly. Run to settle whether
prefix-merging was worth doing in storage; `BEYOND-MVP.md` cites these numbers and this is
where they live, because a read about what the model does is not a fact about files.

| temperature | common prefix, all 8 | distinct paths by depth | fully diverged | shared storage |
| --- | --- | --- | --- | --- |
| 0.3 | 0 tokens | 2, 2, 2, 5, 5, 5, 6, 7 | depth 13 | 13.4% |
| 0.9 | 0 tokens | 3, 7, 8, 8, 8, 8, 8, 8 | depth 3 | 2.3% |
| 1.2 | 0 tokens | 4, 7, 8, 8, 8, 8, 8, 8 | depth 3 | 2.0% |

*(one prompt, n=8, three bands. The trie shape holds. The zero common prefix does not
generalise: 001 found eighteen tokens shared across twenty siblings at 0.1 on a constrained
prompt, and 0.3 is this table's lowest band. Read the zeroes as "at 0.3 and above, on this
prompt".)*

### 2. Temperature as a gate — what does it give access to?

**Agreement declines monotonically with temperature. There is no non-monotonicity.** An
earlier three-sample reading suggested `lock(3)` was U-shaped, high at both 0.2 and 1.3 and
low in between. Twenty samples per band across three prompts says otherwise on all three: the
naive model of temperature was right.
*(001; n=20, three prompts, six bands, pre-registered. A negative result, and the reason to
pre-register.)*

**Depth carries the signal; presence does not.** `lock(3)` is pinned at 1.00 across half of
one prompt's range and never falls below 0.75, while `lock(10)` over the same range runs 1.00
down to 0.05. Three tokens is short enough that agreement there survives almost anything. The
interesting variation is in how *far* agreement extends, not whether it exists — which makes
`lock(10)/lock(3)` the number to watch and made the pre-registered primary measure the blunter
of the two on offer.
*(001; n=20, three prompts.)*

**At low temperature, most of the samples are the same sample.** At 0.1, exact byte-identical
duplicates out of 20: 15, 12 and 2 for the three prompts. Twenty generations on the most
constrained prompt buy five distinct continuations.
*(001; n=20, three prompts. Bears on the prefix-merging rejection in `BEYOND-MVP.md`, which
was decided on shared-storage numbers from 0.3 and above and does not cover this case.)*

### 3. Framing as a change of basis — how much prior has to be visible?

**The prompt sets an envelope, and temperature only moves within it.** This is the largest
effect measured so far and nothing predicted it. Three short, unremarkable English prompts
spread `lock(3)` at fixed temperature about as widely as six temperature bands spread it at
fixed prompt — and the most open prompt at **0.1** is less converged than the most constrained
one at **1.5**. Whatever temperature is doing, the envelope varies more than the thing inside
it.
*(001; n=20, three prompts, six bands. Found by an experiment aimed at question 2.)*

**How much prior is visible changes what gets continued.** One position, 40 bytes of prefix
against 404. With the tail only, the model invents a context — significance testing,
cosmology. With the whole note it continues the note's own argument, one continuation picking
up its *first / second* structure.
*(playbook 3; two points, n=2 each, one prompt. Two points is not a curve.)*

#### The null prompt is not a baseline

Worth writing down because it was believed for a while and is wrong. Generating from an empty
prompt feels like the privileged view of the prior — the model unprompted, saying what it
would say. It isn't. It is one more conditioning, and a strange one: the region of the
distribution reachable from no context at all is narrow and unrepresentative, not neutral.

The prior is whatever it is, and it is not directly observable. Every prompt is a window onto
some part of it, the sliding window is the instrument for moving that window around, and no
position of the window is the true one. So framing is not distortion away from a baseline,
because there is no baseline to be distorted away from. It is the only access there is.

Which makes the instrument more interesting rather than less, and puts the burden somewhere
specific: on choosing windows whose bias is legible, and on saying what it is.

### 4. Survival under retransmission — what persists?

**The content washes out; the genre does not.** Eight steps, each seeing only 120 bytes of
what came before. The seed instruction is out of view within two steps, and by step 7 the text
was numbering its own advice in the same instructional register it had drifted into by step 1.
*(playbook 5; one chain of 8, one seed. Consistent with question 1 and equally unmeasured.)*

### 5. At what level does convergence live?

Emerged from the runs rather than from the framing, and it is the question the other four keep
turning into. Question 1's answer says genre, not tokens. Question 2's says the lexical
measure has real dynamic range but at a level that may not be the interesting one. Question
3's says the prompt sets the envelope — and "envelope" is doing unexamined work in that
sentence.

Nothing here answers it yet. It is what an embedding would be for.

---

## What to run next

Roughly in order of what would sharpen the most per unit of GPU time.

1. **The prompt effect, which is bigger than the one that was being measured.** Many prompts
   at two or three bands, rather than many bands — the axis worth sampling densely is the one
   that turned out to move things. Pick prompts along something articulable (how constrained
   the continuation is, how much of a genre the opening names) so the result is a statement
   rather than a scatter. That choice is the hard part and wants its own pre-registration.
2. **Attractor strength as a number.** Playbook 1 across many prompts at fixed conditions.
   What fraction escape? Does the escape rate move with temperature?
3. **Framing as a sweep, not two points.** `prompt_length` over a range rather than 40 versus
   404, looking for whether character changes gradually or has a threshold.
4. **Retransmission, long.** Forty steps rather than eight, with a fixed window. When does
   seed content die, and does the register stabilise or keep drifting? The cheapest
   long-running experiment available.
5. **Single-token stepping as frequency measurement.** At length 1, N spans over a handful of
   distinct tokens: the multiplicity *is* an empirical frequency, to be set against the
   logprobs recorded beside it. Does the sampler do what the logprobs say?

---

## The experiments

| | what | verdict |
| --- | --- | --- |
| [001](experiments/001-temperature.md) | Temperature across three prompts, `n=20`, six bands | P1 fails — no U. Turned up the prompt effect instead. |

Each file holds a pre-registration written before the run and results written after, in two
commits, so `git log --follow` over one file shows whether the registration was edited once
the numbers were in. That property starts at 002: 001's file begins with a move, since it was
written when this was one document.

**The tree is committed beside the write-up**, at `experiments/NNN-name/`. That follows from
the stance above rather than from tidiness: if a span is not guaranteed to regenerate from
what it carries, the artefact is the evidence, and a verdict citing a tree nobody else has is
a verdict nobody can check. Read one with `LOOM_TREE=experiments/NNN-name scripts/loom.sh`.

The five playbooks and the original sibling-divergence table are **not** in here. They predate
pre-registration, and giving them experiment files would imply a rigour they did not have.
Their record is `PLAYBOOKS.md` and their conclusions are tagged as impressions above.

---

## What the instrument cannot do yet

Tool gaps that block the above, as opposed to conveniences. None needs a format change, which
is the point of the format — they are reads and CLI surface, and each should be built when an
experiment is waiting on it, not before.

- **No genre-level measure.** Every finding under question 1 was read by eye, and `lock(k)` is
  explicitly the wrong level for it. This is the gap that matters most and the only one that
  needs something the project does not have — see embeddings in `BEYOND-MVP.md`.
- **No export.** Getting a tree into anything else means reading the sqlite directly. Fine for
  now; a blocker the moment there is a statistic worth plotting.

Closed, both because 001 needed them: `gen --stay` samples repeatedly at one position without
naming it each time, and `show <position> --depth n` plus `batches --params <key>` make a sweep
readable. Building the second cost an off-by-one in *both* directions, because the display
tree splices zero-width nodes and a node that prints nothing must neither occupy a level nor
be one the cap can cut below — invisible to ordinary use, since every tree the playbooks build
has a single root.

## Constraints on what is measurable

Facts about the apparatus, kept here only as consequences. The facts themselves live where
they rot at the right rate: format in `FORMAT.md` under *Settled by measurement*, inference
and llama-server in `CLAUDE.md` under *Inference*.

- **Local serving is the only option**, not a preference — no hosted provider returns logprobs
  on a raw continuation.
- **Tokens and counterfactuals are independent records.** The sampled token is absent from its
  own top-3 about a third of the time at 0.9, so a counterfactual list is not a ranking with
  the winner marked.
- **`<|endoftext|>` is an ordinary token in the distribution.** The demo caught it sampled at
  rank 0 with two ordinary words ranked below it, producing a span of zero bytes terminating
  as `eos`. Nothing swallows it, and an empty stop list generates straight through it.
- **A token can be a fragment of a character**, and llama-server regroups its per-token records
  onto character boundaries. So a merged row carries no id and no logprob, and any per-token
  statistic is over *entries* rather than model tokens wherever multi-token characters appear.
  Measured at zero on English prompts and everywhere on astral-plane ones.
- **Stop strings off a token boundary lose bytes silently**, so keep them to plausible token
  sequences until the token-replay path exists.
- **A span is not guaranteed to replay byte for byte.** `cache_prompt` is on, and a warm cache
  perturbs the logits enough to occasionally flip a near-tie. The perturbation is unbiased
  floating-point noise from a different batch shape — the cache carries nothing from one
  request's *sampling* into the next — so a distribution is unaffected and only the particular
  draw changes. This is the trade named under *What a finding may claim*, and
  `BEYOND-MVP.md` holds the ways back to exactness.
