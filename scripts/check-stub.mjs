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

// ---- the length asked for is a length -----------------------------------------------

fresh();
is("an arm nothing is held for asks for the whole cap", stub.reach(7), stub.CAP);
is("and a cap given at the call is the one used", stub.reach(7, { cap: 4 }), 4);

/* The whole of why this is a length. `/stub` answers with a prefix, so an implementation
 * that sent an increment would ask for the same first tokens every time. */
stub.landed(7, answer(stub.CAP));
is("an arm read to the cap asks for nothing more", stub.reach(7), null);

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
stub.landed(7, answer(4));
is("and asks once that one lands and came up short", stub.reach(7), stub.CAP);

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
  [stub.recall(7) === undefined, stub.reach(7)], [true, stub.CAP]);

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

is("the arm is one element the caller hangs where it likes",
  arm.classList.contains("arm"), true);

/* An arm read whole is one gesture and unfurls; an arm added to animates only its tail, so
 * the two never both run and a reader never sees settled text move. */
fresh();
is("an arm read whole unfurls",
  stub.draw(stub.landed(7, answer(3))).classList.contains("unfurl"), true);
let grown = stub.draw(stub.landed(7, answer(6)));
is("an arm added to does not unfurl again", grown.classList.contains("unfurl"), false);
is("and marks only its tail as arriving",
  grown.children.map(c => c.classList.contains("lands")),
  [false, false, false, true, true, true]);

/* A newline is escaped, not obeyed. One real break would move every row below it, and the
 * panel holding still is what this stage is for. */
fresh();
is("a newline in an arm is shown and not obeyed",
  words(stub.draw(stub.landed(7, { segments: [cell("a\nb")], spent: true }))), "a\\nb");

// ---- the price, which is what the pulse says -------------------------------------------

/* A row with nothing under it needs no read to be known costly: nothing was ever grown
 * there, so every token of an arm from it would have to be made. */
is("a row with no node under it is costly", stub.costly(null), true);

fresh();
is("an arm nobody has read is not yet costly", stub.costly(7), false);

stub.landed(7, answer(stub.CAP));
is("an arm the record carries to the cap is free", stub.costly(7), false);

fresh();
stub.landed(7, answer(5, true));
is("an arm the record runs out of is costly", stub.costly(7), true);

fresh();
stub.landed(7, answer(stub.CAP, true));
is("but one that ran out exactly at the cap is not, there being no room to spend",
  stub.costly(7), false);

/* An arm with nothing in it is a position to spend at and not a thing to read, so it draws
 * as nothing rather than as an empty box saying the model was asked. */
fresh();
is("an empty arm is not drawn at all",
  stub.draw(stub.landed(7, { segments: [], spent: true })), null);

console.log(bad ? `\n${bad} failed` : "\nnothing failed");
process.exit(bad ? 1 : 0);
