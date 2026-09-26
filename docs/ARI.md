# Auto-Regressive Interferometer

Sep 24, 2026 · @Daniel DiSisto

*An instrument for reading, growing, and navigating autoregressive state. Working name: token-loom.*

## Premise

An autoregressive model does not write text. At each step it takes a context and returns a distribution over the next token. What we call generation is a sampling policy wrapped around that step and run in a loop until something says stop.

That wrapping is convenient, and it hides the most interesting part of the machine. The Auto-Regressive Interferometer removes it. The unit of interaction is not the completion but the **state transition**: one step, or a chunk of steps, from one context to the next.

The model proposes transitions. The operator reads them, decides which become part of the shared state, and can write state directly. The instrument records every transition, keeps every alternative, and exposes the distributions behind them.

```latex
S_t \rightarrow P_\theta(\cdot \mid S_t) \rightarrow H \rightarrow S_{t+1} \rightarrow P_\theta(\cdot \mid S_{t+1}) \rightarrow \cdots
```

The model shapes what is available. The operator shapes the state that availability is computed from. Neither controls the other directly; they are coupled through the context.

The practical consequence is a different question. Prompting asks: what text should I start with? The interferometer asks: **what state should we build, step by step, so that the model's own tendencies carry the trajectory where I want it to go, without the trajectory closing in on itself?** The second half of that question is where most of this document lives.

## Lineage

This project began as token-loom, a planned fork of Loom, janus's branching interface for base models. The ideas it inherits from that line of work are real and acknowledged: continuations as a tree rather than a string, a human curating which branch becomes context, and the base model understood as a proposer of possible futures rather than an author.

It became a standalone build once it was clear the direction would diverge far enough that nothing would go back upstream. The divergence is in emphasis. Loom is primarily a writing and exploration environment. The interferometer is primarily a measurement instrument that is also usable for writing. That shows up in four places:

- **A token-exact store.** Everything is held as tokens with their distributions, not as text to be re-tokenised later.
- **A deterministic reference arm.** Temperature-zero runs are a first-class probe, not just one more sample.
- **Attractors as objects of study.** Loops are detected, located and used, not only avoided.
- **The operator as a variable.** The interaction log is designed to answer questions about how a person learns a fixed model.

## The store

The instrument's state is a **tree of tokens**. A path from the root to any node is a context. The committed path is the one the operator is currently working from; every other branch stays in the tree, inspectable and returnable to.

Nodes enter the tree through two kinds of event:

- **Create.** The operator writes directly. The text is tokenised once, at the moment it is admitted, and stored as tokens. Created spans carry no distribution, because the model did not propose them.
- **Generate.** The model proposes. Each generated token is stored with its logprob and its ranked alternatives, and the event records the sampling conditions it was produced under.

Two rules follow from this. First, **a tree has exactly one vocabulary**. The vocab is built on demand around what the tree actually uses, and mixing tokenisers within a tree is not permitted. Second, the store never re-tokenises committed text. The model always conditions on exactly the token sequence that was produced or admitted, so the logprobs recorded along a path are measurements of that path and not of some re-encoded approximation of it.

The interface respects the same boundary. Generated spans offer a range of selectable overlays: probability, entropy, rank, alternatives. Authored spans offer none. If the operator is working at the level of tokens, translating between tokens and meaning is their job. If they are authoring, the tokeniser does it, once, and the model takes it from there.

## Two arms

An interferometer works by splitting a signal, sending one part down a reference arm and the other down a measurement arm, and reading what differs when they recombine. The instrument has the same structure.

The **reference arm** runs at temperature zero. From any node, it follows the argmax token at each step. Given a fixed state, fixed weights and fixed inference settings, it is reproducible: run it twice and you get the same path. The instrument can cast greedy stubs from any node, at regular intervals along the committed path or wherever the operator asks, without committing them.

The **measurement arm** is everything else: sampled scouts at chosen temperatures, created spans, and the committed path itself.

Because the reference is exact, a difference between the committed path and the greedy stub cast from the same node is attributable to the intervention and nothing else. Sampling noise does not enter the reference. That is the sense in which the name is earned. What the instrument measures is not the text but the displacement between where the model goes by itself and where the trajectory actually went.

The exactness has stated limits. Prompt caching is on. Seeds are random by default and can be pinned. Hardware and batch-level nondeterminism are not controlled for, and small divergences from that source are accepted as functional uncertainty. The reference arm is reproducible in practice on a given machine, not guaranteed across machines.

## Loops are signal

Left to run, the reference arm usually cycles. This is well known as a failure of greedy decoding, and as a way of producing text it often is one. As a probe, it is one of the most useful things the instrument has.

A cycle is an **attractor** made visible: a region of state the model returns to when nothing pushes it elsewhere. Run the reference arm through several cycles and the entropy trace becomes periodic. The point where the loop re-enters itself stands out in that trace. Call it the **pivot**.

At the pivot, the model is choosing between continuing the loop and leaving it. The ranked alternatives at that position are the most likely exits. The instrument surfaces them. The operator can take one, write something else, or leave the loop intact.

That last option matters. A loop is not always a problem. Sometimes it is exactly the structure the work needs at that point: a refrain, a consolidation, a return. The reference arm does not decide whether a loop is good. It shows where the loop is and where the doors out of it are.

A useful picture is a read head moving forward along the tape. The greedy head settles into a groove. The pivot is where the groove is shallowest. The operator decides whether to lift the needle.

## Navigation

The distinction that organises the practice is between a **closed loop** and an **open trajectory**. A closed loop returns to itself. An open trajectory keeps moving: it has direction, it keeps real choices available at each step, and it does not fall back into a cycle when the reference arm is cast from it.

