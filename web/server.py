"""HTTP backend for token loom's web front end.

Headless-first: every operation the browser performs is a plain JSON endpoint, so
the same operations drive a batch script. That is the point of the exercise — the
tkinter app can only be driven by clicking.

    uv run --group web python -m web.server data/local.json

Several trees can be open at once. Each is a *session*, addressed by an opaque id;
the browser draws them as tabs. Mutating endpoints act on the active session.
"""

import argparse
import itertools
import os
from pathlib import Path

from dotenv import load_dotenv

# before importing gpt, which reads keys from the environment at import time
load_dotenv()

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from web import generation
from web.tree import Tree

STATIC = Path(__file__).parent / "static"
DATA_DIR = Path("data")
LABEL_CHARS = 100

app = FastAPI(title="token loom")


class Sessions:
    """Open trees, in insertion order, with one of them active."""

    def __init__(self):
        self.trees = {}
        self.active_id = None
        self._ids = itertools.count(1)

    def add(self, tree):
        session_id = f"s{next(self._ids)}"
        self.trees[session_id] = tree
        self.active_id = session_id
        return session_id

    def open(self, filename):
        """Opening an already-open file activates it rather than duplicating it."""
        resolved = os.path.abspath(filename)
        for session_id, tree in self.trees.items():
            if tree.filename and os.path.abspath(tree.filename) == resolved:
                self.active_id = session_id
                return session_id
        return self.add(Tree.open(filename))

    def close(self, session_id):
        if session_id not in self.trees:
            raise KeyError(session_id)
        remaining = [k for k in self.trees if k != session_id]
        if not remaining:
            raise ValueError("cannot close the last session")
        del self.trees[session_id]
        if self.active_id == session_id:
            self.active_id = remaining[-1]

    def activate(self, session_id):
        if session_id not in self.trees:
            raise KeyError(session_id)
        self.active_id = session_id

    @property
    def active(self):
        return self.trees[self.active_id]


sessions = Sessions()


# -- request bodies -------------------------------------------------------

class SelectBody(BaseModel):
    node_id: str


class TextBody(BaseModel):
    text: str


class OpenBody(BaseModel):
    filename: str


class PathBody(BaseModel):
    path: str


class SaveAsBody(BaseModel):
    name: str
    overwrite: bool = False


class GenerateBody(BaseModel):
    node_id: str
    num_continuations: int | None = None
    temperature: float | None = None
    response_length: int | None = None
    model: str | None = None


# -- serialisation --------------------------------------------------------

def _node_view(node):
    """Truncated labels only.

    loom_demo.json is 764 nodes and 226KB of text; shipping all of it on every
    click is waste. Full text travels only for the selected path, in `read`.
    """
    text = node.get("text", "")
    return {
        "id": node["id"],
        "label": " ".join(text.split())[:LABEL_CHARS],
        "source": node.get("meta", {}).get("source", "root"),
        "has_tokens": bool(node.get("generation")),
        "children": [_node_view(c) for c in node.get("children", [])],
    }


def _state():
    tree = sessions.active
    selected = tree.data.get("selected_node_id")
    return {
        "sessions": [
            {
                "id": session_id,
                "name": t.name,
                "filename": t.filename,
                "dirty": t.dirty,
                "active": session_id == sessions.active_id,
            }
            for session_id, t in sessions.trees.items()
        ],
        "tree": _node_view(tree.root),
        "selected_node_id": selected,
        "read": [{"id": n["id"], "text": n.get("text", "")}
                 for n in tree.ancestry(selected)],
        "settings": tree.settings,
        "scratchpad": tree.scratchpad,
        "models": generation.available_models(),
        "node_count": len(tree.nodes),
    }


def _lookup(node_id):
    try:
        return sessions.active.node(node_id)
    except KeyError as e:
        raise HTTPException(404, str(e)) from None


# -- sessions -------------------------------------------------------------

@app.get("/api/files")
def list_files():
    """Trees available to open. Hidden files (.app_data.json) excluded."""
    if not DATA_DIR.is_dir():
        return {"files": []}
    return {"files": sorted(str(p) for p in DATA_DIR.glob("*.json")
                            if not p.name.startswith("."))}


@app.post("/api/sessions/open")
def open_session(body: OpenBody):
    if not os.path.isfile(body.filename):
        raise HTTPException(404, f"no such file: {body.filename}")
    try:
        sessions.open(body.filename)
    except Exception as e:
        raise HTTPException(400, f"could not open: {e}") from None
    return _state()


@app.post("/api/sessions/new")
def new_session():
    """A blank tree, held in memory until it is given a name by save-as."""
    sessions.add(Tree.empty())
    sessions.active.data["generation_settings"] = generation.default_settings()
    return _state()


@app.post("/api/sessions/{session_id}/activate")
def activate_session(session_id: str):
    try:
        sessions.activate(session_id)
    except KeyError:
        raise HTTPException(404, f"no session {session_id}") from None
    return _state()


@app.delete("/api/sessions/{session_id}")
def close_session(session_id: str):
    try:
        sessions.close(session_id)
    except KeyError:
        raise HTTPException(404, f"no session {session_id}") from None
    except ValueError as e:
        raise HTTPException(400, str(e)) from None
    return _state()


# -- tree -----------------------------------------------------------------

@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")


@app.get("/api/state")
def get_state():
    return _state()


