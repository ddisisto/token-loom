#!/usr/bin/env python
"""Build the worked example from `docs/CORE.md` as a real tree on disk.

**No server and no model.** The adapter is the scripted one the appendix tests use, so
this needs nothing running; what it is for is a fixture that a client can be pointed at.

It is the small hard case. Ordinary English is one token per several characters, and a
tree of it never exercises the other direction -- `🜁` is three tokens spelling one
character, none of them valid UTF-8 alone, and `<|endoftext|>` is a control token that
displays as its own thirteen characters.

    uv run scripts/appendix-tree.py data/appendix
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tests"))

from appendix import MODEL, USER, ScriptedAdapter  # noqa: E402
from tokenloom.core import Store, violations  # noqa: E402


def build(path: Path) -> Store:
    """The seven stages, in the appendix's order. Node ids come out 1 through 12."""
    store = Store.initialise(path, vocabulary="qwen2.5-7b-base")
    adapter = ScriptedAdapter()
    store.create(None, "The sky", vocabulary=adapter, actor=USER)
    store.generate(2, {"top_k": 5, "top_n": 5, "length": 3}, adapter=adapter, actor=USER, seed=42)
    store.generate(2, {"top_k": 5, "top_n": 20, "length": 2}, adapter=adapter, actor=USER, seed=99)
    store.generate(2, {"top_k": 5, "top_n": 5, "length": 3}, adapter=adapter, actor=USER, seed=42)
    store.realise(2, MODEL, 0, actor=USER)
    store.create(8, "<|endoftext|>\U0001f701", vocabulary=adapter, actor=USER, special=True)
    store.generate(12, {"top_k": 5, "top_n": 200, "length": 4}, adapter=adapter, actor=USER, seed=7)
    return store


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="appendix-tree.py", description=__doc__)
    parser.add_argument("out", type=Path)
    parser.add_argument("--force", action="store_true", help="replace an existing directory")
    args = parser.parse_args(argv)

    if args.out.exists():
        if not args.force:
            raise SystemExit(f"{args.out} exists; pass --force to replace it")
        shutil.rmtree(args.out)

    with build(args.out) as store:
        found = violations(store.conn)
        if found:
            raise SystemExit("built a tree that fails an invariant:\n  "
                             + "\n  ".join(str(v) for v in found))
        nodes = store.conn.execute("SELECT COUNT(*) FROM nodes").fetchone()[0]
        acts = store.conn.execute("SELECT COUNT(*) FROM acts").fetchone()[0]
        print(f"{args.out}  {nodes} nodes  {acts} acts  clean")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
