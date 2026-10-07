"""The page's own arithmetic, driven by node against a stub DOM.

Everything else in this suite reaches the surface through its reads and its routes, which
stop at the wire. These live past it: the draw panel decides what a `generate` is asked for,
the overlay decides what a ranking means once it has arrived, the caret decides which node an
act at a position takes, a ranking's rows decide what taking one would cost, and the mark
decides whose a token is. None of them is something anything else disagrees with -- an invalid
pair of sampler settings is caught by the adapter *recording a refusal*, a scale read from the
wrong end produces a page that looks like it is working, a caret one node late writes into the
token the reader meant to reconsider, a row marked as another kind offers the wrong thing and
says nothing about it, and a segment marked as the reader's where the sampler drew it is the
one error `docs/SPINE.md` says nothing else in the record can correct -- so each has a driver
under `scripts/`, and this is what runs them.

The checks themselves are in the scripts, in the language the code under them is written in.
What is here is the hook: a subprocess, its output on failure, and a skip where `node` is not
installed, since nothing else in the project needs it.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
ASSETS = ROOT / "src" / "tokenloom" / "surface" / "page" / "assets"
CHECKS = [
    "check-cursor.mjs",
    "check-draw.mjs",
    "check-mark.mjs",
    "check-overlay.mjs",
    "check-ranking.mjs",
    "check-room.mjs",
    "check-stub.mjs",
]


@pytest.mark.parametrize("script", CHECKS)
def test_an_asset_says_what_it_says_it_says(script):
    """Run one driver and fail with its output, which names the check that went."""
    node = shutil.which("node")
    if node is None:
        pytest.skip("node is not installed; the page's own arithmetic is checked by hand")
    done = subprocess.run(
        [node, str(SCRIPTS / script)], capture_output=True, text=True, timeout=60
    )
    assert done.returncode == 0, done.stdout + done.stderr


def test_every_page_module_parses(tmp_path):
    """**A module that does not parse takes the whole page down and says nothing.**

    The page is ES modules with no build step, so nothing stands between the file and the
    browser to object -- and a duplicate declaration or a stray bracket does not break the
    module it is in, it stops the module graph loading. What the reader gets is a blank
    column and no error anywhere they would look. One cost an afternoon's confusion here
    before it was found by driving a browser.

    The drivers above parse what they import, which is every module the page's arithmetic
    lives in; what nothing imports is `app.js`, because it is the wiring and reaches for a
    document. So this parses without running: the sources are copied under `.mjs`, since
    `--check` takes the module goal from the extension and the page is served as `.js` from
    a directory that has no `package.json` and should not grow one.
    """
    node = shutil.which("node")
    if node is None:
        pytest.skip("node is not installed; the page's modules are parsed by the browser")
    found = sorted(ASSETS.glob("*.js"))
    assert found, f"no modules under {ASSETS}"
    bad = []
    for src in found:
        copy = tmp_path / f"{src.stem}.mjs"
        copy.write_text(src.read_text())
        done = subprocess.run(
            [node, "--check", str(copy)], capture_output=True, text=True, timeout=60
        )
        if done.returncode != 0:
            # The fault and not the last line, which is node's own version banner.
            said = [
                line for line in done.stderr.splitlines() if "Error" in line
            ] or done.stderr.splitlines()
            bad.append(f"{src.name}: {said[0].strip()}")
    assert not bad, "\n".join(bad)


def test_every_driver_under_scripts_is_run():
    """The list above is written out, so a driver added and not hooked up is a failure here
    rather than a file nobody runs. `stub-dom.mjs` is what they import and not a driver."""
    found = {p.name for p in SCRIPTS.glob("check-*.mjs")}
    assert found == set(CHECKS)
