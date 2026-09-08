# Surface — the sampling argument

**One argument, held until it is settled.** `docs/SURFACE.md` is what the surface is designed in,
and this is the one thing it does not yet say: whether a first-pass generation should be greedy
rather than sampled, and what a surface shows of a distribution whose mass sits in three of twenty
recorded alternatives. It is taken up next, and this file goes when it is.

**It is a note and reads like one.** Nothing else cites it, and what it decides moves into
`docs/SURFACE.md` rather than being cited from here.

---

## Sampling vs. greedy decoding considerations
On greedy: I think you're right, and for a stronger reason than flat rows
Sampling and branch exploration do the same job, and the tool only needs one. Sampling explores the distribution by rolling dice and discarding what wasn't rolled. This tool explores it by recording everything ranked and letting you take any of it, keeping what you don't. For exploration the second strictly dominates — nothing is lost, and you choose rather than the RNG. Temperature's remaining jobs are cheap varied continuations with no human in the loop, and being a research variable in its own right. Both real. Neither is the floor.

Two things follow that I think are worth more than the original complaint:

The record becomes interpretable. Under greedy, every node is either the model's top choice given this prefix or a human took rank k. Every edge has a reason. Under sampling the reason is a seed. For something whose premise is that the record goes down to the token, that's a large gain.

It makes deepening a ranking free. "Show me more alternatives here" is a generate of length 1 with a larger top_n — rankings extend and are never truncated, so you can deepen wherever you care and the record accumulates. Under greedy the drawn token is the argmax and almost always already exists, so it merges and costs one act. Under sampling it litters the tree with children you didn't ask for. This is also what takes the pressure off top_n: the default no longer has to be right, because it's revisable per position.

Two costs, one of which you should measure before committing
Greedy base-model text degenerates. Repetition and looping are what temperature 0 does, especially a 7B base over a story prompt. data/example reads well and was drawn at 1.0. Your floor case may read materially worse. That's cheap to check — same prompt, greedy and 1.0, read both — and worth checking, because "the floor case is a clean text reader" is load-bearing. Though note the tension cuts both ways: for a tool aimed at attractors in the prior, watching greedy collapse into a loop is the phenomenon, not a defect.

Greedy is not quite canonical, and you'd be assuming it is. ADAPTER.md measures chunk-boundary and cache-state shifts up to 0.057 that reorder ranks. At a near-tie, argmax can flip — so the greedy path is stable except at exactly the high-uncertainty positions you're planning to branch at. I'd call that good for an instrument, since it surfaces an artefact rather than hiding it under sampling noise. But it needs writing down, because "greedy is reproducible" is the natural assumption and it isn't true where it matters most.

The presentation half, and a tension with what I just wrote
My draft says a logprob is shown as a number and never as a length. Your complaint is that twenty flat rows misrepresent a distribution where three hold the mass. Those pull against each other, and the resolution is a distinction I should have drawn:

The magnitude of one alternative is never drawn — that implies recommendation. The shape of the distribution at a position may be drawn — that describes the model's state. Only the first misleads. So: no bars on individual rows, but do show where the recorded mass runs out, labelled as being over the recorded mass since values sum to less than one.

And the larger idea your framing points at: mark uncertain positions in the reading column itself. You said high-uncertainty positions are the basis for branch exploration — if the text shows you where the model was undecided, that's the instrument, and it's far better than twenty rows available everywhere on demand. Top-1 probability or the top-1/top-2 margin is robust even on a truncated tail.

One consequence you should know, since you said the read set was closed: that needs read 1 to carry, per node, something about the distribution it came from — the parent's top-1 logprob, say — not just the node's own. Cheap in the same descent, but it is a change.

