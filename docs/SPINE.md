# The flagged spine

**An instrument for reading a sampled generation as a record of where sampling did work against the model's preferences — and a loop for spending further inference only where that record says something happened.**

Written for a reader familiar with autoregressive inference and sampling. Nothing here changes how generation works; everything here is about keeping and surfacing what generation already computes.

---

## Premise

Every sampled generation is a sequence of decisions, and ordinary inference discards the record of them. At each position the model produces a full distribution; the sampler draws one token; the distribution — including the token the model ranked first and the price paid for not taking it — is thrown away. What remains is text, indistinguishable from text the model produced greedily, however far from the model's preference it was actually steered.

The premise of this instrument is that the discarded record is the interesting part. Keep it, and a single ordinary generation becomes a measurement: of the model, of the sampler, and of the interaction between them on this context. No parallel machinery, no search, no tree of alternatives to attend to — one path, annotated with what it cost.

## The spine

**One sampled path, drawn however the user likes, with per-position distributions recorded.** Any sampler, any settings — the instrument is agnostic and the settings are part of the record. This path is the spine: a plain realised generation that would read identically in any other tool. What distinguishes it is that nothing about how it came to be has been forgotten.

The spine is the reader's object. They are reading their output, as they would anywhere; the instrument annotates it.

## Flags

**A flag marks each position where the sampled token differs from the argmax token.** These are the positions where sampling did work — where the draw moved the continuation off what the model would have produced on its own. Everywhere else, the sampler was decoration; at a flag, it was causal.

Flags are observations, not hypotheses. Machinery that tries to decide where a model *might* be movable — orderings over candidate branch points, admission thresholds, frontier policies — is placing bets before spending. A flag is a bet already placed and settled: a different token *was* drawn, at a recorded price. That price is the log-ratio between the argmax and the sampled token, and it gives each flag a magnitude.

Three properties fall out immediately:

- **The number and placement of flags is a joint function of model, sampler, and context.** A near-greedy draw flags rarely; a hot one flags densely. The same temperature flags differently on a memorised passage than on open prose. Flag density is itself a reading of how hard the context pins the model down.
- **Per-flag prices sum to the path's accumulated deviation** — the summed log-ratio of every divergence against the token it displaced. The path's total distance from the model's preferred continuation is not a caption on it but a decomposition over it: the reader sees not only how far this generation wandered but exactly where every unit of the wandering was spent.
- **Paths drawn under different samplers remain comparable**, because deviation is measured in the model's own units, not the sampler's nominal settings. A draw at high temperature that happened to hug the argmax path sits low on the axis; a mild draw that hit an unstable region sits high. The realised perturbation is what is measured; the intended one is metadata.

## Two families of measure, not one

**A flag marks where sampling did work. A distribution measure marks where work was available.** These are different maps and both are needed, because a flag can only appear where the draw happened to diverge — and a position where the model was genuinely torn, but the draw took the argmax anyway, is invisible to flags while being precisely the kind of position worth knowing about.

A flag is **draw-relative**: it reads the row the draw took against the row the model preferred, and it is silent wherever the draw did not go. A **distribution measure** reads the ranking alone and is indifferent to what was drawn — entropy at the position, the gap between the top two tokens, the probability mass of the head, whatever else the recorded distributions support. Both are per-position quantities drawn along the path, toggled and thresholded at read time; `docs/SURFACE.md` calls that machinery an **overlay** and takes either kind. What they do not share is what makes a position worth marking, and only the second distinguishes the two populations flags alone conflate:

- **A decision** is a position split strongly between a small number of options — the second token carries real mass. Divergence here is the model entertaining an alternative.
- **A scramble** is a position where the model has no opinion — many near-equal options, a flat head. Divergence here is a die roll. Temperature buys most of its flags at scrambles, because that is where flattening the distribution has the most effect; the decisions are rarer and are the ones that matter.

