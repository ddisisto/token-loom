/* Drive the draw panel against a stub DOM.  `node scripts/check-draw.mjs`
 *
 * What it is here for is the pair `record_rows` and `top_k`, which must not be able to
 * disagree. Nothing on the page objects if they do: the gesture that generates is a scroll,
 * so an invalid pair is not caught on the way out, and the adapter's refusal is *recorded* --
 * which means the browser reports this bug by writing an act into the store. It found one
 * the first time it ran, in the direction a toggle moves.
 *
 * The stub is `stub-dom.mjs`, which the overlay's check drives too. It is not a test harness
 * for the page, and the reading column is not driven from here.
 */

import { El } from "./stub-dom.mjs";

const { draw, keep, panel, set, share, along } = await import(
  new URL("../src/tokenloom/surface/page/assets/draw.js", import.meta.url));

const frag = panel();
const body = frag.children[1];
const rows = new Map();
for (const row of body.children) {
  if (!row.className.startsWith("row")) continue;
  const [top, control] = row.children;
  const name = top.children[0];
  const key = name.children.find(c => typeof c === "string");
  rows.set(key, {
    toggle: name.children.find(c => c instanceof El && c.type === "checkbox"),
    control,
  });
}

let bad = 0;
const is = (what, got, want) => {
  const ok = JSON.stringify(got) === JSON.stringify(want);
  if (!ok) bad++;
  console.log(`${ok ? "ok  " : "FAIL"} ${what}: ${JSON.stringify(got)}` +
              (ok ? "" : ` != ${JSON.stringify(want)}`));
};

const check = (key, on) => { const t = rows.get(key).toggle; t.checked = on; t.onchange(); };
const move = (key, value) => { const c = rows.get(key).control; c.value = String(value); c.oninput(); };
const covered = () => !("top_k" in draw()) || draw().record_rows >= draw().top_k;

is("the defaults are the required five and the floor heat needs", draw(),
   { length: 64, temperature: 0, min_p: 0.02,
     record_rows: 10, record_mass: 0.9, cache_prompt: true });
is("  and a draw keeps none of the chain", "min_p" in keep(), false);

check("top_k", true);
is("naming top_k at the rows already kept moves neither", [draw().top_k, draw().record_rows], [10, 10]);

move("top_k", 40);
is("a wider draw carries the record with it", [draw().top_k, draw().record_rows], [40, 40]);
is("  and the rows control shows what it was moved to", rows.get("record_rows").control.value, "40");

move("record_rows", 12);
is("keeping fewer rows narrows the draw to what they cover", [draw().top_k, draw().record_rows], [12, 12]);

move("top_k", 3);
is("a narrower draw leaves the record where it is", [draw().top_k, draw().record_rows], [3, 12]);

check("top_k", false);
is("a sampler left out is absent and not zero", "top_k" in draw(), false);
move("record_rows", 2);
is("  and an unnamed top_k constrains nothing", draw().record_rows, 2);

check("top_k", true);
is("naming it again lands inside what is kept", [draw().top_k, draw().record_rows], [2, 2]);

check("cache_prompt", false);
is("a required flag is sent false rather than dropped", draw().cache_prompt, false);

is("no reader asks for a seed, so no control offers one", rows.has("seed"), false);
is("the length is set at the edge and not in the panel", rows.has("length"), false);
set("length", 128);
is("  and what the edge sets is what is drawn", draw().length, 128);
set("length", 4);
is("  within its range", draw().length, 8);

is("heat is set in the footer and not in the panel", rows.has("temperature"), false);
is("  from greedy at one end to 2.5 at the other",
   [along("temperature", 0), along("temperature", 1)], [0, 2.5]);
const heats = [...Array(1001).keys()].map(i => along("temperature", i / 1000));
is("  on steps of 0.05 and nothing between",
   heats.every(t => Math.abs(t * 20 - Math.round(t * 20)) < 1e-9 && String(t).length <= 4), true);
is("  never cooler further along",
   heats.every((t, i) => i === 0 || t >= heats[i - 1]), true);
is("  and past either end is that end",
   [along("temperature", -1), along("temperature", 2)], [0, 2.5]);
set("temperature", 1.2);
is("temperature is real and not rounded", draw().temperature, 1.2);
is("  and stands where along the track says it does",
   along("temperature", share("temperature")), 1.2);

// Every reachable pair, driven from both sides.
for (const k of [1, 5, 10, 25, 50]) {
  for (const r of [2, 10, 50]) {
    move("top_k", k); move("record_rows", r);
    if (!covered()) { bad++; console.log(`FAIL uncovered after top_k ${k} then rows ${r}`, draw()); }
    move("record_rows", r); move("top_k", k);
    if (!covered()) { bad++; console.log(`FAIL uncovered after rows ${r} then top_k ${k}`, draw()); }
  }
}
console.log(bad ? `\n${bad} failed` : "\nall covered, nothing failed");
process.exit(bad ? 1 : 0);
