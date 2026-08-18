// The derivations the client owns, and nothing that touches a document.
//
// `CLAUDE.md` says a derived value is the easiest thing to get silently wrong,
// because nothing disagrees with it. Everything in this file is derived, so it
// is kept where `web_test.mjs` can reach it without a browser in the way --
// the same reason `wire.py` holds the rules and the route handlers do not.
//
// Three things here are not obvious and are the reason it is a module rather
// than a handful of helpers in the render:
//
// **Offsets are bytes and strings are UTF-16.** Every `begin`, `end`, `offset`
// and token extent on the wire counts bytes, because bytes are what the format
// anchors on. A JavaScript string counts UTF-16 code units, so slicing one by
// a byte offset is right for ASCII and wrong for the first curly quote a model
// emits. `indexed` builds the conversion both ways, once per span.
//
// **Which child of a fork is on the path is not "the one whose span is on the
// path".** At a counterfactual fork both children can name spans on the path:
// the alternative that was taken, and the remainder of the span it was taken
// from, which is an ancestor of it. What separates them is bytes -- the path
// covers each of its spans from 0 up to where it leaves, and the remainder
// starts exactly where the path left. See `stepsOnto`.
//
// **A run node with no width is a state, not an absence.** It is a span in
// flight or one completed with no bytes, which `core/ops.py:runs` keeps for
// exactly this reason. Cards render them as placeholders.

// -- text ------------------------------------------------------------------

const indexes = new Map();

/** The byte/string conversion for one string, both directions.
 *
 * `strAt[b]` is the string index byte `b` sits at, defined for every byte
 * including the interior ones of a multi-byte character -- those answer with
 * the start of the character they belong to, which is the only useful answer.
 * `byteAt[s]` is the inverse. Both are one longer than what they index, so the
 * end of the text is addressable.
 */
export function indexed(text) {
  const strAt = new Int32Array(byteLength(text) + 1);
  const byteAt = new Int32Array(text.length + 1);
  let b = 0;
  let s = 0;
  for (const ch of text) {
    const n = utf8Length(ch.codePointAt(0));
    for (let k = 0; k < n; k++) strAt[b + k] = s;
    for (let k = 0; k < ch.length; k++) byteAt[s + k] = b;
    b += n;
    s += ch.length;
  }
  strAt[b] = s;
  byteAt[s] = b;
  return { strAt, byteAt, bytes: b };
}

function utf8Length(cp) {
  return cp < 0x80 ? 1 : cp < 0x800 ? 2 : cp < 0x10000 ? 3 : 4;
}

function byteLength(text) {
  let n = 0;
  for (const ch of text) n += utf8Length(ch.codePointAt(0));
  return n;
}

/** A span's text and its conversion, cached.
 *
 * Keyed by id and checked against the text, because a span is immutable once
 * complete but an in-flight one acquires bytes exactly once. Checking is
 * cheaper than being wrong, and the wrong answer here is a stale placeholder
 * that never fills.
 */
export function textOf(tree, spanId) {
  const span = tree.spans[spanId];
  const text = typeof span.text === 'string' ? span.text : '';
  const held = indexes.get(spanId);
  if (held && held.text === text) return held;
  const entry = { text, ...indexed(text) };
  indexes.set(spanId, entry);
  return entry;
}

/** Live spans whose bytes have no string form: `{"b64": ...}` on the wire.
 *
 * The reading surface declines to render these rather than guessing, and says
 * so -- `FRONTEND.md` constraint 12, refusals reach the reader as themselves.
 * The only operation that makes one is branching onto a byte-fallback token,
 * which the flyout does not offer; a tree holding one was made by `loom.py`,
 * where the capability is kept on purpose.
 *
 * Not a decoding failure to work around. A fragment of a character is a real
 * thing to have recorded, and rendering the path would mean decoding across a
 * span boundary and giving up the piece-by-piece addressing everything else
 * here depends on.
 */
export function unrenderable(tree) {
  return Object.keys(tree.live)
    .filter((id) => tree.spans[id].text !== null
      && typeof tree.spans[id].text !== 'string');
}

