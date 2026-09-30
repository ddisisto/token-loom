/* Drive who a segment says put its token there and how far past the model it sits, against
 * nodes as the wire sends them.
 * `node scripts/check-mark.mjs`
 *
 * The mark is one bit read off the acts, one off the provenance field and one off a ranking,
 * and all three fail quietly. A segment marked as the reader's where the sampler drew it
 * tells the operator they chose something they did not, which is the one thing
 * `docs/SPINE.md` says nothing else in the record can correct -- under drive the two look
 * identical on every quantity a ranking carries. And the asymmetry between the halves is a
 * rule and not an oversight: a `realise` is marked whatever it cost, a draw only where it
 * left the top row, so a test that drove both through one path would pass on an
 * implementation that had collapsed them.
 *
 * The scalar is the half nothing else would catch. `--m` is the balance of the share, so the
 * top row is zero and not one, and an inverted ramp reads as a plausible picture of the
 * opposite claim. The arithmetic is computed here rather than eyeballed, since a wrong
 * expected value passes on a wrong implementation.
 */

import * as mark from "../src/tokenloom/surface/page/assets/mark.js";

// ---- what a path node looks like on the wire ------------------------------------------------

const MODEL = 2, OTHER = 3, READER = 1;

// Kinds as `/path` sends them: the provenance field, by source id.
const KINDS = { [MODEL]: "model", [OTHER]: "model", [READER]: "user" };

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

const near = (what, got, want) => is(what, got === null ? null : +got.toFixed(9), want);

const of = (...cells) => mark.read(cells, KINDS);
/** Just the classes, for the checks the scalar is not what is under test. */
const who = (...cells) => mark.read(cells, KINDS).map(m => m && m.cls);
const place = (...cells) => mark.read(cells, KINDS).map(m => m && +m.t.toFixed(9));

// ---- the two halves, and why they are not symmetric ------------------------------------------

/* A draw that took the top row displaced nothing and did nothing. Marking it would put a
 * line under the model's own preference, which is most of a cold path. */
is("a draw on the top row is not marked", who(cell(node())), [null]);

is("a draw below it is the sampler's", who(cell(node({ logprob: Math.log(0.2) }))), ["drew"]);

/* The other direction. `docs/SPINE.md`: an operator who realises the top row has displaced
 * nothing, pays nothing, and still acted -- the bit does not follow from the scalar. */
is("a realise on the top row is still the reader's",
  who(cell(node({ realised: true }))), ["took"]);

is("and so is one below it",
  who(cell(node({ realised: true, logprob: Math.log(0.2) }))), ["took"]);

/* Both can be true of one node: `(parent, token_id, source)` merges, so a reader can take a
 * row a draw had already taken. The act is what the reader did and outranks what the dice
 * also did, which is the whole reason the mark reads the acts rather than the ranking. */
is("a node both realised and drawn reads as the reader's",
  who(cell(node({ realised: true, logprob: Math.log(0.05) }))), ["took"]);

// ---- the reader's own voice --------------------------------------------------------------------

/* `docs/SURFACE.md`: the hue follows the provenance field and not any act's range. A node
 * whose source is of kind `user` is one the reader wrote, whatever was done to it since. */
is("a token the reader wrote is the reader's",
  who(cell(node({ source: READER, among: [], logprob: null }))), ["took"]);

/* And the ranked edge must not stand in for it. A model-sourced token at a position nothing
 * ranked is not the reader's -- the two look alike only while authored positions go
 * unranked, which is exactly the case that would hide the mistake. */
is("a token nothing ranked is not the reader's for that reason alone",
  who(cell(node({ among: [], logprob: null }))), [null]);

/* A reader's token the model did rank is still the reader's, and now it has a value. */
is("an authored token the model ranked is still the reader's",
  who(cell(node({
    source: READER, logprob: Math.log(0.2),
    among: [{ source: READER, rows: 4, mass: 0.9, top: Math.log(0.5), second: Math.log(0.2) }],
  }))), ["took"]);

/* Without the column the reader's half falls back to acts alone, which is what it did before
 * the kinds reached the wire. A page served an older read draws authored text as the
 * model's rather than crashing on it. */
is("with no kinds on the wire an authored token is not marked",
  mark.read([cell(node({ source: READER, among: [], logprob: null }))]).map(m => m && m.cls),
  [null]);

// ---- what the ranking refuses to answer -------------------------------------------------------

is("a token nothing ranked carries no readable place",
  who(cell(node({ among: undefined }))), [null]);

/* Two sources ranked here and `docs/SURFACE.md` has the surface refuse rather than choose.
 * The mark follows that rather than deciding it again. */
