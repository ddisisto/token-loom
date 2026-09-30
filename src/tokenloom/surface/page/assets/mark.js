/* Who put each token where it is.
 *
 * `docs/SPINE.md` allocates a position's displacement whole -- to the operator where a
 * `realise` stands at the node, to the sampler otherwise -- so the record answers this
 * exactly and nothing read off a ranking does. It is not an overlay: it has no domain, no
 * second reading and nothing to compare across positions, so it is not in the list a reader
 * chooses a measure from and it is not subject to *An overlay is asked for*.
 *
 * The two axes are not symmetric, and that follows from the allocation rather than from
 * taste. **A `realise` is marked whatever it cost**, because an operator who takes the top
 * row has displaced nothing and still acted -- the bit does not follow from the scalar. A
 * draw is marked only where it diverged, because a sampler that took the argmax displaced
 * nothing and did nothing; marking those would underline the model's own preference.
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
 *  is on the wire whatever was asked for -- but the two are one mark and are drawn together
 *  or not at all, so this is the whole of it. */
export const wants = () => on;

/** Whether the draw at a node left the model's top row.
 *
 *  Follows `docs/SURFACE.md`'s refusals rather than re-deciding them: a position two sources
 *  ranked has no single answer and one ranked by a source other than this node's says nothing
 *  about this node, so neither is marked. A node with no ranking above it was authored, and
 *  `docs/SPINE.md` has why that is not a third state of this.
 */
const diverged = node => {
  const among = node.among;
  if (!among || among.length !== 1) return false;
  const a = among[0];
  if (a.source !== node.source) return false;
  return node.logprob !== null && a.top !== null && node.logprob < a.top - TIE;
};

/** A class per segment, or null where nothing is to be said about it.
 *
 *  **A segment is marked where any of its nodes is**, because a segment is the addressable
 *  unit and nothing reaches a node inside one -- so a character spelled by three tokens is
 *  the reader's if the reader put any of it there. Only a multi-token character can hold
 *  more than one node, and taking one is a gesture the column does not offer, so a mixed
 *  segment arrives from the command line or not at all.
 *
 *  Returns null when the mark is off, which is the same shape an overlay nobody chose
 *  returns and is what lets the column draw neither.
 */
export function read(segments) {
  if (!on) return null;
  return segments.map(cell =>
    cell.nodes.some(node => node.realised === true) ? "took"
      : cell.nodes.some(diverged) ? "drew"
        : null);
}
