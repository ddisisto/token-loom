# The priced spine

**An instrument for reading a sampled generation as a record of where sampling did work against the model's preferences — and a loop for spending further inference only where that record says something happened.**

Written for a reader familiar with autoregressive inference and sampling. Nothing here changes how generation works; everything here is about keeping and surfacing what generation already computes.

---

## Premise

Every sampled generation is a sequence of decisions, and ordinary inference discards the record of them. At each position the model produces a full distribution; the sampler draws one token; the distribution — including the token the model ranked first and the price paid for not taking it — is thrown away. What remains is text, indistinguishable from text the model produced greedily, however far from the model's preference it was actually steered.

The premise of this instrument is that the discarded record is the interesting part. Keep it, and a single ordinary generation becomes a measurement: of the model, of the sampler, and of the interaction between them on this context. No parallel machinery, no search, no tree of alternatives to attend to — one path, annotated with what it cost.

## The spine

**One sampled path, drawn however the user likes, with per-position distributions recorded.** Any sampler, any settings — the instrument is agnostic and the settings are part of the record. This path is the spine: a plain realised generation that would read identically in any other tool. What distinguishes it is that nothing about how it came to be has been forgotten.

The spine is the reader's object. They are reading their output, as they would anywhere; the instrument annotates it.

## Deviation

**Every position carries a deviation: the log-ratio between the token the model ranked first and the token that was taken.** It is zero where the top row was taken and positive where anything else was, so what runs along a path is one quantity over its whole length rather than a set of marks on otherwise plain text. A position whose deviation is positive is a **divergence** — there, the taker moved the continuation off what the model would have produced alone; everywhere else the sampler was decoration.

**In the field's terms a deviation is a surprisal baselined against the position's mode, and the
baseline is why it is not perplexity.** Perplexity and cross-entropy price the tokens that were
realised; deviation subtracts the price of the cheapest token available, so it reads what the
taking did rather than how well the model predicted — `surprisal(taken) − surprisal(top₁)` is the
whole of it. The unbaselined quantity is used here as well, since what a path costs per unit of
text is a cross-entropy, so the two sit side by side and only the baselined one is this document's
own. **It is not a divergence between distributions**: a KL is an expectation and nothing here
takes one, while a deviation is a single realised log-ratio. Its nearest named relative is a
per-step regret against greedy decoding, and the name is not borrowed because regret asserts the
argmax was correct — which is what *What this asks of a reading surface* exists to prevent.

A deviation is an observation, not a hypothesis. Machinery that tries to decide where a model *might* be movable — orderings over candidate branch points, admission thresholds, frontier policies — is placing bets before spending. A divergence is a bet already placed and settled: a different token *was* taken, at a recorded price.

Three properties fall out immediately:

- **Counting divergences reads the sampler; summing deviation reads the path.** How often a draw leaves the argmax is very largely a function of the temperature it was asked for — *Evidence in hand* measures it from one position in seven thousand to three in five across the dial — so a count is a readout of how a batch was requested. The prices are not, and they are the part an ordinary generation does not keep.
- **Deviation sums along a path, and what it sums is not a distance to one continuation.** Each term is measured against the argmax *given the path as it actually ran to that point*, so once the path has left the model's preference it is being read against a preference that has itself moved. The total accumulates local prices rather than separating two texts, and what makes it worth having is that it decomposes: the reader sees not only how far this generation wandered but where every unit of the wandering went.
- **Paths drawn under different samplers remain comparable**, because deviation is measured in the model's own units, not the sampler's nominal settings. A draw at high temperature that happened to hug the argmax path sits low on the axis; a mild draw that hit an unstable region sits high. The realised perturbation is what is measured; the intended one is metadata.

**What a deviation may be read against is bounded by the rows recorded beneath it.** The recording rule spends depth where the ranking is flat, so a sharp position arrives with a shallow record and a flat one with a deep record, and depth is therefore not independent of anything a measure might band by. *Evidence in hand* has what that costs a reading that ignores it.

## The price has a payer, and `realise` is how it changes hands

**A deviation is an amount and the record says who paid it.** What the log-ratio does not carry is whether the sampler moved the continuation or the reader did. Nothing read off a ranking has separated them yet. `scripts/takers.py` splits a deviation into the toll for leaving the argmax and how far past the best alternative the taker went, on the proposal that the second tells a deliberate divergence from a hot draw, and the two populations sit in nearly the same place on it; *Evidence in hand* has what banding them by depth and by list length then found. The acts separate them exactly, because a `realise` names the node it produced.

