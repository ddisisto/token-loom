/* The room below the text, and the length of draw it stands for.
 *
 * Room is in `vh` and is the space under the last line when the page is scrolled to its end,
 * which is also where the line stands when a scroll there draws. The handle at the page's edge
 * sits at `100 - room` from the top, so its line is the line the text will end on.
 *
 * At either end it parks: a scroll draws nothing, and the length is left where it was. Between
 * them the room is one of a few positions, each a fixed length -- log-spaced and not derived
 * from the text beside it, so a position says the same number every time.
 */

/** Parked at or below the first and at or above the second. */
export const PARK = [30, 85];

/** The room the handle can reach, so the last line never leaves the screen. */
export const REACH = [10, 95];

/** The lengths between the parking ends, shortest nearest the foot. */
export const DETENTS = [8, 16, 32, 64, 128, 256];

const CELL = (PARK[1] - PARK[0]) / DETENTS.length;

/** The room a length's detent stands at: the middle of its cell. */
export function roomFor(length) {
  const i = DETENTS.indexOf(length);
  if (i < 0) throw new RangeError(`${length} is not a detent`);
  return PARK[0] + CELL * (i + 0.5);
}

/** Where a handle asked for `room` comes to rest, and the length it means there, or null
 *  where it parks. */
export function place(room) {
  const r = Math.min(REACH[1], Math.max(REACH[0], room));
  if (r <= PARK[0] || r >= PARK[1]) return { room: r, length: null };
  const i = Math.min(DETENTS.length - 1, Math.floor((r - PARK[0]) / CELL));
  return { room: roomFor(DETENTS[i]), length: DETENTS[i] };
}

// ---- the cue ------------------------------------------------------------------------------

/* A scroll at the end draws, and the end is where the last line meets the mark -- so how far
 * the last line still has to rise is how near the draw is. A counter-point stands at the last
 * line's height on the edge, and within `NEAR` of the mark the two pulse against each other,
 * faster as they close; within `CLOSE` the point grows, as it does under the pointer. The
 * pulse follows the reader's movement and dies away once they stop, so a page left near its
 * end shows the two solid rather than pulsing while it is read. */

/** How far below the mark, in `vh`, the pulse begins, and the point grows. */
export const NEAR = 20;
export const CLOSE = 8;

/** Pulses a second where the pulse begins, and where the points meet. The top is held well
 *  under a display's refresh, where a pulse stops reading as one and starts to strobe. */
export const CALM = 1;
export const CAP = 9;

/** ms after the last movement for the pulse to die away. */
export const FADE = 1500;

/** Pulses a second at `gap` below the mark, log-spaced from `CALM` to `CAP`. */
export function rate(gap) {
  const g = Math.min(NEAR, Math.max(0, gap));
  return CALM * (CAP / CALM) ** (1 - g / NEAR);
}

/** What the edge shows, or null for the point alone.
 *
 *  `gap` is how far below the mark the last line stands, `since` the ms since the page last
 *  moved, `hover` whether the pointer is on the edge. `pulse` is how deep the pulsing runs,
 *  from 0 for solid to 1; `near` and `close` are whether the last line is inside each window.
 *
 *  **Parked shows the point alone**, since nothing draws. **Armed shows the two met and
 *  solid**: the next scroll down draws from anywhere, which is the distance already closed.
 *  Hovered pulses wherever the last line is. */
export function cue({ gap, since, hover = false, armed = false, parked = false }) {
  if (parked) return null;
  if (armed) return { gap: 0, rate: 0, pulse: 0, near: true, close: true };
  const g = Math.max(0, gap);
  const near = g <= NEAR;
  const left = Math.max(0, 1 - since / FADE);
  return { gap: g, rate: rate(g), pulse: hover ? 1 : near ? left : 0, near, close: g <= CLOSE };
}
