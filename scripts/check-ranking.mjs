/* Drive what a ranking's rows are, against rows as the wire sends them.
 * `node scripts/check-ranking.mjs`
 *
 * Three derived things, and all of them fail quietly. The order is a model's and the store
 * does not enforce it, so a list that forgot to sort looks sorted on almost every position
 * and is wrong exactly where a ranking was deepened. Which of the three kinds a row is
 * decides what taking it costs -- nothing, a selection, or a write -- so a row marked as
 * another offers the wrong thing and says nothing about it. And what a row weighs is the
 * second axis of the list: it is what the reader grew and not what the model said, so a
 * weight taken from the wrong place would draw a confident claim about the record in exactly
 * the channel a reader is meant to read the record off.
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
const box = R.list(payload, TOOK, r => { taken = r; }, null);
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

const bare = R.list({ node: 9, rows: [], sources: SOURCES }, null, () => {}, null);
says("a position nothing ranked says so", words(bare), "nothing was ranked");

// ---- what the reader grew -----------------------------------------------------------------

/* The other axis. The order of the rows is the model's opinion of the position, and this is
 * what was grown from each of them -- so the two are read off one list and the interesting
 * case is where they disagree. A weight read from the wrong place would be a claim about the
 * record drawn in the channel a reader reads the record off, and nothing would contradict it.
 *
 * The measure arrives rather than being chosen here, the way the rule does. This is the log
 * reading of subtree size, which is what the panel hands over when nothing is chosen.
 */
const BY_SIZE = { key: "size", unit: "ln nodes", dp: 2, of: u => Math.log1p(u.size) };

const grown = (size, over = {}) =>
  row(0.5, { child: 500 + size, under: { height: 1, size, forks: 0, run: 1 }, ...over });

is("a row nothing realised has no node to weigh",
   R.weight(row(0.5, { child: null, under: null }), BY_SIZE).state, "none");
is("a read that did not ask says so, and is not a row that weighs nothing",
   R.weight(row(0.5, { child: 7 }), BY_SIZE).state, "unasked");
is("a row whose node the descent did not reach is one the toggle is hiding",
   R.weight(row(0.5, { child: 7, under: null }), BY_SIZE).state, "hidden");
near("and a row that was grown from weighs what the measure reads",
     R.weight(grown(20), BY_SIZE).value, Math.log1p(20));
is("  and keeps the count, since a size is checked against nodes and not against a reading",
   R.weight(grown(20), BY_SIZE).count, 20);

/* Against the heaviest row of the source, the way the bar is against the top one: a count of
 * what has been grown has no domain, so there is nothing else to place it against. */
const weights = [grown(999), grown(20), row(0.5, { child: null, under: null })]
  .map(r => R.weight(r, BY_SIZE));
const placed = R.spread(weights);
near("the heaviest row of a source is the whole of the axis", placed[0], 1);
near("  and the rest stand against it in the measure's own space",
     placed[1], Math.log1p(20) / Math.log1p(999));
near("a row that weighs nothing sits at the floor", placed[2], 0);

/* A position nothing was grown at is a list of even rows and not a list of empty ones: there
 * is no heaviest row to divide by, and dividing by nothing would be a hole per row. */
is("with nothing grown anywhere the axis is flat",
   R.spread([row(0.5), row(0.5)].map(r => R.weight(r, BY_SIZE))), [0, 0]);

/* The place goes to the stylesheet and the count to the title. What a row is worth has to be
 * legible exactly, because the size is a glance and a glance is not a number. */
const sized = R.list(
  { node: 9, rows: [grown(999), grown(20, { child: 600 }), row(0.5)], sources: SOURCES },
  null, () => {}, BY_SIZE);
const rows = sized.children.find(kid => kid.classList.contains("list")).children;
is("the row is handed its place on the axis and the stylesheet owns the rest",
   rows.map(li => li.style.props["--w"]),
   ["1.0000", (Math.log1p(20) / Math.log1p(999)).toFixed(4), "0.0000"]);
says("what the size is a count of is said in words", rows[0].title, "999 below this");
says("  and it names the measure it came from", rows[0].title, "size");
says("a row nothing realised says that, rather than being a small one",
     rows[2].title, "nothing has realised this row");
is("  and is marked as being at the floor rather than near it",
   rows.map(li => li.classList.contains("bare")), [false, false, true]);

/* A list drawn before a measure is chosen is the list as it was, and not a list of rows all
 * the same size -- because setting the place to nothing is a claim and leaving it off is not.
 */
const plain = R.list({ node: 9, rows: [grown(999)], sources: SOURCES }, null, () => {}, null);
is("with no measure the axis is not drawn at all",
   plain.children.find(k => k.classList.contains("list")).children[0].style.props["--w"],
   undefined);

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
