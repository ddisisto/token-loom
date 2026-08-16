# Playbooks

Five ways of using the instrument, each worked through end to end against a real model.
`ROADMAP.md` says what token loom is for — attractors in the prior, how temperature gates
access to them, how framing acts as a change of basis, whether anything survives repeated
retransmission. This is what those look like as commands.

Every transcript below is from **`data/demo/`, which is committed**, so it can be read back
with no model and no GPU:

    python loom.py -d data/demo show
    python loom.py -d data/demo batches
    python loom.py -d data/demo params

It was built by `demo.py`, which is the record of how — one root prompt per playbook, in a
single tree, since the format allows several spans with no parent. Rebuilding needs
`scripts/llama-server.sh` and takes a couple of minutes:

    python demo.py --force

**Reproducible at the conditions level, not bit level.** Seeds derive from a fixed base, so
a rebuild against the same model and llama.cpp build gives the same continuations; nothing
here claims GPU float determinism, and `FORMAT.md` explains why that is the right thing to
claim.

**What the model is.** Qwen2.5-7B **base**, not Instruct — a continuation of the prior, not
a reply. That matters for reading the transcripts: base-model text drifts into whatever
corpus region the prompt resembles, which below includes textbook arithmetic and Chinese
ESL exercises. Those are not failures. They are the prior showing through, which is the
thing being looked at.

**Sample sizes here are tiny** — three to eight continuations. Enough to demonstrate a move,
never enough to support a claim. Where something below looks like a result, read it as a
worked example of how the result would be obtained.

---

## 1. Broad sampling — where does the prior go?

The base move. One position, `n` continuations, nothing separating them but the seed.

    python loom.py -d data/demo author 'The lighthouse keeper wrote in his log:' .
    python loom.py -d data/demo gen --temp 0.9 --length 32 -n 8

What came back:

```
├─ s0+0  0..39  Gs0
│    'The lighthouse keeper wrote in his log:'
│  ├─ s1+0  39..120  Ss1
│  │    ' “At 5:00 a.m. I turned on the light. At 7:00 p.m. I turned it off.…'
│  ├─ s2+0  39..130  Ss2
│  │    ' "At 6:00 am, we saw the light of the lighthouse of island A for th…'
│  ├─ s3+0  39..130  Ss3
│  │    ' "At 4:45, the first ship left the port, and every 60 minutes anoth…'
│  ├─ s4+0  39..116  Ss4
│  │    ' "At 6 am, I lit the lamp. At 11 am, I extinguished it. At 6 pm, I …'
│  ├─ s5+0  39..142  Ss5
│  │    ' "At 6:00 AM, I observed a ship and a buoy 50 kilometers away from …'
│  ├─ s6+0  39..145  Ss6
│  │    ' "At 6:00 PM, I noticed that the angle between the hour and minute …'
│  └─ …
```

**All eight open with a timestamp, and seven of the eight are turning into an arithmetic word
problem.** Not a lighthouse keeper's log — a maths textbook using one as set dressing. `s1`
says so outright by the end of its 32 tokens:

    …“At 5:00 a.m. I turned on the light. At 7:00 p.m. I turned it off.” How many

`s6` gets there fastest, reaching for the angle between the hour and minute hands.

**`s8` is the exception**, and worth reading whole rather than skipping:

    …"On May 1st at 3:30 AM, the light went out, I quickly replaced the fuse,
    and the light returned to normal."

An actual log entry. One continuation in eight escaped the attractor — which is precisely the
number you cannot see by sampling once, and precisely the one worth branching from. That is
the whole argument for sampling broadly before sampling deeply: one continuation reads as a
quirk, eight reads as a property of the prompt, and the outlier is only visible against the
seven. The instrument's job is to make the second as cheap as the first.

The move generalises. Read `show` for the shape, then `batches` for the conditions, then
pick the outlier and go deeper from there.

---

## 2. Temperature — what does it gate access to?

The same position three times, at three temperatures. Three batches, three interned
parameter sets, one comparison.

    python loom.py -d data/demo author 'There are three kinds of silence. The first is' .
    python loom.py -d data/demo gen s9 --temp 0.2 --length 28 -n 3
    python loom.py -d data/demo gen s9 --temp 0.8 --length 28 -n 3
    python loom.py -d data/demo gen s9 --temp 1.3 --length 28 -n 3

