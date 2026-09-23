# The autoregressive interferometer

**How the instrument is used.** The loop, what it asks of an instrument, and what it refuses.

**The test it is written against: can a reader run the loop from this alone, and tell what the
method requires from what it merely prefers?** A method fails by arguing for itself — argument is
`docs/PREMISE.md`'s and constrains nothing — and by writing down as a rule what only use can
settle.

Sections are cited by name. What the record is, is `docs/CORE.md`; what a backend must do to
produce it is `docs/ADAPTER.md`; the surface that offers it is `docs/SURFACE.md`. Nothing here
constrains the core, and nothing here is a fact about a backend.

---

## Noise is a prosthesis for absent intent

The decode loop has exactly one place where something other than the model's preference decides
what comes next. In ordinary inference that place holds a random number generator. Temperature,
top-p, min-p and the elaborate ones are shapes of the noise, not alternatives to it.

**The slot exists because nobody is home.** A sampler's whole job is to stand in for a
decision-maker at a position where there is none, which is what makes it defensible in unattended
inference. This method puts a person in the slot, and what the noise then stops being is what
decides.

**A seed does not rescue it.** Reproducible noise is still noise, because nothing in it
corresponds to anything anyone meant. Determinism makes a draw replayable; it does not make it a
decision.

**The elaborate samplers are optimisations of a process this does not run.** Every one of them was
selected against the question *does this read well unattended*, which is the only question
available when no one is watching. That is a real question and this is not it. What they can do
here is shape which proposals come back under drive, which is a use — it is simply not the one
they were tuned for, and nothing about their tuning transfers to it.

**Noise as a decision procedure is the prosthesis. Noise as a stimulus is not.** The claim above
is about who decides, and not about whether a distribution is ever sampled. A draw that stands
because nobody looked at it was decided by a die. The same draw, read afterwards against what it
displaced and then kept or overridden, is a proposal the reader adjudicated — and a reader
deciding late is still the reader deciding. **What the method excludes is the unread deviation,
and not the sampler.**

**It cuts both ways, and the second edge is sharper.** Absent intent on the reader's side is
filled by a sampler. Absent intent on the model's side is where a sampled deviation gets read as a
choice — as voice, as the thing having decided something — when it was a die roll. This is the
first arrangement in which that attribution is checkable: `docs/SPINE.md`'s flag says the dice
moved it, and the price says how far.

## Interference

**Two sources, and a document that is the pattern between them.** The model produces a preference
over continuations at every position; the reader has an intent; what gets written is where the two
meet. Neither is the author and neither is the instrument's subject.

**Coherence is the precondition, not a flourish.** Two wave sources produce a stable pattern only
if they are coherent; otherwise they produce noise that averages to nothing. Here the coherence
condition is that both ends operate in the same vocabulary — the model's tokens are the currency
the reader's intent has to be spelled in, and where a reader cannot say what they mean in terms
the model computes over, there is no pattern to read. This is why the method is worth running on a
context that has been built up and is nearly worthless on one that has not.

**The apparatus is an interferometer and the analogy is mechanical.** A phase shift in one arm is
tiny; the fringes it produces are large and readable, because everything else is held still. One
token changed, and the continuation carries that one change out into a different document — and
the difference is attributable to the change precisely because nothing else moved. Greedy is what
holds the rest still.

**Which arm is the reference is a setting and not a fact.** Greedy holds the model still, so the
model is the reference and the reader's intent is what is being measured. Hold the intent still
instead — the same lead-in and the same interventions, run across models, quantisations or
context depths — and the arms swap: the reader becomes the reference and the machine is the
specimen. `docs/CORE.md` puts `source` in the merge key, so one tree ranked by several models is a
shape the record already admits and nothing has yet produced.

**An arm can also be driven rather than held, and that is the third configuration.** Temperature
is displacement applied on purpose — it pushes the path off the model's preference by an amount
the record then measures, position by position, as `docs/SPINE.md`'s flags and their prices. Drive
it and read what answers, and what answers is not the position but **the context**: how far this
context lets a path be pushed before it goes somewhere the reader will not follow. That is a
reading taken from any point, looking back at everything before it, and it is the one reading here
that cannot be taken at the zero of the dial.

**What it measures is the trajectory and not the distributions.** `docs/SPINE.md` establishes that
a hotter draw does not widen a ranking — the recorded values are pre-temperature — so driving the
dial does not change what is measured at a position. It changes which positions the path arrives
at. The response curve is therefore *where this context lets a path go under drive*, which is a
real quantity and not the one it would be mistaken for.