That distinction is a read-time one: nothing about the generation depends on it, and the threshold that separates the two can be moved with a slider, wrong at zero cost.

**Neither family can see a loop, and the reason is that neither is wrong about it.** Both read confidence — one the draw against the model's preference, the other the ranking alone — and a repetition loop is confident: a model that has said a phrase three times ranks it highest the fourth, and every position inside the loop is a decision cleanly made. So a degenerate region reads as the calmest text on the page under either measure, correctly. What tells a loop from fluent prose is not in the distribution at all but in what the tokens are, which is why `docs/SURFACE.md` admits a measure of the vocabulary below a node and why that is the only kind of measure that could mark one. `data/continuations` holds the case: one path drawn at temperature zero settles into a single sentence repeated four times. What settles the claim is drawing each measure over that path and seeing which of them marks it.

## Stubs

**A stub is a short greedy rollout from the token the sample displaced.** The spine shows where the sampled token went; the stub shows where the model wanted to go. Together with the flag they form a chain — sampled → argmax → stub — that turns a token-level event into a legible counterfactual: *here, the draw went one way; had it not, this is the continuation that was foregone.*

Stubs answer the question a flag alone cannot: **did the divergence last?** Most flags are cosmetic — a synonym drawn, the continuation re-converging within a few tokens. That re-convergence is a finding in itself: the position looked open and was not; the model absorbed the perturbation and returned to its path. A flag whose stub goes somewhere genuinely different is the other kind — a real fork, found by observation rather than predicted by heuristic.

Whether a stub has re-converged is left to the reader's judgement, deliberately. It is not obvious the question has a closed form, and the chain presented plainly — this token, that token, this continuation — is enough for a reader to decide how and whether to continue. Formalising re-convergence (n-gram overlap over a window, embedding distance, anything else) is analysis performed later over recorded chains, not a gate built into the loop.

Stub mechanics, first cut: a flat 20 tokens, greedy, generated on demand for flags the reader touches. Greedy rollouts are deterministic — a pure function of the position — so each is generated once ever, and every stub deepens the record for any later reading of the same region. A stub that immediately cycles is not a failure but a diagnosis, delivered exactly where it applies: *from here, the model's preference is a loop.* Attractor detection arrives as a per-position annotation, free.

## What this asks of a reading surface

**Text with a margin, not a chart.** The reader is reading; the instrument annotates. How that is drawn is `docs/SURFACE.md`'s and is not answered here — what this asks for is that the annotation stay subordinate to the prose, since a reader who has to leave the text to consult the instrument is reading the instrument.

One demand is not cosmetic. **A stub should read as the model's habit and not as the right answer.** The instrument wants a reader who was moved off the greedy continuation to notice they were moved, not to defer to greedy; recessive rendering is what that comes to, and it is the one place where getting the visual weight wrong changes what a reader concludes.

**Nothing here needs more than one screen.** A context, one draw, and the flags on is already the loop; everything past that is the loop used more.

## Continuation and recursion

The loop above is one spine, read. What follows from it is chosen by the reader, and every choice decomposes into the same three moves:

- **Select positions to inflate** — by touching flags directly, or by thresholding an overlay (every flag above this deviation, every position above this entropy). What was a generation-time policy problem in a controller becomes a read-time filter.
- **Choose how to inflate** — greedy stubs are the default and the cheapest, but a stub is just a short generation and other policies are admissible where they earn their spend.
- **Analyse what came back** — re-convergence, n-gram structure, embedding distance between chains — producing further overlays, returned to the same margin.

And any stub can be **promoted to a spine of its own**: the reader walks into the counterfactual and the whole apparatus applies from there. The structure underneath is a tree — spines and stubs share prefixes and accumulate — but the tree is never the reading surface. It is reached one promotion at a time, on demand, which recovers branching exploration as a gesture rather than imposing it as a default.

## Aggregation

