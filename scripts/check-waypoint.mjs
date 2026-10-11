/* Drive what the page keeps of the reader's waypoints.  `node scripts/check-waypoint.mjs`
 *
 * Two things fail quietly here. Storage that refuses is the ordinary case in a private window,
 * and a page that threw on it would not load at all. And a nesting that lost a waypoint, or
 * put one under the wrong root, would read as a list that is merely short.
 */

const w = await import(new URL("../src/tokenloom/surface/page/assets/waypoint.js", import.meta.url));

let bad = 0;
const is = (what, got, want) => {
  const ok = JSON.stringify(got) === JSON.stringify(want);
  if (!ok) bad++;
  console.log(`${ok ? "ok  " : "FAIL"} ${what}: ${JSON.stringify(got)}` +
              (ok ? "" : ` != ${JSON.stringify(want)}`));
};

const memory = () => {
  const held = new Map();
  return { getItem: k => held.get(k) ?? null, setItem: (k, v) => held.set(k, String(v)) };
};
const refusing = { getItem() { throw new Error("denied"); }, setItem() { throw new Error("full"); } };

// ---- keeping ----------------------------------------------------------------------------

const store = memory();
is("nothing kept is none", w.load(store, "a"), []);
let list = w.toggle([], 7, 100);
list = w.toggle(list, 3, 200);
is("set in order, each with when", list, [{ node: 7, created: 100 }, { node: 3, created: 200 }]);
is("  and set again is cleared", w.toggle(list, 7, 300), [{ node: 3, created: 200 }]);
is("  and kept is what comes back", [w.save(store, "a", list), w.load(store, "a")], [true, list]);
is("one tree's are not another's", w.load(store, "b"), []);
is("storage that refuses has none and keeps nothing",
   [w.load(refusing, "a"), w.save(refusing, "a", list), w.load(null, "a")], [[], false, []]);
store.setItem("tokenloom:waypoints:c", "{not json");
store.setItem("tokenloom:waypoints:d", '[{"node":4},{"node":"x"},null]');
is("what was kept wrong is none, or the part that is right",
   [w.load(store, "c"), w.load(store, "d")], [[], [{ node: 4 }]]);

// ---- nesting ------------------------------------------------------------------------------

const row = (node, root, under) => ({ node, root, under, live: true, lead: "", token: "" });
const kept = [7, 3, 9, 4, 12, 99].map((node, i) => ({ node, created: i }));
// 3 is above 7 and 4; 12 is another root's; 9 is under 7; 99 is gone.
const rows = [row(4, 1, 3), row(99, 0, null), row(9, 1, 7), row(12, 2, null),
              row(3, 1, null), row(7, 1, 3)];
rows[1] = { node: 99, missing: true };
const tree = w.nest(rows, kept);
const shape = items => items.map(i => [i.node, shape(i.below)]);
is("each stands under its root, nearest above first",
   [...tree].map(([root, items]) => [root, shape(items)]),
   [[1, [[3, [[7, [[9, []]]], [4, []]]]]], [2, [[12, []]]]]);
const count = items => items.reduce((n, i) => n + 1 + count(i.below), 0);
is("  and none is lost but the one the tree does not hold",
   [...tree.values()].reduce((n, items) => n + count(items), 0), kept.length - 1);
is("one whose nearest above is not kept stands under its root",
   shape(w.nest([row(5, 1, 40)], [{ node: 5 }]).get(1)), [[5, []]]);

process.exit(bad ? 1 : 0);