**Read as a share, the price is bounded and the payer is a partition of it.** Take `p(taken) / p(top)` as the model's share of a position: one where the draw took the argmax, and falling toward zero as the taker went further down. The balance is the **displacement**, and it is allocated whole — to the operator where a `realise` stands at that node, and to the sampler otherwise. It is the quantity deviation already is, in a bounded space rather than a log one, since `deviation = −log(share)`. What the bounded form buys is a domain nobody had to choose, and something that can be attributed. **Both terms are always there.** A draw records its own value beside the ranking rather than inside it, so the share reads at every drawn position however few alternatives were kept with it, and a deep draw does not have to be reached by widening the rows above it.

**The share is the coordinate `min_p` thresholds on, exactly.** That sampler keeps a token when
`p(token) / p(top)` is at least its setting, which is the share under another name — so a
threshold on deviation is a threshold on `min_p` read in log space, and any gate here can be
stated as the setting that would have excluded what it selects. A gap of 2.0 nats is a second row
at a share of 0.135; a deviation of 3.0 is 0.050, which is this server's default. The
correspondence is exact rather than analogous, and it is worth saying because a reader who has
tuned that dial has already calibrated this axis — nothing had to be chosen for that to be true.

**The balance is to the argmax and not to one.** A position's remaining probability is the model's own uncertainty, which is a different thing from something other than the model having decided. A greedy draw where the top row holds 0.4 is maximally uncertain and has displaced nothing — it took the argmax, deterministically, which is the whole of what makes it the reference arm. Balancing to one would charge it 0.6 and leave the instrument with no zero.

**`realise` transfers the displacement rather than adding to it.** A reader taking a row the sampler had already drawn arrives at the same node, since `(parent, token_id, source)` merges, and writes an act saying they took it. Nothing about the position moved; what moved is who the displacement is charged to. So this is not an ownership two acts contend for but an attribution the later one changes, and a node both acts cover is not a conflict to resolve.

**Agreeing costs nothing, and that is why the payer cannot be read off the price.** An operator who realises the top row has displaced nothing, pays nothing, and still acted. A position therefore carries one scalar and one bit, and the bit does not follow from the scalar — which is what `docs/SURFACE.md` arrives at from the drawing side when it keeps a mark beside a measure.

**An authored token allocates the same way wherever a ranking stands above it.** What is particular about a `create` is that nothing offered the token, not that the reader takes the whole displacement by default: a reader who writes what the model would have ranked high has displaced little, and that is the control case measuring itself rather than being asserted. Where no ranking stands above the node there is no share to read, which is an absence and not a zero.

**The share is derived, and it is read against a source.** The ranking is the observation and the store holds it; the share is arithmetic over stored logprobs and is not a column. So it moves when a ranking deepens, which is true of everything derived — and it moves when the source differs, which is the more interesting case. A ranking is an observation under conditions, and two deployments ranking one path disagree exactly where the deployment is what is being measured. *Stubs* names the conditions the reference arm is exact under; they are these conditions.

## Two families of measure, not one

**Deviation marks where sampling did work. A distribution measure marks where work was available.** These are different maps and both are needed, because deviation can only be positive where the draw happened to diverge — and a position where the model was genuinely torn, but the draw took the argmax anyway, reads as zero while being precisely the kind of position worth knowing about.

Deviation is **draw-relative**: it reads the row the draw took against the row the model preferred, and it says nothing wherever the draw did not go. A **distribution measure** reads the ranking alone and is indifferent to what was drawn — entropy at the position, the gap between the top two tokens, the probability mass of the head, whatever else the recorded distributions support. Both are per-position quantities drawn along the path, toggled and thresholded at read time; `docs/SURFACE.md` calls that machinery an **overlay** and takes either kind. What they do not share is what makes a position worth marking, and only the second distinguishes the two populations deviation alone conflates:

- **A decision** is a position split strongly between a small number of options — the second token carries real mass. Divergence here is the model entertaining an alternative.
- **A scramble** is a position where the model has no opinion — many near-equal options, a flat head. Divergence here is a die roll. Temperature buys most of its divergences at scrambles, because that is where flattening the distribution has the most effect; the decisions are rarer and are the ones that matter.

That distinction is a read-time one: nothing about the generation depends on it, and the threshold that separates the two can be moved with a slider, wrong at zero cost.

**Neither family can see a loop, and the reason is not that a loop is calm.** Both read confidence — one the draw against the model's preference, the other the ranking alone — and *Evidence in hand* measures that confidence does not locate a degenerate region in either direction: certainty does not find them, and some run at a *lower* top-token probability than the path around them. So a loop may read as the calmest text on the page or as the most agitated, and neither reading is a fault in the measure; a loop is simply not what either one looks at. What tells a loop from fluent prose is not in the distribution at all but in what the tokens are, which is why `docs/SURFACE.md` admits a measure of the vocabulary below a node — and why only a measure of that kind, reading tokens rather than distributions, could mark one. `data/continuations` holds the case: one path drawn at temperature zero settles into a single sentence repeated four times. What settles the claim is drawing each measure over that path and seeing which of them marks it.

