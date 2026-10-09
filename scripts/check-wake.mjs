/* Drive what a draw leaves in its wake against what it promises.  `node scripts/check-wake.mjs`
 *
 * The page rebuilds while any of this is running, and resumes each animation from a delay
 * computed here -- so the things that must hold are that the arrivals stay in order and inside
 * their span however long the draw, and that a trace resumed later is the same trace further on.
 */

const { STEP, SPAN, RISE, LINGER, lag, arrived, delay, trail } =
  await import(new URL("../src/tokenloom/surface/page/assets/wake.js", import.meta.url));

let bad = 0;
const is = (what, got, want) => {
  const ok = JSON.stringify(got) === JSON.stringify(want);
  if (!ok) bad++;
  console.log(`${ok ? "ok  " : "FAIL"} ${what}: ${JSON.stringify(got)}` +
              (ok ? "" : ` != ${JSON.stringify(want)}`));
};
const near = (a, b) => Math.abs(a - b) < 1e-9;

is("one token arrives at once", [lag(0, 1), arrived(1)], [0, RISE]);
is("  and nothing takes no time", arrived(0), 0);
is("a short draw arrives a step apart", [lag(1, 8), lag(7, 8)], [STEP, 7 * STEP]);
const counts = [2, 8, 21, 64, 256, 400];
is("  and none takes longer than the span to start its last token",
   counts.map(n => lag(n - 1, n) <= SPAN + 1e-9), counts.map(() => true));
is("  which a long draw fills exactly", near(lag(399, 400), SPAN), true);
is("  and every arrival is in order",
   counts.every(n => [...Array(n).keys()].every(i => i === 0 || lag(i, n) > lag(i - 1, n))), true);
is("  and all of it is in by the span and one rise",
   counts.every(n => arrived(n) <= SPAN + RISE + 1e-9), true);
is("  and a longer draw never arrives sooner",
   counts.every((n, i) => i === 0 || arrived(n) >= arrived(counts[i - 1])), true);

const t = { node: 7, born: 1000, hold: 500 };
is("a trace just left holds for the whole of its hold", delay(t, 1000), 500);
is("  and resumed later is the same trace further on",
   [delay(t, 1300), delay(t, 1500), delay(t, 3000)], [200, 0, -1500]);
is("  and is kept while it fades and not after",
   [trail([t], 1000 + 500 + LINGER - 1).length, trail([t], 1000 + 500 + LINGER).length], [1, 0]);
const old = { node: 1, born: 0, hold: 0 }, mid = { node: 2, born: 2000, hold: 300 };
is("a trail drops only what has faded, in the order it was left",
   trail([old, mid, t], LINGER + 100).map(x => x.node), [2, 7]);

process.exit(bad ? 1 : 0);
