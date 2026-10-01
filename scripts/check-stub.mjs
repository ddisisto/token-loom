/* Drive the loop that grows a hovered reference arm.  `node scripts/check-stub.mjs`
 *
 * The arithmetic here is small and every piece of it fails quietly. A reach that asked for
 * an increment instead of a length would return a correct-looking arm one burst long for
 * ever; a loop that did not stop at `spent` would ask the same question until the pointer
 * moved; a landing that applied a short answer over a long one would make the text retreat
 * on a slow network and look like the model changing its mind.
 *
 * The three ways of being finished are checked apart, because they are one `null` to the
 * caller and three different things to the reader -- full has more to sell, spent has
 * nothing more to show, and asking is a request already in the air.
 */

import { words } from "./stub-dom.mjs";
import * as stub from "../src/tokenloom/surface/page/assets/stub.js";

// ---- what a read returns ------------------------------------------------------------------

/** `nodes` per cell, so a cell can hold the two halves of one character. */
const cell = (text, nodes = 1) => ({
  text, decodes: true, nodes: Array.from({ length: nodes }, (_, i) => ({ id: i })),
});

/** An answer of `n` tokens, one cell each. `spent` is the record running out first. */
const answer = (n, spent = false) => ({
  segments: Array.from({ length: n }, (_, i) => cell(` t${i}`)), spent,
});

// ---- reporting ------------------------------------------------------------------------------

let bad = 0;
function is(what, got, want) {
  const ok = JSON.stringify(got) === JSON.stringify(want);
  if (!ok) bad += 1;
  console.log(`${ok ? "ok  " : "FAIL"} ${what}: ${JSON.stringify(got)}`
    + (ok ? "" : ` != ${JSON.stringify(want)}`));
}

const fresh = () => stub.forget();

// ---- the length asked for is a length ---------------------------------------------------

fresh();
is("an arm nothing is held for asks for one burst", stub.reach(7), stub.BURST);

/* The whole of why this is a length. `/stub` answers with a prefix, so the second ask is for
 * everything again and a little more -- an implementation that sent the increment would get
 * the first ten tokens back every time and grow for ever without moving. */
stub.landed(7, answer(stub.BURST));
is("and the next ask is for the longer prefix and not for the increment",
  stub.reach(7), stub.BURST * 2);

/* The cap is a cap on the arm and not on the number of asks, so the last one is short. */
fresh();
stub.landed(7, answer(stub.CAP - 3));
is("the last ask is cut to the cap", stub.reach(7), stub.CAP);

fresh();
is("a cap below one burst is still the cap", stub.reach(7, { cap: 4 }), 4);

// ---- the three ways of being finished ----------------------------------------------------

fresh();
stub.landed(7, answer(stub.CAP));
is("a full arm asks for nothing", stub.reach(7), null);
is("and says it is full", [stub.full(7), stub.spent(7)], [true, false]);

/* Spent is the record having no more of this arm. Asking again returns the same answer, so
 * the loop stops -- and this is where whatever spends will take over, which is why it is a
 * state and not just a stopped timer. */
fresh();
stub.landed(7, answer(4, true));
is("a spent arm asks for nothing although it is short", stub.reach(7), null);
is("and says which of the two it was", [stub.full(7), stub.spent(7)], [false, true]);

fresh();
stub.asking(7, true);
is("an arm with a request in the air asks for nothing", stub.reach(7), null);
stub.landed(7, answer(stub.BURST));
is("and asks again once that one lands", stub.reach(7), stub.BURST * 2);

// ---- what is new, and what only looks new ------------------------------------------------

fresh();
let out = stub.landed(7, answer(3));
is("every cell of a first answer is new", [out.cells.length, out.fresh], [3, 0]);

out = stub.landed(7, answer(5));
is("and only the part past what was held is new on the second",
  [out.cells.length, out.fresh], [5, 3]);

/* Counted in nodes rather than cells. Two tokens spelling one character arrive as one cell,
 * so a boundary inside a character would put the count a cell out and animate text that was
 * already on the screen. */
fresh();
stub.landed(7, { segments: [cell("a"), cell("b")], spent: false });
out = stub.landed(7, { segments: [cell("a"), cell("b"), cell("é", 2), cell("c")],
                       spent: false });
is("a cell is new by the nodes before it and not by its place",
  out.fresh, 2);

/* A half-character held from the last answer and completed by this one is not new. The cell
 * changed, and drawing it as arriving would animate a character the reader is already
 * reading. */
fresh();
stub.landed(7, { segments: [cell("a"), cell("�")], spent: false });
out = stub.landed(7, { segments: [cell("a"), cell("é", 2), cell("b")], spent: false });
is("a character completed by this answer is not counted as arriving", out.fresh, 2);

is("the boundary walker stops at the end rather than past it",
  stub.freshFrom([cell("a"), cell("b")], 99), 2);

// ---- an arm only grows -----------------------------------------------------------------

/* A stale short answer landing after a long one. Applying it would shorten the arm on the
 * screen, which reads as the model retracting something rather than as a network. */
fresh();
stub.landed(7, answer(20));
out = stub.landed(7, answer(5));
is("a shorter answer does not shorten the arm", out.cells.length, 20);
is("and nothing of it is drawn as new", out.fresh, 20);

/* But what it says about the record is still true, because `spent` is a fact about the tree
 * and not about how much of it this answer carried. */
fresh();
stub.landed(7, answer(20));
stub.landed(7, answer(5, true));
is("although what it says about the record is taken", stub.spent(7), true);

// ---- what is held, and for how long ------------------------------------------------------

fresh();
stub.landed(7, answer(6));
stub.landed(9, answer(2));
is("arms are held apart by the node they descend from",
  [stub.recall(7).grown, stub.recall(9).grown], [6, 2]);

stub.forget();
is("and dropped together when the record moves under them",
  [stub.recall(7) === undefined, stub.reach(7)], [true, stub.BURST]);

// ---- what it is drawn as ------------------------------------------------------------------

fresh();
stub.landed(7, answer(2));
let arm = stub.draw(stub.landed(7, answer(4)));
is("every cell of the arm is drawn, in order",
  words(arm), " t0  t1  t2  t3");
is("and only what arrived in this answer is marked as arriving",
  arm.children.map(c => c.classList.contains("lands")), [false, false, true, true]);

fresh();
arm = stub.draw(stub.landed(7, { segments: [cell("a"), { ...cell("\ufffd"), decodes: false }],
                                 spent: true }));
is("a cell that spells no character is marked and still shown",
  arm.children.map(c => c.classList.contains("raw")), [false, true]);

is("the arm is one element the caller hangs where it likes", arm.className, "arm");

/* An arm with nothing in it is a position to spend at and not a thing to read, so it draws
 * as nothing rather than as an empty box saying the model was asked. */
fresh();
is("an empty arm is not drawn at all",
  stub.draw(stub.landed(7, { segments: [], spent: true })), null);

console.log(bad ? `\n${bad} failed` : "\nnothing failed");
process.exit(bad ? 1 : 0);
