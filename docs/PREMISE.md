# The premise: a context is a shared vocabulary

**An essay, and the only document here that constrains nothing.** It says what makes a context
worth studying and why that makes this instrument the shape it is. Nothing cites it, nothing
should, and it is wrong in the ordinary way an argument can be wrong rather than in the way a
specification can be out of date.

---

## The claim

A context is successful to the extent that two things hold at once: **what comes out of it is
comprehensible to the reader, and the vocabulary it is built in bridges consistently between
them and the model.** That is the whole criterion. Not correctness, not quality against any
external rubric, not preference scores. A context is an object that two very different kinds of
processing have to meet inside, and how well it serves that meeting is the only thing about it
that matters.

Put that way, the interesting property of a context is not a property of its text. It is a
property of a *relation* — between one reader's inner context and the basis the model computes
in. The text is the evidence, and a great deal of the evidence is thrown away by ordinary
inference.

## Why vocabulary is the right word for it

A model does not hold meanings; it holds a distribution over its own vocabulary, conditioned on
everything so far. A reader does not hold tokens; they hold whatever they hold. Between the two
sits a context that has to be spellable in the model's units and legible in the reader's, and
the work of building one is the work of finding terms that do both jobs.

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
metric for a successful context, and inventing one would be smuggling in a proxy for the thing
actually being measured. An instrument that scored contexts would be answering a question nobody
has posed well enough to score. This one exists to make a judgement better informed — to put the
model's own numbers next to the text they produced — and not to replace it.

## The cost of saying so

Two things follow that are worth stating rather than discovering.

**The selective pressure runs through one reader.** A vocabulary shaped by what this particular
person found comprehensible is a personal instrument, and its findings inherit that. This is a
real limit and not a confession; a tool that measured everyone's contexts equally well would be
measuring something other than the relation described above.

**The record is objective and the criterion is not.** Every quantity the store holds — a
logprob, a rank, a price paid for a divergence — is a fact about the model. Whether the context
bridged is a call the reader makes. The instrument's whole job sits in that gap: it does not
close it, it puts the two sides where they can be read against each other.
