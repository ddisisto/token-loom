/* Drive the caret's rules against segments the page would be given.
 * `node scripts/check-cursor.mjs`
 *
 * What is here is the part that is derived and would otherwise be got quietly wrong: where
 * the caret rests when nobody has placed it, and where a segment puts it when one is chosen.
 * Both are off-by-one in the direction that looks right -- a caret one node late writes into
 * the token the reader meant to reconsider, and a caret at the end of a path that ends
 * mid-character names a position no act can be taken at.
 *
 * Nothing here draws. The caret is built in the column with the rest of the text, and a
 * check that wanted to see it would be asking for a browser.
 */

const C = await import(
  new URL("../src/tokenloom/surface/page/assets/cursor.js", import.meta.url));

// ---- what a path looks like on the wire ----------------------------------------------------

let ids = 0;

/** One segment per node, which is the common case. `over` is what makes it unusual. */
const cell = (over = {}) => {
  const id = ++ids;
  return {
    text: "x", decodes: true,
    nodes: [{ id, parent: id - 1 || null, live: true, ...over }],
    ...(over.decodes === undefined ? {} : { decodes: over.decodes }),
  };
};

/** A run of ordinary segments, parented in a chain as a path's are -- and rooted, since a
 *  path begins at a root and a root hangs from nothing. */
const path = n => Array.from({ length: n }, (_, i) => cell(i === 0 ? { parent: null } : {}));

// ---- reporting -------------------------------------------------------------------------------

let bad = 0;
function is(what, got, want) {
  const ok = JSON.stringify(got) === JSON.stringify(want);
  if (!ok) bad += 1;
  console.log(`${ok ? "ok  " : "FAIL"} ${what}: ${JSON.stringify(got)}`
    + (ok ? "" : ` != ${JSON.stringify(want)}`));
}

// ---- where the caret rests ---------------------------------------------------------------------

const plain = path(4);
is("with nothing pointed at, the caret rests at the end of the path",
   C.resting(plain), plain.at(-1).nodes[0].id);
is("and a path with nothing in it leaves it nowhere", C.resting([]), null);

/* A path may end mid-character, and those trailing bytes are a position no act can be taken
 * at: the backend will not evaluate a prompt ending inside one. The caret stops short of
 * them, which is the whole reason this is not simply the leaf. */
const ragged = [...path(3), cell({ decodes: false })];
is("trailing bytes waiting for their character are not where the caret rests",
   C.resting(ragged), ragged[2].nodes[0].id);

/* What is set aside is drawn to be read and to be brought back, not to be written under, so
 * the caret does not follow a path into it. It is always a suffix, the rule taking the live
 * path first. */
const pruned = [...path(2), cell({ live: false }), cell({ live: false })];
is("and neither is anything set aside", C.resting(pruned), pruned[1].nodes[0].id);
is("a path that is set aside throughout leaves the caret nowhere",
   C.resting([cell({ live: false })]), null);

/* A segment is set aside if any of its nodes is -- it cannot be split, so a character
 * spelled across the boundary goes with the part that is hidden. */
const split = { text: "⚕", decodes: true, nodes: [
  { id: 900, parent: 899, live: true }, { id: 901, parent: 900, live: false }] };
const upto = path(2);
is("a segment holding one node that is set aside is set aside", C.aside(split), true);
is("  so the caret does not rest inside it", C.resting([...upto, split]),
   upto.at(-1).nodes[0].id);

// ---- where pointing puts it ----------------------------------------------------------------------

/* The caret lands *before* the segment pointed at, which is the node its first token hangs
 * from. So what a reader points at is the token they are reconsidering, and the caret sits
 * where an alternative to it would -- which is the node whose ranking holds that alternative.
 */
const four = path(4);
is("pointing at a segment puts the caret before it",
   C.chosen(four, 2), four[1].nodes[0].id);
is("  which is one node back and never the one pointed at",
   C.chosen(four, 2) === four[2].nodes[0].id, false);

is("the first segment of a path has nothing before it, so the caret stays put",
   C.chosen(four, 0), null);
is("and so does pointing past the end", C.chosen(four, 9), null);
is("nothing acts under what is set aside, so pointing there stays put too",
   C.chosen(pruned, 2), null);

/* A multi-token character is one segment and cannot be split, so the caret lands before the
 * whole of it rather than between its tokens. */
const wide = { text: "⚕", decodes: true, nodes: [
  { id: 800, parent: 42, live: true }, { id: 801, parent: 800, live: true }] };
is("a character spelled by several tokens takes the caret before all of them",
   C.chosen([wide], 0), 42);

// ---- following the window ---------------------------------------------------------------------

