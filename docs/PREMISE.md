# The premise: a context is a shared vocabulary

**An essay, and the only document here that constrains nothing.** It says what makes a context
worth studying and why that makes this instrument the shape it is. Nothing cites it, nothing
should, and it is wrong in the ordinary way an argument can be wrong rather than in the way a
specification can be out of date.

---

## The claim

A context is successful to the extent that two things hold at once: **what comes out of it is
comprehensible to the reader, and the vocabulary it is built in bridges consistently between
them and the model.** A context is an object that two very different kinds of processing have to
meet inside, and how well it serves that meeting is the whole of what this measures.

**Whether the thing built is any good is a second question, and at depth it is downstream of the
first rather than beside it.** Correctness, fitness for a task, whether the code runs — these are
real and they are asked of the artefact, not of the context. The relation between them is not two
independent axes. A shallow exchange can be correct through a bridge that never formed; nobody
needs a shared vocabulary to be told what two and two make. A two-hundred-thousand-token session
cannot be, because there is no route to a coherent artefact that far in except through terms both
ends can operate on. **The bridge is necessary and it is not sufficient**, and it becomes more
necessary the deeper the context runs — which is the axis this is interested in.

Put that way, the interesting property of a context is not a property of its text. It is a
property of a *relation* — between one reader's inner context and the basis the model computes
in. The text is the evidence, and a great deal of the evidence is thrown away by ordinary
inference.

## Why vocabulary is the word, and where it stops being enough

Whatever semantic structure a model has, it is *accessed* through a distribution over its own
vocabulary, conditioned on everything so far. That is a claim about the interface and not about
the model, and the stronger claim — that there is nothing in there to access — is one this
argument neither needs nor can defend. A reader does not hold tokens; they hold whatever they
hold. Between the two sits a context that has to be spellable in the model's units and legible in
the reader's, and the work of building one is the work of finding terms that do both jobs.

**The word is doing double duty on purpose, and the two senses have to stay apart.** A
vocabulary, in the rest of this project, is a specific thing: the token set a tree is created
against, the table a reader derives bytes from, the name that must not cover two models. The
shared vocabulary this essay is about is built *on top of* that one, in the same currency — which
is the whole reason the pun is worth making, since it says the bridge is assembled out of exactly
what the model computes in.

**But what actually accumulates is broader than terms, and the honest word for it is a basis.**
Conventions, structural patterns, where things are kept, what a commit message is expected to
carry, which arguments do not get made twice, what no longer needs saying at all — *every fact
has one home* is not a term, it is a coordination rule, and it does as much work as any name in
here. A basis is the set of things everything else gets expressed in terms of, and **a vocabulary
is the most visible part of one.** The visible part is where this starts looking, because it is
the part that can be pointed at and counted.

That work is ordinary and continuous. A phrase that gets picked up and reused, a name that turns
out to carry more than it was given, a framing that the model starts extending without being
asked again — these are the vocabulary establishing itself. A term the model keeps sliding off,
or one the reader has to re-explain every few thousand tokens, is the divide failing to close.

The bridge is not built once. It is built at every position, out of a choice among alternatives,
and **that is why this instrument records what else was available.** A context that reads
fluently because the model had no other option is a different object from one that reads
fluently because it was steered there, and the text alone cannot tell them apart. Only the
discarded part of the record can.

## These sessions are the selective pressure

This project is built inside exactly the interaction it studies, and not as an analogy. The
sessions that produce it are long single-model contexts, built deliberately, in a vocabulary
that has to work for both ends or the work does not get done. That is the whole test, applied
continuously, with a real cost for failing it.

The mechanics are visible. A working session here runs to something like 124,000 tokens by the
time it is worth writing this down, and the productive ones reach perhaps 300,000 before a
compaction or a fresh start. **Compaction is the vocabulary being tested.** What survives it is
what was load-bearing enough to restate; what does not survive was decoration, however much of
the window it occupied.

And what carries across the boundary is not the summary. It is **the files and the commits.** A
commit message written in this repository's voice is a vocabulary artefact — it is why a term
means the same thing three sessions later, why a claim can be cited rather than re-argued, and
why a decision does not get relitigated every time the window turns over. The documents are the
persistent shared vocabulary; the session is where it gets exercised and where it fails
usefully. The rule that every fact has one home is not tidiness. It is what keeps the bridge
from developing two ends.

## What gets studied, and by whose judgement

Single-model interactions, at increasing context depth, chosen because they are interesting.
That is the selection criterion and it is not a placeholder for a better one.

