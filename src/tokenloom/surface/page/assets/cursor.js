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

export const node = () => at;

export const place = id => { at = id; };

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
