# The autoregressive interferometer

**How the instrument is used.** The loop, what it asks of an instrument, and what it refuses.

**The test it is written against: can a reader run the loop from this alone, and tell what the
method requires from what it merely prefers?** A method fails by arguing for itself and by
writing down as a rule what only use can settle.

Sections are cited by name. What the record is, is `docs/CORE.md`; what a backend must do to
produce it is `docs/ADAPTER.md`; the surface that offers it is `docs/SURFACE.md`; what has been
measured is `docs/SPINE.md`'s *Evidence in hand*. Nothing here constrains the core, and nothing
here is a fact about a backend.

---

## The mode is nobody's voice

**A base model's distribution is a mixture over everyone who might have written the text so far,
and its most probable continuation is not a typical one from any of them.** The argmax at a
position is what the writers the context still admits most nearly agree on, so a greedy path is
the common denominator of a crowd: fluent, generic, and prone to looping once it runs out of
things they would all say. *Evidence in hand* has loops in a quarter of near-greedy paths, several
from the first drawn token, and none at the highest temperature.

**A draw off the mode is a commitment, and the model builds on it.** A token the crowd would not
all have chosen narrows who could be writing, and every later position is conditioned on that.
This is what a sampler supplies and the mode cannot: not noise laid over a voice, but the choice of
one. A hot draw under a bound reads as more specific than a greedy one from the same position for
that reason, and stays coherent because the model follows its own cues.

**So greedy is a setting and a reference, not a goal.** It is the right setting where the context
has already narrowed the crowd to one writer — code, a fixed form, a fact — so that the mode and a
typical draw coincide. It is the reference wherever a difference has to be attributed to one
change, which is *Interference*. Elsewhere, steering a context until its argmax says what was
wanted is steering toward the blandest version of it, and `docs/SPINE.md`'s *The failure mode is a
loop the operator built* is where that ends.

**The sampler proposes and the reader decides what stands.** A draw supplies a commitment nobody
had to think of; the reader keeps it, takes another row, writes a token, or draws again. What the
method excludes is not sampling but losing what a choice displaced — *What the method refuses*.

## A bound makes heat usable

**What may be drawn and how evenly it is drawn are two settings.** A truncation bound applied
before temperature is computed on the model's own distribution, and temperature then only flattens
what survived it. So a hot draw is a width and a heat together, and neither says much alone. The
llama.cpp adapter orders its chain this way, `top_k`, `top_p`, `min_p`, then temperature.

**`min_p` holds under heat and `top_p` does not.** Unbounded, temperature 2.0 is salad from the
first token. Under `top_p` alone it lasts tens of tokens: a tail token flattens the next ranking, a
flatter ranking admits more tail, and the path runs away. `min_p` admits only tokens within a fixed
share of the top one however flat the ranking gets, so it has no such loop, and at 0.02 it keeps a
draw at 2.0 prose for as long as it runs. *Evidence in hand* has the measurement.

**The two trade against each other.** At 2.0 under `min_p` 0.02 a path costs about what an
unbounded draw at 1.0 costs per token, with half as many tokens from deep in the tail, and raising
the floor pulls a hot draw back toward the head. **The share `min_p` thresholds on is
`docs/SPINE.md`'s share exactly**, so the floor is also a ceiling on the deviation axis: under
`min_p` 0.02 no draw deviates by more than −ln 0.02, 3.9 nats.

## Interference

**Two arms, and what is read is the difference between them.** The measurement arm is the path as
it went, under whatever draw and with whatever the reader took or wrote. The reference arm is the
model from the same position. What is read is where the two part, at what price, and whether the
parting lasted.

**The reference is a single arm or a spread, and they answer different questions.** A greedy stub
is exact: nothing random entered it, so a difference from it is attributable to the one change.
Several draws from one position are the other kind of reference. They say what the model does from
here when it is allowed to commit, and the path is read against that population rather than
against its mode. Where the draws agree the position was a basin; where they part, it was a fork.

