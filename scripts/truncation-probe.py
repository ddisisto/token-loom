"""Whether a hot draw stays prose because of its temperature or because of its bound.

`docs/SPINE.md`'s *Evidence in hand* has the figures this produced. Each site is a position whose
path was drawn at temperature 2.0 and read as prose; each condition draws from it again, at 2.0
under each bound alone and under none, at 1.0 under none, and greedily.

    uv run python scripts/truncation-probe.py draw data/probe results.json
    uv run python scripts/truncation-probe.py report data/probe results.json

`draw` writes acts, so it is pointed at a copy and never at a tree that matters. The sites are
node ids in `data/daniel` as it stood on 2026-10-04, so a copy of anything else wants its own.
It is resumable: what is in the results file is not drawn again. A request the server fails is
recorded with its error, since a failure is one of the readings.
"""

from __future__ import annotations

import argparse
import json
import re
import secrets
import sqlite3
import statistics as st
import sys
from collections import defaultdict
from pathlib import Path
from types import SimpleNamespace

from tokenloom.adapters.llamacpp.adapter import MAX_SEED
from tokenloom.cli import DEFAULT_SERVER, adapter_for
from tokenloom.core import Source, Store
from tokenloom.core import reads as R

# name: (origin, length, the chain the original was drawn under)
SITES = {
    "S1-readme": (102560, 200, {"top_k": 20, "temperature": 2}),
    "S2-sampler-eos": (59461, 200, {"top_p": 0.95, "min_p": 0.02, "temperature": 2}),
    "S3-temp-essay": (75930, 48, {"top_p": 0.95, "min_p": 0.02, "temperature": 2}),
    "S4-dialogue": (75309, 48, {"top_p": 0.95, "min_p": 0.02, "temperature": 2}),
    "S3L-temp-essay-200": (75930, 200, {"top_p": 0.95, "min_p": 0.02, "temperature": 2}),
}

# Five draws a stochastic condition and one greedy, which is deterministic.
DRAWS = 5


def conditions(original):
    return [
        ("A-original", original),
        ("B-T2-none", {"temperature": 2}),
        ("C-T2-top_p.95", {"temperature": 2, "top_p": 0.95}),
        ("D0-T2-min_p.02", {"temperature": 2, "min_p": 0.02}),
        ("D1-T2-min_p.05", {"temperature": 2, "min_p": 0.05}),
        ("D2-T2-min_p.10", {"temperature": 2, "min_p": 0.1}),
        ("E-T1-none", {"temperature": 1.0}),
        ("F-greedy", {"temperature": 0}),
    ]


def draw(tree: Path, out: Path) -> None:
    results = json.loads(out.read_text()) if out.exists() else {}
    adapter = adapter_for(SimpleNamespace(server=DEFAULT_SERVER, gguf=None, model=None))
    for site, (origin, length, original) in SITES.items():
        for cond, chain in conditions(original):
            for d in range(DRAWS if chain["temperature"] > 0 else 1):
                key = f"{site}|{cond}|{d}"
                if key in results:
                    continue
                params = {"length": length, "record_rows": 20, "record_mass": 0.95,
                          "cache_prompt": True, **chain}
                if chain["temperature"] > 0:
                    params["seed"] = secrets.randbelow(MAX_SEED + 1)
                try:
                    with Store.open(tree, write=True) as store:
                        act, answer = store.generate(origin, params, adapter=adapter,
                                                     actor=Source("user", "probe"))
                    results[key] = {"act": act, "params": params,
                                    "terminator": answer.terminator}
                except Exception as e:
                    results[key] = {"error": f"{type(e).__name__}: {e}", "params": params}
                print(key, results[key], flush=True)
                out.write_text(json.dumps(results, indent=1))


# Basic Latin, Latin extensions, general punctuation and arrows. Anything else in an English
# context is the tail showing through.
LATIN = re.compile(r"[\x00-\x7f -ɏ -⁯←-⇿]")


def foreign(spelling: bytes) -> bool:
    try:
        text = spelling.decode("utf-8")
    except UnicodeDecodeError:
        return True
    return any(not LATIN.match(ch) for ch in text if not ch.isspace())


def repeated_4grams(ids: list[int]) -> float:
    grams = [tuple(ids[i:i + 4]) for i in range(len(ids) - 3)]
    return 1 - len(set(grams)) / len(grams) if grams else 0.0


def read(conn, act: int) -> dict:
    nodes = R.act_tokens(conn, act)
    spell = R.token_bytes(conn, [n.token_id for n in nodes])
    logprobs = [R.node_logprob(conn, n.id) for n in nodes]
    valued = [lp for lp in logprobs if lp is not None]
    text = b"".join(spell[n.token_id] for n in nodes).decode("utf-8", "replace")
    return {
        "text": text,
        "foreign": sum(foreign(spell[n.token_id]) for n in nodes) / max(1, len(nodes)),
        "mean": st.mean(valued) if valued else float("nan"),
        "deep": sum(lp < -5 for lp in valued) / max(1, len(valued)),
        "repeats": repeated_4grams([n.token_id for n in nodes]),
        # Mean drawn logprob over successive 25-token windows, which is where a path that
        # runs away shows it.
        "windows": [st.mean(valued[i:i + 25]) for i in range(0, len(valued), 25)],
    }


def report(tree: Path, out: Path) -> None:
    results = json.loads(out.read_text())
    conn = sqlite3.connect(f"file:{tree}/bulk.sqlite?mode=ro", uri=True)
    cells, failed = defaultdict(list), defaultdict(int)
    for key, r in results.items():
        site, cond, _ = key.split("|")
        if "error" in r:
            failed[(site, cond)] += 1
        else:
            cells[(site, cond)].append(read(conn, r["act"]))

    print("| site | condition | draws | failed | mean logprob | below -5 | foreign "
          "| 4-gram repeats |")
    print("|---|---|---|---|---|---|---|---|")
    for site, cond in sorted(set(cells) | set(failed)):
        rs = cells[(site, cond)]
        if not rs:
            print(f"| {site} | {cond} | 0 | {failed[(site, cond)]} | | | | |")
            continue
        print(f"| {site} | {cond} | {len(rs)} | {failed[(site, cond)]} "
              f"| {st.mean(r['mean'] for r in rs):.2f} | {st.mean(r['deep'] for r in rs):.2f} "
              f"| {st.mean(r['foreign'] for r in rs):.3f} "
              f"| {st.mean(r['repeats'] for r in rs):.3f} |")

    print("\nmean drawn logprob by 25-token window, 200-token draws:\n")
    for (site, cond), rs in sorted(cells.items()):
        for i, r in enumerate(rs):
            if len(r["windows"]) >= 8:
                print(f"{site:20} {cond:16} {i} " + " ".join(f"{w:6.1f}" for w in r["windows"]))

    print("\nthe first draw of each cell:\n")
    for (site, cond), rs in sorted(cells.items()):
        print(f"--- {site} {cond}\n{rs[0]['text'][:400]}\n")


def main() -> int:
    ap = argparse.ArgumentParser(prog="truncation-probe.py", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("step", choices=("draw", "report"))
    ap.add_argument("tree", type=Path, help="a copy; `draw` writes to it")
    ap.add_argument("results", type=Path, help="where the acts drawn are kept, as JSON")
    args = ap.parse_args()
    (draw if args.step == "draw" else report)(args.tree, args.results)
    return 0


if __name__ == "__main__":
    sys.exit(main())