One spine's flags are one draw's story. **Across many spines over the same context, flag positions aggregate into a fork map**: positions that flag repeatedly, across draws and across sampler settings, are the context's real decision points — identified by repeated observation rather than by a ranking heuristic. Positions that flag once and re-converge are noise the aggregate washes out. Stubs that loop, collected across a region, map the attractors.

This is the analyst's layer, and it asks nothing of the reading loop: it is queries over what the loop naturally sheds. The resistance of a model on a context — how much has to be spent to move it, and whether it can be moved at all — is assembled here, from flags whose prices are recorded and stubs whose destinations are known. A context on which flags are rare, expensive, and uniformly re-convergent is a context with one attractor and a model that will not leave it, and that finding is the sort the instrument exists to make visible.

## Why this shape

- **Annotation over ordinary use, not a parallel workflow.** The marginal cost of the instrument at generation time is retaining logprobs — information already computed. Everything else is read-time. A tool that transforms normal inference is used; a tool that demands its own attention economy is visited.
- **Observation over prediction.** Every mechanism here reads what a draw actually did, then spends further inference only where something happened. The alternative — machinery for predicting where divergence would be worth buying — is deferred until aggregated observation shows what such machinery would need to be right about.
- **Policy at read time, reversibly.** Thresholds, filters, and convergence judgements all live where they can be changed at no cost. The only generation-time decisions are the sampler settings the user already makes and a flat stub length, and both are recorded rather than load-bearing.
- **The reader's judgement is the sensor.** Which flags get touched, which stubs get promoted, where reading stops — the loop runs on attention, and attention leaves a record. What that record is later good for is a question the aggregate answers; nothing in the loop depends on answering it first.

## Evidence in hand

From the continuation probe, and carried here when `docs/CONTROLLER.md` was superseded — that
document's loop is gone and its measurements are not. Each bears on something below.

**Selecting positions by the gap picks scrambles, not decisions.** Over the probe's 12,683
recorded positions, the top five per cent of nodes chosen by each criterion: by **absolute
probability**, a top token of 0.479 and a second of 0.352, the two carrying 83% of the mass
between them; by **margin**, 0.144 and 0.138; by **ratio**, 0.198 and 0.191. The last two select
the flattest population in the tree — positions where the *winning* token is worth 0.14 and the
model has no opinion to explore. This is a finding about using an overlay to *choose* where to
spend, and not about a flag's magnitude, where the same quantity is the honest price of a
divergence that was already observed.

**Loops are common, and certainty does not find them.** Loops appeared in a quarter of near-greedy
paths, at periods from 7 to 26, in four cases from the very first generated token, and not once at
the highest temperature. **Three of the nine ran at a *lower* top-token probability than the path
around them**, so a detector built on certainty alone misses them. Separately, at near-greedy
sampling 42% to 78% of a path's positions already sat above 0.9, with unbroken runs past a
hundred — so near-certainty is the ordinary state of a path and not a signal within it.

**Branching cheaply is cheap by a wide margin.** Opening seven branch points off a near-greedy
spine cost 1.8 to 3.2 nats of accumulated deviation, against 122 to 204 nats for a single path
sampled at the highest temperature. What that does *not* establish is whether paths branched that
cheaply are as different as paths bought at that price; the probe had no continuations below its
branch points.

**A recorded depth of 20 was ample.** The ceiling truncated 40% of positions, and at those the
twentieth row carried a median probability of 0.0054 — far below anything a selection criterion
reaches. What a narrower record costs a different policy is untested, and rankings extend without
being rewritten, so a later widening is paid for one generation at a time.

**Recorded depth varies with the flatness it is measuring, by a factor of five.** Over the
longest path in `data/continuations` — 392 nodes, 385 of them standing in a ranking, recorded at
a mass of 0.9 and a ceiling of 10 — the 283 positions whose top token carried above 0.9 hold a
median of 2 rows, which is the floor the rule sets; the 31 below 0.5 hold 10, the ceiling, having
reached a median mass of only 0.882. The rule spends depth where there is spread, so a
depth-bound measure is thin exactly where it has least to say and deep where it has most. Nothing
has to move the bounds for this to happen, and that the variation is not arbitrary is what makes
carrying it worth more than levelling it away.