@app.post("/api/select")
def select(body: SelectBody):
    _lookup(body.node_id)
    tree = sessions.active
    with tree.lock:
        tree.select(body.node_id)
    return _state()


@app.get("/api/node/{node_id}/prompt")
def get_prompt(node_id: str):
    """What the model would actually be sent. Useful on its own when debugging."""
    _lookup(node_id)
    tree = sessions.active
    return {"prompt": tree.prompt(node_id, tree.settings.get("prompt_length"))}


@app.get("/api/node/{node_id}/tokens")
def get_tokens(node_id: str):
    _lookup(node_id)
    return {"tokens": sessions.active.tokens(node_id)}


@app.patch("/api/node/{node_id}")
def edit_node(node_id: str, body: TextBody):
    _lookup(node_id)
    tree = sessions.active
    with tree.lock:
        tree.edit(node_id, body.text)
    return _state()


@app.post("/api/node/{node_id}/child")
def add_child(node_id: str, body: TextBody):
    _lookup(node_id)
    tree = sessions.active
    with tree.lock:
        node = tree.add_child(node_id, body.text, source="prompt")
        tree.select(node["id"])
    return _state()


@app.delete("/api/node/{node_id}")
def delete_node(node_id: str):
    _lookup(node_id)
    tree = sessions.active
    with tree.lock:
        try:
            tree.delete(node_id)
        except ValueError as e:
            raise HTTPException(400, str(e)) from None
    return _state()


@app.post("/api/generate")
def generate(body: GenerateBody):
    """Blocking. FastAPI runs sync handlers in a threadpool, so this is fine."""
    _lookup(body.node_id)
    tree = sessions.active
    settings = dict(tree.settings)
    for key in ("num_continuations", "temperature", "response_length", "model"):
        value = getattr(body, key)
        if value is not None:
            settings[key] = value

    prompt = tree.prompt(body.node_id, settings.get("prompt_length"))
    response, error = generation.generate(prompt, settings)
    if error:
        raise HTTPException(502, error)

    with tree.lock:
        tree.record_response(response)
        new_ids = []
        for index, completion in enumerate(response["completions"]):
            node = tree.add_child(
                body.node_id,
                completion["text"],
                generation={"id": response["id"], "index": index},
            )
            new_ids.append(node["id"])
        tree.settings.update(settings)

    return {**_state(), "new_node_ids": new_ids}


# -- scratchpad -----------------------------------------------------------

@app.put("/api/scratchpad")
def set_scratchpad(body: TextBody):
    tree = sessions.active
    with tree.lock:
        tree.set_scratchpad(body.text)
    return {"ok": True}


@app.post("/api/scratchpad/load")
def load_into_scratchpad(body: PathBody):
    """Pull a file in as raw seed material. Any readable path — these live outside
    the repo as often as in it."""
    path = Path(body.path).expanduser()
    if not path.is_file():
        raise HTTPException(404, f"no such file: {path}")
    try:
        text = path.read_text(errors="replace")
    except OSError as e:
        raise HTTPException(400, f"could not read: {e}") from None
    tree = sessions.active
    with tree.lock:
        existing = tree.scratchpad
        tree.set_scratchpad(f"{existing}\n\n{text}" if existing else text)
    return _state()


@app.post("/api/scratchpad/seed")
def seed_from_scratchpad(body: TextBody):
    """Turn scratchpad text into a node under the current selection."""
    tree = sessions.active
    if not body.text.strip():
        raise HTTPException(400, "nothing selected to seed from")
    with tree.lock:
        node = tree.add_child(tree.data["selected_node_id"], body.text,
                              source="prompt")
        tree.select(node["id"])
    return _state()


@app.post("/api/save")
def save():
    tree = sessions.active
    if not tree.filename:
        raise HTTPException(400, "this tree has never been saved -- use save as")
    with tree.lock:
        filename = tree.save()
    return {"saved": filename, **_state()}


@app.post("/api/save-as")
def save_as(body: SaveAsBody):
    """Flat files inside data/ only. Rejects anything with a path in it rather
    than resolving it, and refuses to clobber an existing tree unless told to --
    these files are not disposable."""
    name = body.name.strip()
    if not name:
        raise HTTPException(400, "no name given")
    if not name.endswith(".json"):
        name += ".json"
    if Path(name).name != name or name.startswith("."):
        raise HTTPException(400, "name must be a plain filename inside data/")
    path = DATA_DIR / name
    if path.exists() and not body.overwrite:
        raise HTTPException(409, f"{path} already exists")
    tree = sessions.active
    with tree.lock:
        filename = tree.save(str(path))
    return {"saved": filename, **_state()}


def main():
    parser = argparse.ArgumentParser(description="token loom web server")
    parser.add_argument("filename", nargs="*", help="tree JSON to open")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=8080, type=int)
    args = parser.parse_args()

    for filename in args.filename:
        sessions.open(filename)
        tree = sessions.active
        print(f"opened {filename} ({len(tree.nodes)} nodes)")
    if not sessions.trees:
        sessions.add(Tree.empty())
        print("opened a blank tree")
    for tree in sessions.trees.values():
        if not tree.settings:
            tree.data["generation_settings"] = generation.default_settings()

    print(f"serving on http://{args.host}:{args.port}")
    uvicorn.run(app, host=args.host, port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