## Stubs

**A stub is a short greedy rollout from the token the sample displaced.** The spine shows where the sampled token went; the stub shows where the model wanted to go. Together with the divergence they form a chain — sampled → argmax → stub — that turns a token-level event into a legible counterfactual: *here, the draw went one way; had it not, this is the continuation that was foregone.*

Stubs answer the question a price alone cannot: **did the divergence last?** Most divergences are cosmetic — a synonym drawn, the continuation re-converging within a few tokens. That re-convergence is a finding in itself: the position looked open and was not; the model absorbed the perturbation and returned to its path. A divergence whose stub goes somewhere genuinely different is the other kind — a real fork, found by observation rather than predicted by heuristic.

Whether a stub has re-converged is left to the reader's judgement, deliberately. It is not obvious the question has a closed form, and the chain presented plainly — this token, that token, this continuation — is enough for a reader to decide how and whether to continue. Formalising re-convergence (n-gram overlap over a window, embedding distance, anything else) is analysis performed later over recorded chains, not a gate built into the loop. **The tree will not hand that analysis its answer.** A trie merges shared prefixes, so two continuations that part at a position and then say the same thing stay two branches the whole way down; re-convergence is a comparison over token sequences and is never a merge.

**The greed is what earns the name, and it is a condition rather than a decoration.** An interferometer splits a signal, sends one part down a reference arm and the other down a measurement arm, and reads what differs when they recombine. The spine is the measurement arm — the path as it actually went, under whatever sampling and whatever interventions. The stub is the reference: the model left alone from the same position. A difference between them is attributable to the intervention **only because no sampling noise entered the reference**, which is what a temperature of zero buys and the only thing it is bought for. A stub drawn with any width to it would make the comparison a comparison of two draws, and there would be nothing to read off it.

**So the arm is exact only under conditions, and they are worth naming where the claim is made.** `src/tokenloom/adapters/llamacpp/README.md` measures them: cold, a rollout reproduces bit for bit; warm, the prompt cache is a second variable, and a *partial* hit moves logprobs by up to 0.58 and has moved a greedy path off its cold course. Hardware and batch-level nondeterminism are not controlled for either, and a seed does not reach the cache. What follows is not that the reference is useless but that it is a reference *on this machine, in this cache state* — exact where it is read against a spine drawn under the same conditions, and advisory across them.

**A stub is asked for by hovering the row it belongs to.** The reader opens the rankings at a position, moves onto a row, and the row grows to show where taking it would lead — which is what a stub is for and where it comes from. Nothing rolls out unasked; `Deliberately open` has whether anything should.

Stub mechanics: greedy, short, and born set aside, so what a hover spends enters neither the live path nor the continuation rule. Replacement is foreclosed and deliberately: a stub that disappoints is not redrawn into a better one, because wanting a different continuation there is wanting a different question asked — rank two at that position, or a hotter draw — and both are the reader's to ask.

**A rollout is a pure function of the position only when the cache is cold, and hovering is the warm case.** `src/tokenloom/adapters/llamacpp/README.md` measures it: a *partial* hit — the cache holding a prefix of a different path, which is exactly what moving between rows at one node produces — shifts logprobs by up to 0.58 and moved a **greedy** path off its cold course at position 11 of 20. So a ranking recorded warm is a function of the model, the path, and what was generated before it, and cold is the only state that reproduces. Turning the cache off recovers exactness at a full prompt pass per hover, which is the feature.

What that costs is bounded and worth stating plainly. **The row's own token is exact**, being read from the stored ranking rather than inferred again, so what a reader takes when they take the token is not in question; it is the continuation past it that is advisory. And a stub is no longer guaranteed to merge on a second rollout, so the same row hovered twice under different cache states can leave two near-identical hidden arms rather than one. Not rolling a row that already carries a stub is what keeps that from accumulating.

**Hovering rows at one node is nearly free after the first.** Every row there shares the path above it, so the second and later rollouts reprocess a single token — measured at `prompt_n` 1 and 26 ms, against 190 ms to draw eight tokens. The first hover at a position pays for the position. That is what makes trying several of them an ordinary gesture rather than a decision.

**What several stubs at one position say together is whether the position matters.** One says where a row would have gone; several say whether the rows go anywhere different. Rows that all re-converge mark a position in a basin — the model arrives at much the same place whichever is taken, and an intervention there will not hold. Rows that go separate ways mark a fork where the choice sticks. That is a different question from how far the draw fell and a better one for deciding where to spend attention: a deviation says the dice went far, and this says going far would have mattered. It asks for nothing beyond what hovering already costs, because the reader weighing the rows is performing it.