is("a position two sources ranked says nothing",
  who(cell(node({
    logprob: Math.log(0.2),
    among: [
      { source: MODEL, rows: 2, mass: 0.9, top: Math.log(0.5), second: Math.log(0.2) },
      { source: OTHER, rows: 2, mass: 0.9, top: Math.log(0.6), second: Math.log(0.1) },
    ],
  }))), [null]);

/* A ranking by a source other than this node's says nothing about this node's draw. */
is("a ranking from another source is not this one's",
  who(cell(node({
    source: OTHER, logprob: Math.log(0.2),
    among: [{ source: MODEL, rows: 2, mass: 0.9, top: Math.log(0.5), second: Math.log(0.2) }],
  }))), [null]);

/* Backends do not present near-ties in a reproducible order, so the top row and a tie with
 * it are the same row. An exact comparison would call about half of them a divergence. */
is("a tie with the top row is the top row",
  who(cell(node({ logprob: Math.log(0.5) - 1e-12 }))), [null]);

// ---- the place on the scale ----------------------------------------------------------------

/* `docs/SPINE.md`: the share is `p(taken)/p(top)` and the displacement is its balance, which
 * is what is drawn. The balance is to the argmax and not to one, so the top row is the foot
 * of the scale and greedy has a zero to sit at. */
near("a realise of the top row sits at the foot of the scale",
  mark.read([cell(node({ realised: true }))], KINDS)[0].t, 0);

near("and a draw a fifth as likely sits four fifths up",
  mark.read([cell(node({ logprob: Math.log(0.1) }))], KINDS)[0].t, 1 - 0.1 / 0.5);

near("the reader's scale is read the same way",
  mark.read([cell(node({ realised: true, logprob: Math.log(0.2) }))], KINDS)[0].t,
  1 - 0.2 / 0.5);

/* A ranked position is never a placeholder, and an unranked one always is. */
is("a ranked line is a reading", mark.read([cell(node({ realised: true }))], KINDS)[0].odd,
  false);
is("an unranked authored line is a placeholder at the top of the scale",
  mark.read([cell(node({ source: READER, among: [], logprob: null }))], KINDS)
    .map(m => [m.t, m.odd]), [[1, true]]);

/* The title carries which of the three the line is, since the appearance no longer can. */
const said = of(cell(node({ source: READER, among: [], logprob: null })),
  cell(node({ realised: true })), cell(node({ logprob: Math.log(0.1) })));
is("and the title says which of the three it is",
  said.map(m => m.title.split(" · ")[0]),
  ["the reader wrote this", "the reader took this row", "the sampler left the top row"]);
is("with the share beside it where there is one",
  said[1].title.split(" · ")[1], "share 1.00 of the top row");

// ---- a segment is the unit, and it may hold several nodes -------------------------------------

/* A character spelled by several tokens is one segment and nothing addresses a node inside
 * it, so the reader's hand anywhere in it is the reader's hand on it. */
is("any node realised marks the segment",
  who(cell(node(), node({ realised: true }), node())), ["took"]);
is("any node diverged marks it as the sampler's",
  who(cell(node(), node({ logprob: Math.log(0.1) }))), ["drew"]);
is("and the reader outranks the sampler within one segment",
  who(cell(node({ logprob: Math.log(0.1) }), node({ realised: true }))), ["took"]);

/* The strongest claim in the segment is what it draws at, for the same reason any node marks
 * the whole of it. Here the marked half is two realises and the further one wins. */
near("the furthest node in a segment is the place it draws at",
  mark.read([cell(node({ realised: true, logprob: Math.log(0.4) }),
    node({ realised: true, logprob: Math.log(0.05) }))], KINDS)[0].t, 1 - 0.05 / 0.5);

/* One unreadable node makes the whole segment unreadable, because part of what the line
 * covers has no value under it and the line cannot say so for half its length. */
is("one unranked node in a segment makes the line a placeholder",
  mark.read([cell(node({ realised: true }), node({ realised: true, among: [], logprob: null }))],
    KINDS).map(m => [m.t, m.odd]), [[1, true]]);

// ---- the switch ---------------------------------------------------------------------------------

/* Off returns null rather than a row of nulls, which is the shape an overlay nobody chose
 * returns -- so the column draws neither by the same test. */
is("a path carries one answer per segment",
  who(cell(node({ realised: true })), cell(node()), cell(node({ logprob: Math.log(0.1) }))),
  ["took", null, "drew"]);
is("and one place per answer",
  place(cell(node({ realised: true })), cell(node()))
    .map(t => t === null ? null : "a number"), ["a number", null]);

mark.want(false);
is("off is nothing at all and not a row of nulls",
  of(cell(node({ realised: true }))), null);
is("and the read stops being asked for", mark.wants(), false);
mark.want(true);
is("on again, and it is", mark.wants(), true);

console.log(bad ? `\n${bad} failed` : "\nnothing failed");
process.exit(bad ? 1 : 0);
