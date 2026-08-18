// What the reader looks at: the path, the margin, and the cards.
//
// Everything here draws; nothing here decides. The derivations are in
// `path.mjs` and the state machine is in `main.mjs`, so this file can be read
// against `INTERACTION.md` one element at a time.
//
// **Every piece of text carries the address it came from.** A `.piece` element
// names its span and the byte it begins at, which is what makes a click in the
// prose resolve to a `(span, offset)` -- `FRONTEND.md` constraint 7, and the
// one property the surface cannot be opened up to accept later. It is here
// rather than left to the flyout because the flyout is the *second* thing that
// needs it and the render is the first.
//
// **The path is laid out once and drawn twice.** One flow, cloned, with the
// two copies clipped to complementary L-shapes and the lower one translated
// down to open a gap for the target. Nothing reflows when the target moves --
// which is not a performance concern but the whole point, since text that
// re-wraps as the reader navigates is text they have to find their place in
// again. `place` below is where that happens, and `path.mjs:clips` is the
// arithmetic behind it.

import {
  activePath, clips, endOf, forks, nodeState, nodeText, pieceText, polygon,
} from './path.mjs';

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

// -- the path --------------------------------------------------------------

/** Draw the active path as one continuous prose flow.
 *
 * **Runs are inline.** A run boundary is where one generation stopped and the
 * next began, and it falls mid-sentence far more often than not -- so a block
 * per run turned a page of prose into a stack of stripes, each starting on its
 * own line for no reason the reader could see. Inline is what makes the joins
 * invisible, which is what `INTERACTION.md` means by reading behind the tip
 * being reading.
 *
 * **No run tinting.** An earlier pass shaded alternate runs, which works on
 * blocks and cannot work on these: an inline background wraps raggedly and
 * reads as highlighter. Nothing is lost -- the margin already says where the
 * forks are.
 *
 * The zero-width `.mark` at each fork is the only thing in the flow that is not
 * text, and it is what `place` measures: `height: 1lh` with `vertical-align:
 * top` makes its rect the *line box*, where the obvious `1em` at the baseline
 * gives the smaller font box and would clip several pixels into the line above
 * and leave a sliver of the one below.
 */
export function renderFlow(host, tree) {
  host.replaceChildren();
  const nodes = activePath(tree);
  const points = forks(tree);
  const forkOf = new Map(points.map((f, i) => [f.node, i]));

  for (const node of nodes) {
    const here = forkOf.has(node) ? forkOf.get(node) : -1;
    if (!node.pieces.length) continue;
    const run = el('span', 'run');
    for (const piece of node.pieces) {
      const text = pieceText(tree, piece);
      if (!text) continue;
      const chunk = el('span', 'piece', text);
      chunk.dataset.span = piece.span;
      chunk.dataset.begin = String(piece.begin);
      run.append(chunk);
    }
    if (here >= 0) {
      const mark = el('i', 'mark');
      mark.dataset.fork = String(here);
      run.append(mark);
    }
    host.append(run);
  }
  return points;
}

/** Copy the flow, clip both halves, and open the gap the target sits in.
 *
 * Returns the vertical displacement, which the margin needs: everything below
 * the target moved by it and the chips have to move with it.
 *
 * The order is forced by what depends on what. The flow must be laid out
 * before the fork can be measured; the band must be positioned and filled
 * before its height is known; and the displacement is a function of that
 * height, so the clips and the stack's own height come last.
 *
 * A target with no mark is the root fork, which has no pieces and so no
 * position in the text. Zero for all three is the right reading of it rather
 * than a fallback: the whole path is below a target at the root.
 */
export function place(parts, targetIndex, { muted }) {
  const { stack, above, below, band } = parts;

  const base = stack.getBoundingClientRect();
  const flow = above.getBoundingClientRect();
  const width = flow.width;
  const height = flow.height;

  let x = 0;
  let lineTop = 0;
  let lineBottom = 0;
  const mark = above.querySelector(`.mark[data-fork="${targetIndex}"]`);
  if (mark) {
    const at = mark.getBoundingClientRect();
    x = at.left - base.left;
    lineTop = at.top - base.top;
    lineBottom = at.bottom - base.top;
  }

  // full width of the page rather than of the column, measured rather than
  // computed in `vw` units, which count the scrollbar and would overflow
  const page = document.documentElement.clientWidth;
  band.style.left = `${-base.left}px`;
  band.style.width = `${page}px`;
  band.style.top = `${lineBottom}px`;
  // the selected card aligns with the path above it, so the strip starts where
  // the reading column does and not where the band does
  band.style.setProperty('--origin', `${base.left}px`);

  const bandHeight = band.getBoundingClientRect().height;
  const shift = (lineBottom - lineTop) + bandHeight;

  const shape = clips({ width, height, x, lineTop, lineBottom });
  above.style.clipPath = polygon(shape.above);
  below.style.clipPath = polygon(shape.below);
  below.style.transform = `translateY(${shift}px)`;
  below.classList.toggle('muted', Boolean(muted));
  stack.style.height = `${height + shift}px`;

  return shift;
}