**A stub ends three ways, and they mean different things.** It fills the room it was given, and there is more if the reader asks for it. It cycles, and the model's preference from here is an attractor — not a failure but a diagnosis, delivered exactly where it applies: *from here, the model's preference is a loop.* Or it reaches EOS, and the model would have ended the document at a position the draw carried past. The last is the sharpest of the three, because this is a base model and its EOS is a document boundary rather than a refusal to answer. The record tells them apart already: `acts.terminator` carries `eos` against `limit`, and a cycle over token ids is detectable without reading any text. Collapsing them would tell a reader that an exhausted model and a finished document are the same event.

**Detect and stop, rather than penalise and continue.** The instrument ordinarily reached for against a loop is a repetition penalty, and it is barred here by what a stub is: a penalty is a sampler, and a rollout drawn under one is no longer the model's habit. So a cycle ends the stub instead of being suppressed inside it, and the ending is the annotation. Attractor detection arrives per position, free.

**The three endings are also the eligibility test.** A stub is extendable unless it ran out of length, cycled, or ended — the same list read from the side of whatever would extend it rather than the reader's. So what marks a stub's ending and what decides whether to spend more on it are one decision, made once.

**A stub placed unbidden is an alarm, and not a map of where the work is.** *Evidence in hand*
measures where an operator actually intervened, and it is the low-gap end — the positions the
model was torn at, which are far too dense to draw a second line over. Those are reached by
asking, at a position, which is a gesture the surface already has. What can be placed unbidden is
the sparse opposite: the model was confident and the draw went elsewhere, which is the thing a
reader is least likely to notice for themselves. Both are worth having and only one of them is a
line.

**What spawns that alarm is how much the model cared, and not how far the draw fell.** *Evidence in hand* measures both, and they are not independent: at a divergence the draw took something at or below the second row, so **a deviation is never less than the gap**. Selecting on deviation therefore admits every position where a flat ranking was sampled from — which is most of them, and which is a wall rather than a second line. The reason is room and not meaning: the token a rollout starts from may be near-arbitrary where the ranking is flat, but the continuation from it is the model's either way. Selecting on the gap admits the positions where the model was sure and something went elsewhere, which is the whole of what a stub is for. The gap subsumes deviation up to its own threshold, so this is one dial rather than two.

**How deep is what the row can show, and a reader who wants more says so.** A stub shown beside a ranking is read against the room a panel has and not against the prose, which is what taking it out of the column bought. A flat short length is therefore enough to start, and *Deliberately open* has what would settle a better one.

## What this asks of a reading surface

**Text with a margin, not a chart.** The reader is reading; the instrument annotates. How that is drawn is `docs/SURFACE.md`'s and is not answered here — what this asks for is that the annotation stay subordinate to the prose, since a reader who has to leave the text to consult the instrument is reading the instrument.

One demand is not cosmetic. **A stub should read as the model's habit and not as the right answer.** The instrument wants a reader who was moved off the greedy continuation to notice they were moved, not to defer to greedy; recessive rendering is what that comes to, and it is the one place where getting the visual weight wrong changes what a reader concludes.

**Nothing here needs more than one screen.** A context, one draw, and deviation drawn along it is already the loop; everything past that is the loop used more.

## Continuation and recursion

The loop above is one spine, read. What follows from it is chosen by the reader, and every choice decomposes into the same three moves:

- **Select positions to inflate** — by touching divergences directly, or by thresholding an overlay (every position above this deviation, every position above this entropy). What was a generation-time policy problem in a controller becomes a read-time filter.
- **Choose how to inflate** — greedy stubs are the default and the cheapest, but a stub is just a short generation and other policies are admissible where they earn their spend.
- **Analyse what came back** — re-convergence, n-gram structure, embedding distance between chains — producing further overlays, returned to the same margin.

And any stub can be **promoted to a spine of its own**: the reader walks into the counterfactual and the whole apparatus applies from there. The structure underneath is a tree — spines and stubs share prefixes and accumulate — but the tree is never the reading surface. It is reached one promotion at a time, on demand, which recovers branching exploration as a gesture rather than imposing it as a default.

## Aggregation

One spine's divergences are one draw's story. **Across many spines over the same context, they aggregate into a fork map**: positions that diverge repeatedly, across draws and across sampler settings, are the context's real decision points — identified by repeated observation rather than by a ranking heuristic. Positions that diverge once and re-converge are noise the aggregate washes out. Stubs that loop, collected across a region, map the attractors.

This is the analyst's layer, and it asks nothing of the reading loop: it is queries over what the loop naturally sheds. The resistance of a model on a context — how much has to be spent to move it, and whether it can be moved at all — is assembled here, from divergences whose prices are recorded and stubs whose destinations are known. A context on which divergences are rare, expensive, and uniformly re-convergent is a context with one attractor and a model that will not leave it, and that finding is the sort the instrument exists to make visible.