**The position is named explicitly here.** `gen` leaves the cursor at the tip of the first
span it made, so a second bare `gen` would continue *from that continuation* rather than
sample the same point again — which is the right default for walking forward (playbook 5)
and the wrong one for sampling in place. `s9` names the tip of the prompt span, so all three
batches hang off one position.

`--stay` is the same move without the repetition: it leaves the cursor at the generation
point, so `cursor s9` once and then `gen --stay` as many times as the sweep needs. Three
calls is short enough to name the position each time; twenty is not, and a sweep that names
it wrong once produces a chain rather than a batch and does not look wrong afterwards.

| temp | what the three continuations did |
| --- | --- |
| 0.2 | *the silence of* the grave / the one who has nothing to say / the fool |
| 0.8 | *when you are alone* / *when you have nothing to say* / the silence of the person who… |
| 1.3 | *the silence of* a person who is listening / a man in possession of all the truth / the dead |

The interesting reading is not "higher temperature is more varied". It is that **0.2 and 1.3
are both locked onto the same syntactic frame** — *the silence of X* — and differ only in
what fills `X`, while 0.8 is the band that got out of the frame entirely and started
sentences a different way.

Whether that survives more than three samples is exactly the question, and this is the shape
of the experiment that would answer it: same position, same length, vary one parameter,
read the batches back.

`batches` is what makes a batch legible afterwards, because it prints the conditions once
and the seeds beside each continuation:

```
b3  3 span(s)  from s9+46  p3
  {'temperature': 1.3, 'top_p': 1, 'top_n': 3, 'length': 28, 'stop': [], …}
  [0] s16   seed 31429     length  ' the silence of a person who is listening. Hi…'
  [1] s17   seed 31430     length  ' the silence of a man who is in possession of…'
  [2] s18   seed 31431     length  ' the silence of the dead. It is a heavy and o…'
```

And `params` is the list of experiments the tree holds, because interning is by value — two
entries are two genuinely different sets of conditions:

```
p1  3 span(s)      p2  3 span(s)      p3  3 span(s)
  length     28      length     28      length     28
  temperature 0.2    temperature 0.8    temperature 1.3
```

---

## 3. Framing — what changes when the model sees less of the same prefix?

`prompt_length` is a **recorded parameter, not a viewport setting**. Two generations from
one position with different slice starts are two different experiments — the same
continuation point, a different amount of the prior visible.

The prompt is a 404-byte note on method, ending `…The first thing worth saying about the
results is`. Generate from its tip twice: once seeing 40 bytes, once seeing all of it.

    python loom.py -d data/demo gen s19 --prompt-length 40  --temp 0.8 --length 28 -n 2
    python loom.py -d data/demo gen s19 --prompt-length 468 --temp 0.8 --length 28 -n 2

| visible | continuation |
| --- | --- |
| 40 bytes | *…that they are all statistically significant. The result for the…* |
| 40 bytes | *…that they do not contradict the notion that the universe is isotropic…* |
| all 404 | *…that they are all of them true. The second thing worth saying is…* |
| all 404 | *…how stable the results are. For all the models, and all the vari…* |

With 40 bytes the model sees only the tail — *the first thing worth saying about the results
is* — and invents a context for it: significance testing, cosmology. With the whole note it
has the actual subject, and continues the note's own argument, one of them even picking up
its *first / second* structure.

**Same position. Same temperature. Different basis.** That is the claim "framing acts as a
change of basis" made directly manipulable rather than argued about.

The record keeps it. Both spans hang off the same parent and differ in where the slice
started:

```
s20  sampled  at s19+404  …  p4  slice from s19+364
s22  sampled  at s19+404  …  p5  slice from s19+0
```

`slice from` is an address, so it survives export of a subtree and can be checked against the
path it claims to lie on — which is validator check 3, and the reason the field is not a
plain offset.

---

## 4. The road not taken — how far does one token propagate?

At every sampled token the model also ranked alternatives it did not take. Branching to one
**needs no generation**: the alternative was recorded when the span was. That is the payoff
that makes storing counterfactuals worth their size.

    python loom.py -d data/demo tokens s25

```
   idx   byte      id  token              logprob   alternatives, by rank
     0     29    1059  ' her'             -1.7088   0 ' a'(-1.67) 1*' her'(-1.71) 2 ' the'(-1.81)
     1     33    6554  ' mother'          -2.0166   0*' mother'(-2.02) 1 ' son'(-2.15) 2 ' husband'(-2.28)
     2     40   20446  ' lying'           -3.8986   0 ' sitting'(-2.13) 1 ' ______'(-2.38) 2 ' standing'(-2.51)
     3     46     389  ' on'              -0.4495   0*' on'(-0.45) 1 ' in'(-2.44) 2 ' dead'(-2.73)
```