The range is wide on purpose:

- a **greedy repetitive loop**, whose origin and potentiality are worth knowing — where the
  attractor came from, and what it would have taken to leave
- a **flowing storyline** with invented characters, where the vocabulary is mostly things that
  did not exist a thousand tokens ago
- a **functional artefact** — a project plan, a piece of code — where comprehensibility is
  checkable against something outside the context
- an **agentic coding session**, which is this, and which is the most demanding case because the
  vocabulary has to survive tool results, compaction, and a repository that talks back

For small models and simpler interactions, higher sampling rates. That is where it starts,
because that is where a draw is cheap and a divergence is easy to see.

**Where this points once the browsing has turned up something worth asking properly**: attractors
in the prior and what it takes to leave one, how temperature gates access to them, framing as a
change of basis, and what survives repeated retransmission. The third of those is this essay's
own subject seen from the other side — a framing that takes hold *is* a change of basis, and the
question is what it costs and what it makes reachable. None of them is being designed for, and
they are written here rather than into the format so that they stay findable without becoming
constraints.

**The reader's judgement is the sensor**, and the honest version of that is: there is no external
metric for a successful *context*, and inventing one would be smuggling in a proxy for the thing
actually being measured. The metrics that suggest themselves — the code runs, the plan achieved
its objective, the repository is in the state that was meant — are every one of them tests of an
artefact, and an artefact can come out right through a bridge that never formed or fail to come
out at all because the work was hard. An instrument that scored contexts would be answering a
question nobody has posed well enough to score. This one exists to make a judgement better
informed — to put the model's own numbers next to the text they produced — and not to replace it.

**One external test does bear on the context itself**, and it is worth naming because it is the
exception: whether another reader, given only what persisted, can reconstruct the distinctions
that were meant. That is a test of the basis and not of what was built with it. It is also the
sharpest form of the limit below.

## The cost of saying so

Two things follow that are worth stating rather than discovering.

**The selective pressure runs through one reader.** A vocabulary shaped by what this particular
person found comprehensible is a personal instrument, and its findings inherit that. This is a
real limit and not a confession; a tool that measured everyone's contexts equally well would be
measuring something other than the relation described above.

It has a sharper form. After long enough, a model operating fluently in an established basis may
have got better at the concepts or merely better at predicting *this reader*, and from inside
the collaboration those look identical. **The question only bites for terms with a life outside
it.** There is no *priced spine* independent of this project, so for a term invented here,
predicting the reader and representing the concept are the same act and the distinction is empty.
For a term that existed before — one the wider world also uses — they come apart, and that is
where an answer would have to be looked for.

**The record is objective and the criterion is not.** Every quantity the store holds — a
logprob, a rank, a price paid for a divergence — is a fact about the model. Whether the context
bridged is a call the reader makes. The instrument's whole job sits in that gap: it does not
close it, it puts the two sides where they can be read against each other.

## What the instrument measures, and what it does not

**It measures the reader's position, not the context's quality.** *The claim* refuses an external
score for a context and that refusal stands: whether a context bridged is a call one reader
makes, and an instrument that scored it would be answering a question nobody has posed well
enough to score. What can be measured is something else — whether that reader is still in a
position to make the call.

**The judgement is exercised by letting stand or not, which is why it survives having no
criterion.** A reader does not need to know what a good continuation would be in order to know
they do not want more of this one, or that this one will do. Either is local and needs no target,
which is what makes it available at every position rather than only at the end of something. The
sampler supplies what is judged: a commitment the model's mode would not have made, which the
model then builds on.

**The instrument need not know the goal, and the rejections still carry it.** These are not the
same statement and the difference is the whole of what makes the logs worth reading. A reader
filtering what they do not want more of is not doing something orthogonal to their purpose;
they are doing something *underdetermined* by it, which nothing outside them has to be told in
order for the filtering to work. What they declined is evidence about the purpose all the same,
and `docs/SPINE.md`'s questions about how an operator learns a model are questions about exactly
that residue.

**The path on screen is what the reader let stand, and only the model's side has a number
beside it.** At each position it is what best fitted whatever the reader was after in that moment
— an objective that is theirs, that moves, and that nothing asks them to state. **The model
supplies a field and the operator supplies a point.** A ranking is a number at every token; a
choice is one token, with no distribution behind it to read off. Nothing recovers what the reader
would have assigned to the row they passed over, and an instrument that asked them would be
measuring the answer rather than the choice.

