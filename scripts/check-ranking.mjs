/* Drive what a ranking's rows are, against rows as the wire sends them.
 * `node scripts/check-ranking.mjs`
 *
 * Two derived things, and both fail quietly. The order is a model's and the store does not
 * enforce it, so a list that forgot to sort looks sorted on almost every position and is
 * wrong exactly where a ranking was deepened. And which of the three kinds a row is decides
 * what taking it costs -- nothing, a selection, or a write -- so a row marked as another
 * offers the wrong thing and says nothing about it.
 */

import { words } from "./stub-dom.mjs";

const R = await import(
  new URL("../src/tokenloom/surface/page/assets/ranking.js", import.meta.url));

// ---- what a row looks like on the wire ------------------------------------------------------

const MODEL = 2, OTHER = 3;
const SOURCES = { 2: "model:qwen", 3: "model:other" };

let rank = 0;
const row = (p, over = {}) => ({
  source: MODEL, rank: rank++, token: 100 + rank, logprob: Math.log(p),
  text: "x", decodes: true, child: null, ...over,
});

// ---- reporting --------------------------------------------------------------------------------

let bad = 0;
function is(what, got, want) {
  const ok = JSON.stringify(got) === JSON.stringify(want);
  if (!ok) bad += 1;
  console.log(`${ok ? "ok  " : "FAIL"} ${what}: ${JSON.stringify(got)}`
    + (ok ? "" : ` != ${JSON.stringify(want)}`));
}
function near(what, got, want) {
  const ok = Number.isFinite(got) && Math.abs(got - want) < 1e-9;
  if (!ok) bad += 1;
  console.log(`${ok ? "ok  " : "FAIL"} ${what}: ${got}` + (ok ? "" : ` != ${want}`));
}
function says(what, got, want) {
  const ok = typeof got === "string" && got.includes(want);
  if (!ok) bad += 1;
  console.log(`${ok ? "ok  " : "FAIL"} ${what}: ${JSON.stringify(got)}`
    + (ok ? "" : ` has no ${JSON.stringify(want)}`));
}

// ---- the order ----------------------------------------------------------------------------------

/* Recorded order is arrival order, and a ranking deepened by a later act appends -- so a
 * near-tie at the join leaves two rows the wrong way round and every other position looks
 * fine. The rows below are in the order the store would hand them over. */
const joined = [row(0.6), row(0.2), row(0.25), row(0.01)];
const [[, ordered]] = R.sorted(joined);
is("rows within a source are put in descending logprob",
   ordered.map(r => Math.exp(r.logprob).toFixed(2)), ["0.60", "0.25", "0.20", "0.01"]);
is("  and none is dropped doing it", ordered.length, joined.length);

/* Across sources it does not sort. A node several models ranked holds several rankings, and
 * one order over their union would stand rows side by side that were never alternatives. */
const two = [row(0.1, { source: OTHER }), row(0.9), row(0.5, { source: OTHER })];
const groups = R.sorted(two);
is("each source keeps its own ranking", groups.map(([who, rs]) => [who, rs.length]),
   [[OTHER, 2], [MODEL, 1]]);
is("  in the order they first appear, and not merged", groups.map(([who]) => who),
   [OTHER, MODEL]);

// ---- which of the three a row is -------------------------------------------------------------------

/* What tells them apart is the record and not anything the page decided: a row carries the
 * node that realised it or nothing, and the path says which of those is the one in front of
 * the reader. */
const TOOK = 41, AWAY = 42;
is("the row the path took is the one whose child is next",
   R.kind(row(0.5, { child: TOOK }), TOOK), "took");
is("a row realised off the path is somewhere to go",
   R.kind(row(0.5, { child: AWAY }), TOOK), "elsewhere");
is("a row nothing ever took is the only one that would write",
   R.kind(row(0.5, { child: null }), TOOK), "unrealised");

/* A child carrying `deleted` is still a child: the merge key forbids realising it again, and
 * what brings it back is `undelete`. The wire says so by sending the id either way. */
is("a row whose node was set aside is still realised",
   R.kind(row(0.5, { child: AWAY }), TOOK), "elsewhere");

/* Where a path ends, nothing comes next -- and then no row is the one taken, rather than the
 * first of them being it by accident. */
is("at a leaf no row is the one taken",
   [row(0.9, { child: 7 }), row(0.1)].map(r => R.kind(r, null)),
   ["elsewhere", "unrealised"]);

// ---- how much they hold ------------------------------------------------------------------------------

/* The rows sum to less than one because the rest of the vocabulary was never recorded, which
 * is a quantity worth saying and not a shortfall to hide. */
near("what the rows hold is their probabilities and not their count",
     R.recorded([row(0.6), row(0.25), row(0.1)]), 0.95);

// ---- the list as it stands beside the column ---------------------------------------------------------

const payload = {
  node: 9,
  rows: [row(0.1), row(0.7, { child: TOOK }), row(0.2, { child: AWAY, text: "\nyes" })],
  sources: SOURCES,
};
let taken = null;
const box = R.list(payload, TOOK, r => { taken = r; });
const list = box.children.find(kid => kid.classList.contains("list"));
is("the rows are drawn in order and marked by kind",
   list.children.map(li => li.className), ["took", "elsewhere", "unrealised"]);
says("the source is named over its own rows", words(box.children[0]), "model:qwen");
says("  with how much of the distribution they hold", words(box.children[0]),
     "1.000 of the mass recorded");

/* A row is one line by its own construction, so a newline in a token is shown and not
 * obeyed -- the column is where a newline is a newline. */
says("a newline in a token is shown rather than obeyed", words(list.children[1]), "\\nyes");
is("  and the text is not what the column would have drawn",
   words(list.children[1]).includes("\n"), false);

/* The bar is against the top row of this source, so a position the model was unsure of does
 * not read as a page of empty bars. */
const bars = list.children.map(li => li.children[0].style.props["--p"]);
is("the bar is each row against the top one of its source", bars,
   ["1.0000", (0.2 / 0.7).toFixed(4), (0.1 / 0.7).toFixed(4)]);

list.children[1].onclick();
is("taking a row hands it over whole and decides nothing about it",
   [taken.child, taken.text], [AWAY, "\nyes"]);

const bare = R.list({ node: 9, rows: [], sources: SOURCES }, null, () => {});
says("a position nothing ranked says so", words(bare), "nothing was ranked");

// ---- what is held ------------------------------------------------------------------------------------

/* The rows only grow, so they would keep for the life of the page -- but `child` does not,
 * and an act is what changes it. Hovering is what makes this load-bearing. */
is("nothing is asked for until the reader asks", R.asked(), false);
R.want(true);
is("and asking is what turns it on", R.asked(), true);
R.remember(9, payload);
is("what was read is kept", R.recall(9), payload);
R.forget();
is("and an act is what makes it wrong, so it is dropped whole", R.recall(9), undefined);
R.want(false);

console.log(bad ? `\n${bad} failed` : "\nnothing failed");
process.exit(bad ? 1 : 0);
