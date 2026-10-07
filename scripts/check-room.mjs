/* Drive the room below the text against what it promises.  `node scripts/check-room.mjs`
 *
 * The handle's position is a length, and a reader learns the positions -- so the one thing
 * that must hold is that a position says the same length every time, and that the ends draw
 * nothing. Nothing on the page would object to a detent one cell off; the draw would just be
 * a different size than the readout said.
 */

const { PARK, REACH, DETENTS, roomFor, place, NEAR, CLOSE, CALM, CAP, FADE, rate, cue } =
  await import(new URL("../src/tokenloom/surface/page/assets/room.js", import.meta.url));
const { draw } = await import(
  new URL("../src/tokenloom/surface/page/assets/draw.js", import.meta.url));

let bad = 0;
const is = (what, got, want) => {
  const ok = JSON.stringify(got) === JSON.stringify(want);
  if (!ok) bad++;
  console.log(`${ok ? "ok  " : "FAIL"} ${what}: ${JSON.stringify(got)}` +
              (ok ? "" : ` != ${JSON.stringify(want)}`));
};

is("every detent comes to rest where it stands",
   DETENTS.map(n => place(roomFor(n))), DETENTS.map(n => ({ room: roomFor(n), length: n })));

const rooms = DETENTS.map(roomFor);
is("  and inside the band that draws",
   rooms.every(r => r > PARK[0] && r < PARK[1]), true);
const gaps = rooms.slice(1).map((r, i) => r - rooms[i]);
is("  evenly spaced",
   gaps.every(g => Math.abs(g - gaps[0]) < 1e-9), true);

// Every room the hand can ask for, a tenth of a vh apart.
const asked = [];
for (let r = 0; r <= 100; r += 0.1) asked.push(place(r));
is("a handle anywhere rests on a detent or parks",
   asked.every(p => p.length === null || p.room === roomFor(p.length)), true);
const lengths = asked.map(p => p.length).filter(n => n !== null);
is("  and more room is never a shorter draw",
   lengths.every((n, i) => i === 0 || n >= lengths[i - 1]), true);
is("  and reaches every detent", [...new Set(lengths)], DETENTS);

is("the ends park", [place(PARK[0]).length, place(PARK[1]).length], [null, null]);
is("  and a parked handle stays where it was put", place(20).room, 20);
is("  and no closer to an edge than the reach",
   [place(0).room, place(100).room], REACH);
is("just inside either end draws",
   [place(PARK[0] + 0.01).length, place(PARK[1] - 0.01).length],
   [DETENTS[0], DETENTS.at(-1)]);

is("the draw's own length is a detent, so the page opens on one",
   DETENTS.includes(draw().length), true);

// ---- the cue

const near = (a, b) => Math.abs(a - b) < 1e-9;
is("the pulse begins calm and ends at its cap", [rate(NEAR), rate(0)], [CALM, CAP]);
is("  log-spaced, so halfway is the geometric mean",
   near(rate(NEAR / 2), Math.sqrt(CALM * CAP)), true);
const steps = [...Array(201).keys()].map(i => i / 10);
is("  and closing never slows it",
   steps.every((g, i) => i === 0 || rate(g) <= rate(steps[i - 1])), true);
is("the point grows inside the pulse's window and not before it", CLOSE < NEAR, true);

const at = (gap, since, more = {}) => cue({ gap, since, ...more });
is("parked is the point alone, hovered or armed",
   [at(0, 0, { parked: true }), at(0, 0, { parked: true, hover: true }),
    at(0, 0, { parked: true, armed: true })], [null, null, null]);
is("armed is the two met and solid", at(30, 0, { armed: true }),
   { gap: 0, rate: 0, pulse: 0, near: true, close: true });
is("far from the end the two are solid, however recent the movement",
   [at(NEAR + 1, 0).pulse, at(NEAR + 1, 0).near, at(NEAR + 1, 0).close], [0, false, false]);
is("  unless the edge is hovered, which pulses at the calmest",
   [at(NEAR + 20, 1e6, { hover: true }).pulse, at(NEAR + 20, 1e6, { hover: true }).rate],
   [1, CALM]);
is("moving inside the window is the full pulse", at(NEAR / 2, 0).pulse, 1);
is("  and it fades with stillness",
   at(NEAR / 2, FADE / 2).pulse < 1 && at(NEAR / 2, FADE / 2).pulse > 0, true);
is("  and is solid once still, and still shown", at(NEAR / 2, FADE).pulse, 0);
const fading = [0, 300, 600, 900, 1200, 1499].map(t => at(NEAR / 2, t).pulse);
is("  and no moment of stillness brings it back",
   fading.every((p, i) => i === 0 || p <= fading[i - 1]), true);
is("the point grows only within CLOSE",
   [at(CLOSE, 0).close, at(CLOSE + 0.1, 0).close], [true, false]);

process.exit(bad ? 1 : 0);
