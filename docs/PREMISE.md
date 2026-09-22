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
it.** There is no *flagged spine* independent of this project, so for a term invented here,
predicting the reader and representing the concept are the same act and the distinction is empty.
For a term that existed before — one the wider world also uses — they come apart, and that is
where an answer would have to be looked for.

**The record is objective and the criterion is not.** Every quantity the store holds — a
logprob, a rank, a price paid for a divergence — is a fact about the model. Whether the context
bridged is a call the reader makes. The instrument's whole job sits in that gap: it does not
close it, it puts the two sides where they can be read against each other.

## What would show this wrong

An argument that names nothing that would unseat it is decoration. These are not a programme of
work and carry no order; what gets built is `docs/NEXT.md`, and what has been measured is
`docs/flagged-spine.md` under *Evidence in hand*.

- **Crystallisation should be visible, and cheaply.** If a term acquires operational meaning
  through use, the same term should cost fewer nats late in a context than early — one token,
  measured at two depths, in a tree this instrument already builds. If it costs the same, either
  nothing crystallised or the effect is not where this says it is. **This one needs no machinery
  that does not exist.**
- **A basis that closes the divide should show up as the model being pinned down.** Flag density
  reads how hard a context holds a model to its preferences, so if a basis is doing the work
  claimed for it, flag density against context depth is where it would appear. The result is not
  predicted here — a basis might equally open production up rather than narrow it, and which of
  those happens is the more interesting reading either way.
- **The bridge should generalise, or it is one reader's habit.** A term perturbed, paraphrased,
  or replaced by a synonym should behave differently from an established one, and a second reader
  given only what persisted should be able to reconstruct the distinctions. If nothing survives
  either, the thesis is about accommodation and not about meeting.
- **Compaction should preserve the load-bearing and not the frequent.** The claim is that what
  survives is what was structural. A term that occupied a great deal of the window and did no
  work, surviving; a rule that did all the work, lost — either would say the mechanism is
  something other than what is described here.