**Which arm is the reference is a setting and not a fact.** Hold the model still and the reader's
interventions are what is measured. Hold the interventions still — the same lead-in and the same
acts, run across models, quantisations or context depths — and the model is the specimen.
`docs/CORE.md` puts `source` in the merge key, so one tree ranked by several models is a shape the
record already admits and nothing has yet produced.

**Heat asks a question of the context.** Drive it and read what comes back: how far this context
lets a path be pushed before it goes somewhere the reader will not follow. The recorded values are
pre-temperature, so heat does not change what is measured at a position. It changes which
positions the path reaches.

## The loop

**Write a lead-in. Draw a short run. Read it. Where it went somewhere you did not want, take
another row, write a token or draw again — or change the lead-in. Continue.**

**The operator reads from the head, as `min_p` does.** They read the top rows, or a spread they
judge representative, and they do not enumerate. What is close enough to the top is admitted, and
something other than rank chooses among it — for the bound, heat; for the reader, what the text is
for.

**Attention is the scarce thing, and learning where to spend it is the skill.** A reader working a
document quickly finds which stretches need looking at and which can be let run, which is the
adaptive half of `docs/SPINE.md`'s *Fixed model, adaptive operator*. It is also why nothing here
wants exhaustive rollout: a position the reader passed over is one they judged not worth the cost.

**The record keeps attention spent, not attention paid.** A row hovered into a stub is a `generate`
and is in the record; a row the eye passed over leaves nothing, there being no verb for a look. So
the positions carrying several stubs are the ones the reader thought worth the question, and that
accumulates as a side effect of working.

**There are four moves at a position.**

| move | act | what it costs |
| --- | --- | --- |
| take a row the model ranked | `realise`, then continue | the log-ratio against the top row |
| write a token | `create` | nothing the record can price |
| draw again from here | `generate` | the new path's own prices; the old path stays beside it |
| let a draw stand | none of its own | nothing |

**Continuing is the acceptance signal, and the record already holds it.** Asking for the next run
is a deliberate act taken after reading the last, so it carries acceptance of everything above it
without a gesture of its own. *Generate until EOS* is one act over the whole output and signals
nothing about any part of it, so short runs are what give the next `generate` something to mean.
**What it accepts is that the reader passed, and not that they read closely.** Skimming and
studying are one signal and the instrument does not try to tell them apart.

**Of the moves that write, `create` alone has no price.** It writes a token with no row in the
ranking it stands in, so it is off the scale rather than at its end, and a document's measured
deviation covers only the part of the reader's intent the model had offered. It is worth knowing
which kind of intervention a passage was built from.

**Drawing again discards nothing.** At zero it produces nothing new: the same node and parameters
give the same tokens, every node merges, and only the act is written — `docs/CORE.md`'s worked
example at stage 4. Under heat it produces a sibling, and the path turned from stays to be read
against its replacement. What has no gesture is *another one, and forget that one*, and the record
is what refuses it.

**Adjusting the lead-in is a move upstream of every position.** Where a continuation is wrong in a
way no single token will fix, what comes before is the cheapest thing to change, and it is the same
act at a different place.

**Short runs, because reading is the work.** A run is as much as the reader will actually read
before deciding whether anything needs changing, and it is set by that and by nothing about the
model.

**Lead-ins are what the method accumulates.** One that reliably gets the model to where the reader
wants to start is selected for by use rather than designed. A lead-in is a root, and starting from
one again is a `create` with the same text.

### Loops

**A loop is what the mode does when the crowd has nothing left to agree on.** Greedy reaches one
easily; a draw under heat and a bound rarely does, because each commitment gives the model
something to build on. A loop from the first drawn token says the lead-in is wrong, and one further
down says the context has run out of what it needed.