// -- the path --------------------------------------------------------------

/** The chain of positions from the root down to `pos`, root first.
 *
 * Mirrors `Tree.ancestry`. Each entry names a span and how much of it lies on
 * the path -- so an entry's offset is where the path *leaves* that span, and
 * every span on the path is entered at its own byte 0.
 */
export function ancestry(tree, pos) {
  const chain = [];
  while (pos !== null && pos !== undefined) {
    chain.push(pos);
    pos = tree.spans[pos.span].parent;
  }
  return chain.reverse();
}

/** Where the path leaves each span it passes through, and which span it ends
 * on. Everything below decides by bytes, and this is the byte record. */
export function leaving(tree) {
  const chain = ancestry(tree, tree.selected);
  const leave = Object.create(null);
  for (const p of chain) leave[p.span] = p.offset;
  return { leave, tipSpan: chain.length ? chain[chain.length - 1].span : null };
}

/** Does this run node continue the path?
 *
 * The test is on bytes rather than on span identity, and that is the whole
 * subtlety. After a counterfactual branch the fork's two children are the
 * alternative `c` and the remainder of the span `s` it came from, and both `c`
 * and `s` are on the path -- `s` as the ancestor the path passed through. The
 * path covers `s` over `[0, leave)` and the remainder starts at `leave`, so it
 * covers no byte the path does. That is what separates them.
 *
 * **The rule has to select exactly one child, not merely the right one first.**
 * `core/ops.py:outline` used to emit the resuming branch after the branches
 * leaving the fork, which made "the first child whose span is on the path"
 * right by accident on every tree it produced. It now emits it first -- so
 * that rule would name the span the path *left*, every time. Nothing on the
 * wire promises either order -- `wire.py` sends runs as composition and says
 * so -- and a rule that holds only in the order it was handed breaks the first
 * time anything reorders, which is a thing that has now happened.
 * `web_test.mjs` asserts uniqueness rather than position for exactly that
 * reason, and the naive rule passed every other check in it.
 *
 * The one case bytes cannot separate: the path ends at byte 0 of its tip span,
 * so it covers nothing of it. Then a node starting there is where the reader
 * is, and no sibling can be confused with it -- a sibling would be a different
 * span, and a span the path does not reach is not in the chain at all.
 */
export function continues(node, { leave, tipSpan }) {
  if (!node.pieces.length) return false;
  const piece = node.pieces[0];
  if (!Object.hasOwn(leave, piece.span)) return false;
  const to = leave[piece.span];
  return piece.begin < to
    || (piece.begin === 0 && to === 0 && piece.span === tipSpan);
}

/** The run nodes from the root to where the reader is standing, in order.
 *
 * The first is the whole-tree node `runs` is rooted at, which carries no
 * pieces when the tree has several roots or none. Callers render pieces, so an
 * empty one costs nothing and removing it would make the fork indexing below
 * disagree with the tree it came from.
 */
export function activePath(tree) {
  const where = leaving(tree);
  const nodes = [];
  let node = tree.runs;
  for (;;) {
    nodes.push(node);
    const next = node.children.find((c) => continues(c, where));
    if (!next) return nodes;
    node = next;
  }
}

/** Every fork the path passes through, plus the one it ends at.
 *
 * `active` is the index of the child the path took, or `-1` at the tip, where
 * the children are alternatives on offer rather than choices already made.
 * That is the same structure twice on purpose: `INTERACTION.md` returns the
 * slider to an earlier fork, and the two have to be the same thing for that to
 * be a movement rather than a mode.
 */
export function forks(tree) {
  const nodes = activePath(tree);
  const out = [];
  for (let i = 0; i < nodes.length; i++) {
    const node = nodes[i];
    if (!node.children.length) continue;
    const active = i + 1 < nodes.length ? node.children.indexOf(nodes[i + 1]) : -1;
    out.push({ node, at: endOf(node), children: node.children, active });
  }
  return out;
}

/** The position a run node ends at -- where its fork sits, and where a
 * generation from it attaches. `null` for a node with no pieces at all. */