## The loop

**Write a lead-in. Generate a small batch. Read it. Where it went somewhere you did not want,
change the one token — or change the lead-in. Continue.**

That is the whole of it, and everything below is what each step costs. The one setting it does not
name is how hard the draw was pushed, which is the next three paragraphs and is the only thing
that differs between composing and surveying.

**Greedy is the zero of the dial and the place to start from, not the only place to be.** At zero
the model draws its own preferred token at every position, so the only departure from what it
would have written unaided is one a person made, and a path's accumulated deviation is not a
mixture to be decomposed: it is the price, in the model's own units, of this document being this
one.

**Off zero, the loop runs backwards and is the same loop.** Generate ahead under drive, read what
came back, and return to the flags — each one a position where the sampler went somewhere the
model would not have, marked and priced. At each, the reader does what they would have done
forward: take a different row, write a token, or let the draw stand. This is the mode for
brainstorming against the model rather than composing with it, and the two are settings of one
instrument rather than two methods.

**A flag is a debt, and that is the whole of the discipline.** Driving opens one at every position
where the draw left the model's preference; reading it closes it, whichever way the reader
decides. Greedy simply opens none, which is why it is the place to start and not a rule. **A
passage carrying unread flags carries deviations nobody owns**, and the method's claim on it is
exactly as strong as the reading it has had — which is a thing the reader can know about their own
document rather than a prohibition on how it was made.

**Which is why the balance is a reading decision and not a policy.** Drive is cheap where the
reader means to survey and expensive where they mean to commit, and the same document can be built
both ways in different passages. What is not free is leaving the debt: a stretch generated under
drive and never returned to is a stretch the model and the dice wrote together.

**There are three moves at a position and they are not alike.**

| move | act | what it costs |
| --- | --- | --- |
| take a token the model ranked and did not take | `realise`, then continue | the log-ratio against the token it displaced |
| write a token the model never offered | `create` | nothing the record can price |
| let a drawn token stand, having read it | none of its own | nothing, and *Continuing is the acceptance signal* is why |

**The third only arises off zero**, which is why the zero loop never had to answer it. Under drive
the reader meets flags they agree with, and leaving one alone writes nothing.

**Continuing is the acceptance signal, and the record already holds it.** Asking for the next
batch is a deliberate act taken after reading the last one, so it carries acceptance of everything
above it without a gesture of its own. Under the standard convention there is nothing like this —
*generate until EOS* is one act over the whole output, and an operator who took it has signalled
nothing about any part of it. Small batches are what give the next `generate` something to mean.

**What it accepts is that the reader passed, and not that they read closely.** Skimming and
studying are one signal here and the instrument does not try to tell them apart. A reader can
always scroll back and reconsider; how carefully they went the first time is theirs.

**Of the two that write, only one has a price.** A `realise` is scored against what the model
thought of the choice. A `create` writes a token with no row in the ranking it stands in — which
`docs/SURFACE.md` has as the ordinary case rather than a fault, since a reader writes at a
position a model ranked — so it is off the scale rather than at its end. It follows
that a document's measured deviation covers the part of the reader's intent the model had
anticipated, and the rest is unpriced. That is honest rather than defective, and it is worth
knowing which kind of intervention a passage was built from.

**And one move is not at a position at all: adjusting the lead-in.** Where a continuation is wrong
in a way one token will not fix — and where the model loops from its first drawn token, which
*Degeneration* covers — the fault is upstream of every position being read. Changing what comes
before is the cheapest correction there is, and it is the same act at a different place.

**Rerolling is unavailable at either end of the dial, for two different reasons.** At zero it
cannot happen: the same node, the same parameters and a backend that reproduces its own requests
give the same tokens, every node merges, and only the act is written — `docs/CORE.md`'s worked
example is exactly this at stage 4, so the instrument's answer to *give me another one* is a
recorded act that produced nothing. Under drive it happens and discards nothing: the path the
reader turned away from stays in the tree as a sibling, to be read against its replacement. What
the instrument has no gesture for is the one that matters — *another one, and forget that one* —
and the record is what refuses it.

**Small batches, because reading is the work.** The generation is cheap and the attention is not.
A batch is as much as the reader will actually read before deciding whether anything needs
changing, and it is set by that and by nothing about the model.

