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

import {
  activePath, endOf, forks, nodeState, nodeText, pieceText,
} from './path.mjs';

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

// -- the path --------------------------------------------------------------

/** Draw the active path as continuous prose, with the cards in their place.
 *
 * Runs are tinted alternately rather than ruled off. The boundary is drawn at
 * runs because a run boundary is where a choice was made, which is what a
 * reader scanning back is looking for -- and it coincides with a span boundary
 * everywhere except inside a fork, where the span boundary would be noise.
 *
 * **The card strip is inserted where its fork sits, not below the path.** The
 * surface is one sequence read downwards with a cross-section opened at the
 * position the reader is standing on: what is above is what has been read, what
 * is below is what continues, and the alternatives lie across. A strip pinned
 * to the foot of the page instead put the choice arbitrarily far from the text
 * it belonged to -- going back to an early fork left the cards off-screen
 * entirely -- and broke the symmetry the whole interaction is, which is that
 * confirming folds a cross-section into the sequence and going back opens one
 * out of it.
 *
 * `mutedFrom` is the fork the reader has come back to; everything after it is
 * what they are about to leave, and is dimmed rather than removed. Nothing has
 * been lost at that point and the render should not suggest otherwise.
 */
export function renderPath(host, tree, { mutedFrom = -1, strip = null } = {}) {
  host.replaceChildren();
  const nodes = activePath(tree);
  const points = forks(tree);
  const forkOf = new Map(points.map((f, i) => [f.node, i]));
  const openAt = mutedFrom >= 0 ? mutedFrom : points.length - 1;

  let muted = false;
  nodes.forEach((node, i) => {
    const here = forkOf.has(node) ? forkOf.get(node) : -1;
    if (node.pieces.length) {
      const run = el('div', `run ${i % 2 ? 'odd' : 'even'}${muted ? ' muted' : ''}`);
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
    if (here >= 0 && here === openAt && strip) host.append(strip);
    if (here >= 0 && here === mutedFrom) muted = true;
  });
  return points;
}

/** Chips in the margin, one per fork, on the line its fork falls on.
 *
 * Placed after layout rather than during it, because where a fork lands on the
 * page is a fact about the rendered text and not about the tree. Several chips
 * can share a line and sit side by side, which is what a burst of short runs
 * produces.
 *
 * The tip's fork gets no chip. It is not a choice already made, and the card
 * slider is already showing it.
 */
export function renderMargin(host, column, points, active) {
  host.replaceChildren();
  const top = column.getBoundingClientRect().top;
  const lines = new Map();
  for (const mark of column.querySelectorAll('.mark')) {
    const index = Number(mark.dataset.fork);
    if (index === points.length - 1) continue;
    const fork = points[index];
    const y = Math.round(mark.getBoundingClientRect().top - top);
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
 * The strip slides so the selected card sits at the left edge, aligned with
 * the path above it -- the eye should not have to travel between reading and
 * choosing.
 */
export function cardStrip(tree, fork, selected, { growable }) {
  if (!fork) return null;
  const slice = el('div', 'slice');
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
  slice.append(strip);
  return slice;
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