export function endOf(node) {
  if (!node.pieces.length) return null;
  const last = node.pieces[node.pieces.length - 1];
  return { span: last.span, offset: last.end };
}

// -- reading a node --------------------------------------------------------

/** The text of one piece, sliced by bytes and returned as a string. */
export function pieceText(tree, piece) {
  const { text, strAt } = textOf(tree, piece.span);
  return text.slice(strAt[piece.begin], strAt[piece.end]);
}

/** The text of a whole run node, its pieces in order. */
export function nodeText(tree, node) {
  return node.pieces.map((p) => pieceText(tree, p)).join('');
}

/** What a card should draw: `ready`, `flight`, or `empty`.
 *
 * `flight` and `empty` are both nodes of no width, and they are different
 * answers: one is a placeholder that will fill, the other is a generation that
 * produced nothing and never will. Telling them apart is `complete` on the
 * span, which the wire sends as its own field for exactly this.
 */
export function nodeState(tree, node) {
  if (node.width) return 'ready';
  if (!node.pieces.length) return 'empty';
  return tree.spans[node.pieces[0].span].complete ? 'empty' : 'flight';
}

/** The byte offset a string index inside a span corresponds to. */
export function byteOffset(tree, spanId, strIndex) {
  return textOf(tree, spanId).byteAt[strIndex];
}

/** The string index a byte offset inside a span corresponds to. */
export function stringIndex(tree, spanId, byte) {
  return textOf(tree, spanId).strAt[byte];
}

/** Forget every cached conversion. Tests hold trees that reuse span ids. */
export function forget() {
  indexes.clear();
}

// -- the two clips ---------------------------------------------------------

/** The two shapes the path is drawn through, in pixels.
 *
 * `INTERACTION.md`: the path is laid out once and drawn twice, and the section
 * the reader is standing on is lifted out of the sequence into the card band.
 * So there are three parts and not two -- above stops at `head`, the band holds
 * everything from `head` to `tail`, and below resumes at `tail`. Nothing is
 * drawn twice, which is the point: the selected card *is* that section, and
 * leaving it in the prose as well put a verbatim copy of it directly under its
 * own card.
 *
 * `head === tail` is the case where nothing has been chosen yet -- the path
 * ends at the fork and there is no section to lift. The two shapes then tile
 * the layout exactly, which is what they did before there was a third part.
 *
 * Pure arithmetic on a measurement, which is why it is here rather than in the
 * render: `web_test.mjs` samples the plane and checks that every point falls in
 * the half its position in reading order says it should. A sliver counted twice
 * reads as a bold line and a sliver missed reads as a crack, both at one pixel
 * and neither with anything to disagree with them.
 *
 * **Always six vertices, even when a rectangle would do.** A split on the first
 * or last line makes an edge degenerate, and dropping it would leave the shapes
 * with different point counts at different moments -- `clip-path` interpolates
 * polygons only between equal counts, so a retarget across the first line would
 * jump instead of moving.
 */
export function clips({ width, height, head, tail }) {
  return {
    above: [
      [0, 0], [width, 0], [width, head.lineTop],
      [head.x, head.lineTop], [head.x, head.lineBottom], [0, head.lineBottom],
    ],
    below: [
      [tail.x, tail.lineTop], [width, tail.lineTop], [width, height],
      [0, height], [0, tail.lineBottom], [tail.x, tail.lineBottom],
    ],
  };
}

/** A point list as the CSS function. */
export function polygon(points) {
  return `polygon(${points.map(([x, y]) => `${x}px ${y}px`).join(', ')})`;
}

/** Twice the signed area of a polygon -- the shoelace sum. Tests only, but it
 * lives beside what it checks so the two cannot drift apart. */
export function area(points) {
  let sum = 0;
  for (let i = 0; i < points.length; i++) {
    const [x1, y1] = points[i];
    const [x2, y2] = points[(i + 1) % points.length];
    sum += x1 * y2 - x2 * y1;
  }
  return Math.abs(sum) / 2;
}
