"""The page's own arithmetic, driven by node against a stub DOM.

Everything else in this suite reaches the surface through its reads and its routes, which
stop at the wire. These live past it: the draw panel decides what a `generate` is asked for,
the overlay decides what a ranking means once it has arrived, and the caret decides which
node an act at a position takes. All three are things nothing else disagrees with -- an
invalid pair of sampler settings is caught by the adapter *recording a refusal*, a scale read
from the wrong end produces a page that looks like it is working, and a caret one node late
writes into the token the reader meant to reconsider -- so each has a driver under
`scripts/`, and this is what runs them.

The checks themselves are in the scripts, in the language the code under them is written in.
What is here is the hook: a subprocess, its output on failure, and a skip where `node` is not
installed, since nothing else in the project needs it.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
CHECKS = ["check-cursor.mjs", "check-draw.mjs", "check-overlay.mjs"]


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


def test_every_driver_under_scripts_is_run():
    """The list above is written out, so a driver added and not hooked up is a failure here
    rather than a file nobody runs. `stub-dom.mjs` is what they import and not a driver."""
    found = {p.name for p in SCRIPTS.glob("check-*.mjs")}
    assert found == set(CHECKS)