Navigation is the work of keeping a trajectory open while steering it. The moves are few:

| Move | What it does |
| --- | --- |
| Create | Writes state directly, with no reference to the current distribution |
| Generate | Asks the model for a chunk at a chosen length and temperature |
| Accept / reject | Commits a proposed chunk, or leaves it as a side branch |
| Branch / return | Works from any earlier node without losing the current one |
| Heat | Raises temperature to scout: widens what the model will show |
| Cool | Lowers temperature to consolidate: holds close to local preference |
| Probe | Casts a greedy stub to see where the model goes unassisted |

A typical sequence: the reference arm reveals a loop. The operator takes an exit at the pivot, or creates one. They cool the trajectory and push it through a narrow **passage**, a stretch where the direction is fragile and a single bad step would drop it back into the old attractor or a new one. Once through, they heat to see what has opened up. They probe again. They repeat.

Temperature in this picture is not a quality setting. It is the width of the aperture, and it is changed deliberately, at particular points, for particular reasons.

These moves do not need to land in a fixed order, and they do not need a goal fixed in advance. The operator only needs to recognise a useful transition when it appears.

## The failure mode: building a new loop

The obvious success criterion is convergence: the context increasingly produces what the operator wants. That criterion is gameable, and the operator is the one who games it.

A context can be made so over-determined that the model has no real choice left. Entropy along the path collapses. Every proposal matches the operator's intent, because the operator has effectively written the intent into every position. By the convergence measure, this looks like mastery. In fact it is a closed loop the operator built by hand: an attractor with the operator inside it, and the model reduced to an echo.

So the criterion has to be two-sided. **A trajectory is going well when it moves in the intended direction and stays open.** Concretely, that means:

- Branching entropy along the committed path stays above a floor, rather than trending to zero.
- Greedy stubs cast from recent nodes do not immediately cycle.
- Accepted tokens are not always rank one; the model is still offering choices the operator takes.
- The model still surprises the operator, and some of those surprises get committed.

All four are measurable from what the store already records. None of them is a target in itself; each is a check against the others. The hypothesis the instrument exists to test is that skilled operation shows up as this combination, direction with openness, and that it can be distinguished from sophisticated puppeteering in the logs.

## Reading as generation

With a local model and a warm cache, proposing the next chunk is cheap enough that reading and generating can merge. The operator reaches the end of the committed path, a chunk is proposed, they read it, and the text grows as it is read. There is no job to wait for.

Chunk length sets how much is delegated per transition. Eight tokens is close supervision. Two hundred is a long leash. Running to a stop condition is full delegation for that stretch. The process is the same at every length; only the grain changes, and the operator can change it mid-path.

The real budget is not compute but the operator's attention. Every proposal read is time spent. That time is tracked, currently as the operator's own work effort, split across building, thinking, and operating. Time from proposal to decision is also cheap to log per event, and will be, because attention is the quantity the adaptation questions below are really about.

## Probability as diagnostic

Probability does not say whether a continuation is right. It says what the model finds natural from here, and that is a question worth asking on its own terms.

Surprise comes in two kinds, and they mean different things. A low-probability continuation that surprises the operator is a finding about what exploration can reach: a door that was there but rarely opened. A high-probability continuation that surprises the operator is a finding about the state itself: the model is confident about something the operator did not expect, which usually means the context says more, or something different, than the operator thought it did.

The second kind is the more valuable, and the one most worth stopping for before committing. The overlays on generated spans exist largely to make it visible at a glance.

## Fixed model, adaptive operator

The weights do not change during a session. The operator does. Over time they learn the model: its attractors, where its pivots tend to fall, where a one-token intervention moves everything and where a paragraph moves nothing, and when its confidence is worth doubting. The system is a fixed generative landscape and an adaptive navigator of it.

This is not continual learning in the parameter sense. It is continual adaptation on the human side, and because every transition is logged, it is measurable. The questions the instrument is built to ask:

1. Does intervention frequency fall with experience, and do interventions get smaller?
2. Do interventions concentrate at pivots, or at other identifiable points in the entropy trace?
3. Does the rank distribution of accepted tokens shift as the operator learns the model?
4. Does time from proposal to decision fall, and where does it stay high?
5. Do experienced trajectories stay open longer, by the criteria above, while still reaching their direction?
6. Does guided navigation reach regions of state that sampling alone rarely visits?

One further comparison comes almost for free. Post-trained models still perform the base function, and the store does not care which model it is attached to. Running a base model and a post-trained sibling from identical contexts should show what post-training does to the landscape itself: the expectation is flatter entropy, fewer real branches, and deeper attractors, but that is a prediction to check, not a claim.

Scope, stated plainly: at present the operator is also the builder. That is the right condition for exploratory, first-person work, and it is how the questions above were found. It is not sufficient for claims about operators in general. Those will need people who did not build the instrument.

## Status

**Working now:** a local base model under llama.cpp; the token tree store with create and generate events; per-token logprobs and alternatives on generated spans; on-demand single vocab per tree; selectable overlays on generated text; prompt caching and settable seeds. Sessions are being run and data is accumulating.

**In planning:** per-path vocabulary analysis, loop and pivot detection over the entropy trace, divergence measures between committed paths and reference stubs, and per-event decision timing.

**Next:** use the instrument in earnest, then turn the questions above from a list into analyses of the logs. A short demonstration, one attractor found, one escape taken and one trajectory kept open, would communicate the idea better than this document does.

The model stays fixed. The context grows. The operator learns. The instrument's job is to make all three observable at once.
