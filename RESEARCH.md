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

---

## What to run next

Roughly in order of what would sharpen the most per unit of GPU time.

1. **The temperature non-monotonicity, properly.** Playbook 2 at n=20 per band, across 5–6
   bands from 0.1 to 1.5, on three different prompts. If the frame-lock at both extremes is
   real it is the most interesting thing here; if it is three-sample noise, that is worth
   knowing in an hour rather than believing for a month.
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
- **No batch filtering.** `show` renders everything; a sweep of six temperature bands would
  be unreadable. `batches` is per-call and there is nothing between "one call" and "the whole
  tree".
- **`gen` moves the cursor** to the span it made, so repeated sampling at one position means
  naming the position each time. Right for walking forward, wrong for sampling in place, and
  worth a flag rather than a change of default.

None of these needs a format change, which is the point of the format. They are reads and CLI
surface, and each should be built when an experiment is actually waiting on it — not before.