## The failure mode is a loop the operator built

**The obvious success criterion is convergence, and the operator is the one who games it.** A context can be made so over-determined that the model has no real choice left in it. Entropy along the path collapses, every proposal matches what was wanted, and by the convergence measure this looks like mastery. It is a closed loop built by hand: an attractor with the operator inside it, and the model reduced to an echo.

**So the criterion is two-sided. A trajectory is going well when it moves in the intended direction and stays open.** Concretely, and all four measurable from what the store already holds:

- Branching entropy along the path stays above a floor rather than trending to zero.
- Stubs cast from recent nodes do not immediately cycle.
- Accepted tokens are not always rank one; the model is still offering choices that get taken.
- The model still surprises the reader, and some of those surprises are kept.

**None of them is a target and each is a check against the others**, which is what keeps them from becoming the next thing to game. They are also not a score, and the distinction is what lets them exist at all: what they measure is the process and not the artefact — whether choices are still arriving for the reader to decline, and not whether declining them went well. Nothing here says a context is good, which is a call the reader makes and no instrument takes from them. The hypothesis is that skilled operation shows up as direction with openness, and that it is distinguishable in the logs from sophisticated puppeteering.

**The second check is the one the instrument already computes.** A stub that immediately cycles is a diagnosis delivered per position, and a region where every stub cycles is the trajectory closing. *Evidence in hand* has six of 443 generated runs ending in a cycle over one worked session, which is what the check reads as passing.

## Fixed model, adaptive operator

**The weights do not change during a session and the reader does.** Over time they learn the model: its attractors, where its pivots fall, where a one-token intervention moves everything and where a paragraph moves nothing, and when its confidence is worth doubting. It is a fixed landscape and an adaptive navigator of it, and because every act is recorded with a timestamp the adaptation is measurable rather than merely claimed. What the record is asked:

1. Does intervention frequency fall with experience, and do interventions get smaller?
2. Do interventions concentrate at pivots, or at other identifiable points in the trace?
3. Does the rank distribution of accepted tokens shift as the reader learns the model?
4. Does time from decision to decision fall, and where does it stay high?
5. Do experienced trajectories stay open longer by the checks above, while still arriving somewhere?
6. Does guided navigation reach regions of state that sampling alone rarely visits?

**Every one of these is a curve against time and not a number**, which is what `acts.created` makes free and what a single measurement would miss. It also means a feature that changes how a reader behaves does not spoil the measurement; the change is what question three is asking about.

**One comparison comes almost free.** A post-trained model still performs the base function and the store does not care which it is attached to, so running a base model and a post-trained sibling from identical contexts should show what post-training does to the landscape: flatter entropy, fewer real branches, deeper attractors. That is a prediction to check rather than a claim.

**Stated plainly: the operator is also the builder.** That is the right condition for exploratory first-person work and it is how these questions were found. It is not sufficient for claims about operators in general, which will need people who did not build the instrument.

## Why this shape

- **Annotation over ordinary use, not a parallel workflow.** The marginal cost of the instrument at generation time is retaining logprobs — information already computed. Everything else is read-time. A tool that transforms normal inference is used; a tool that demands its own attention economy is visited.
- **Observation over prediction.** Every mechanism here reads what a draw actually did, then spends further inference only where something happened. The alternative — machinery for predicting where divergence would be worth buying — is deferred until aggregated observation shows what such machinery would need to be right about.
- **Policy at read time, reversibly.** Thresholds, filters, and convergence judgements all live where they can be changed at no cost. The only generation-time decisions are the sampler settings the user already makes and a flat stub length, and both are recorded rather than load-bearing.
- **The reader's judgement is the sensor.** Which divergences get touched, which stubs get promoted, where reading stops — the loop runs on attention, and attention leaves a record. What that record is later good for is a question the aggregate answers; nothing in the loop depends on answering it first.

## Evidence in hand

From the continuation probe, and carried here when `docs/CONTROLLER.md` was superseded — that
document's loop is gone and its measurements are not. Each bears on something below.

**The trees these were taken from have grown since, and the figures were not all taken at one
state.** They are stamped now — `data/continuations` at `4099f102…`, `data/logozoa` at
`10d921ba…`, both on 2026-09-28 — so a figure taken from here on can name a state, and the ones
above that date cannot be pinned to one more exactly than *before it*. Neither tree is in the
repository, so a stamp is checkable by whoever holds the tree and by nobody else. **Nothing here
turns on an exact count**; what the figures carry is direction and order of magnitude, and a
reading that needed the third digit would be reading them wrong.

