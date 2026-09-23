/* Drive the overlay against a stub DOM.  `node scripts/check-overlay.mjs`
 *
 * What it is here for is arithmetic nothing disagrees with. An overlay turns a ranking into a
 * colour, and a colour is not a number a reader can check: a wrong polarity, a domain read
 * from the wrong end or a state marked as another all produce a page that looks like it is
 * working. So the checks are on the invariants rather than the values -- that the token which
 * took the top row is the unflagged one, that two readings of a measure agree on which
 * position is hottest, that a position with no value is never a position with a low one.
 *
 * The stub is `stub-dom.mjs`, shared with the draw panel's check. No reading column is driven
 * from here; what the page does with a mark is the page's.
 */

import { words } from "./stub-dom.mjs";

const O = await import(
  new URL("../src/tokenloom/surface/page/assets/overlay.js", import.meta.url));

// ---- driving the panel -------------------------------------------------------------------

let moved = 0;
const frag = O.panel(() => { moved += 1; });
const [head, body] = frag.children;

const groups = new Map();
for (const kid of body.children) {
  if (!kid.classList.contains("pick")) continue;
  const [what, row] = kid.children;
  groups.set(what.textContent, row.children);
}
const note = body.children.at(-1);

function tap(group, label) {
  const found = groups.get(group).find(chip => chip.textContent === label);
  if (!found) {
    const had = groups.get(group).map(chip => chip.textContent).join(", ");
    throw new Error(`no ${group} chip "${label}" among ${had}`);
  }
  found.onclick();
}
const lit = group =>
  groups.get(group).filter(chip => chip.classList.contains("on")).map(c => c.textContent);

// ---- what a position looks like on the wire ------------------------------------------------

const MODEL = 2, OTHER = 3, USER = 1;
const SOURCES = { 1: "user", 2: "model:qwen", 3: "model:other" };

/* Round numbers in probability space, so every expectation below is arithmetic and not a
 * constant someone read off a run. */
const P_TOP = 0.6, P_SECOND = 0.25, P_TOOK = 0.1, P_LEAST = 0.02;
const TOP = Math.log(P_TOP), SECOND = Math.log(P_SECOND), TOOK = Math.log(P_TOOK);
const LEAST = Math.log(P_LEAST);
const FLAG = TOP - TOOK;      // = ln 6
const GAP = TOP - SECOND;     // = ln 2.4
const FLOOR = TOP - LEAST;    // = ln 30, the least a censored draw can have paid
const CEILING = 5;            // the flag's fixed domain, in nats

let ids = 0;
const among = (over = {}) =>
  ({ source: MODEL, rows: 5, mass: 0.95, top: TOP, second: SECOND, least: LEAST, ...over });
const node = (over = {}) => ({
  id: ++ids, parent: 0, token: 7, source: MODEL, deleted: null,
  live: true, logprob: TOOK, fork: false, among: [among()], ...over,
});
const cell = (...nodes) => ({ text: "x".repeat(nodes.length), decodes: true, nodes });
/** One segment per node, which is the common case and what most of these ask about. */
const apart = (...nodes) => O.read(nodes.map(one => cell(one)), SOURCES);

// ---- reporting ------------------------------------------------------------------------------

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

// ---- the column a reader has not asked anything of --------------------------------------------

is("nothing is chosen until a reader chooses", [O.asked(), head.textContent],
   [false, "overlay"]);
is("and an unasked column carries no mark at all", O.read([cell(node())], SOURCES), null);

// ---- the flag ----------------------------------------------------------------------------------

tap("measure", "flag");
is("choosing one says so and asks the page to read again", [O.asked(), head.textContent, moved],
   [true, "flag", 1]);

const flagged = apart(node())[0];
is("a drawn token off the top row is a value", flagged.cls, "val");
near("  placed at its flag over the fixed ceiling", flagged.t, FLAG / CEILING);
says("  and saying what it paid", flagged.title, `${FLAG.toFixed(2)} nats`);

// The invariant, not the number: whatever the arithmetic, exactly the token that took the top
// row is the one with nothing to pay.
const took = apart(node({ logprob: TOP }))[0];
is("the token that took the top row is the unflagged one", [took.cls, took.t], ["val", 0]);

// ---- a position with no value is not a position with a low one -----------------------------------

const authored = apart(node({ source: USER, logprob: null }))[0];
const past = apart(node({ logprob: null }))[0];
const two = apart(node({ among: [among(), among({ source: OTHER })] }))[0];
const bare = apart(node({ among: [] }))[0];

is("a token this source did not draw is off the scale", authored.cls, "off");
says("  and says who put it there", authored.title, "user");
is("two sources get no value and no choice between them", two.cls, "clash");
is("a position nothing ranked is not marked at all", bare, null);
is("none of the marks is the foot of the scale, and none is another",
   new Set([authored.cls, past.cls, two.cls, "val"]).size, 4);
is("and nothing without a value carries a place on the scale",
   [authored.t, two.t], [undefined, undefined]);

// ---- a draw past the recorded rows is censored and not missing -------------------------------

/* The rows written are a prefix of the model's, so a token they do not hold sits at or below
 * the lowest of them -- which bounds the flag from one side. Reading that as *no value* throws
 * away the one thing the record does say, and reading it as *a value* claims what it does not. */
is("a draw the rows do not hold is bounded rather than blank", past.cls, "bound");
near("  placed where the rows say it is at least", past.t, FLOOR / CEILING);
says("  and saying it is a floor", past.title, `at least ${FLOOR.toFixed(2)} nats`);
says("  and why there is no more to say", past.title, "fell past the 5 rows recorded");

