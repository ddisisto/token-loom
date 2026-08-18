// The finer grain: what else a token could have been.
//
// Potential rather than actual. Nothing in the path is marked as having
// alternatives -- the text reads as text, and any token answers when asked.
// Taking one costs no generation at all, because the alternative was recorded
// when the span was; it is the fastest move the instrument has.
//
// On the path only, never on a card. A card is an alternative not yet taken,
// and the finer grain belongs to text the reader has committed to.

import { api } from './api.mjs';
import { byteOffset, stringIndex } from './path.mjs';

const held = new Map();

/** A span's token overlay, fetched once and kept.
 *
 * Per span and on demand, so nothing is materialised for text nobody
 * interrogates. Safe to keep because a complete span never changes.
 */
async function tokensOf(spanId) {
  if (!held.has(spanId)) held.set(spanId, api.tokens(spanId));
  try {
    return await held.get(spanId);
  } catch (e) {
    held.delete(spanId);
    throw e;
  }
}

/** Which byte of which span a click in the prose landed on.
 *
 * The piece element carries the span it belongs to and the byte it begins at.
 * The browser answers with an offset into the text node, in UTF-16 units, so
 * the piece's own start has to be converted to a string index and the sum
 * converted back to a byte. Doing that inline is right on ASCII and one
 * character out on the first accented word, which is why `path.mjs` owns both
 * halves and this only composes them.
 */
export function addressOf(tree, event) {
  const piece = event.target.closest('.piece');
  if (!piece) return null;
  const units = caretIn(piece, event);
  if (units === null) return null;
  const spanId = piece.dataset.span;
  const from = stringIndex(tree, spanId, Number(piece.dataset.begin));
  return { span: spanId, offset: byteOffset(tree, spanId, from + units) };
}

/** The caret offset within a piece, in UTF-16 units, or null if the click
 * missed its text. Two spellings of one API and no third: a browser with
 * neither cannot resolve a click to a position, and the flyout simply does not
 * open rather than opening on a guess. */
function caretIn(piece, event) {
  if (document.caretPositionFromPoint) {
    const at = document.caretPositionFromPoint(event.clientX, event.clientY);
    if (!at || !piece.contains(at.offsetNode)) return null;
    return at.offset;
  }
  if (document.caretRangeFromPoint) {
    const at = document.caretRangeFromPoint(event.clientX, event.clientY);
    if (!at || !piece.contains(at.startContainer)) return null;
    return at.startOffset;
  }
  return null;
}

/** Draw the flyout for one token beside where it was clicked. */
export function render(host, entry, x, y, { onTake }) {
  host.replaceChildren();
  host.style.left = `${x}px`;
  host.style.top = `${y}px`;
  host.hidden = false;

  const head = document.createElement('div');
  head.className = 'head';
  head.textContent = show(entry.text);
  const lp = document.createElement('span');
  lp.className = 'lp';
  lp.textContent = entry.logprob === null ? '' : entry.logprob.toFixed(2);
  head.append(lp);
  host.append(head);

  if (entry.token_id === null) {
    host.append(note('This character is spelled by several tokens, so the '
      + 'record has one entry for the whole of it and no alternatives to it.'));
    return;
  }
  if (!entry.counterfactuals.length) {
    host.append(note('The model ranked nothing else here.'));
    return;
  }
  for (const c of entry.counterfactuals) {
    const spellable = typeof c.text === 'string';
    const row = document.createElement('button');
    row.className = `alt${spellable ? '' : ' fragment'}`;
    row.disabled = !spellable;
    row.textContent = spellable ? show(c.text) : '⋯';
    const lp2 = document.createElement('span');
    lp2.className = 'lp';
    lp2.textContent = c.logprob === null ? '' : c.logprob.toFixed(2);
    row.append(lp2);
    if (spellable) {
      row.addEventListener('click', () => onTake(c.rank));
    } else {
      // a byte-fallback token is a fragment of a character, and a span of one
      // has no string form. `loom.py` can still take it; the reading surface
      // declines rather than rendering bytes it cannot spell.
      row.title = 'a fragment of a character, which this surface cannot show';
    }
    host.append(row);
  }
}

function note(text) {
  const p = document.createElement('p');
  p.className = 'note';
  p.textContent = text;
  return p;
}

function show(text) {
  if (typeof text !== 'string') return '⋯';
  return text.replace(/\n/g, '⏎').replace(/^ /, '␣');
}

/** The token whose byte extent contains `offset`, or null. */
export async function tokenAt(spanId, offset) {
  const tokens = await tokensOf(spanId);
  return tokens.find((t) => t.begin <= offset && offset < t.end) || null;
}

export function forget() {
  held.clear();
}
