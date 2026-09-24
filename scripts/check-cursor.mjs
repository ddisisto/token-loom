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

// ---- what is held ---------------------------------------------------------------------------------

is("nothing is pointed at before a tree is read", C.node(), null);
C.place(17);
is("and what is placed is what is held", C.node(), 17);
C.place(null);
is("putting it nowhere is a place too", C.node(), null);

console.log(bad ? `\n${bad} failed` : "\nnothing failed");
process.exit(bad ? 1 : 0);
