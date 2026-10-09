/* What a draw leaves in its wake, so a reader who looked away finds their place again.
 *
 * While the draw is asked for, the wait after the caret glows where the text will land. When
 * it lands, the tokens come in one after another in its place and keep the glow until the
 * last of them is in -- then fade, slowly. Draws in quick succession leave one each, so a
 * short trail shows the way the text came.
 *
 * The page is rebuilt on every read, so nothing here is an element. A trace is what a draw
 * brought and when it landed, and what a rebuild needs is how far into its animation each one
 * already is: a negative delay resumes it there, a positive one is still to come.
 */

/** ms between one token's arrival and the next, at most. */
export const STEP = 30;

/** ms the arrivals are spread over, at most, so a long draw is no slower to read than a short
 *  one. */
export const SPAN = 600;

/** ms each token takes to come in. */
export const RISE = 180;

/** ms a trace takes to fade, once the text it led to is all in. */
export const LINGER = 4000;

/** ms after the first token starts that the `i`th of `count` does. */
export function lag(i, count) {
  if (count <= 1) return 0;
  return i * Math.min(STEP, SPAN / (count - 1));
}

/** ms from the first token starting to the last being in. */
export function arrived(count) {
  if (count <= 0) return 0;
  return lag(count - 1, count) + RISE;
}

/** A trace's animation delay at `now`: what it holds lit for, less how long it has been. */
export function delay(trace, now) {
  return trace.hold - (now - trace.born);
}

/** The traces still to be drawn at `now`. */
export function trail(traces, now) {
  return traces.filter(t => now - t.born < t.hold + LINGER);
}