/* A bound is measured to the last recorded row, so it sits exactly where a draw that *took*
 * that row would sit -- no further, because nothing says how much further, and no nearer,
 * because every recorded row is one the draw did not take. That holds in either reading,
 * which is what makes it the invariant rather than the arithmetic of one of them. */
for (const reading of ["nats", "ratio"]) {
  tap("reading", reading);
  const [limit, last] = apart(node({ logprob: null }), node({ logprob: LEAST }));
  near(`a bound sits where the last recorded row would, read in ${reading}`, limit.t, last.t);
  is(`  and is marked as a bound and not as that value, in ${reading}`,
     [limit.cls, last.cls], ["bound", "val"]);
}

tap("reading", "ratio");
const other = apart(node({ logprob: null }))[0];
says("inverting the space inverts which side the bound is on", other.title, "at most");
says("  and the number is the ratio at the last recorded row", other.title,
     Math.exp(LEAST - TOP).toFixed(3));
tap("reading", "nats");

// ---- the two divisions cross -------------------------------------------------------------------

/* The same position: silent under a draw-relative measure, and priced under a draw-independent
 * one. This is what keeps `draw` a declaration rather than a comment. */
tap("measure", "gap");
const same = apart(node({ source: USER, logprob: null }))[0];
is("a draw-independent measure has a value where the draw did not go", same.cls, "val");
near("  and it is the top row against the next", same.t, (CEILING - GAP) / CEILING);

const thin = apart(node({ among: [among({ rows: 1, second: null })] }))[0];
is("one recorded row leaves the gap with nothing to measure", thin.cls, "hole");
says("  and no bound either, because nothing here is one", thin.title, "no value");

/* A distribution measure marks where work was available, so a pair of rivals is the loud
 * position and one the model had nearly settled is the quiet one. Read the other way round
 * it colours the confident half of a path and looks like it is working, which is what a real
 * tree said before this check existed. */
const rivals = node({ among: [among({ second: Math.log(0.55) })] });
const settled = node({ among: [among({ second: Math.log(0.01) })] });
for (const reading of ["nats", "ratio"]) {
  tap("reading", reading);
  const [close, far] = apart(rivals, settled).map(mark => mark.t);
  is(`two rivals outweigh a settled position, read in ${reading}`, close > far, true);
}
tap("reading", "nats");

// ---- linear against log is a choice on one measure -------------------------------------------

tap("measure", "flag");
const hotter = [P_TOOK, 0.3, 0.55].map(p => node({ logprob: Math.log(p) }));
const inNats = apart(...hotter).map(mark => mark.t);
tap("reading", "ratio");
const inRatio = apart(...hotter).map(mark => mark.t);

is("the reading is named by the measure and not by the scale", lit("reading"), ["ratio"]);
is("two readings do not agree on the number", inNats.map((t, i) => t === inRatio[i]),
   [false, false, false]);
const order = list => list.map((_, i) => i).sort((a, b) => list[a] - list[b]);
is("  and do agree on which position is hottest", order(inNats), order(inRatio));

// ---- fixed before relative -----------------------------------------------------------------

/* A descending reading -- one whose domain runs from high to low -- must keep its polarity
 * when the domain comes from the path. Getting this backwards colours the calmest position as
 * the hottest and nothing else disagrees. */
tap("domain", "path");
const stretched = apart(...hotter).map(mark => mark.t);
is("the path's own range still runs from calm to hot",
   [Math.min(...stretched), Math.max(...stretched)], [0, 1]);
is("  and in the same order as the fixed one", order(stretched), order(inRatio));

tap("reading", "nats");
const short = apart(node({ logprob: TOOK }), node({ logprob: Math.log(0.5) }));
const long = apart(node({ logprob: TOOK }), node({ logprob: Math.log(0.0001) }));
is("a path-relative scale moves with the path it is read over",
   short[0].t === long[0].t, false);

tap("domain", "fixed");
const fixedShort = apart(node({ logprob: TOOK }), node({ logprob: Math.log(0.5) }));
const fixedLong = apart(node({ logprob: TOOK }), node({ logprob: Math.log(0.0001) }));
near("a fixed one means the same thing in both", fixedShort[0].t, FLAG / CEILING);
is("  whatever else the path holds", fixedShort[0].t === fixedLong[0].t, true);

// ---- the unit ---------------------------------------------------------------------------------

const split = O.read([cell(node(), node({ logprob: TOP }))], SOURCES)[0];
is("a span of more than one node is marked and not coloured",
   [split.cls, split.t], ["split", undefined]);
says("  and the breakdown is what it says", split.title, `${FLAG.toFixed(2)} nats`);
says("  for every node in it", split.title, "0.00 nats");

const quiet = O.read([cell(node({ among: [] }), node({ among: [] }))], SOURCES)[0];
is("a span nothing ranked is not a split, because there is nothing to split", quiet, null);

// ---- a depth-bound overlay carries its depth ----------------------------------------------------

const deep = [among({ rows: 2, mass: 0.99 }), among({ rows: 10, mass: 0.88 })];
apart(...deep.map(a => node({ among: [a] })));
is("a robust measure says nothing about depth", words(note).includes("rows"), false);

tap("measure", "mass");
apart(...deep.map(a => node({ among: [a] })));
says("a depth-bound one carries the depths it was computed over", words(note), "2–10 rows");
apart(node({ among: [deep[1]] }), node({ among: [deep[1]] }));
says("  and says so when there is only one of them", words(note), "10 rows throughout");

tap("measure", "none");
is("putting it away leaves the column bare again",
   [O.asked(), head.textContent, words(note)], [false, "overlay", ""]);

console.log(bad ? `\n${bad} failed` : "\nnothing failed");
process.exit(bad ? 1 : 0);
