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