`*` marks the alternative actually sampled. **Token 2 has no `*` at all** — at temperature
0.9 the sampled token is absent from its own top-3 about a third of the time, which is why
`tokens` and `counterfactuals` are independent records rather than one list with a marked
entry. The model sampled `' lying'` at −3.90 when `' sitting'` sat at −2.13.

Note what token 2's rank-1 alternative is: `' ______'`. The model is holding a fill-in-the-
blank exercise open as a live possibility, three tokens in. Take it and you would be reading
the prior's other intention for this sentence.

Take rank 0 instead, and continue from it:

    python loom.py -d data/demo branch s25 2 0
    python loom.py -d data/demo gen --temp 0.9 --length 36

The branch is a span anchored at byte 11 of `s25`. **`s25` is not cut, not copied and not
touched** — it still holds all of its bytes, and which of them are on the path depends only
on which child you descend into. That is the whole of why branching mid-span costs what
branching at a tip costs.

Both continuations drift into Chinese-annotated ESL material, which is a real and reportable
property of this base model on this prompt rather than something to hide.

---

## 5. Retransmission — does anything survive being passed forward?

Generate from the tip repeatedly with a **short** `prompt_length`, so each step sees only the
tail of what the step before produced. The text passes through the model again and again with
its beginning falling out of view.

    python loom.py -d data/demo gen --prompt-length 120 --temp 0.9 --length 24    # ×8

Bare `gen` this time, eight times: the cursor following the first new span is exactly what
walking forward wants.

```
0: s29   ' For example, "It\'s cold and rainy outside." Now, make a new sen'
1: s30   ' sentence. \n\nYour sentence should include a descriptive adjectiv'
2: s31   '\'s warm and dry inside," to better describe the current weather '
3: s32   ' vivid and interesting.'
4: s33   ' For instance, instead of saying "It is raining," say "The rain '
5: s34   ' down in torrents.'
6: s35   ''
7: s36   ' The rain is falling heavily.\n3. Use sensory language: Use langu'
```

The opening instruction — *begin with a plain sentence about the weather* — is gone from view
within two steps, and what persists is not the weather but the **instructional register**.
By step 7 it is numbering its own advice. The content washed out; the genre did not. That is
the shape of the retransmission question, and the reason a sliding window is the right
instrument for it: nothing is being remembered except through the text itself.

### The empty span, which is the point

**Step 6 produced no bytes.** It is not an error, a gap, or a dropped record:

    python loom.py -d data/demo tokens s35

```
s35  sampled  at s34+18  548..548  p7  seed 31444  batch b14[0]  slice from s33+4  eos

   idx   byte      id  token              logprob   alternatives, by rank
     0    548  151643  ''                 -1.2769   0*''(-1.28) 1 ' The'(-2.80) 2 ' ('(-2.82)
```

The model sampled **`<|endoftext|>`** — token 151643, at rank 0, at −1.28. The span records
it as a token with an id and a logprob that contributes zero bytes, and terminates as `eos`
rather than `length`.

This is end-of-text treated as what it is: another token in the vocabulary, in the
distribution, with two ordinary words ranked below it. Nothing swallows it and nothing
special-cases it. A span of zero bytes is a legitimate record of a real event — *here the
model chose to stop* — and it sits in the tree beside the seven steps that did not.

---

## What to reach for

| you want to know | the move |
| --- | --- |
| where a prompt tends to go | `gen -n 8`, then `show` |
| whether that tendency is temperature-dependent | three batches, one `--temp` each, then `batches` |
| whether it depends on how much prior is visible | two batches, one `--prompt-length` each |
| what a single token was holding open | `tokens`, look for rows with no `*` |
| where that other token led | `branch <span> <idx> 0`, then `gen` |
| whether anything survives iteration | `gen` from the tip repeatedly, short `--prompt-length` |
| what conditions produced any of it | `params`, and `batches` for one call |
| many samples at one point | `cursor <pos>` once, then `gen --stay` |
| any of it, once the tree is large | `show <pos> --depth n`, `batches --params <key>` |

Everything above is `loom.py`, which is the **reference client** — the floor for what the
Phase 2 API has to do, not a scratch tool that precedes it. If a move is worth making here it
is worth making there.