**That is why a displacement is charged whole rather than split.** `docs/SPINE.md` locates the
choice in the model's units, which is the only coordinate the two have in common — so the
quantity says how far past the model's preference the choice went, and never how far toward
anything of the reader's. Read instead as two arms that interfere where they agree, the
instrument would need two fields and there is one. Read as a point located in a field, it needs
exactly what the record already holds. The allocation is the correct one and not merely the
tractable one, which is worth saying because it looks like a simplification.

**So the failure to watch for is not a bad context but a reader with nothing left to decline.** A
context can be driven so far that every continuation is the one that was wanted, and from the
inside that is indistinguishable from having learned the model. Steering until the model's argmax
says what was wanted is the direct route there: the mode of a base model is what every writer the
context admits would agree on, and narrowing that to the reader's own wish closes the loop by
hand. `docs/SPINE.md` carries the
checks against it. None of them scores the work; each asks whether choices are still arriving to
be refused. **They are measurements of a process and not of a context**, which is how they stand
beside the refusal above rather than against it.

**Nothing here is specific to a base model or to continuation.** The unit is an ordered sequence
of tokens, and a chat-templated exchange is one of those — so the states this can hold are a
superset of the states any of those interfaces can be in, reachable in any order rather than
only by appending. Three conditions come with that and are stated elsewhere: a tree holds one
vocabulary, so the superset is within a tokeniser and not across models; the store can represent
a chat context without interpreting its roles or turn boundaries, which `docs/SURFACE.md` still
has open; and it needs the tokeniser and the server, which is why `CLAUDE.md` says nothing here
can reach a hosted model. What the claim buys is narrower than it sounds and is the part that
matters: the approach is not a base-model curiosity, and what it finds is not confined to the
one place it is easiest to see.

## What would show this wrong

An argument that names nothing that would unseat it is decoration. These are not a programme of
work and carry no order; what has been measured is `docs/SPINE.md` under *Evidence in hand*.

- **Crystallisation should be visible, and cheaply — against a control.** If a term acquires
  operational meaning through use, the same term should cost fewer nats late in a context than
  early. But any repeated token gets cheaper, because a model copies what is already in its
  context, so the reading is the difference against a term repeated as often that did no work. If
  the two fall alike, what was seen was copying. **This needs no machinery that does not exist.**
- **A basis that closes the divide should show up as the model being pinned down.** What a path
  costs per unit of text reads how hard a context holds a model to its preferences, so if a basis
  is doing the work claimed for it, that rate against context depth is where it would appear —
  and the rate rather than a count of divergences, which `docs/SPINE.md` measures as a readout of
  the temperature dial instead. The result is not
  predicted here — a basis might equally open production up rather than narrow it, and which of
  those happens is the more interesting reading either way.
- **The bridge should generalise, or it is one reader's habit.** A term perturbed, paraphrased,
  or replaced by a synonym should behave differently from an established one, and a second reader
  given only what persisted should be able to reconstruct the distinctions. If nothing survives
  either, the thesis is about accommodation and not about meeting. **What makes the first half an
  observation rather than an intuition is holding the continuation fixed and varying the
  context**: two contexts from one shared prefix, the same downstream tokens under both, and the
  price read position by position. **The profile is the reading and the sum is not** — unlike a
  deviation, which is never negative, this difference carries a sign at every position, so the few
  positions a perturbation reaches are cancelled by drift at all the ones it does not and a total
  can report nothing where one position carried everything. It is the crystallisation measure run
  the other way round, and unlike that one it wants something the store cannot yet do — nothing
  prices a sequence the model did not draw.
- **The measures should survive leaving the conditions they were found in.** They are developed
  where a divergence is cheap and easy to see — short contexts and a seven-billion parameter base
  model — and the bet is that what they read scales into long and complex ones. The sessions this
  essay opens with are not among what the instrument can observe: no hosted model returns the
  record, so they are the motivation and never the data.
  The counter is specific and worth stating as such: further into a context, and with a more
  capable model, degeneracy is rarer and what divergence remains is subtler and more semantic, so
  a reading built on the distance between a ranking's top two rows may find nothing there at all.
  If the measures go quiet where the work gets hard, they were instruments for the easy case.
- **Compaction should preserve the load-bearing and not the frequent.** A term that occupied a
  great deal of the window and did no work, surviving; a rule that did all the work, lost —
  either would say the mechanism is something other than what is described here. This one is not
  the instrument's to run, and it reads the summarising model's priors as much as the basis.