**Selecting positions by the gap picks scrambles, not decisions.** Over the probe's 12,683
recorded positions, the top five per cent of nodes chosen by each criterion: by **absolute
probability**, a top token of 0.479 and a second of 0.352, the two carrying 83% of the mass
between them; by **margin**, 0.144 and 0.138; by **ratio**, 0.198 and 0.191. The last two select
the flattest population in the tree — positions where the *winning* token is worth 0.14 and the
model has no opinion to explore. This is a finding about using an overlay to *choose* where to
spend, and not about a deviation's magnitude, where the same quantity is the honest price of a
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

**The recording rule spends its rows where the ranking is flat**, so the span from the top row to
the last is **widest at the shallowest depth**. Over the 13,315 ranked positions of
`data/continuations`, the 4,553 positions holding two rows — the floor the rule sets — span a median
of 5.81 nats, against 3.1 to 4.4 across every depth from three to nine. The rule is the reason. Two
rows suffice only where one token already carried the mass, and those positions carry a median top
probability of 0.991, so the second row is far beneath the first. Where the rule ran to its ceiling
instead the position was flat — median top probability 0.26 at ten rows and 0.28 at twenty — and the
rows are packed, 2.46 nats across ten of them and 3.95 across twenty. **So depth and span run
opposite ways**, and a reading taken across positions of unlike depth is comparing two different
things.

**The measurements below are what a draw with no recorded value used to cost, and they are the case
for `docs/ADAPTER.md`'s obligation 7.** A source now reports what its own draw was worth, so a draw
landing past the recorded rows is priced like any other. They remain true of every tree written
before that, where such a draw has no value and the record does not say why.

**Censoring was the draw read against the record, and not either one alone.** `data/continuations`
holds 62 such positions in 13,595 nodes, and every one came from a single 90-token draw at
temperature 1.4 recorded to ten rows — 62 of that act's 90 tokens, against none at all from the
sixteen earlier acts at the same temperature that recorded to twenty. So a hot draw did not go
unpriced by being hot; it went unpriced where the record was sized for a colder one. That made
`record_rows` a choice about how much of a hot path stayed readable rather than only a cost, and
the one parameter whose right value cannot be known before the draw it is recording. Obligation 7
takes the readability out of that trade and leaves the cost.

**On a worked tree it was not a curiosity but the majority case.** `data/logozoa` was recorded at
ten rows until late and is 88% greedy draws, so its divergences concentrate in the hot minority the
record was sized too small for: 2,730 of its 4,406 divergences carry no value against 1,676 priced.
Two thirds of what a sum over that tree would add is therefore missing rather than small — which is
what made this worth fixing in the contract rather than working around in a reading.

**A steered tree disagrees with its own top rows at a third of its forks.** Over the 53 forks
of `data/continuations`, the most-grown arm is the model's top-ranked token at 36 of them and
is not at 17 — at ranks 1 through 16, and at six of the seventeen the top row holds nothing at
all. So the aggregate is not a restatement of the ranking, and the channel that draws it has
something to show. **It does not settle whether a well-sampled tree is its own reference arm**,
because this tree was steered rather than sampled: it carries authored roots, `create` acts,
deletions and deliberate forks, and every one of those puts weight somewhere the sampler would
not have. What the number measures is where the reader departed from the model, which is the
other thing the same quantity reads — and the measurement that separates them is still the one
below, how realisation falls with rank.

**The frontier outruns any reader almost immediately.** One 150-token path contributes 14 candidate
edges above probability 0.40, 25 above 0.30, and 118 above 0.10 — and each path those open
contributes as many again. Readability is the binding constraint, not inference cost.

**How often the draw leaves the argmax is a readout of the temperature dial, not of the text.**
Over the 298 generated runs of `data/continuations`, the share of positions that diverge runs
1 in 7030 at temperature 0, 3.0% at 0.05–0.35, 27.4% at 0.4–0.8, and 58.7% above 0.9. So the
rarity of a divergence is a property of how a batch was asked for and not of what it says, and a
document drawn greedily carries none at all — which is the mode this method spends most of its
time in. The texture that reads off a page as alternating dense and empty regions is a record of
method, which is a real thing to be able to see, and it is not the text speaking.

**At a divergence the deviation is never less than the gap, which makes the gap the only dial.** A draw
that left the argmax took something at or below the second row, so `top₁ − taken ≥ top₁ − top₂` by
construction. The counts show it exactly: over the same runs, selecting on gap > 1.0 admits 1241
positions and selecting on *both* gap > 1.0 and deviation > 1.0 admits the same 1241; at gap > 2.0 both
admit 347. Nothing is added by the second condition until its threshold passes the first.

**Selecting on the gap is what leaves room for a stub, and selecting on deviation does not.** Room
is the distance to the next selected position, which is the depth a stub can be shown at.
`scripts/stub-gate.py` is this measurement, over every generated run, against a 400-token screen:

