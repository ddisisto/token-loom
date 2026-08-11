# web

A web front end for loom. It began as a spike, to answer one question — **does the
domain logic survive being pulled out of the Tk objects?** — and the answer was yes,
so it stayed.

Run it:

    uv run --group web python -m web.server data/local.json

Then open <http://127.0.0.1:8080>. The tkinter app is untouched and still works.

## What it does

The read view is the main surface: the selected path's text, full width. Where the
path forked, a fork chip sits inline at that point and expands to show the siblings;
the selected node's own children are listed below as what lies ahead. Depth costs
vertical space, which scrolls, rather than horizontal space, which runs out.

Arrow keys walk the tree (up/down for parent/child, left/right for siblings); Enter
generates. `+ child` writes your own continuation, `Edit` changes the selected node's
text, `Probs` shades the selected node's tokens by improbability — which needs a model
that returns logprobs on a raw continuation, in practice the local one. `Tree` toggles
the whole-tree pane, which is an escape hatch rather than the way you navigate.

Several trees can be open at once as tabs. `+ new tree` starts a blank one; `Save as`
names it. Nothing is written to disk until you save. The file format is loom's own — a
tree saved here reopens in the tkinter app.

## What it doesn't do

No memory, no templates, no global context, no tags, no chapters, no multiverse view,
no hoisting, no frames. The prompt is simply the root-to-node text, tail-truncated to
`prompt_length`. Those are the expensive half, and they remain the open question:
which of them are load-bearing enough to port.

## Layout

- `tree.py` — the tree and its mutations. Imports `util/util_tree.py` unchanged.
- `generation.py` — wraps `gpt.gen`, which was already free of Tk and of the tree.
- `server.py` — JSON endpoints. Every UI action is one call, so a batch script can
  drive the same operations without a browser.
- `static/index.html` — the whole front end. No build step, no dependencies.

## What the spike established

- `model.py` and `gpt.py` import no tkinter at all. The coupling is at *runtime*
  (`self.app`, `event_generate`, the callback registry), not at import.
- The tree primitives in `util/util_tree.py` were already a clean, reusable layer.
  `tree.py` calls them directly and adds only indexing and mutation.
- The generation-thread machinery — worker thread, main-thread hand-back queue, the
  virtual events that silently never fire across threads — is *entirely* an artifact
  of Tk owning the main loop. A request handler blocks and returns. That whole class
  of bug does not exist here.
- Roughly 200 lines of Python replace what the tkinter app spends thousands on, for
  this subset. The subset is small, and the omissions above are where the real cost
  is hiding.