/* The gesture that asks for a draw is the scroll and the draw lands at the caret, so a caret
 * scrolled off the screen aims an act at a position nobody is looking at. What is derived here
 * is which seat the window leaves it on, and it is wrong in three directions that all look
 * right: one that lands on a seat no act can be taken at, one that drags a caret the reader
 * placed on purpose, and one that draws at the top of the last screenful of a page the reader
 * scrolled to the foot of.
 *
 * The geometry belongs to the page. What arrives is where each segment stands: above the
 * window, inside it, or below.
 */
const band = (from, to) => i => (i < from ? -1 : i > to ? 1 : 0);

const nine = path(9);
const idAt = i => nine[i].nodes[0].id;

/* Pointing somewhere is deliberate and a scroll is not a retraction of it. */
is("a caret already in the window does not move",
   C.seated(nine, idAt(4), band(2, 6)), idAt(4));
is("  even where it is the very first thing shown",
   C.seated(nine, idAt(2), band(2, 6)), idAt(2));

/* A caret nobody has placed follows the end of the path and not the window. The gesture that
 * draws at it needs the foot of the page, where the end of the path is on the screen anyway,
 * so there is nothing to rescue -- and dragging it would turn *left alone it follows the end*
 * into *it follows whatever is on the screen*, which is a different rule. */
is("a caret at rest stays at the end of the path, however far off the screen that is",
   C.seated(nine, idAt(8), band(0, 3)), idAt(8));
is("  and it is the resting seat and not the last cell that is exempt",
   C.seated(ragged, ragged[2].nodes[0].id, band(0, 1)), ragged[2].nodes[0].id);

/* The edge it belongs against is the one the reader has read down to, which at the end of the
 * page is the end of the path -- and that is what the scroll gesture there has always meant.
 * The nearest seat on the way down would be the first in the window, which draws at the top of
 * the screenful the reader is looking at the bottom of. */
is("one scrolled off the top comes back to the last whole segment shown",
   C.seated(nine, idAt(0), band(3, 7)), idAt(7));
is("and one placed below it comes back to the same place",
   C.seated(nine, idAt(7), band(1, 5)), idAt(5));

/* The seats are the ones an act can be taken at, which is the same rule the resting position
 * follows -- a window showing trailing bytes offers nowhere the backend will evaluate. */
const ragged2 = [...path(4), cell({ decodes: false })];
is("trailing bytes at the foot of the window are not the seat",
   C.seated(ragged2, ragged2[0].nodes[0].id, band(3, 4)), ragged2[3].nodes[0].id);
is("  and a window holding nothing else has none at all",
   C.seated(ragged2, ragged2[0].nodes[0].id, band(4, 4)), null);
const shut = [...path(2), cell({ live: false }), cell({ live: false })];
is("what is set aside is not a seat either",
   C.seated(shut, shut[0].nodes[0].id, band(2, 3)), null);

/* Null and not a guess. A window showing no whole segment leaves the caret where it was,
 * which is wrong in a way the reader can see and fix. */
is("a window with nothing whole in it moves nothing", C.seated(nine, idAt(4), () => -1), null);
is("and so does a path with nothing in it", C.seated([], null, band(0, 9)), null);

/* A caret that is not on what is drawn at all -- taking a row lands it wherever the row went,
 * which need not be a seat on this path. */
is("a caret that is nowhere on the path is seated like one that has left the window",
   C.seated(nine, 99999, band(4, 8)), idAt(8));

// ---- what is held ---------------------------------------------------------------------------------

is("nothing is pointed at before a tree is read", C.node(), null);
C.place(17);
is("and what is placed is what is held", C.node(), 17);
C.place(null);
is("putting it nowhere is a place too", C.node(), null);

/* Arming is the one state in which reading on writes: the next scroll down asks for a draw
 * wherever the page is standing, rather than at the end where arriving is what makes the
 * gesture deliberate. So nothing may arm it but the act that earns it, and anything that
 * moves what a draw would land on has to clear it -- an arming made against the old position
 * is a write at the new one that the reader never asked for.
 */
is("a caret is not armed until something arms it", C.armed(), false);
C.place(17);
C.arm();
is("and the act that earns it is what does", C.armed(), true);
C.place(18);
is("moving it disarms, because what a draw would land on has moved", C.armed(), false);

/* A read places the caret every time, so a page that redraws itself is a page that has
 * disarmed -- which is what keeps the state from outliving the act it came from. */
C.arm();
C.place(18);
is("and placing it where it already was disarms just the same", C.armed(), false);

/* Nowhere is not somewhere to draw from, so arming there is not a thing that can be true. */
C.place(null);
C.arm();
is("a caret that is nowhere cannot be armed", C.armed(), false);

console.log(bad ? `\n${bad} failed` : "\nnothing failed");
process.exit(bad ? 1 : 0);