**Templates are what the method accumulates.** A lead-in that reliably gets the model to where the
reader wants to start is a reusable artefact, and it is selected for by use rather than designed.
The store already holds them: a lead-in is a root, and starting from one again is a `create` with
the same text. Whether the surface should help with this is in *Deliberately open*.

**It gets cheaper quickly, and the reason matters.** The expensive part is reading, the cost of
reading is proportional to how much the reader cares about what comes out, and a reader who cares
is already paying it — in re-reading rerolls, in discarding whole outputs for one wrong clause.
The method does not add that cost. It moves it to where one token's worth of correction is enough.

## What each end of the dial buys

**At zero, attributability.** Only one thing moved, so the difference between the document and the
model's own continuation is the reader, position by position.

**At zero, the counterfactual arrives first, free, and in the right order.** A sampled loop spends
inference to find out where the model wanted to go — `docs/SPINE.md` calls that a stub. At zero
the rejected continuation was generated *before* the intervention, by the reading pass, and stays
in the tree as the sibling the reader branched away from. Nothing is spent to see it, and it is
there while the decision is being made rather than after.

**At zero the flag is empty, and the moment it fills, it is the reader's.** The token taken is the
top-ranked one at every position, so a path the model produced alone carries no flags at all.
Where `docs/SPINE.md` reads a flag as the sampler having acted in the reader's name, here every
flag is one the reader made. Same overlay, inverted population.

**Under drive, reach — and the counterfactual inverts with it.** The model proposes where the
reader had none, which is the whole of the brainstorming mode, and the flags are the index of
where it did so. What was free at zero now costs: the greedy continuation is the road not taken,
so seeing it means spending a stub. That is precisely the machinery `docs/SPINE.md` specifies, and
this is the mode that needs it — at zero it has nothing to do.

**So the two ends want different overlays.** At zero a flag marks the reader's own interventions,
which they already know about, and what earns its place is a measure read off the rankings —
where the model was torn, where it was not. Under drive the flag is the working index and the
first thing the column should draw.

### Degeneration

**The case for the noise is real and it was measured here.** `docs/SPINE.md`'s *Evidence in hand*
found loops in a quarter of near-greedy paths, several from the first generated token, and none at
all at the highest temperature. Greedy decoding falls into attractors, and temperature walks it
out. That is the field's argument for sampling and it is not wrong.

**The answer is that the sampler does not cure the attractor, it conceals it.** It rolls the model
out of the loop, and the reader never learns there was one. Under this method a loop is the single
most informative thing the model can do: it is the model reporting that it has nothing here, and
it arrives in plain sight at exactly the position where the reader was going to intervene anyway.
The same document already says as much about a stub that cycles — not a failure but a diagnosis.
Running greedy makes the whole path that diagnostic.

**A loop is therefore a place to act, and raising the dial is one of the acts.** A loop from the
first drawn token says the lead-in is wrong. A loop further down says the context has run out of
what it needed, which is a finding about the context. Drive is a legitimate answer to both — the
difference from unattended inference is not that the noise is absent but that **the loop was seen
first**, so what the drive is answering is known, and the flags it opens are read. Concealment is
what happens when greedy was never run. Whether there are contexts on which zero is unusable
throughout is in *Deliberately open*.

## Cost is a rate, not a total

**A total says less the longer the document runs.** Accumulated deviation over a whole path grows
without bound and stops discriminating between passages. Over a window it is a rate, and a rate is
something a reader can hold. This is the decision the recording bounds already made on the other
axis — depth is bounded forward because unbounded depth buys nothing anyone reaches — taken again
for cost.

**An operator runs this accounting whether or not the instrument offers it.** The pattern where a
ten-word prompt and one click return ten thousand words that go out unread is a cost calculation
with its answer already in it: near-zero spend, maximum output. What is unavailable to that
operator is any reading of what the document cost per passage, because nothing measured it. Here
it is measured, and windowing is what makes it legible instead of a total nobody can use.

**Flag density is the window's readable form.** Flags per unit of text, drawn along the column, is
a map the reader builds by scrolling rather than by asking for it. Attention returns to dense
regions when something meaningful is to be changed and passes over sparse ones, where the draw and
the model's preference agreed.

