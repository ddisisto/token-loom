/* Where the reader is pointing, and where they may point.
 *
 * The caret sits *after* a node, so the node is what names it -- and that node is the anchor
 * every act and every question at a position takes. `docs/SURFACE.md` has selecting a token
 * asking what else was live at that position, which is the ranking at its *parent*; a caret
 * before a segment sits at exactly that parent, so the ranking to open there, the sibling a
 * `realise` would make and the branch a draw from here would start are one node and not
 * three.
 *
 * It is the page's one piece of reader state. What path is drawn, where a write lands and
 * what a ranking would be asked about are all derived from it, because a second node held
 * beside it is a second thing that can disagree.
 *
 * Nothing here draws. The caret is built in the column with the rest of the text, and what
 * this answers is the part that is derived and would otherwise be got quietly wrong: where
 * the caret rests when nobody has placed it, and where a segment puts it when one is chosen.
 */

/** A segment is set aside if any of its nodes is. It cannot be split, so a character spelled
 *  across the boundary goes with the part that is hidden. */
export const aside = cell => cell.nodes.some(n => !n.live);

let at = null;
let waiting = false;

export const node = () => at;

/** Put the caret somewhere. It disarms: what a draw would land on has just moved, so an
 *  arming made against the old position is a write the reader did not ask for at the new
 *  one. Only `arm` sets it, and only after the act that earned it. */
export const place = id => { at = id; waiting = false; };

/** Arm the caret: the next scroll down asks for a draw here, wherever the page is standing.
 *
 *  The ordinary gesture is the end of the page, which is a place the reader has to arrive at
 *  and can therefore mean. This one has no such place, so what makes it deliberate is that
 *  it is only ever set by a click on something in view -- `realise` is the act that sets it,
 *  and the row clicked to make it was drawn where the reader was looking.
 *
 *  It survives exactly until something happens: the draw, or the caret moving, or any read
 *  that places the caret again. So a page left alone is never a page that will write.
 */
export const arm = () => { waiting = at !== null; };

export const armed = () => waiting;

/** Where the caret rests when nothing has placed it: after the last segment that has a
 *  string form and is not set aside.
 *
 *  Not simply the leaf. A path may end mid-character, and those trailing bytes are a position
 *  no act can be taken at -- the backend will not evaluate a prompt that ends inside one, and
 *  a draw that repeated them would merge onto the same nodes. A path may also carry on past
 *  its live leaf when what is set aside is shown, and the caret does not follow it there:
 *  what is hidden is drawn to be read and to be brought back, not to be written under.
 */
export function resting(cells) {
  for (let i = cells.length - 1; i >= 0; i -= 1) {
    if (cells[i].decodes && !aside(cells[i])) return cells[i].nodes.at(-1).id;
  }
  return null;
}

/** Where the window seats the caret, given where each segment stands in it.
 *
 *  `place` answers -1, 0 or 1 for a segment above the band the window leaves for it, inside
 *  it, or below. The band and not the window: a caret hard against an edge is one the reader
 *  has to hunt for, and the line it marks is worth a line of context either side. Where that
 *  band is drawn is the caller's, because this file has no DOM -- what is here is the part
 *  that goes quietly wrong.
 *
 *  A caret off the screen is a caret the reader cannot see a draw land on, and the gesture
 *  that asks for one is the scroll -- so scrolling away from it would aim an act at a
 *  position nobody is looking at. Following the window is what makes *the draw lands where
 *  you are looking* true rather than usually true.
 *
 *  **A caret already in the window does not move.** Pointing somewhere is deliberate and a
 *  scroll is not a retraction of it, so this rescues a caret that has left rather than
 *  dragging one that has not.
 *
 *  **Neither does one at rest.** A caret nobody has placed follows the end of the path and
 *  not the window -- that is the batch discipline and not a default, and the gesture that
 *  draws at it needs the foot of the page, where the end of the path is on the screen anyway.
 *  So a reader who has pointed at nothing scrolls without moving anything, and the one who
 *  has keeps a caret they can see. Resting is read from the path rather than remembered,
 *  which is why it cannot fall out of step with where the caret actually is.
 *
 *  **What it lands on is the last whole segment, and not the nearest one.** Two reasons, and
 *  they are the same reason: the caret is the frontier of what has been read, so the edge it
 *  belongs against is the one the reader has read down to -- and at the end of the page that
 *  edge is the end of the path, which is what the scroll gesture there has always meant. The
 *  nearest seat would be the first in the window on the way down, which would draw thousands
 *  of tokens above the foot of a page the reader scrolled to the foot of, and would subdue
 *  every line they were looking at.
 *
 *  Null where there is nowhere: a window showing no whole segment, or showing only what is
 *  set aside or waiting for its character. The caret then stays where it was, which is wrong
 *  in a way the reader can see and fix, rather than moving somewhere no act can be taken.
 */
export function seated(cells, node, place) {
  if (node === resting(cells)) return node;
  const at = cells.findIndex(cell => cell.nodes.at(-1).id === node);
  if (at >= 0 && place(at) === 0) return node;
  for (let i = cells.length - 1; i >= 0; i -= 1) {
    if (place(i) === 0 && cells[i].decodes && !aside(cells[i])) return cells[i].nodes.at(-1).id;
  }
  return null;
}

/** Where choosing a segment puts the caret: immediately before it, which is the node its
 *  first token hangs from.
 *
 *  So what a reader points at is the token they are reconsidering, and the caret lands where
 *  an alternative to it would. The first segment of a path has nothing before it -- a root
 *  hangs from no node -- and neither has anything set aside, so both answer null and the
 *  caret stays where it was.
 */
export function chosen(cells, i) {
  const cell = cells[i];
  if (!cell || aside(cell)) return null;
  return cell.nodes[0].parent ?? null;
}