**It reproduces on a path five times longer whose confidence profile is the opposite.** Over
2,036 ranked positions under the same bounds, positions above 0.9 again hold a median of 2 rows
and those below 0.5 again hold 10. What differs is the mix: 74% of the first path sits above 0.9
against 20% of the second, so one path is mostly floor-bound and the other mostly ceiling-bound
while the rule's response to flatness is identical. **A path's recorded depth is therefore a
reading of the path and not a setting of the session**, which is why an overlay carries it.

**Temperature cannot be what flattens a ranking**, since
`src/tokenloom/adapters/llamacpp/README.md` measures the recorded values as pre-temperature and
bit-identical across a sweep of it. So a hotter draw does not widen the record at a position; it
lands the path on positions that are wider. Which of those two paths is flatter *because* of how
it was drawn, rather than because of where it went, is not settled by this and would want one
context drawn several ways.

**A ranking says most about what it left out where it holds least.** A draw that landed outside
the recorded rows is censored rather than missing — what was written is a prefix, so the token
taken sits at or below the lowest row — and how much that says is the span from the top row to
the last, which `docs/SURFACE.md` draws as a bound. Over the 13,315 ranked positions of
`data/continuations`, that span is **widest at the shallowest depth**: the 4,553 positions holding
two rows, which is the floor the rule sets, span a median of 5.81 nats, against 3.1 to 4.4 across
every depth from three to nine. The rule is the reason. Two rows suffice only where one token
already carried the mass, and those positions carry a median top probability of 0.991, so the
second row is far beneath the first. Where the rule ran to its ceiling instead the position was
flat — median top probability 0.26 at ten rows and 0.28 at twenty — and the rows are packed, 2.46
nats across ten of them and 3.95 across twenty. **So a bound is strong exactly where a reader
would expect the record to be weak**, and the deepest records give the loosest ones.

**Censoring is the draw read against the record, and not either one alone.** The same tree holds
62 censored positions in 13,595 nodes, and every one came from a single 90-token draw at
temperature 1.4 recorded to ten rows — 62 of that act's 90 tokens, against none at all from the
sixteen earlier acts at the same temperature that recorded to twenty. So a hot draw does not
censor by being hot; it censors where the record was sized for a colder one. That makes
`record_rows` a choice about how much of a hot path stays readable rather than only a cost, and
it is the one parameter whose right value cannot be known before the draw it is recording.

**The frontier outruns any reader almost immediately.** One 150-token path contributes 14 candidate
edges above probability 0.40, 25 above 0.30, and 118 above 0.10 — and each path those open
contributes as many again. Readability is the binding constraint, not inference cost.

## Deliberately open

Each of these is left to be settled by use of the instrument, and each names what would settle it:

- **Whether re-convergence has a workable formal measure.** Settled by comparing candidate measures against reader judgements over recorded chains — no generation required.
- **Stub policy beyond a flat 20.** Settled by where readers actually stop reading stubs, and which stubs they extend.
- **Which distribution measure best predicts the flags that turn out to matter** — entropy, gap, head-mass, or something composite. *Evidence in hand* rules out the obvious answer for selection and leaves the question. Settled by the fork map: aggregate which positions produced lasting divergence, and score each measure as a predictor of them.
- **Whether automated inflation earns its place** — thresholds that spawn stubs unprompted, or policies that spend ahead of the reader. Settled by whether readers, given the manual loop, converge on repetitive selection patterns a policy could serve.
- **Which embeddings, if analysis wants them.** Settled by probing candidates against chains that already exist; nothing upstream depends on the choice.