**Sparse is not the same as settled, and the exception is the one that matters.** A repetition
loop is confident at every position, so it flags rarely and reads as the calmest stretch on the
page. `docs/SPINE.md` has this as a property of both measure families rather than a fault in
either — they read confidence, and a loop is confident — and names the only kind of measure that
can mark one: what vocabulary lies below. So the density map is trustworthy about where the drive
did work and silent about where the model stopped doing any, and a reader navigating by it alone
will skim straight over the region they most need to see.

**Uniform high density is the dial gone too far.** A path flagged everywhere is one where the
drive is buying scrambles rather than decisions, and the instrument gets harder to use in exact
proportion: everything is marked, so nothing is. That gives the dial a working range the reader
finds by feel, and no rule has to state it.

**A flag stays a flag.** It is objective — the draw went where the model would not have, at a
recorded price — and nothing a reader does changes that. Making a flag something a reader can
discharge would put the measure under the reader's hand and cost the map its meaning.

**Prominence is what varies, and the record decides it.** The origin of the most recent act on a
path is a watermark: everything above it was continued past, because asking for what is below it
is the acceptance signal. So the flags of the newest stretch draw most prominently and the rest
subdue once, and the boundary is derived from the acts and the ancestry rather than from anything
the surface remembers. **This needs no reader state.** `docs/SURFACE.md` keeps such state in the
session and out of the record deliberately; here the question that looked like it would need some
turns out to be answerable from the store.

## What the method asks of an instrument

**Required — the loop does not run without these.**

- **The ranking at any position, reached with no ceremony.** It is the hot path and not a
  secondary gesture: every intervention of the priced kind starts by asking what else was live
  here.
- **Taking a row as one gesture.** `docs/SURFACE.md` already has the reader meaning one thing
  where the record keeps two acts. That is the most frequent gesture in the instrument, so the
  cost of the second act belongs entirely below the surface.
- **A continuation rule that does not throw the reader back onto what they just rejected.**
  Branching at an early token of a long run and then being returned to that run is the method's
  most common shape, not an edge case. Which member of the family that implies is that document's
  open question; what the method contributes to it is that the rule must follow what the reader
  most recently took.
- **The recording bounds under the reader's hand.** They are the aperture and they decide what can
  be reached at all.
- **A way to find the flags, once the dial is off zero.** They are the debts, and a mode that
  opens them without showing where they are is a mode that cannot be worked. At zero this is not
  needed, which is the only thing that makes it conditional rather than first.
- **Their density legible while scrolling, and the newest stretch told from what was passed.**
  *Cost is a rate, not a total* is why both: the map is built by moving over the text rather than
  by querying it, and the watermark that separates new from seen is read off the acts.

**The parameters, and what each is for here.**

| parameter | what it does under this method |
| --- | --- |
| `record_rows`, `record_mass` | the aperture — how many alternatives a position can offer |
| `temperature` and the samplers under it | the drive — how far the path is pushed off the model's preference, and how many debts come back |
| `length` | how much is read before the next decision |
| `cache_prompt` | `false` near zero; *Determinism stops being a diagnostic* is why, and why it matters less under drive |
| `seed` | nothing to seed at zero; under drive it is what makes a driven path replayable |

**The aperture has to open with the dial, and the two are not independent.** Driving harder lands
the draw further down the ranking, and a record sized for a colder draw censors it: the row the
draw took falls past what was written, so the price of that flag comes back as a bound rather than
a reading. `docs/SPINE.md` measures exactly this — every censored position in `data/continuations`
came from one hot draw recorded to a depth that earlier, equally hot draws had exceeded, so a
draw censors not by being hot but by being recorded for something colder. Turning one dial without
the other buys deviation the record cannot price.

**Preferred, and not required.** The band answers *what lies below this fork*, which is reading
across branches and a different activity from composing along one.

**Refused — and it is one thing, not a list.** A deviation that is never read. Everything the
method refuses reduces to that: a draw left standing because nobody looked, a stretch generated
under drive and never returned to, and any gesture that would let a reader replace a passage
without the displaced one remaining to be read against it.

**And one thing the record refuses on its own account.** A sampler that reshapes what gets
*recorded* rather than only where the path goes is not drive, it is contamination of the
measurement — see *Determinism stops being a diagnostic*.

## Determinism stops being a diagnostic

**Under greedy the argmax is the output, so anything that reorders the top two rows writes a
different document.** `docs/ADAPTER.md`'s *Determinism* records a chunk boundary moving logprobs
by up to 0.057 and a partial cache hit by 0.58 across eighty rows, both reordering ranks. It files
them as diagnostics because the format absorbs them: rows are recorded in the order presented and
nothing is rewritten. That absorption is about the *record*. It does not reach the text, and under
this method the text is what the reader is choosing.

