/* Drive the draw panel against a stub DOM.  `node scripts/check-draw.mjs`
 *
 * What it is here for first is the pair `record_rows` and `top_k`, which must not be able to
 * disagree. Nothing on the page objects if they do: the gesture that generates is a scroll,
 * so an invalid pair is not caught on the way out, and the adapter's refusal is *recorded* --
 * which means the browser reports this bug by writing an act into the store. It found one
 * the first time it ran, in the direction a toggle moves.
 *
 * Second is what a position along a line means: every parameter is set by where a point
 * stands, so a scale read from the wrong end, an idle end that sends a value, or a round trip
 * that drifts is a draw asked for something other than what the line shows.
 *
 * The stub is `stub-dom.mjs`, which the overlay's check drives too. It is not a test harness
 * for the page, and the reading column is not driven from here.
 */

import { El, words } from "./stub-dom.mjs";

const { draw, keep, panel, set, share, along, place, said, IDLE } = await import(
  new URL("../src/tokenloom/surface/page/assets/draw.js", import.meta.url));

const shown = panel();
const names = [];
const walk = node => {
  if (!(node instanceof El)) return;
  if (node.className === "name") names.push(node.textContent);
  node.children.forEach(walk);
};
walk(shown);

let bad = 0;
const is = (what, got, want) => {
  const ok = JSON.stringify(got) === JSON.stringify(want);
  if (!ok) bad++;
  console.log(`${ok ? "ok  " : "FAIL"} ${what}: ${JSON.stringify(got)}` +
              (ok ? "" : ` != ${JSON.stringify(want)}`));
};
const covered = () => !("top_k" in draw()) || draw().record_rows >= draw().top_k;
// The position a value stands at, found by asking the line rather than inverting it here.
const shareOf = (key, value) => {
  for (let i = 0; i <= 10000; i++) if (along(key, i / 10000) === value) return i / 10000;
  throw new Error(`${value} is nowhere along ${key}`);
};
const to = (key, value) => place(key, shareOf(key, value));

is("the defaults are the required five and the floor heat needs", draw(),
   { length: 64, temperature: 0, min_p: 0.02,
     record_rows: 10, record_mass: 0.9, cache_prompt: true });
is("  and a draw keeps none of the chain", "min_p" in keep(), false);
is("the panel shows what is not set elsewhere, in order", names,
   ["top_k", "top_p", "min_p", "record_rows", "record_mass", "cache_prompt"]);
is("no reader asks for a seed, so no control offers one", words(shown).includes("seed"), false);

// ---- the lines

const grid = [...Array(1001).keys()].map(i => i / 1000);
for (const key of ["top_k", "top_p", "min_p", "record_rows", "record_mass", "temperature"]) {
  const values = grid.map(s => along(key, s)).filter(v => v !== null);
  is(`${key}: further along is never less`,
     values.every((v, i) => i === 0 || v >= values[i - 1]), true);
  is("  and every value it reaches stands where it is reached",
     [...new Set(values)].every(v => { set(key, v); return along(key, share(key)) === v; }), true);
}

is("the idle ends are where nothing is done",
   [along("min_p", 0), along("top_p", 1), along("top_k", 1), along("record_mass", 1)],
   [null, null, null, null]);
is("  and just inside them is the line's own end",
   [along("min_p", IDLE), along("top_p", 1 - IDLE), along("top_k", 1 - IDLE),
    along("record_mass", 1 - IDLE)], [0.005, 0.995, 50, 0.995]);
is("lines without an idle end reach both ends",
   [along("temperature", 0), along("temperature", 1), along("record_rows", 0),
    along("record_rows", 1)], [0, 2.5, 2, 50]);

is("min_p is fine near the bottom: 0.01 to 0.02 is longer than 0.4 to 0.5",
   shareOf("min_p", 0.02) - shareOf("min_p", 0.01) > shareOf("min_p", 0.5) - shareOf("min_p", 0.4),
   true);
is("a mass is fine near the top: 0.95 to 0.99 is longer than 0.5 to 0.6",
   shareOf("top_p", 0.99) - shareOf("top_p", 0.95) > shareOf("top_p", 0.6) - shareOf("top_p", 0.5),
   true);
is("heat is on steps of 0.05 and nothing between",
   grid.map(s => along("temperature", s))
     .every(t => Math.abs(t * 20 - Math.round(t * 20)) < 1e-9 && String(t).length <= 4), true);

place("min_p", 0);
is("an optional sampler at its idle end is left out, not sent at zero",
   ["min_p" in draw(), said("min_p"), share("min_p")], [false, "off", 0]);
to("min_p", 0.02);
is("  and back on it is sent", draw().min_p, 0.02);

place("record_mass", 1);
is("a required bound at its idle end is sent at what does nothing",
   [draw().record_mass, said("record_mass"), share("record_mass")], [1, "all", 1]);
to("record_mass", 0.9);

// ---- the pair

to("record_rows", 10);
to("top_k", 10);
is("naming top_k at the rows already kept moves neither", [draw().top_k, draw().record_rows], [10, 10]);

to("top_k", 40);
is("a wider draw carries the record with it", [draw().top_k, draw().record_rows], [40, 40]);

to("record_rows", 12);
is("keeping fewer rows narrows the draw to what they cover", [draw().top_k, draw().record_rows], [12, 12]);

to("top_k", 3);
is("a narrower draw leaves the record where it is", [draw().top_k, draw().record_rows], [3, 12]);

place("top_k", 1);
is("a sampler left out is absent and not zero", "top_k" in draw(), false);
to("record_rows", 2);
is("  and an unnamed top_k constrains nothing", draw().record_rows, 2);

place("top_k", 0.5);
is("naming it again lands inside what is kept", covered(), true);

// Every reachable pair, driven from both sides.
const ks = [...new Set(grid.map(s => along("top_k", s)).filter(v => v !== null))];
const rs = [...new Set(grid.map(s => along("record_rows", s)))];
for (const k of ks) {
  for (const r of [rs[0], rs[Math.floor(rs.length / 2)], rs.at(-1)]) {
    to("top_k", k); to("record_rows", r);
    if (!covered()) { bad++; console.log(`FAIL uncovered after top_k ${k} then rows ${r}`, draw()); }
    to("record_rows", r); to("top_k", k);
    if (!covered()) { bad++; console.log(`FAIL uncovered after rows ${r} then top_k ${k}`, draw()); }
  }
}

set("length", 128);
is("what the edge sets is what is drawn", draw().length, 128);
set("length", 4);
is("  within its range", draw().length, 8);
set("temperature", 1.2);
is("temperature is real and not rounded", draw().temperature, 1.2);

console.log(bad ? `\n${bad} failed` : "\nall covered, nothing failed");
process.exit(bad ? 1 : 0);