/** Chips in the margin, one per fork, on the line its fork falls on.
 *
 * Placed after layout rather than during it, because where a fork lands on the
 * page is a fact about the rendered text and not about the tree. Several chips
 * can share a line and sit side by side, which is what a burst of short runs
 * produces.
 *
 * **Read off one copy and displaced.** The marks are measured in the above
 * copy, which is the one that never moves; a fork past the target is drawn by
 * the below copy, which has moved down by `shift`, so its chip moves with it.
 * Measuring each chip in whichever copy displays it would give the same answer
 * and require knowing which that is.
 *
 * The target's own fork gets no chip. It is not a choice already made, and it
 * is already open.
 */
export function renderMargin(host, above, points, active, shift) {
  host.replaceChildren();
  const top = above.getBoundingClientRect().top;
  const lines = new Map();
  for (const mark of above.querySelectorAll('.mark')) {
    const index = Number(mark.dataset.fork);
    if (index === points.length - 1 || index === active) continue;
    const fork = points[index];
    const moved = index > active ? shift : 0;
    const y = Math.round(mark.getBoundingClientRect().top - top + moved);
    const chip = el('button', `chip${index === active ? ' at' : ''}`,
      `⑂${fork.active + 1}/${fork.children.length}`);
    chip.dataset.fork = String(index);
    chip.title = `fork ${index + 1}: alternative ${fork.active + 1} of `
      + `${fork.children.length}`;
    const row = lines.get(y) || [];
    row.push(chip);
    lines.set(y, row);
  }
  for (const [y, row] of lines) {
    const line = el('div', 'chips');
    line.style.top = `${y}px`;
    line.append(...row.slice(0, 5));
    host.append(line);
  }
}

// -- the cards -------------------------------------------------------------

/** The alternatives on offer, one card per run leaving the fork.
 *
 * A card is a run rather than a span, and where an alternative is the
 * remainder of a span that already exists its card begins partway through
 * that span. That is invisible here on purpose: the children of a run node are
 * the cards uniformly, with no case analysis over how each fork came to be.
 *
 * The band takes the full width of the page; a card does not, and stays about
 * half the reading column. Those are two different claims and only the first
 * changed when the target opened out: what expands is the room the sibling
 * stack is given, not the size of any one alternative. The strip slides so the
 * selected card sits at the column's left edge, aligned with the path above
 * it -- the eye should not travel between reading and choosing -- and the extra
 * width is what makes the neighbours legible rather than implied.
 */
export function cardStrip(tree, fork, selected, { growable }) {
  if (!fork) return null;
  const strip = el('div', 'strip');
  fork.children.forEach((node, i) => {
    const state = nodeState(tree, node);
    const card = el('div', `card ${state}${i === selected ? ' on' : ''}`);
    card.dataset.card = String(i);
    if (state === 'ready') {
      card.append(el('div', 'text', nodeText(tree, node)));
    } else if (state === 'flight') {
      card.append(el('div', 'waiting', ''));
      card.title = 'still generating';
    } else {
      card.append(el('div', 'nothing', 'no bytes'));
      card.title = 'this continuation produced nothing at all';
    }
    strip.append(card);
  });
  if (growable) {
    const more = el('div', 'card more');
    more.dataset.grow = '1';
    more.append(el('div', 'nothing', '+'));
    more.title = 'ask for another continuation';
    strip.append(more);
  }
  strip.style.setProperty('--at', String(selected));
  return strip;
}

// -- banners ---------------------------------------------------------------

/** A refusal, in the server's own words, dismissed by the reader.
 *
 * Nothing is retried and nothing is paraphrased. `FRONTEND.md` constraint 12:
 * a prompt that does not fit, a response that lost bytes, and a request with
 * no model server behind it are each reported and dismissed rather than worked
 * around.
 */
export function banner(host, text) {
  const note = el('div', 'banner');
  note.append(el('span', 'says', text));
  const close = el('button', 'dismiss', '×');
  close.addEventListener('click', () => note.remove());
  note.append(close);
  host.append(note);
  return note;
}

export { endOf };
