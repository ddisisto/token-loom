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

  // every run ends in a mark, not only the ones that fork: the section lifted
  // into the band runs from one run's end to the next one's, so `place` needs
  // both edges and only one of them is a fork
  const nodeOf = [];
  nodes.forEach((node, k) => {
    const here = forkOf.has(node) ? forkOf.get(node) : -1;
    if (here >= 0) nodeOf[here] = k;
    if (!node.pieces.length) return;
    const run = el('span', 'run');
    for (const piece of node.pieces) {
      const text = pieceText(tree, piece);
      if (!text) continue;
      const chunk = el('span', 'piece', text);
      chunk.dataset.span = piece.span;
      chunk.dataset.begin = String(piece.begin);
      run.append(chunk);
    }
    const mark = el('i', 'mark');
    mark.dataset.node = String(k);
    if (here >= 0) mark.dataset.fork = String(here);
    run.append(mark);
    host.append(run);
  });
  return { points, nodeOf };
}

/** Clip the two copies, lift the target section out between them, and open
 * the gap the band sits in.
 *
 * Returns the vertical displacement, which the margin needs: everything past
 * the target moved by it and the chips have to move with it.
 *
 * **Three parts, not two.** `head` is where the target's fork falls and above
 * stops; `tail` is where the run leaving that fork ends and below resumes. The
 * section between them is what the band is a cross-section of, and it is drawn
 * by the band alone. Leaving it in the prose as well is what put a verbatim
 * second copy of the selected card directly beneath its own card -- invisible
 * while the path continued past it, and the whole of what was on screen once
 * the chosen branch was a leaf.
 *
 * `head === tail` where nothing has been chosen at the target yet: the path
 * ends at the fork, there is no section to lift, and the two halves tile.
 *
 * The order is forced by what depends on what. The flow must be laid out
 * before the two edges can be measured; the band must be positioned and filled
 * before its height is known; and the displacement is a function of that
 * height, so the clips and the stack's own height come last.
 *
 * A target with no mark is the root fork, which has no pieces and so no
 * position in the text. Zero for all three is the right reading of it rather
 * than a fallback: the whole path lies at or below a target at the root.
 */
export function place(parts, nodeIndex, { muted }) {
  const { stack, above, below, band } = parts;

  const base = stack.getBoundingClientRect();
  const flow = above.getBoundingClientRect();
  const width = flow.width;
  const height = flow.height;

  const edgeAt = (mark) => {
    const at = mark.getBoundingClientRect();
    return {
      x: at.left - base.left,
      lineTop: at.top - base.top,
      lineBottom: at.bottom - base.top,
    };
  };
  const start = above.querySelector(`.mark[data-node="${nodeIndex}"]`);
  const head = start ? edgeAt(start) : { x: 0, lineTop: 0, lineBottom: 0 };
  const next = above.querySelector(`.mark[data-node="${nodeIndex + 1}"]`);
  const tail = next ? edgeAt(next) : head;

  // full width of the page rather than of the column, measured rather than
  // computed in `vw` units, which count the scrollbar and would overflow
  const page = document.documentElement.clientWidth;
  band.style.left = `${-base.left}px`;
  band.style.width = `${page}px`;
  band.style.top = `${head.lineBottom}px`;
  // the selected card aligns with the path above it, so the strip starts where
  // the reading column does and not where the band does
  band.style.setProperty('--origin', `${base.left}px`);

  const bandHeight = band.getBoundingClientRect().height;
  // below resumes directly under the band. Where the lifted section is taller
  // than the band that replaced it this is negative, and below moves *up* --
  // correct, and the reason the stack's height is a max rather than a sum.
  const shift = (head.lineBottom + bandHeight) - tail.lineTop;

  const shape = clips({ width, height, head, tail });
  above.style.clipPath = polygon(shape.above);
  below.style.clipPath = polygon(shape.below);
  below.style.transform = `translateY(${shift}px)`;
  below.classList.toggle('muted', Boolean(muted));
  stack.style.height =
    `${Math.max(head.lineBottom + bandHeight, height + shift)}px`;

  return shift;
}

/** Bring the target into view, and no further.
 *
 * `FRONTEND.md` constraint 6 says the page never moves except as the direct
 * consequence of something the reader did -- so this is called by the acts and
 * never by a poll or a resize. Text arriving must not yank the page; an arrow
 * key that moves the target is the reader asking to go there, and leaving them
 * to chase it down the page by hand is the interface refusing to follow its
 * own cursor.
 *
 * Minimal, and to the nearer edge: already-visible is left alone, and a target
 * taller than the window aligns its top rather than scrolling past its start.
 * The line above the band comes with it, because the text a choice follows
 * from is part of the choice.
 */
export function follow(band, lead) {
  const at = band.getBoundingClientRect();
  const top = at.top - lead;
  const room = window.innerHeight - MARGIN * 2;
  let delta = 0;
  if (at.bottom - top > room || top < MARGIN) delta = top - MARGIN;
  else if (at.bottom > window.innerHeight - MARGIN) {
    delta = at.bottom - (window.innerHeight - MARGIN);
  }
  if (delta) window.scrollBy(0, delta);
}

const MARGIN = 24;

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
  for (const mark of above.querySelectorAll('.mark[data-fork]')) {
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

/** What a card with no bytes says, by why it has none.
 *
 * A continuation that produced nothing is a recorded answer rather than a
 * failure to render, and which answer it is decides what the reader can do
 * next: the model emitting end-of-text is a hard stop at that tip, and an
 * interrupted batch is not. `<|endoftext|>` rather than "no bytes" because
 * anyone working at this level reads it immediately, and because it says why
 * nothing continues from there -- which "no bytes" leaves the reader to
 * discover by pressing down and having nothing happen.
 *
 * The terminator is on the wire for every complete span, so this is read
 * rather than assumed. `length` cannot really produce an empty span and is
 * listed so the map is total against `core/store.py`.
 */
const ENDED = {
  eos: '<|endoftext|>',
  aborted: 'aborted',
  context: 'context full',
  stop: 'stop string',
  length: 'no bytes',
};

const WHY = {
  eos: 'the model emitted end-of-text before anything else: nothing continues '
    + 'from here',
  aborted: 'the batch was interrupted before this continuation produced '
    + 'anything',
  context: 'the path fills the context, so there was no room to generate',
  stop: 'a stop string matched before any bytes were emitted',
  length: 'the call produced no bytes',
};

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
      const held = node.pieces.length ? tree.spans[node.pieces[0].span] : null;
      const why = held ? held.terminator : null;
      card.append(el('div', 'nothing', ENDED[why] || 'no bytes'));
      card.title = WHY[why] || 'this continuation produced nothing at all';
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
