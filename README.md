# token loom

**Write with a base model a token at a time, and see what else it ranked at every position.**

![The draw, the marked path, and the rows at the caret](docs/images/banner.png)

You give a base model some text and it continues. Every token it draws is stored with the
alternatives it ranked there and their probabilities, in a tree that branches wherever you or the
model went more than one way. The page sets one path through that tree as prose. Point at any
token to see what else was live there, take one of those alternatives instead, or continue from
where you are.

## How this differs from what it is like

- **[socketteer/loom](https://github.com/socketteer/loom)** and its descendants branch on
  generations: you draw several continuations and choose among them. This is inspired by it and
  branches on tokens. A branch can start at any token the model ranked, including ones it did
  not sample.
- **A logprob viewer** shows the alternatives along one completion. Here they are kept, and
  every one of them is a place to branch from.
- **The record is token-exact.** Paths are stored as the token ids the model saw and emitted,
  never as text to be tokenised again. Tokenising two pieces of text separately and joining them
  does not generally give the tokens of the joined text, so a store of text would hand the model
  sequences it never produced.
- **Every draw records how it was made**: the model, the temperature and the bounds. How a tree
  was built is in the tree.

## Try it without a model

Reading a tree needs nothing but the repository. `data/demo` ships with it.

```sh
uv sync
uv run tokenloom serve data/demo --port 8097     # then open http://localhost:8097/
```

## Grow your own

**Needs:** Python 3.13 and [uv](https://docs.astral.sh/uv/); a
[llama.cpp](https://github.com/ggml-org/llama.cpp) build with `llama-server` on the path; the
Hugging Face CLI (`hf`) to fetch the model; and about 5.2GB of VRAM for the default model at 16k
context.

It is local only. The record needs per-token ids and logprobs on a raw continuation, which no
hosted provider returns. The default model is Qwen2.5-7B **base**
([`mradermacher/Qwen2.5-7B-i1-GGUF`](https://huggingface.co/mradermacher/Qwen2.5-7B-i1-GGUF),
i1-Q4_K_M). An instruct model works, but continuing raw text is what this is built around.

```sh
scripts/llama-server.sh                          # fetches the model once, serves it on 8081

uv run tokenloom init data/mine --vocab qwen2.5-7b-base
uv run tokenloom create data/mine 'It is a truth universally acknowledged, that'
uv run tokenloom serve data/mine --port 8097
```

`create` prints the node ids it made. From there, the page is the way in: it continues a path,
branches at a ranked alternative, and sets the draw's temperature, length and bounds. Every
change the page makes, the command line can make too:

| command | what it does |
|---|---|
| `generate TREE --at NODE` | draw from the model; `--length`, `--temperature`, `--min-p`, `--top-p`, `--top-k` |
| `realise TREE --at NODE --token ID` | take a ranked alternative; no model is called |
| `create TREE TEXT --at NODE` | add your own text, as a new root or after a node |
| `delete TREE NODE` | set a branch aside; `--undo` brings it back |
| `path TREE NODE`, `tree TREE`, `acts TREE` | read a path, the shape, or the history |
| `stamp TREE` | record what the tree hashes to, for quoting it |

`uv run tokenloom --help` and `--help` on each command give the rest. Only `generate` calls the
model, and `create` uses the server for its tokeniser; everything else, reads included, runs
without one. `uv run pytest` needs no server either; `-m live` runs only the tests that do.

## What it is for

Two things, honestly stated:

- **Writing with a base model.** A base model has no assistant voice. It continues whatever it
  is given, and steering it a token at a time is a different activity from prompting it.
- **Seeing what a sampler does.** Temperature, min_p and top_p can be watched acting on real
  rankings. At temperature 2.0 under a min_p floor, for instance, a draw stays prose; take the
  floor away and it turns to word salad. [`docs/SPINE.md`](docs/SPINE.md) has the
  figures.

Past that, it is built to explore with, for its own sake.

## Two names

The idea is the **Autoregressive Interferometer**: read a path against what the model does left
alone from the same position, the way an interferometer reads one arm of a split signal against a
reference arm. **token loom** is the implementation, `tokenloom` is its package, and the two names
are not interchangeable.

## The documents

These are working notes, written while the thing is built. Each one is written to a different
test.

- **[`docs/PREMISE.md`](docs/PREMISE.md)**: why any of this is worth building. An essay, and
  nothing depends on it.
- **[`docs/CORE.md`](docs/CORE.md)**: what the format is. Nodes, edges, sources, rankings, acts,
  the on-disk shape and its invariants, written so that someone could implement a reader from it
  alone.
- **[`docs/ADAPTER.md`](docs/ADAPTER.md)**: what a model backend must do to produce that record.
- **[`docs/INTERFERENCE.md`](docs/INTERFERENCE.md)**: the method: a person reading what a
  sampler proposes and deciding what stands. A base model's most probable path is nobody's voice,
  so greedy decoding is a reference and a setting rather than a goal, and high temperature is
  usable under a bound that holds.
- **[`docs/SPINE.md`](docs/SPINE.md)**: the measures drawn along a path, and the evidence for
  them so far.
- **[`docs/SURFACE.md`](docs/SURFACE.md)**: the reading page's design. Drafted, and each open
  question says what would settle it.
- **[`docs/LAYERS.md`](docs/LAYERS.md)**: what the page draws over the text: the measures, the
  scales they are read on, and the mark saying who put each token there.
- **[`docs/NEXT.md`](docs/NEXT.md)**: what gets built next and in what order. Items are deleted
  once they close.

`CLAUDE.md` holds the rules for changing the code and the documents.

## Where it is

**Working:** the store and every write to it from the command line; a reading page that sets a
path as prose, shows what was ranked at any token, continues or branches from there, draws a
measure along the path, and puts the draw's length, heat and sampler settings beside the text. It
is used daily, by one person.

**Next:** several draws at a position shown side by side, so you can see where they agree. `docs/NEXT.md` has the order, and
`docs/ADAPTER.md`'s Status has what the backend leaves open.

**By design:** one tree, one writer, one person reading, one local model. The documents say why.
