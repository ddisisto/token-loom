#!/usr/bin/env python
"""What a `record_mass` and `record_rows` pair costs, in rows kept per position.

**Needs a running server.** It generates greedily over a spread of prompts, asks for a wide
ranking at every position, and then applies the bounds locally -- so one run answers for
every pair in the table rather than one.

What it is for is choosing those two defaults, and re-choosing them for a model that is not
the one they were chosen against. The shape they turn on is not a property of the format: a
distribution is sharp where the model is sure and flat where it is not, the flat positions
are the ones worth branching at, and how the two mix is a property of the model and of what
it is reading.

`record_rows` alone is the flat cost of recording -- every position pays it. A mass bound is
what makes a wide ceiling affordable, so the column to read is the last one.

    uv run scripts/mass.py
    uv run scripts/mass.py --length 64 --ceiling 400
"""

from __future__ import annotations

import argparse
import math
import os
import sys

from tokenloom.adapters.llamacpp.adapter import LlamaCppAdapter, reaches
from tokenloom.adapters.llamacpp.client import LlamaCppClient
from tokenloom.adapters.llamacpp.vocab import GgufVocabulary
from tokenloom.core import Ranked, Source

#: Deliberately unalike. Arithmetic and code are near-deterministic continuations and
#: literary prose is not, and a default chosen against either alone is chosen against the
#: wrong thing.
PROMPTS = (
    "The capital of France is",
    "The sky above the port was the color of television, tuned to a dead channel.",
    "def fibonacci(n):\n    if n <= 1:\n        return n\n    return",
    "Q: What is 17 times 23?\nA:",
    "Once upon a time, in a village at the edge of the",
)
MASSES = (1.0, 0.95, 0.9, 0.8, 0.7)
CEILINGS = (20, 40, 80)


def connect(server: str) -> LlamaCppAdapter:
    client = LlamaCppClient(server, timeout=600)
    props = client.props()
    if not os.path.exists(props.model_path):
        sys.exit(f"the server's model file is not reachable: {props.model_path}")
    vocabulary = GgufVocabulary.cached(props.model_path, props.model_alias)
    name = os.path.basename(props.model_path).removesuffix(".gguf")
    return LlamaCppAdapter(Source("model", name), vocabulary, client)


def rankings(adapter: LlamaCppAdapter, length: int, ceiling: int) -> list[tuple[Ranked, ...]]:
    """One greedy run per prompt, keeping every position that came back ranked."""
    out = []
    for prompt in PROMPTS:
        ids = [t.id for t in adapter.tokenize(prompt.encode())]
        answer = adapter.generate(
            ids,
            {
                "length": length,
                "record_rows": ceiling,
                "record_mass": 1.0,  # never reached, so: every row the ceiling allows
                "top_k": 1,
                "temperature": 0.0,
                "cache_prompt": False,
            },
        )
        if answer.terminator == "refused":
            sys.exit(f"refused: {answer.reason}")
        out += [p.ranking for p in answer.positions if p.ranking is not None]
    return out


def main() -> int:
    ap = argparse.ArgumentParser(prog="mass.py", description=__doc__)
    ap.add_argument("--server", default=os.environ.get("TOKENLOOM_SERVER",
                                                       "http://localhost:8081"))
    ap.add_argument("--length", type=int, default=32, help="tokens drawn per prompt")
    ap.add_argument("--ceiling", type=int, default=400,
                    help="rows asked of the server; every bound below is applied to these")
    args = ap.parse_args()

    adapter = connect(args.server)
    found = rankings(adapter, args.length, args.ceiling)
    print(f"{adapter.source.name}: {len(found)} ranked positions over {len(PROMPTS)} prompts, "
          f"{args.ceiling} rows each\n")

    total = [sum(math.exp(r.logprob) for r in ranking) for ranking in found]
    total.sort()
    print(f"  mass those {args.ceiling} rows hold: min {total[0]:.4f}  "
          f"p50 {total[len(total) // 2]:.4f}  max {total[-1]:.4f}")
    print("  the rest is the vocabulary they do not report, and never truncation.\n")

    flat = float(min(CEILINGS))
    print(f"  {'record_mass':>11}  {'record_rows':>11}  {'mean':>6}  {'p50':>4} {'p90':>4}  "
          f"{'at ceiling':>10}  {f'vs flat {int(flat)}':>11}")
    for mass in MASSES:
        for ceiling in CEILINGS:
            # The bounds the adapter applies: the mass, two rows, and the token drawn --
            # which under greedy is rank 0 and so never the one that binds.
            kept = [min(ceiling, max(2, reaches(r, mass))) for r in found]
            kept.sort()
            mean = sum(kept) / len(kept)
            print(f"  {mass:>11}  {ceiling:>11}  {mean:>6.1f}  "
                  f"{kept[len(kept) // 2]:>4} {kept[int(len(kept) * 0.9)]:>4}  "
                  f"{sum(1 for k in kept if k == ceiling) / len(kept):>9.0%}  "
                  f"{mean / flat:>10.2f}x")
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