| gate | stubs per screen | median room | room ≥ 8 tokens |
|---|---|---|---|
| every divergence | 74 | 0 | 3% |
| deviation > 3.0 | 18 | 2 | 21% |
| gap > 1.0 | 20 | 3 | 24% |
| gap > 2.0 | 6 | 10 | 57% |

Ungated the counterfactual is a second token against nearly every first, which is not a document
laid beside a document but one document struck through. At gap > 2.0 it is six annotations to a
screen at a median of ten tokens, over half of them long enough to read as language.

**Every number below that reads a `realise` reads one operator, who is also the builder.** The
record holds only what was written, and looking writes nothing, so the realised rows are already
the subset that was not merely scrolled past — but a realised row can still be a casual one, and
nothing separates the two. `Fixed model, adaptive operator` has why that condition is the right
one for the questions and insufficient for claims about operators in general; what it means here
is narrower, that these are one person's habits and not a reader's.

**The gate's room reproduces on a steered tree and its density does not.** `data/logozoa` is one
worked session — 82,508 nodes, 1,036 `realise` acts against 2,536 draws, 4,922 authored tokens —
and `gap > 2.0` lands there at a median room of 9 and 57% of stubs at eight tokens or more,
against 10 and 57% on `data/continuations`. What differs is how many: 2 stubs to a screen against
6. A worked tree is mostly greedy, and a gate that fires where the model was sure fires rarely on
a path drawn from what the model was sure about. So the gate's *shape* is a property of the
measure and its *rate* is a property of how the tree was made, and only the first transfers. The
deviation gate does worse here than there, 15 to a screen at no room, because a steered tree
makes large deviations deliberately and deviation cannot tell those from a hot sampler.

**But the positions its operator chose are the other end of the same measure.** Where they
realised a row, the top-to-second gap has a median of 1.14 nats and is above 2.0 at 33% of them;
over every ranked node in the tree the median is 5.69 and 74% are above 2.0. So intervention
concentrates where the model was torn, and an automatic stub lands where it was sure. They are
not competing answers — a reader asks at the position they are working, and what is placed for
them unasked is what they would not have gone looking for. It does say the line is an alarm and
not a map. (The comparison is against every ranked node rather than every node the reader passed,
which is the cleaner population and is not recoverable from the record.)

**What looked like a preference for the second row was the recording rule.** Of 1,025 realised
divergences, 46% take the second row — but 300 of them stand at a ranking two rows deep, where
the second row is the only divergence there is. Among the 725 with a third row to take, 24% take
the second. An operator offered a choice does not mostly nudge, and the earlier reading of this
number was counting positions that offered none.

**Recorded depth bounds what a divergence can say, and the rule ties depth to the very thing a
reader would band by.** Rows are written until the mass is covered, so a sharp position stops at
the floor of two and a flat one runs to the ceiling — which means depth falls as the gap rises,
by construction rather than by accident. Band any reading of the takers by gap and the high-gap
bands fill with positions that had two rows: every realised divergence above a gap of 4.0 takes
the second row, at 100%, because the record holds no third one there. The measure is reading the
rule back out. `scripts/takers.py` is this, and the correction is to band by depth, where both
takers sit trivially at 100% at a depth of two and the question dissolves.

**Neither taker chooses by how long the list is.** The ceiling was raised from ten rows to fifty
partway through `data/logozoa`, and where fifty were recorded the reader's median realised row is
the fourth, against the sixth where ten to nineteen were — lower in absolute terms while the list
grew fivefold. A taker picking without regard to the rows would hold its rank in proportion to
the depth, and neither does. The reader's sample there is 25 positions, so this rules the
artefact out rather than measuring the behaviour.

**Degenerate regions are rare in worked use.** Forty-five of `data/logozoa`'s 2,314 generated runs
of twelve tokens or more end in a repetition, 1.9%, across 67,000 greedy positions; on
`data/continuations` it is 16 of 272, 5.9%, and the difference is that almost all of the worked
tree is drawn cold and short. Loop detection is insurance rather than a common path, and the
pivot is not urgent work. `scripts/cycles.py` states the rule the count means, which no earlier
version of this number did — two repeats of a short block is ordinary English, so a block must
repeat across at least twelve tokens to count.

**The earlier numbers were measured on a tree nobody steered.** `data/continuations`
holds 118 `realise` acts against 23,997 nodes, so almost every divergence counted above is a
sampler leaving the argmax and not a reader doing it. In a document made by this method the
divergences would mostly be interventions, which are priced by construction and should sit at
the sharp end of the gap — a reader realises a row because they disagreed with a model that was
sure. The gate would then admit more of what matters and less of what does not, so these numbers
are the pessimistic case. `data/logozoa` is the steered document the earlier version of this
entry was waiting for, and the entries above are what it said: the gate's room transferred and
its rate did not.

