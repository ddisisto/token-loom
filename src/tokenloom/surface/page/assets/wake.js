/* What a draw leaves in its wake, so a reader who looked away finds their place again.
 *
 * While a draw is asked for, a placeholder stands after the caret for each token it may bring,
 * so a longer draw is a longer row of them and a longer wait. When it lands, its segments take
 * the placeholders over one after another, pushing what is left of the row ahead of them; a
 * draw cut short leaves some over, and they go when the last segment is in. The whole run
 * glows until `AFTER` past that, sinks to `DIM` over `DECAY`, and goes out over `WINK`. Draws
 * in quick succession leave one each, so a short trail shows the way the text came.
 *
 * The page is rebuilt on every read, so nothing here is an element. A trace is what a draw
 * brought and when it landed, and what a rebuild needs is how far along each one already is.
 */

/** ms between one segment's arrival and the next, at most. */
export const STEP = 30;

/** ms the arrivals are spread over, at most, so a long draw is no slower to read than a short
 *  one. */
export const SPAN = 600;

/** ms each segment takes to come in. */
export const RISE = 180;

/** ms the run stays lit once its last segment is in. */
export const AFTER = 1000;

/** ms it takes to sink to `DIM` of its glow, and then to go out from there. */
export const DECAY = 4000;
export const DIM = 0.25;
export const WINK = 250;

/** ms after the first segment starts that the `i`th of `count` does. */
export function lag(i, count) {
  if (count <= 1) return 0;
  return i * Math.min(STEP, SPAN / (count - 1));
}

/** ms from the first segment starting to the last being in. */
export function arrived(count) {
  if (count <= 0) return 0;
  return lag(count - 1, count) + RISE;
}

/** How many of `count` segments have started `since` ms after landing. */
export function shown(since, count) {
  if (count <= 0 || since < 0) return 0;
  if (count === 1) return 1;
  return Math.min(count, Math.floor(since / lag(1, count) + 1e-9) + 1);
}

/** How many placeholders stand ahead of `tokens` arrived of a draw asked for `length`. */
export function tail(length, tokens) {
  return Math.max(0, length - tokens);
}

/** ms a run of `count` segments stays fully lit from landing: through its arrival, unless
 *  it arrives at once, and `AFTER` beyond. */
export function hold(count, still = false) {
  return (still ? 0 : arrived(count)) + AFTER;
}

/** How long a trace has until it starts to sink, at `now`, negative once it has. */
export function delay(trace, now) {
  return trace.hold - (now - trace.born);
}

/** The traces still to be drawn at `now`. */
export function trail(traces, now) {
  return traces.filter(t => now - t.born < t.hold + DECAY + WINK);
}
