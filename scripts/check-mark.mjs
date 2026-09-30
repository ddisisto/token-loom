/* Drive who a segment says put its token there, against nodes as the wire sends them.
 * `node scripts/check-mark.mjs`
 *
 * The mark is one bit read off the acts and one read off a ranking, and both fail quietly.
 * A segment marked as the reader's where the sampler drew it tells the operator they chose
 * something they did not, which is the one thing `docs/SPINE.md` says nothing else in the
 * record can correct -- under drive the two look identical on every quantity a ranking
 * carries. And the asymmetry between the halves is a rule and not an oversight: a `realise`
 * is marked whatever it cost, a draw only where it left the top row, so a test that drove
 * both through one path would pass on an implementation that had collapsed them.
 */

import * as mark from "../src/tokenloom/surface/page/assets/mark.js";

// ---- what a path node looks like on the wire ------------------------------------------------

const MODEL = 2, OTHER = 3;

let next = 100;

/* `logprob` is the node's own value and `among` is the ranking it stood in, which is the
 * parent's -- the wire keys that onto the node because what a column draws is the position
 * the node occupies. `top` is the highest row recorded there. */
const node = (over = {}) => ({
  id: next++, parent: 1, token: 500, source: MODEL, deleted: false, live: true,
  logprob: Math.log(0.5), fork: false, realised: false,
  among: [{ source: MODEL, rows: 4, mass: 0.9, top: Math.log(0.5), second: Math.log(0.2) }],
  ...over,
});

const cell = (...nodes) => ({ text: "x", decodes: true, nodes });

// ---- reporting --------------------------------------------------------------------------------

let bad = 0;
function is(what, got, want) {
  const ok = JSON.stringify(got) === JSON.stringify(want);
  if (!ok) bad += 1;
  console.log(`${ok ? "ok  " : "FAIL"} ${what}: ${JSON.stringify(got)}`
    + (ok ? "" : ` != ${JSON.stringify(want)}`));
}

const of = (...cells) => mark.read(cells);

// ---- the two halves, and why they are not symmetric ------------------------------------------

/* A draw that took the top row displaced nothing and did nothing. Marking it would put a
 * line under the model's own preference, which is most of a cold path. */
is("a draw on the top row is not marked", of(cell(node())), [null]);

is("a draw below it is the sampler's",
  of(cell(node({ logprob: Math.log(0.2) }))), ["drew"]);

/* The other direction. `docs/SPINE.md`: an operator who realises the top row has displaced
 * nothing, pays nothing, and still acted -- the bit does not follow from the scalar. */
is("a realise on the top row is still the reader's",
  of(cell(node({ realised: true }))), ["took"]);

is("and so is one below it",
  of(cell(node({ realised: true, logprob: Math.log(0.2) }))), ["took"]);

/* Both can be true of one node: `(parent, token_id, source)` merges, so a reader can take a
 * row a draw had already taken. The act is what the reader did and outranks what the dice
 * also did, which is the whole reason the mark reads the acts rather than the ranking. */
is("a node both realised and drawn reads as the reader's",
  of(cell(node({ realised: true, logprob: Math.log(0.05) }))), ["took"]);

// ---- what the ranking refuses to answer -------------------------------------------------------

/* An authored token has no ranking above it, so there is no top row it was taken instead of.
 * `docs/SPINE.md` has why that is an absence and not a third state. */
is("a token nothing ranked is not marked",
  of(cell(node({ among: [], logprob: null }))), [null]);
is("and neither is one whose key never came", of(cell(node({ among: undefined }))), [null]);

/* Two sources ranked here and `docs/SURFACE.md` has the surface refuse rather than choose.
 * The mark follows that rather than deciding it again. */
is("a position two sources ranked says nothing",
  of(cell(node({
    logprob: Math.log(0.2),
    among: [
      { source: MODEL, rows: 2, mass: 0.9, top: Math.log(0.5), second: Math.log(0.2) },
      { source: OTHER, rows: 2, mass: 0.9, top: Math.log(0.6), second: Math.log(0.1) },
    ],
  }))), [null]);

/* A ranking by a source other than this node's says nothing about this node's draw. */
is("a ranking from another source is not this one's",
  of(cell(node({
    source: OTHER, logprob: Math.log(0.2),
    among: [{ source: MODEL, rows: 2, mass: 0.9, top: Math.log(0.5), second: Math.log(0.2) }],
  }))), [null]);

/* Backends do not present near-ties in a reproducible order, so the top row and a tie with
 * it are the same row. An exact comparison would call about half of them a divergence. */
is("a tie with the top row is the top row",
  of(cell(node({ logprob: Math.log(0.5) - 1e-12 }))), [null]);

// ---- a segment is the unit, and it may hold several nodes -------------------------------------

/* A character spelled by several tokens is one segment and nothing addresses a node inside
 * it, so the reader's hand anywhere in it is the reader's hand on it. */
is("any node realised marks the segment",
  of(cell(node(), node({ realised: true }), node())), ["took"]);
is("any node diverged marks it as the sampler's",
  of(cell(node(), node({ logprob: Math.log(0.1) }))), ["drew"]);
is("and the reader outranks the sampler within one segment",
  of(cell(node({ logprob: Math.log(0.1) }), node({ realised: true }))), ["took"]);

// ---- the switch ---------------------------------------------------------------------------------

/* Off returns null rather than a row of nulls, which is the shape an overlay nobody chose
 * returns -- so the column draws neither by the same test. */
is("a path carries one answer per segment",
  of(cell(node({ realised: true })), cell(node()), cell(node({ logprob: Math.log(0.1) }))),
  ["took", null, "drew"]);

mark.want(false);
is("off is nothing at all and not a row of nulls",
  of(cell(node({ realised: true }))), null);
is("and the read stops being asked for", mark.wants(), false);
mark.want(true);
is("on again, and it is", mark.wants(), true);

console.log(bad ? `\n${bad} failed` : "\nnothing failed");
process.exit(bad ? 1 : 0);