**Running cold into a basin on purpose is a probe.** Staying in one well past the point the loop is
established tends to distil something specific — the framing problem, or the piece the context is
missing, as the model's own view of it has that. The place to act on it is usually earlier, where
the context could still have been shaped, so a basin run out with no intention of keeping it is a
way of learning where to steer next time. **This is anecdotal**, from many deliberate pushes rather
than anything counted.

**A loop is not always a fault.** Refrain, anaphora, liturgy and a chorus are repetition doing
work, and the reader is the only thing here qualified to tell one from a collapse. The instrument
reports that a passage repeats and never that it is broken — which is the case against a
repetition penalty that stands even if it left the record untouched: it compiles that judgement
into every position, where the reader never sees it made.

## Cost is a rate, not a total

**A total says less the longer the document runs.** Accumulated deviation grows without bound and
stops discriminating between passages. Over a window it is a rate, and a rate is something a reader
can hold.

**Deviation per unit of text, drawn along the column, is a map built by scrolling.** Attention
returns to expensive regions when something is to be changed and passes over cheap ones, where the
draw and the model's preference mostly agreed.

**Under heat the count stops discriminating and the price does not.** Above 0.9 most positions
diverge, so a mark per divergence marks nearly everything. Counting and summing rank a run's
windows alike near zero and come apart as heat rises — *Evidence in hand* has both — so the summed
price is the one to draw and the count is what it degenerates to when the prices are all alike.
What separates passages under heat is what the divergences cost and whether the model was sure
where they happened, which is the gap `docs/SPINE.md` gates a stub on.

**The map reads the draw and not the text.** Sparse says the draw and the model's preference
agreed, and never that what they agreed on was worth keeping. Neither family of measure locates a
loop, which `docs/SPINE.md` has under *Two families of measure, not one*. That costs nothing
while someone is reading, since a loop is the least camouflaged thing a text can do, and costs
something only where measures are read without the prose.

**A divergence stays a divergence.** The draw went where the model would not have, at a recorded
price, and nothing a reader does changes that. Letting a reader discharge one would put the measure
under the reader's hand and cost the map its meaning.

## What the method asks of an instrument

**Required — the loop does not run without these.**

- **The ranking at any position, reached with no ceremony.** Every priced intervention starts by
  asking what else was live here.
- **Taking a row as one gesture.** `docs/SURFACE.md` has the reader meaning one thing where the
  record keeps two acts, and it is the most frequent gesture in the instrument.
- **A continuation rule that does not throw the reader back onto what they just turned from.**
  Branching early in a long run and being returned to that run is the method's most common shape.
  Which rule follows is `docs/SURFACE.md`'s open question; what the method contributes is that the
  rule must follow what the reader most recently took.
- **The draw's settings under the reader's hand, the bound beside the heat.** They are what the
  reader moves between runs, and heat without its bound is a setting that means nothing.
- **The recording bounds within reach.** They are the aperture and decide what can be reached.
- **Divergences findable, and their cost legible while scrolling.** Under heat they are the index
  of where the path committed.

**The parameters, and what each is for here.**

| parameter | what it does under this method |
| --- | --- |
| `length` | how much is read before the next decision |
| `temperature` | how evenly the admitted set is drawn from |
| `min_p`, `top_p`, `top_k` | how wide the admitted set is; `min_p` is the one that holds under heat |
| `record_rows`, `record_mass` | the aperture — how many alternatives a position can offer |
| `cache_prompt` | *Determinism* |
| `seed` | nothing to seed at zero; under heat, what makes a path replayable |

**The aperture opens with the heat.** A hotter draw lands further down the ranking, and a record
sized for a colder one leaves it with fewer alternatives around it to branch into and to read any
quantity against. Its own value is recorded either way, which is `docs/ADAPTER.md`'s obligation 7.

## What the method refuses

**One thing: a choice whose displaced alternative does not remain to be read against it.** A draw
that is replaced leaves its path in the tree, a row taken leaves the ranking it was taken from, and
no gesture may let a reader overwrite a passage so that what stood there is gone.

