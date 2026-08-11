"""Loom's tree, without Tk.

The tkinter app's `TreeModel` mixes three concerns: the tree itself, generation, and
Tk callback plumbing. This is the first of those, pulled out on its own. It reuses the
primitives in `util/util_tree.py` unchanged — those were already free of Tk, which was
the main thing this set out to establish.

The on-disk format is loom's, unmodified. A tree written here still opens in the
tkinter app, and vice versa.
"""

import os
import threading
from copy import deepcopy

from util.util import json_create, json_open, timestamp
from util.util_tree import (ancestry_plaintext, flatten_tree, new_node,
                            node_ancestry)

EMPTY_TREE = {
    # no "id" — flatten_tree() assigns one on first index, as it does for imported trees
    "root": {"text": "", "mutable": False, "visited": True, "children": []},
    "chapters": {},
    "canonical": [],
    "summaries": {},
    "model_responses": {},
}


class Tree:
    """A loom tree, plus the index and mutations the UI needs.

    Every mutation reindexes rather than trying to keep the index incrementally
    correct. Trees are small enough that this is free, and it removes a whole class
    of bug the original has to think about.
    """

    def __init__(self, data, filename=None):
        self.data = data
        self.filename = filename
        self.lock = threading.Lock()
        self.dirty = False
        self.data.setdefault("model_responses", {})
        self.reindex()
        if not self.data.get("selected_node_id") in self.nodes:
            self.data["selected_node_id"] = self.root["id"]

    @property
    def name(self):
        return os.path.basename(self.filename) if self.filename else "untitled"

    @classmethod
    def open(cls, filename):
        return cls(json_open(filename), filename)

    @classmethod
    def empty(cls):
        return cls(deepcopy(EMPTY_TREE))

    def save(self, filename=None):
        filename = filename or self.filename
        if not filename:
            raise ValueError("no filename to save to")
        json_create(filename, self.data)
        self.filename = filename
        self.dirty = False
        return filename

    # -- reading ----------------------------------------------------------

    def reindex(self):
        self.nodes = {node["id"]: node for node in flatten_tree(self.root)}

    @property
    def root(self):
        return self.data["root"]

    @property
    def settings(self):
        return self.data.setdefault("generation_settings", {})

    @property
    def scratchpad(self):
        """Free text that travels with the tree but is not part of it.

        Stored at the top level of the tree file. loom preserves keys it doesn't
        recognise, so a tree with a scratchpad still round-trips through the
        tkinter app.
        """
        return self.data.get("scratchpad", "")

    def set_scratchpad(self, text):
        self.data["scratchpad"] = text
        self.dirty = True

    def node(self, node_id):
        try:
            return self.nodes[node_id]
        except KeyError:
            raise KeyError(f"no node {node_id}") from None

    def ancestry(self, node_id):
        return node_ancestry(self.node(node_id), self.nodes)

    def prompt(self, node_id, char_limit=None):
        """The text the model actually sees: root-to-node, tail-truncated.

        The tkinter app also folds in memory, global context and templates here.
        Still left out — those are the expensive half, and not yet ported.
        """
        text = ancestry_plaintext(self.ancestry(node_id))
        return text[-char_limit:] if char_limit else text

    def tokens(self, node_id):
        """Per-token logprobs for a generated node, or None if it has none."""
        node = self.node(node_id)
        generation = node.get("generation")
        if not generation:
            return None
        response = self.data["model_responses"].get(generation.get("id"))
        if not response:
            return None
        try:
            return response["completions"][generation["index"]]["tokens"]
        except (IndexError, KeyError):
            return None

    # -- mutating ---------------------------------------------------------

    def add_child(self, parent_id, text, source="AI", generation=None):
        parent = self.node(parent_id)
        node = new_node(text=text, mutable=source != "AI")
        node["parent_id"] = parent_id
        node["open"] = 1
        node["visited"] = False
        node["meta"] = {
            "creation_timestamp": timestamp(),
            "source": source,
            "modified": False,
        }
        if generation:
            node["generation"] = generation
        parent.setdefault("children", []).append(node)
        self.nodes[node["id"]] = node
        self.dirty = True
        return node

    def record_response(self, response):
        """Stash a full formatted response so nodes can point at its token data."""
        self.data["model_responses"][response["id"]] = response
        self.dirty = True

    def edit(self, node_id, text):
        node = self.node(node_id)
        node["text"] = text
        node.setdefault("meta", {})["modified"] = True
        self.dirty = True
        return node

    def delete(self, node_id):
        node = self.node(node_id)
        if node is self.root:
            raise ValueError("cannot delete the root")
        parent = self.nodes[node["parent_id"]]
        parent["children"] = [c for c in parent["children"] if c["id"] != node_id]
        if self.data.get("selected_node_id") in _subtree_ids(node):
            self.data["selected_node_id"] = parent["id"]
        self.reindex()
        self.dirty = True
        return parent["id"]

    def select(self, node_id):
        self.node(node_id)["visited"] = True
        self.data["selected_node_id"] = node_id
        return node_id


def _subtree_ids(node):
    return {n["id"] for n in flatten_tree(node)}