**So the configuration near zero is the cache off**, which is what the command line already sends
for correctness. What it costs is latency on every batch, against a method that wants short
batches and a fast turn — and that is a real tension rather than a settled trade.

**Under drive the same disagreement stops threatening the text and starts threatening replay.** A
driven draw is stochastic by construction, so a perturbation that occasionally moves which token
comes back is not corrupting a correct answer — there was no single answer to corrupt. What it
does break is a named seed's claim to reproduce a path, since the same seed over shifted
probabilities is a different draw. So the dial moves what `cache_prompt` is being traded against:
correctness of the text at one end, reproducibility of a particular exploration at the other.

**Chunk length is carried in the record and needs nothing.** `length` is in every act's `params`,
so where a call started and how far it ran is already readable.

**A sampler that reshapes the recorded distribution is worse than useless here, and may be
forbidden outright.** `docs/ADAPTER.md`'s obligation 5 requires a ranking to be the model's own
distribution and a function of the model and the path alone. Repetition penalty and its relatives
act on logits, and whether they reach the values a backend reports is a question about that
backend. *Status* has what is not known.

## Deliberately open

Each of these is left to use, and each names what would settle it.

- **What a batch length should be.** Fixed, or chosen per passage, or falling as a document
  tightens. Settled by where readers actually stop and intervene.
- **Whether templates want anything from the store.** A lead-in is a root and reusing one is a
  `create`, so nothing is missing; what is untested is whether a reader wants to find the
  lead-ins that produced documents they kept, across trees. Settled by reusing them by hand until
  it is tedious or turns out not to be.
- **Whether the pattern of density says more than the level.** *Cost is a rate, not a total* has
  uniform high density as the dial gone too far. What it does not say is whether density that
  *clusters* — thick where the text turns, thin where it runs — is a different object from the
  same rate spread evenly, and whether the difference is the drive having found something rather
  than merely having been applied. It is the question of where the cost was well spent rather than
  how much of it there was. Settled by reading driven paths whose densities match and whose
  distributions do not.
- **What window.** A rate needs one, and a fixed span of text, a paragraph, a single act and a
  decaying one all read differently over the same path. Settled by which one makes the map usable
  while scrolling.
- **Where on the dial, and chosen by what.** Per passage, per intent, or falling as a document
  tightens — and whether the reader sets it deliberately or reaches for it when a stretch goes
  flat. Settled by which way the hand moves in practice.
- **Whether the response curve is a reading worth taking.** *Interference* has drive as a way of
  asking a question of the context rather than of a position, and nothing has asked one. Settled
  by sweeping the dial over one context and seeing whether flag density and the distribution of
  prices say anything a single draw did not.
- **Whether there are contexts on which zero is unusable throughout.** *Degeneration* argues a
  loop is a finding and a place to act. A context where every lead-in loops, or where
  interventions do not hold, would say zero has a range rather than a universal claim. Settled by
  running it widely enough to find one or fail to.
- **Whether the reference-arm swap is worth running.** Holding the reader's interventions still
  and varying the model is the other experiment the apparatus admits. Settled by a tree several
  models have ranked, which nothing has yet produced.
- **How much of a document a reader can hold while composing it.** The method assumes the reader
  is reading everything; a long document may defeat that, and what happens to intervention quality
  when it does is unknown. Settled by building something long.

---

## Status

**What has no home yet.**

- **Whether a penalty sampler contaminates a recorded ranking on llama.cpp.**
  `src/tokenloom/adapters/llamacpp/README.md` establishes that the recorded values are
  pre-temperature and bit-identical across a sweep of it. Temperature sits at the end of that
  backend's sampler chain and the penalties sit at the front, so what is measured says nothing
  about them. If a penalty reaches the reported probabilities, a request naming one writes
  rankings that are not a function of the model and the path, keyed on a node they are not a
  function of, merging with rows that are — quietly wrong rather than an error, which is the class
  that README exists for. The probe is cheap: sweep the penalty and see whether the recorded
  values move. This is the adapter's to settle and leaves here when it does.
- **How often the top two rows sit within the disagreement.** *Determinism stops being a
  diagnostic* turns a reordering into a different document, and nothing has measured how often the
  gap is small enough for one. It is a count over a tree that already exists.