**The top row is realised almost everywhere and the subtree below it is not the reader's.**
`scripts/realisation-by-rank.py` takes the measurement *Deliberately open* asks for before a
hover may roll stubs, over three trees. Realisation by rank is a cliff and not a curve:

| tree | rank 1 | rank 2 | rank 3 | past 8 |
|---|---|---|---|---|
| `data/3` | 94.3% | 1.9% | 1.6% | 1.2% |
| `data/logozoa` | 96.2% | 1.2% | 1.5% | 0.1% |
| `data/continuations` | 80.6% | 5.8% | 5.5% | 1.4% |

And it rises with visits, which is the hypothesis's own mechanism: on `data/3` the top row has a
node at 94.2% of positions where one row was taken, 96.8% where two were, 98.6% at three or four
and 100% above that. So **the greedy child is indeed the first row to acquire a node**, and a
visited tree does hold the model's preference as readable text rather than as a number.

**What it does not hold is greedy as a continuation.** Where two or more rows at one position
were taken, the largest subtree belongs to the top row at 3.8% of positions on `data/3`, 6.6% on
`data/logozoa` and 23.1% on `data/continuations` — so a rule that argmaxes an aggregate over the
subtree converges on the reader and not on the model. That is the half of the question that was
load-bearing, and the answer is no: the top row gets a node and is then abandoned, because the
reason a reader opened the rankings at all was to take something else. **An aggregate over the
subtree is a map of where attention went**, which `Fixed model, adaptive operator` wants and a
reference arm cannot be built from.

**Which also bounds what a hover could spoil.** The number the warning protects is already
between 81% and 96%, so a pointer that rolls from the top row has at most four to nineteen
points to move it by, and the reading that carries the information is about the reader and is
the one a hover feeds rather than floods. The precondition is met and the ordering it imposed is
discharged.

**Liveness no longer separates a stub from a branch the reader set aside, and the exclusion
needs a second signal.** *Deliberately open* has stubs excluded by liveness alone and no
archaeology over act parameters needed, which held while `delete` had one use. It has two:
`data/logozoa` carries 10,949 nodes under a `delete` and `data/demo` carries 4,373 of 4,756,
none of them stubs. A tree that rolls stubs will hold both under one flag, and a measurement
that wants one of them will have to read the act — so what the surface records when it rolls one
is a decision that falls due with the hover and not after it.

## Deliberately open

Each of these is left to be settled by use of the instrument, and each names what would settle it:

- **How far from its origin a single perturbation can still be read, and in what.** *Stubs* has
  re-convergence as a local question — did the divergence last a few tokens — and it is the wrong
  shape for what traces of frozen paths actually show. Divergence in all directions at once is
  rare. What is common is a disturbance whose immediate effect washes out and whose downstream
  effect is a change of *rate* rather than of content: in a loop, a phase shift or a change of
  repetition period; in open-ended text, a change of topic or of format. Those blur the line a
  token-by-token comparison is drawn along, which is why a path can look recovered and not be.
  **Entropy and the gap are the candidates, read as a series rather than per position**, so what
  this asks for is frequency analysis over a path and not a second scalar at one. Observed over
  cooling loops of 10 to 500 tokens across forks, and over open-ended contexts. Whether a
  perturbation can act far from its origin after seemingly doing nothing is unsettled and is the
  thing worth settling. It needs recorded pairs and no new act, so it waits on the surface rather
  than on the format.
- **Whether re-convergence has a workable formal measure.** Settled by comparing candidate measures against reader judgements over recorded chains — no generation required.
- **Stub depth beyond the room it is given.** *Stubs* sets depth from the distance to the next
  stub, which makes the policy a consequence of the gate rather than a number of its own. What is
  open is whether a reader wants that ceiling lifted where a stub was going somewhere — settled by
  where readers actually stop reading stubs, and which ones they extend by hand.
- **Which distribution measure best predicts the divergences that turn out to matter** — entropy, gap, head-mass, or something composite. *Evidence in hand* rules out the obvious answer for selection and leaves the question. Settled by the fork map: aggregate which positions produced lasting divergence, and score each measure as a predictor of them.
- **Whether automated inflation earns its place** — thresholds that spawn stubs unprompted, or
  policies that spend ahead of the reader. *Evidence in hand* now answers the part that was
  arithmetic: if stubs are spawned automatically, the gate is the gap and the density it yields is
  legible. It does not answer whether a reader wants inference spent without asking, which is the
  part that was ever in question. Settled by whether readers, given the manual loop, converge on
  repetitive selection patterns a policy could serve — and the manual loop has to exist first.
- **Which embeddings, if analysis wants them.** Settled by probing candidates against chains that already exist; nothing upstream depends on the choice.