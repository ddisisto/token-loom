# spike

A web front end for loom, built to answer one question: **does the domain logic
survive being pulled out of the Tk objects?**

Run it:

    uv run --group spike python -m spike.server data/local.json

Then open <http://127.0.0.1:8080>. The tkinter app is untouched and still works.

## What it does

Tree on the left, the read view on the right, controls along the bottom. Click a node
to select it; arrow keys walk the tree (up/down for parent/child, left/right for
siblings); Enter generates. `+ child` writes your own continuation, `Edit` changes the
selected node's text, `Probs` shades the selected node's tokens by improbability.

Nothing is written to disk until you press `Save`. The file format is loom's own — a
tree saved here reopens in the tkinter app.

## What it doesn't do

No memory, no templates, no global context, no tags, no chapters, no multiverse view,
no hoisting, no frames. The prompt is simply the root-to-node text, tail-truncated to
`prompt_length`. Those omissions are the point: this is a structural probe, not a
replacement.

## Layout

- `tree.py` — the tree and its mutations. Imports `util/util_tree.py` unchanged.
- `generation.py` — wraps `gpt.gen`, which was already free of Tk and of the tree.
- `server.py` — JSON endpoints. Every UI action is one call, so a batch script can
  drive the same operations without a browser.
- `static/index.html` — the whole front end. No build step, no dependencies.

## What the spike found

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