**And one the record refuses on its own account: a sampler that reshapes what is *recorded* rather
than only where the path goes.** That is not drive but contamination of the measurement.
`docs/ADAPTER.md`'s obligation 5 requires a ranking to be a function of the model and the path
alone. A repetition penalty acts on logits, and whether it reaches the values a backend reports is
a question about that backend.

## Determinism

**Where a greedy path is the document, anything that reorders the top two rows writes a different
one.** `docs/ADAPTER.md`'s *Determinism* records a chunk boundary moving logprobs by up to 0.057 and
a partial cache hit by 0.58, both reordering ranks. The format absorbs that, since rows are recorded
as presented, but the text does not: under greedy the argmax is the output. So a greedy path meant
to stand is drawn with the cache off, which is what the command line sends.

**A reference arm tolerates it.** A stub is read and not kept, and `docs/SPINE.md`'s *Stubs* has it
as exact cold and advisory warm — the trade that keeps a hover to tens of milliseconds.

**Under heat the disagreement threatens replay and not the text.** A hot draw had no single answer
to corrupt. What a perturbation breaks is a seed's claim to reproduce a path, since the same seed
over shifted probabilities is a different draw.

## Deliberately open

Each of these is left to use, and each names what would settle it.

- **Where greedy is the right setting.** *The mode is nobody's voice* predicts that the more a
  context has narrowed who could be writing, the less greedy loops and the closer it reads to a
  draw. Settled by greedy runs over contexts of differing constraint, read for loops against the
  entropy along them.
- **Whether commitment is what heat buys.** If a hot path stays coherent because each draw narrows
  the writer, a greedy stub cast from deep in a hot path should loop less and read more
  specifically than one cast from the lead-in the path began at. Settled by pairs of stubs over hot
  paths that already exist.
- **Which bound holds best under heat.** `min_p` is measured against `top_p`, and `top_k` at 20 held
  at 1.4 for 150 tokens; `top_n_sigma` and a bound anchored to a floor (`docs/future/FLOORS.md`) are
  untried. Settled by the same comparison at the same positions.
- **Where to set the pair, and chosen by what.** Per passage, per intent, or tightening as a
  document does — and whether the reader sets them deliberately or reaches for them when a stretch
  goes flat. Settled by which way the hand moves in practice.
- **What a run's length should be.** Fixed, chosen per passage, or falling as a document tightens.
  Settled by where readers actually stop and intervene.
- **What window.** A rate needs one, and a fixed span, a paragraph, a single act and a decaying one
  all read differently over the same path. Settled by which one makes the map usable while
  scrolling.
- **Whether the pattern of cost says more than the level.** Cost that clusters — thick where the
  text turns, thin where it runs — may be a different object from the same rate spread evenly, and
  the difference may be the draw having found something rather than merely having been hot.
  Settled by reading hot paths whose rates match and whose distributions do not.
- **Whether a repeat detector earns a place, and where.** A reader sees a loop unaided, so its value
  is wherever the text is not being read: an aggregate, a scan across trees. What it must not do is
  call a refrain a fault. Settled by whether anything here is ever read without prose.
- **Whether lead-ins want anything from the store.** Reusing one is a `create`, so nothing is
  missing; what is untested is whether a reader wants to find the lead-ins behind documents they
  kept, across trees. Settled by reusing them by hand until it is tedious or turns out not to be.
- **Whether the response curve is a reading worth taking.** Sweeping heat and bound over one context
  asks the question *Interference* puts to heat directly, and nothing has asked it. Settled by
  whether the divergences and their prices across the sweep say anything a single draw did not.
- **Whether the reference-arm swap is worth running.** Settled by a tree several models have
  ranked, which nothing has yet produced.
- **How much of a document a reader can hold while composing it.** The method assumes the reader
  reads everything, and a long document may defeat that. Settled by building something long.
