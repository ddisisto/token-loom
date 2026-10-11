/* Waypoints: positions the reader marked so as to find them again.
 *
 * A waypoint is a node and the time it was set. Its path is the node's ancestry, so nothing
 * else is kept and nothing kept can disagree with the record. They are kept in the browser,
 * keyed by the tree, since the address names the server and not the tree it was started
 * against. What a list of them shows -- where each stands and what leads up to it -- is read
 * from the server and never kept.
 *
 * Storage can be missing or refuse, in a private window or with site data blocked, and then
 * there are simply none: a waypoint is a way back and never a reason the page will not load.
 */

const KEY = "tokenloom:waypoints:";

/** The waypoints kept for `tree`, in the order they were set. */
export function load(storage, tree) {
  try {
    const list = JSON.parse(storage?.getItem(KEY + tree) ?? "[]");
    return Array.isArray(list) ? list.filter(w => Number.isInteger(w?.node)) : [];
  } catch {
    return [];
  }
}

/** Keep `list` for `tree`, and say whether it was kept. */
export function save(storage, tree, list) {
  try {
    storage.setItem(KEY + tree, JSON.stringify(list));
    return true;
  } catch {
    return false;
  }
}

export const has = (list, node) => list.some(w => w.node === node);

/** `list` with a waypoint at `node` set at `now`, or with the one there cleared. */
export function toggle(list, node, now) {
  return has(list, node) ? list.filter(w => w.node !== node)
                         : [...list, { node, created: now }];
}

/** What the server said of each waypoint, nested: by root, the ones with no other above
 *  them, each carrying `below` the ones it is nearest above. Siblings stand in the order
 *  they were set. One the tree does not hold is left out, and is still kept. */
export function nest(rows, list) {
  const order = new Map(list.map((w, i) => [w.node, i]));
  const kept = rows.filter(r => !r.missing && order.has(r.node))
                   .sort((a, b) => order.get(a.node) - order.get(b.node));
  const items = new Map(kept.map(r => [r.node, { ...r, below: [] }]));
  const roots = new Map();
  for (const item of items.values()) {
    if (items.has(item.under)) items.get(item.under).below.push(item);
    else roots.set(item.root, [...(roots.get(item.root) ?? []), item]);
  }
  return roots;
}
