/* Who put each token where it is, and how far past the model's preference they went.
 *
 * `docs/SPINE.md` allocates a position's displacement whole -- to the operator where a
 * `realise` stands at the node or the source is the reader's own, to the sampler otherwise --
 * so the record answers this exactly and nothing read off a ranking does. It is not an
 * overlay: it has no domain, no second reading and nothing to compare across positions, so it
 * is not in the list a reader chooses a measure from and it is not subject to *An overlay is
 * asked for*.
 *
 * The two axes are not symmetric, and that follows from the allocation rather than from
 * taste. **A `realise` is marked whatever it cost**, because an operator who takes the top
 * row has displaced nothing and still acted -- the bit does not follow from the scalar. A
 * draw is marked only where it diverged, because a sampler that took the argmax displaced
 * nothing and did nothing; marking those would underline the model's own preference.
 *
 * **The scalar rides the same ink as the bit.** Each taker owns a hue and the place on that
 * taker's own scale is handed over as `--m`, so the bit picks the scale and the scalar picks
 * the place on it. Neither scale reaches nothing at its foot: a `realise` of the top row sits
 * at zero and is still an act, so the floor is where a flat colour would have been.
 */

// Two logprobs within this of each other are one row. Backends do not present near-ties in a
// reproducible order, so an exact comparison would call a tie a divergence about half the time.
const TIE = 1e-9;

let on = true;

/** Whether the mark is drawn. Default on: it costs one bounded statement, and a reader
 *  reading prose wants to know which words are theirs whether or not they asked for a
 *  colour over them. The switch is what makes that assessable rather than asserted. */
export const want = value => { on = value; };

/** What the read has to ask for. Only the sampler's half needs the ranking -- a `realise`
 *  and a source are on the wire whatever was asked for -- but the two are one mark and are
 *  drawn together or not at all, so this is the whole of it. */
export const wants = () => on;

/** The ranking this node's own source recorded at this position, or null where there is none
 *  to read from.
 *
 *  Follows `docs/SURFACE.md`'s refusals rather than re-deciding them: a position two sources
 *  ranked has no single answer and one ranked by a source other than this node's says nothing
 *  about this node. A node with no ranking above it was never priced, which is an absence and
 *  not a low value -- `docs/SPINE.md` has why.
 */
const ranking = node => {
  const among = node.among;
  if (!among || among.length !== 1) return null;
  const a = among[0];
  if (a.source !== node.source || a.top === null) return null;
  return a;
};

/** Whether the draw at a node left the model's top row. The bit, and not the scalar: a
 *  displacement too small to see is still a divergence and a tie is still the top row. */
const diverged = node => {
  const a = ranking(node);
  return a !== null && node.logprob !== null && node.logprob < a.top - TIE;
};

/** Whether the reader wrote this token, read off the provenance field and not off a proxy.
 *  `docs/CORE.md` has a `create` naming the source its nodes take, which defaults to the
 *  actor, so a source of kind `user` *is* the reader. What must not be used for this is the
 *  ranked edge: it says what the model thought and never who put the token there. */
const authored = (node, kinds) => kinds?.[String(node.source)] === "user";

/** How far past the model's preference this node's token sits, between 0 and 1, or null
 *  where nothing priced it.
 *
 *  `docs/SPINE.md` has the share as `p(taken)/p(top)` and the displacement as its balance, so
 *  this is `1 - share` and the top row is zero. The balance is to the argmax and not to one,
 *  which is what leaves greedy with a zero to sit at.
 */
const displaced = node => {
  const a = ranking(node);
  if (a === null || node.logprob === null) return null;
  return Math.min(1, Math.max(0, 1 - Math.exp(node.logprob - a.top)));
};

const who = (cls, nodes) =>
  cls === "drew" ? "the sampler left the top row"
    : nodes.some(n => n.realised === true) ? "the reader took this row"
      : "the reader wrote this";

/** One line under a segment: which scale, where on it, and what it says.
 *
 *  **A position nothing ranked draws at the top of the scale and is a placeholder rather than
 *  a reading.** The model offered nothing and the reader supplied all of it, so the top is
 *  where it belongs while nothing is known -- but it carries no information, and `odd` is
 *  what marks it as a value needing handling so the convention does not read as a measurement.
 */
function line(cls, nodes) {
  const places = nodes.map(displaced);
  const odd = places.some(place => place === null);
  // The strongest claim in the segment, for the same reason any node marks the whole of it.
  const t = odd ? 1 : Math.max(...places);
  return {
    cls,
    t,
    odd,
    title: `${who(cls, nodes)} · ` + (odd
      ? "nothing ranked this position, so the line is a placeholder and not a reading"
      : `share ${(1 - t).toFixed(2)} of the top row`),
  };
}

/** What each segment's line says, or null where there is nothing to say about it.
 *
 *  **A segment is marked where any of its nodes is**, because a segment is the addressable
 *  unit and nothing reaches a node inside one -- so a character spelled by three tokens is
 *  the reader's if the reader put any of it there. Only a multi-token character can hold
 *  more than one node, and taking one is a gesture the column does not offer, so a mixed
 *  segment arrives from the command line or not at all.
 *
 *  `kinds` is the source kind by id, as `/path` sends it. Without it the reader's half falls
 *  back to acts alone and authored text draws as the model's, which is what it did before the
 *  column was on the wire.
 *
 *  Returns null when the mark is off, which is the same shape an overlay nobody chose
 *  returns and is what lets the column draw neither.
 */
export function read(segments, kinds) {
  if (!on) return null;
  return segments.map(cell => {
    const mine = cell.nodes.filter(n => n.realised === true || authored(n, kinds));
    if (mine.length) return line("took", mine);
    const drawn = cell.nodes.filter(diverged);
    return drawn.length ? line("drew", drawn) : null;
  });
}
