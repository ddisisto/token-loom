"""Tree primitives, reduced to what the web front end actually calls.

These were the reusable layer under the tkinter app's `TreeModel`, and the part of it
worth keeping — but only six of thirty-eight functions were ever reached from `web/`.
The rest served features that did not survive the removal: subtree filtering and
copying for the multiverse view, path distance and nearest-common-ancestor for the
tree visualiser, stochastic descent by subtree weight, a Miro-board importer, and
several one-off format fixers. They went, and numpy and html2text with them.

Phase 1 of the roadmap replaces all of this: a trie over bytes, with tokens as a
per-span overlay. What is left here is therefore the honest measure of what that has
to carry — index the tree, walk ancestry, join text, mint a node, and keep bulk data
reachable — not a library to be ported.
"""

import uuid


def new_node(node_id=None, text='', mutable=True):
    if not node_id:
        node_id = str(uuid.uuid1())
    return {"id": node_id,
            "text": text,
            "children": [],
            "mutable": mutable}


# Adds an id to any node lacking one and a parent_id to every child, returning the
# tree flat. Called on load and after every mutation, so it doubles as the indexer.
def flatten_tree(d):
    if "id" not in d:
        d["id"] = str(uuid.uuid1())

    flat_children = []
    for child in d.get("children", []):
        child["parent_id"] = d["id"]
        flat_children.extend(flatten_tree(child))

    return [d, *flat_children]


# Returns a list of ancestor nodes beginning with the progenitor
def node_ancestry(node, node_dict):
    ancestry = [node]
    while "parent_id" in node:
        if node['parent_id'] in node_dict:
            node = node_dict[node["parent_id"]]
            ancestry.insert(0, node)
        else:
            break
    return ancestry


def ancestry_plaintext(ancestry):
    return "".join(node['text'] for node in ancestry)


def referenced_response_ids(root):
    """Ids in `model_responses` that some node still points at.

    A node's `generation` is {'id': response_id, 'index': i}. Several siblings
    from one call share a response id and differ only by index, so a response is
    reachable while *any* of them survives.
    """
    reachable = set()
    for node in flatten_tree(root):
        generation = node.get('generation')
        if isinstance(generation, dict) and generation.get('id'):
            reachable.add(generation['id'])
    return reachable


def collect_orphaned_responses(tree_data):
    """Drop token data no node points at any more, in place. Returns the ids dropped.

    Deleting a node used to leave its response behind forever -- one session left
    14 orphans and 600KB, and generating against a local model that returns
    logprobs for every token makes that grow much faster.
    """
    responses = tree_data.get('model_responses')
    if not responses:
        return []
    reachable = referenced_response_ids(tree_data['root'])
    orphaned = [key for key in responses if key not in reachable]
    for key in orphaned:
        del responses[key]
    return orphaned
